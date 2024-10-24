import functools
import json
import re
from dataclasses import dataclass
from dataclasses import field
from random import Random
from pathlib import Path
from enum import StrEnum

from circuzz.ir.config import GeneratorKind
from circuzz.ir.nodes import Circuit

from circuzz.common.probability import bernoulli

from circuzz.common.metamorphism import MetamorphicCircuitBundle
from circuzz.common.metamorphism import MetamorphicKind

from circuzz.common.command import ExecStatus

from circuzz.common.helper import assert_circuit_compatibility
from circuzz.common.helper import remove_ansi_escape_sequences

from circuzz.common.filesystem import clean_or_create_dir

from circuzz.common.colorlogs import get_color_logger

from experiment.config import Config, OnlineTuning

from .nodes import Statement
from .nodes import Module

from .command import corset_check
from .command import corset_compile
from .command import corset_prove

from .ir2corset import IR2CorsetVisitor
from .emitter import EmitVisitor

logger = get_color_logger()

# TODO: find out what triggers this (low priority)
PANIC_NOT_YET_IMPLEMENTED_STDERR = "not yet implemented"
PANIC_NOT_YET_IMPLEMENTED_RETURNCODE = 101
PANIC_NOT_IMPLEMENTED_STDERR = "not implemented"
PANIC_NOT_IMPLEMENTED_RETURNCODE = 101

# default error for violated constraints
CONSTRAINT_VIOLATION_ERROR_STDERR = "constraints failed:"
CONSTRAINT_VIOLATION_ERROR_RETURNCODE = 1

# out of memory error during rust-corset check
# NOTE: If this occurs, it is most likely introduced
#       by memory limitations
OUT_OF_MEMORY_RUST_STDERR = "memory allocation of"
OUT_OF_MEMORY_RUST_RETURNCODE = -6

# out of memory error during corset go prover client
# NOTE: If this occurs, it is most likely introduced
#       by memory limitations
OUT_OF_MEMORY_GO_STDERR = "out of memory"
OUT_OF_MEMORY_GO_RETURNCODE = 2
CANNOT_ALLOCATE_MEMORY_GO_STDERR = "runtime: cannot allocate memory"
CANNOT_ALLOCATE_MEMORY_GO_RETURNCODE = 2

# This can have many reasons, ranging from out of memory or
# creating too many threads. In general, this should be
# caught and ignored.
RESOURCE_TEMPORARILY_UNAVAILABLE_RETURNCODE = 2
RESOURCE_TEMPORARILY_UNAVAILABLE_STDERR = "Resource temporarily unavailable"

# TODO: find out what triggers this (low priority)
# go-corset compilation limit, this is triggered in the prove & verification client
PANIC_CONTEXT_HAS_NO_MODULE_RETURNCODE = 2
PANIC_CONTEXT_HAS_NO_MODULE_STDERR = "panic: void context has no module"

# This is used to find out if the verifier failed during the constraint check.
# It does NOT mean there is an actual error. This is present together with "FAILED".
GLOBAL_CONSTRAINT_CHECK_FAILED_STDOUT = "global constraint check failed"
GLOBAL_CONSTRAINT_CHECK_FAILED_STDERR = "started to run the dummy verifier"
GLOBAL_CONSTRAINT_CHECK_FAILED_RETURNCODE = 1

class CorsetError(StrEnum):
    UNKNOWN_EXECUTION_ERROR = "unknown execution error"
    UNKNOWN_COMPILATION_ERROR = "unknown compilation error"
    UNKNOWN_PROOF_VERIFICATION_ERROR = "unknown proof & verification error"
    METAMORPHIC_VIOLATION_TRANSFORMATIONS = "metamorphic violation (transformations)"
    METAMORPHIC_VIOLATION_FLAGS_CONSTRAINTS = "metamorphic violation (flags with different constraints)"
    METAMORPHIC_VIOLATION_FLAGS_ERRORS = "metamorphic violation (flags with different error states)"
    ORACLE_VIOLATION_CHECKER_VERIFIER = "oracle violation for constraint checker and verifier"

@dataclass
class TestIteration():
    # check result
    rust_corset_check      : bool | None = None
    rust_corset_check_time : float | None = None

    # compile result
    rust_corset_compile      : bool | None = None
    rust_corset_compile_time : float | None = None

    # go corset result
    go_corset_compile      : bool | None = None
    go_corset_compile_time : float | None = None

    # wizard witness generation
    wizard_compile      : bool | None = None
    wizard_compile_time : float | None = None

    # wizard proof generation
    wizard_prove      : bool | None = None
    wizard_prove_time : float | None = None

    # wizard verification
    wizard_verify      : bool | None = None
    wizard_verify_time : float | None = None

    # custom go client for go-corset and wizard
    # proof - verification setup.
    go_custom_cli      : bool | None = None
    go_custom_cli_time : float | None = None

    # executed without any errors
    ignored_error : str | None = None

    # flags
    expansions : int = -1
    native : bool = False
    auto_constraints : list[str] = field(default_factory=list)

    guard_variable : bool = False

    # timeouts and ignores
    timeout : bool = False
    out_of_memory : bool = False

    # constraints that violates the single or cross execution
    constraints: list[str] | None = None

    # reference to other iteration for cross execution violations
    error_references : list[int] = field(default_factory=list)

    # kind of error
    error: str | None = None

    def is_error(self) -> bool:
        return self.error != None

@dataclass
class CorsetResult():
    iterations : list[TestIteration] = field(default_factory=list)

# ================================================================
#                       IR to Corset
# ================================================================


def generate_module_body(bundle: MetamorphicCircuitBundle, use_guard_variable: bool) -> list[Statement]:
    """
    Creates a list of constraint statements for the given circuit bundle, where
    circuit is a single constraint. The beginning of the list contains a single
    column definition for the shared inputs (and the hardcoded guard variable
    if specified).
    """
    statements = []
    transformer = IR2CorsetVisitor(use_guard_variable=use_guard_variable)
    statements.append(transformer.columns(bundle.origin))
    circuits = [bundle.origin] + bundle.bundle
    for circuit in circuits:
        statements.append(transformer.constraint(circuit))
    return statements

def generate_modules(bundle: MetamorphicCircuitBundle, use_guard_variable: bool) -> list[Module]:
    """
    Creates a list of modules using the provided bundles. If `use_guard_variable`
    is NOT set, exhaustively testing the input makes no sense and the list only
    contains a single module. If `use_guard_variable` is set, this function returns
    `INPUT_SIGNALS ** 2` to enable exhaustively testing all input values (given the
    domain [0, 1]). Therefore, if multiple modules are returned they contain the same
    circuit constraint body.

    TODO: rework to also work with arithmetic generators as exhaustive testing makes
          no sense due to state explosion.
    """

    # constraints are all modules.
    constraint_definitions = generate_module_body(bundle, use_guard_variable)

    input_signal_size = len(bundle.origin.inputs)
    module_size = 1

    if use_guard_variable:
        # generate a module per signal assignment combination
        module_size = 2 ** input_signal_size

    module_names = [f"module-{i}" for i in range(module_size)]
    modules = []
    for module_name in module_names:
        modules.append(Module(module_name, constraint_definitions))
    return modules


# ================================================================
#                        Project Setup
# ================================================================


def generate_circuits_txt(circuits: list[Circuit]) -> str:
    """
    Generates the content of a `circuit.txt` file for debugging purposes.
    """
    return "\n\n".join([str(circuit) for circuit in circuits])

def generate_test_lisp(modules: list[Module]) -> str:
    """
    Generates the content of a `test.lisp` file for `corset`.
    """
    emitter = EmitVisitor()
    listp_content = ""
    for module in modules:
        listp_content += emitter.emit(module)
        listp_content += "\n"
    return listp_content

def generate_trace_maps \
    ( modules: list[Module]
    , input_signals: list[str]
    , is_exhaustive: bool
    ) -> tuple[dict[str, dict[str, list[int]]], dict[str, list[int]]]:

    """
    Generates two dictionaries containing information for `trace.json`
    file for `corset` and `trace-go.json` for `go-corset`.
    If `is_exhaustive` is set, the final product should contain
    all combinations of input values (assuming the domain
    is [0, 1]) bundled together in `2**len(input_signals)` modules.

    Otherwise, the input contains a `1` as `0` is tested anyways by
    corsets zero padding.

    TODO: rework for arithmetic generator
    """

    trace_map : dict[str, dict[str, list[int]]] = {}

    if is_exhaustive:
        # sanity check if we have enough modules
        assert 2**len(input_signals) == len(modules), \
            "too few modules, unable to generate exhaustive input over [0, 1]"

        # enumeration over modules already provides an assignment in form of a bitmap
        for assignment, module in enumerate(modules):
            module_name = module.name
            trace_map[module_name] = {} # generate dic for each module
            for bit, x in enumerate(input_signals):
                # relate input signal position to a specific bit in assignment bitmap
                trace_map[module_name][x] = [((assignment >> bit) & 1)] # probe bit and use result
            # corset has a zero padded column for all input rows. To deal with this
            # we use a little hack where we introduce a hardcoded non-zero valued
            # guard variable (see IR2CorsetVisitor), which we need to set for each module.
            trace_map[module_name][IR2CorsetVisitor.GUARD_VARIABLE] = [1]
    else:
        # sanity check if we only have a single module
        assert len(modules) == 1, "too many modules for non exhaustive testing"
        module = modules[0] # extract the single module
        module_name = module.name
        trace_map[module_name] = {}
        for sig in input_signals:
            trace_map[module_name][sig] = [1]

    # flatten the map to { "module-name.column" : value-list, ... }
    flat_trace_map : dict[str, list[int]] = {}
    for module in trace_map:
        for column in trace_map[module]:
            values = trace_map[module][column][::] # copy values
            flat_key = f"{module}.{column}"
            flat_trace_map[flat_key] = values

    return trace_map, flat_trace_map


def setup \
    ( working_dir: Path
    , modules: list[Module]
    , bundle: MetamorphicCircuitBundle
    , is_exhaustive: bool
    ):
    """
    Deterministic setup of a corset project in the given directory.
    The project has following structure:
    ~~~
        DIR/
         |- test.lisp
         |- trace.json
         |- trace-go.json
         |- circuits.txt
    ~~~
    Where `test.lisp` contains the bundled constraints, `trace.json` and `trace-go.json`
    contain assignments for the constraints in a hierarchial and flat manner respectively.
    Finally, `circuits.txt` contains the circuzz-IR of the circuit.
    """

    clean_or_create_dir(working_dir)

    input_signals = bundle.origin.inputs
    circuits = [bundle.origin] + bundle.bundle

    test_lisp = working_dir / "test.lisp"
    test_lisp_content = generate_test_lisp(modules)
    with open(test_lisp, "w") as file_handler:
        file_handler.write(test_lisp_content)

    trace_map, flat_trace_map = generate_trace_maps(modules, input_signals, is_exhaustive)
    trace_json = working_dir / "trace.json"
    with open(trace_json, "w") as file_handler:
        file_handler.write(json.dumps(trace_map, indent=4))
    trace_go_json = working_dir / "trace-go.json"
    with open(trace_go_json, "w") as file_handler:
        file_handler.write(json.dumps(flat_trace_map, indent=4))

    circuits_txt = working_dir / "circuits.txt"
    circuits_txt_content = generate_circuits_txt(circuits)
    with open(circuits_txt, "w") as file_handler:
        file_handler.write(circuits_txt_content)


# ================================================================
#                         Execution
# ================================================================

def rust_corset_check \
    ( working_dir: Path
    , flags: tuple[int, bool, list[str]]
    , timeout: float | None
    , memory_limit: int | None
    ) -> ExecStatus:

    """
    Executes a corset check with particular flags, timeout and memory limits.
    The past working directory is expected to look like the following:
    ~~~
        DIR/
         |- test.lisp
         |- trace.json
         |- ...
    ~~~
    This function returns the execution status of the `corset check` command.
    """

    relative_test_lisp = Path("test.lisp")
    absolute_test_lisp = working_dir / "test.lisp"
    if not absolute_test_lisp.is_file():
        raise ValueError(f"Unable to find 'test.lisp' inside '{working_dir}'!")

    relative_trace_json = Path("trace.json")
    absolute_trace_json = working_dir / "trace.json"
    if not absolute_trace_json.is_file():
        raise ValueError(f"Unable to find 'trace.json' inside '{working_dir}'!")

    expansion, native, auto_constraints = flags
    status = corset_check(relative_test_lisp, relative_trace_json, expansion, \
        native, auto_constraints, working_dir, timeout, memory_limit)

    return status

# ================================================================
#                         Compile
# ================================================================

def rust_corset_compile \
    ( working_dir: Path
    , flags: tuple[int, bool, list[str]]
    , timeout: float | None
    , memory_limit: int | None
    ) -> ExecStatus:

    """
    Executes a corset compile with particular flags, timeout and memory limits.
    The past working directory is expected to look like the following:
    ~~~
        DIR/
         |- test.lisp
         |- ...
    ~~~
    This function returns the execution status of the `corset compile` command.
    It also generates a test.bin file inside of the target directory
    """

    relative_test_lisp = Path("test.lisp")
    absolute_test_lisp = working_dir / "test.lisp"
    if not absolute_test_lisp.is_file():
        raise ValueError(f"Unable to find 'test.lisp' inside '{working_dir}'!")

    relative_test_bin = Path("test.bin")

    expansion, native, auto_constraints = flags
    status = corset_compile(relative_test_lisp, relative_test_bin, expansion, \
        native, auto_constraints, working_dir, timeout, memory_limit)

    return status

# ================================================================
#            Proof and Verification Helper Exec
# ================================================================

def custom_cli \
    ( working_dir: Path
    , timeout: float | None
    , memory_limit: int | None
    ) -> ExecStatus:

    """
    Executes a corset wizard prove and verification process using go-corset.
    The past working directory is expected to look like the following:
    ~~~
        DIR/
         |- test.bin
         |- trace-go.json
         |- ...
    ~~~
    This function returns the execution status of the custom `corset-prover` executable.
    """

    relative_go_trace = Path("trace-go.json")
    absolute_go_trace = working_dir / "trace-go.json"
    if not absolute_go_trace.is_file():
        raise ValueError(f"Unable to find 'trace-go.json' inside '{working_dir}'!")

    relative_test_bin = Path("test.bin")
    absolute_test_bin = working_dir / "test.bin"
    if not absolute_test_bin.is_file():
        raise ValueError(f"Unable to find 'test.bin' inside '{working_dir}'!")

    status = corset_prove(relative_test_bin, relative_go_trace, \
        working_dir, timeout, memory_limit)
    return status

# =======================================================
#                     Analyze
# =======================================================


def has_no_errors(exec_status: ExecStatus) -> bool:
    # NOTE: IMPORTANT: corset finishes also with 0 if there was an error!
    #       Therefore, if we want to make sure nothing happened, we have to
    #       check for an empty stdout and stderr!
    return exec_status.returncode == 0 and \
           exec_status.stdout == "" and \
           exec_status.stderr == ""

def has_constraint_violation(exec_status: ExecStatus) -> bool:
    return CONSTRAINT_VIOLATION_ERROR_STDERR in exec_status.stderr and \
           CONSTRAINT_VIOLATION_ERROR_RETURNCODE == exec_status.returncode

def has_not_implemented_panic(exec_status: ExecStatus) -> bool:
    return (PANIC_NOT_YET_IMPLEMENTED_RETURNCODE == exec_status.returncode and \
            PANIC_NOT_YET_IMPLEMENTED_STDERR in exec_status.stderr) or \
           (PANIC_NOT_IMPLEMENTED_RETURNCODE == exec_status.returncode and \
            PANIC_NOT_IMPLEMENTED_STDERR in exec_status.stderr)

def has_out_of_memory_rust_panic(exec_status: ExecStatus) -> bool:
    return OUT_OF_MEMORY_RUST_RETURNCODE == exec_status.returncode and \
           OUT_OF_MEMORY_RUST_STDERR in exec_status.stderr

def has_out_of_memory_go_panic(exec_status: ExecStatus) -> bool:
    return OUT_OF_MEMORY_GO_RETURNCODE == exec_status.returncode and \
           OUT_OF_MEMORY_GO_STDERR in exec_status.stderr

def has_cannot_allocate_memory_go_panic(exec_status: ExecStatus) -> bool:
    return CANNOT_ALLOCATE_MEMORY_GO_RETURNCODE == exec_status.returncode and \
           CANNOT_ALLOCATE_MEMORY_GO_STDERR in exec_status.stderr

def has_resource_temporarily_unavailable_go_panic(exec_status: ExecStatus) -> bool:
    return RESOURCE_TEMPORARILY_UNAVAILABLE_RETURNCODE == exec_status.returncode and \
           RESOURCE_TEMPORARILY_UNAVAILABLE_STDERR in exec_status.stderr

def has_panic_context_has_no_module(exec_status: ExecStatus) -> bool:
    return PANIC_CONTEXT_HAS_NO_MODULE_RETURNCODE == exec_status.returncode and \
           PANIC_CONTEXT_HAS_NO_MODULE_STDERR in exec_status.stderr

def has_global_constraint_check_failed(exec_status: ExecStatus) -> bool:
    return GLOBAL_CONSTRAINT_CHECK_FAILED_RETURNCODE == exec_status.returncode and \
           GLOBAL_CONSTRAINT_CHECK_FAILED_STDERR in exec_status.stderr and \
           GLOBAL_CONSTRAINT_CHECK_FAILED_STDOUT in exec_status.stdout

def is_timeout(exec_status: ExecStatus) -> bool:
    return exec_status.is_timeout

def has_ignored_error_for_corset_check(exec_status: ExecStatus) -> bool:
    # ignore / skip unimplemented panics and known bigint panic
    # issue for outer loop element
    #
    # TODO: think about removing timeout and memory consumption from this list
    return has_not_implemented_panic(exec_status) or \
           has_out_of_memory_rust_panic(exec_status) or \
           is_timeout(exec_status)

def get_difference \
    ( cons1: dict[str, set[str]]
    , cons2: dict[str, set[str]]
    ) -> list[str]:
    result = set()
    for key in cons1:
        cons_set1 = cons1[key]
        diff_set = cons_set1
        if key in cons2:
            cons_set2 = cons2[key]
            diff_set = cons_set1.symmetric_difference(cons_set2)
        result.update(diff_set)
    return list(result)

def parse_failed_constraints_from_stderr(stderr: str) -> dict[str, set[str]]:
    """
    Takes a `corset check` STDERR string and returns a map of
    module to constraint list that failed.

    EXAMPLE:

    ```
    constraints failed: module-0.constraint, module-1.constraint, ...
    ```

    results in `{"module-0" : ["constraint"], "module-1" : ["constraint"]}`
    """
    # remove ansi bold and color escape sequences if present
    escaped_stderr = remove_ansi_escape_sequences(stderr)
    # DOTALL is needed to match newlines
    pattern = re.compile(r'.*constraints failed: ((?:[\w|-]+\.[\w|-]+(?:\,\ )?)+).*', flags=re.DOTALL)
    match = pattern.match(escaped_stderr)

    result = {}
    if match:
        constraint_line, *_ = match.groups()
        for module_constraint in constraint_line.split(", "):
            module, constraint = module_constraint.split(".")
            if not module in result:
                result[module] = set()
            result[module].add(constraint)

    return result

def analyze_single_rust_corset_checks \
    ( bundle : MetamorphicCircuitBundle
    , exec_status: ExecStatus
    , test_iteration: TestIteration
    ) -> TestIteration:

    """
    Analyzes the result of a normal `corset check` execution of a single corset file
    with multiple metamorphic related constraints.

    NOTE: currently only the same amount is check, nevertheless we expect the names of the
          circuits to match the names of the constraints in the error message!
    """

    logger.info(f"analyze single execution ('{exec_status.command}')")

    test_iteration.rust_corset_check = exec_status.returncode == 0
    test_iteration.rust_corset_check_time = exec_status.delta_time

    # early abort for successful instances
    if has_no_errors(exec_status):
        return test_iteration # -> ok

    # check for different errors
    if has_constraint_violation(exec_status):
        origin = bundle.origin.name
        bundle_names = [c.name for c in bundle.bundle]
        failed_constraints = parse_failed_constraints_from_stderr(exec_status.stderr)
        for _, constraints in failed_constraints.items():
            for other, kind in zip(bundle_names, bundle.kinds):
                violated_constraints = []
                if (origin in constraints) != (other in constraints):
                    if (other in constraints) or kind != MetamorphicKind.WEAKER:
                        # violates weaker and equality
                        logger.error(f"violation of metamorphic transformations")
                        logger.debug(exec_status)
                        violated_constraints.append(other)
                if len(violated_constraints) > 0:
                    test_iteration.error = CorsetError.METAMORPHIC_VIOLATION_TRANSFORMATIONS
                    test_iteration.constraints = violated_constraints
                    return test_iteration

    elif has_not_implemented_panic(exec_status):
        test_iteration.ignored_error = "not implemented panic"

    elif has_out_of_memory_rust_panic(exec_status):
        # TODO: report this and find out why it uses so much memory
        logger.warning(f"instance reached memory limit for corset check")
        test_iteration.ignored_error = "out of memory"
        test_iteration.out_of_memory = True

    elif is_timeout(exec_status):
        # TODO: report this and find out why it takes so much time
        logger.warning(f"instance triggered timeout for corset check")
        test_iteration.ignored_error = "timeout"
        test_iteration.timeout = True

    else:
        logger.error(f"unknown execution error")
        logger.debug(exec_status)
        test_iteration.error = CorsetError.UNKNOWN_EXECUTION_ERROR

    return test_iteration # -> ok / no violations

def analyze_cross_corset_checks \
    ( bundle : MetamorphicCircuitBundle
    , exec_status_list : list[ExecStatus]
    , corset_result : CorsetResult
    ):

    """
    Analyzes the result of a list of `corset check` execution of a single corset file
    with multiple metamorphic related constraints.
    """

    logger.info(f"analyze all executions")

    # TODO: think about also comparing the different errors that might occur
    #       and not only the constraints. e.g. panic vs no panic
    executions = len(exec_status_list)
    for idx1 in range(executions):
        status1 = exec_status_list[idx1]

        if has_ignored_error_for_corset_check(status1):
            continue # ignore this execution and skip to next
        status1_constraints = parse_failed_constraints_from_stderr(status1.stderr)

        for idx2 in range(idx1+1, executions): # break symmetry and avoid equals
            status2 = exec_status_list[idx2]

            if has_ignored_error_for_corset_check(status2):
                continue # ignore this execution and skip to next
            status2_constraints = parse_failed_constraints_from_stderr(status2.stderr)

            if status1_constraints != status2_constraints:
                logger.error(f"violation of metamorphic flag testing (different constraints)")
                logger.debug(status1)
                logger.debug(status2)

                difference = get_difference(status1_constraints, status2_constraints)
                if bundle.origin.name in difference:
                    difference = None # if the original generated circuit fails, all instances fail

                corset_result.iterations[idx1].error = CorsetError.METAMORPHIC_VIOLATION_FLAGS_CONSTRAINTS
                corset_result.iterations[idx1].constraints = difference
                corset_result.iterations[idx1].error_references.append(idx2)
                corset_result.iterations[idx2].error = CorsetError.METAMORPHIC_VIOLATION_FLAGS_CONSTRAINTS
                corset_result.iterations[idx2].constraints = difference
                corset_result.iterations[idx2].error_references.append(idx1)

                return # err => abort

            if has_no_errors(status1) != has_no_errors(status2):
                logger.error(f"violation of metamorphic flag testing (error vs no error)")
                logger.debug(status1)
                logger.debug(status2)
                corset_result.iterations[idx1].error = CorsetError.METAMORPHIC_VIOLATION_FLAGS_ERRORS
                corset_result.iterations[idx1].error_references.append(idx2)
                corset_result.iterations[idx2].error = CorsetError.METAMORPHIC_VIOLATION_FLAGS_ERRORS
                corset_result.iterations[idx2].error_references.append(idx1)
                return # err => abort

    return # ok

def analyze_rust_corset_compile(test_iteration: TestIteration, compile_status: ExecStatus):

    test_iteration.rust_corset_compile = compile_status.returncode == 0
    test_iteration.rust_corset_compile_time = compile_status.delta_time

    if compile_status.returncode != 0:
        if has_out_of_memory_rust_panic(compile_status):
            # TODO: report this and find out why it uses so much memory
            logger.warning(f"instance reached memory limit for corset compile")
            test_iteration.ignored_error = "out of memory"
            test_iteration.out_of_memory = True
        elif is_timeout(compile_status):
            # TODO: report this and find out why it takes so much time
            logger.warning(f"instance triggered timeout for corset compile")
            test_iteration.ignored_error = "timeout"
            test_iteration.timeout = True
        else:
            logger.error(f"unknown compilation error")
            logger.debug(compile_status)
            test_iteration.error = CorsetError.UNKNOWN_COMPILATION_ERROR

def analyze_custom_cli \
    ( test_iteration: TestIteration
    , custom_client_status: ExecStatus
    , check_status_list: list[ExecStatus]
    , online_tuning: OnlineTuning
    ):

    #
    # Set general test iteration info for client
    #

    test_iteration.go_custom_cli = custom_client_status.returncode == 0
    test_iteration.go_custom_cli_time = custom_client_status.delta_time

    #
    # parse the output of custom client
    #

    stdout_lines = custom_client_status.stdout.split("\n")
    for stdout_line in stdout_lines:
        if stdout_line.startswith("<@> go-corset compile => "):
            test_iteration.go_corset_compile = "ok" in stdout_line

        elif stdout_line.startswith("<@> go-corset compile time => "):
            test_iteration.go_corset_compile_time = \
                float(stdout_line.removeprefix("<@> go-corset compile time => "))
            online_tuning.add_general_execution_time(test_iteration.go_corset_compile_time)

        elif stdout_line.startswith("<@> wizard compile => "):
            test_iteration.wizard_compile = "ok" in stdout_line

        elif stdout_line.startswith("<@> wizard compile time => "):
            test_iteration.wizard_compile_time = \
                float(stdout_line.removeprefix("<@> wizard compile time => "))
            online_tuning.add_prove_or_verify_time(test_iteration.wizard_compile_time)

        elif stdout_line.startswith("<@> wizard prove => "):
            test_iteration.wizard_prove = "ok" in stdout_line

        elif stdout_line.startswith("<@> wizard prove time => "):
            test_iteration.wizard_prove_time = \
                float(stdout_line.removeprefix("<@> wizard prove time => "))
            online_tuning.add_prove_or_verify_time(test_iteration.wizard_prove_time)

        elif stdout_line.startswith("<@> wizard verify => "):
            test_iteration.wizard_verify = "ok" in stdout_line

        elif stdout_line.startswith("<@> wizard verify time => "):
            test_iteration.wizard_verify_time = \
                float(stdout_line.removeprefix("<@> wizard verify time => "))
            online_tuning.add_prove_or_verify_time(test_iteration.wizard_verify_time)

    #
    # prepare the status results of previous check runs
    #

    successful_corset_checks = all([e.returncode == 0 for e in \
        check_status_list if not has_ignored_error_for_corset_check(e)])

    #
    # analyze the client result
    #

    if custom_client_status.returncode != 0:

        # check for know issues, otherwise treat it as error

        if has_panic_context_has_no_module(custom_client_status):
            logger.warning(f"ignore '{PANIC_CONTEXT_HAS_NO_MODULE_STDERR}' in custom corset-prove client")
            test_iteration.ignored_error = PANIC_CONTEXT_HAS_NO_MODULE_STDERR

        elif has_global_constraint_check_failed(custom_client_status):
            # trace does not satisfy the constraint system. This has to be
            # checked with the results of the corset check runs.
            if successful_corset_checks:
                logger.error(f"constraint check succeeded while verifier failed")
                for check_status in check_status_list:
                    logger.debug(check_status)
                logger.debug(custom_client_status)
                test_iteration.error = CorsetError.ORACLE_VIOLATION_CHECKER_VERIFIER

        elif has_out_of_memory_go_panic(custom_client_status) or \
             has_cannot_allocate_memory_go_panic(custom_client_status):
            # TODO: report this and find out why it uses so much memory
            logger.warning(f"instance reached memory limit for corset prover")
            test_iteration.ignored_error = "out of memory"
            test_iteration.out_of_memory = True

        elif has_resource_temporarily_unavailable_go_panic(custom_client_status):
            logger.warning(f"instance triggered resource temporarily unavailable")
            test_iteration.ignored_error = "resource temporarily unavailable"

        elif is_timeout(custom_client_status):
            # TODO: report this and find out why it takes so much time
            logger.warning(f"instance triggered timeout for corset prover")
            test_iteration.ignored_error = "timeout"
            test_iteration.timeout = True

        else: # unknown error
            logger.error(f"unknown prove & verify error")
            logger.debug(custom_client_status)
            test_iteration.error = CorsetError.UNKNOWN_PROOF_VERIFICATION_ERROR

    else: # custom_client_status.returncode == 0

        # trace does satisfy the constraint system. This has to be
        # checked with the results of the corset check runs.
        if not successful_corset_checks:
            logger.error(f"corset constraint check failed while verifier succeeded")
            for check_status in check_status_list:
                logger.debug(check_status)
            logger.debug(custom_client_status)
            test_iteration.error = CorsetError.ORACLE_VIOLATION_CHECKER_VERIFIER

# ================================================================
#                          Testing
# ================================================================


@functools.cache
def cached_corset_flags() -> list[tuple[int, bool, list[str]]]:
    flags = []
    for e in [0, 1, 2, 3, 4]:
        for n in [True, False]:
            for c in [[], ["nhood"], ["sorts"], ["nhood", "sorts"]]:
                flags.append((e, n, c))
    return flags

def get_random_corset_flags(rng: Random, amount: int) -> list[tuple[int, bool, list[str]]]:
    """
    Returns a list of rust corset flags. The list always contains the default flag settings
    (no flags) and the recommended flag setting if the amount is >= 2. The rest of the
    requested amount is filled with arbitrary flags.
    """

    flags = []
    cached_flags = cached_corset_flags()[::] # create a copy to not temper with cache

    default_flags = (0, False, [])
    recommended_flags = (4, True, ["nhood", "sorts"])

    # if the passed 'amount' variables permits it, we always use the
    # default and recommended set of flags.

    if amount >= 1:
        cached_flags.remove(default_flags)
        flags.append(default_flags)
        amount -= 1

    if amount >= 1:
        cached_flags.remove(recommended_flags)
        flags.append(recommended_flags)
        amount -= 1

    while len(cached_flags) > 0 and amount > 0:
        selected_flag = rng.choice(cached_flags)
        cached_flags.remove(selected_flag)
        flags.append(selected_flag)
        amount -= 1

    return flags

def run_metamorphic_tests \
    ( bundle: MetamorphicCircuitBundle
    , seed: int
    , working_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> CorsetResult:

    """
    This method assumes that the corset test data is generated with the BOOLEAN IR Generator.
    Based on the input it will test the test cases exhaustively. This means that for
    EVERY possible BOOLEAN assignment (i.e. 2 ^ number_of_inputs) a module is generated and
    every circuit is a constraint inside of this module.
    If a violation is detected, an error message is returned, otherwise `None`.
    """

    # check that only boolean generators are used!
    generatorKind = config.ir.generation.generator
    if generatorKind != GeneratorKind.BOOLEAN:
        raise NotImplementedError(f"corset is unable to deal with '{generatorKind}' generator!")

    # sanity checks
    assert_circuit_compatibility([bundle.origin] + bundle.bundle)

    # start a new experiment
    rng = Random(seed)

    # check if we use a guard variable
    use_guard_variable = bernoulli(0.1, rng)

    # generate modules for circuit bundles
    modules = generate_modules(bundle, use_guard_variable)
    assert len(modules) > 0, "unexpected empty module list"

    # create a project
    setup(working_dir, modules, bundle, use_guard_variable)

    # get different flags per execution
    executions = config.corset.executions
    flags = get_random_corset_flags(rng, executions)

    # set timeout and memory limits
    timeout = config.corset.general_timeout
    rust_corset_check_timeout = config.corset.rust_corset_check_timeout
    memory_limit = config.corset.general_memory_limit

    corset_result = CorsetResult()

    check_status_list : list[ExecStatus] = []
    test_iteration : TestIteration | None = None

    #
    # Metamorphic transformation comparison
    #

    for flag in flags:

        # setup current test iteration
        expansions, native, auto_constraints = flag
        test_iteration = TestIteration()
        test_iteration.expansions = expansions
        test_iteration.native = native
        test_iteration.auto_constraints = auto_constraints
        test_iteration.guard_variable = use_guard_variable
        corset_result.iterations.append(test_iteration)

        #
        # corset check constraints
        #

        check_status = rust_corset_check(working_dir, flag, rust_corset_check_timeout, memory_limit)
        online_tuning.add_general_execution_time(check_status.delta_time)
        check_status_list.append(check_status)

        analyze_single_rust_corset_checks(bundle, check_status, test_iteration)

        if test_iteration.is_error():
            return corset_result # early abort

        if check_status.returncode != 0:
            logger.info("corset check failed...")


    #
    # Metamorphic flag comparison (cross check executions)
    #

    analyze_cross_corset_checks(bundle, check_status_list, corset_result)
    if any([i.is_error() for i in corset_result.iterations]):
        return corset_result # early abort

    # <-- else: successful constraint checks with no critical errors,
    #           i.e. known / ignored errors are allowed.
    #           Compilation and verification should not have unexpected
    #           errors from here on, i.e. errors not related to the
    #           constraint system or resource limits.

    # if all checks are only failing because of constraints violations we should
    # be able to compile the circuits. We store the information about compilation
    # and proofs inside of the last iteration of the result.
    if test_iteration != None:

        assert not test_iteration.is_error(), "unexpected error in last iteration"

        #
        # corset compilation
        #

        # TODO: If the compilation allows for more flags we should move it to the flags loop
        default_flag =  (0, False, [])
        compile_status = rust_corset_compile(working_dir, default_flag, timeout, memory_limit)
        analyze_rust_corset_compile(test_iteration, compile_status)
        online_tuning.add_general_execution_time(compile_status.delta_time)

        if compile_status.returncode != 0:
            return corset_result

        #
        # Prove & Verification Section
        #

        # check if the bundle is suitable for the prover
        if len(bundle.bundle) == 0 or \
           len(bundle.bundle[0].inputs) == 0 or \
           len(bundle.bundle[0].statements) == 0:
            logger.info("too few circuit parts to start proof & verification"
                + "(missing inputs or constraints) ==> skipped")
            logger.debug(f"main circuit:\n{bundle.bundle[0]}")
            return corset_result # early abort

        # We have the opportunity to execute the corset prove and
        # verify process, so we count a tick here.
        online_tuning.inc_prove_and_verify_ticks()

        # check for available resources of the online tuner
        if online_tuning.is_prove_and_verify(rng):

            logger.debug("corset proof & verification was started")

            online_tuning.inc_prove_and_verify_exec()

            #
            # run corset helper client for proof and verification steps
            #

            custom_client_status = custom_cli(working_dir, timeout, memory_limit)
            analyze_custom_cli(test_iteration, custom_client_status,
                check_status_list, online_tuning)

    return corset_result