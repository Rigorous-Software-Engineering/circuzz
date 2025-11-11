from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
import re
from pathlib import Path
from random import Random

from circuzz.common.command import ExecStatus
from circuzz.common.field import CurvePrime
from circuzz.common.helper import assert_circuit_compatibility
from circuzz.common.helper import remove_ansi_escape_sequences
from circuzz.common.field import random_field_element
from circuzz.common.filesystem import clean_or_create_dir
from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.metamorphism import MetamorphicKind
from circuzz.ir.config import GeneratorKind
from circuzz.ir.nodes import Circuit
from circuzz.common.colorlogs import get_color_logger

from experiment.config import Config, OnlineTuning

from .utils import get_system_nargo_verison
from .utils import parse_signals_from_noir_output
from .utils import parse_signal_from_debug_output
from .emitter import EmitVisitor
from .ir2noir import IR2NoirVisitor
from .command import bb_prove
from .command import bb_verify
from .command import bb_write_vk
from .command import noir_execute

logger = get_color_logger()

PROJECT_NAME = "Test"
WITNESS_NAME = "witness"

EXPRESSION_WIDTH_DEFAULT = 4
# TODO: maybe we can still use this for testing?
# NOTE: changing the expression higher than 4 produces errors in bb
#       (see BB_ASSERTION_LINEAR_COMBINATION) which is why we do not
#       use anything else but the default value 4.
# EXPRESSION_WIDTH_MIN = 3
# EXPRESSION_WIDTH_MAX = 10

EXECUTION_ASSERTION_STDERR = "error: Assertion failed:"

# NOTE: this is triggered in version <0.31
EXECUTION_CONSTRAINED_FAILED_STDERR = "Failed to solve program: 'Cannot satisfy constraint'"

# This error is triggered a lot in older versions and prevents a clean re-find of old bugs.
# TODO: investigate why this is triggered
FAILED_TO_SOLVE_PROGRAM_OPCODE_STDERR = "Cannot solve opcode: expression has too many unknowns"
FAILED_TO_SOLVE_PROGRAM_OPCODE_RETURNCODE = 1


class NoirError(StrEnum):
    UNKNOWN_EXECUTION_ERROR = "unknown execution error"
    UNKNOWN_PROOF_ERROR = "unknown proof error"
    UNKNOWN_VK_KEY_ERROR = "unknown vk key generation error"
    UNKNOWN_VERIFICATION_ERROR = "unknown verification error"

    DIVERGING_SIGNALS_IN_DEBUG = "diverging debug signals"
    DIVERGING_SIGNALS_IN_OUTPUT = "diverging output signals"
    MISSING_SIGNALS_IN_OUTPUT = "missing output signals"

    METAMORPHIC_VIOLATION_EXECUTION = "metamorphic violated execution"
    METAMORPHIC_VIOLATION_PROOF = "metamorphic violation proof"
    METAMORPHIC_VIOLATION_VERIFICATION = "metamorphic violation verification"

@dataclass
class TestIteration():
    c1_execute      : bool | None = None
    c1_execute_time : float | None = None
    c2_execute      : bool | None = None
    c2_execute_time : float | None = None

    c1_vk      : bool | None = None
    c1_vk_time : float | None = None
    c2_vk      : bool | None = None
    c2_vk_time : float | None = None

    c1_bb_prove      : bool | None = None
    c1_bb_prove_time : float | None = None
    c2_bb_prove      : bool | None = None
    c2_bb_prove_time : float | None = None

    c1_bb_verify      : bool | None = None
    c1_bb_verify_time : float | None = None
    c2_bb_verify      : bool | None = None
    c2_bb_verify_time : float | None = None

    c1_ignored_error : str | None = None
    c2_ignored_error : str | None = None

    error : str | None = None

    def is_error(self) -> bool:
        return self.error != None

@dataclass
class NoirResult():
    iterations : list[TestIteration] = field(default_factory=list)

# ================================================================
#                           Helper
# ================================================================

def update_prover_toml(project_dir: Path, input_map: dict[str, str]):
    """
    Writes the input signals into a 'Prover.toml' file in the given project path.

    ```
        PROJECT/
            |__ circuit.txt
            |__ Nargo.toml
            |__ Prover.toml
            |__ src/
                 |__ main.noir
    ```
    """
    prover_toml = project_dir / "Prover.toml"
    with open(prover_toml, 'w') as file_handler:
        file_handler.write(
            "\n".join([f"{key}=\"{value}\"" for key, value in input_map.items()]))


def extract_assertion(error_msg: str) -> str | None:
    """
    Parses a noir error message and tries to extract an assertion message.
    If no assertion can be found `None` is returned.
    """
    assertion_failed_pattern = r"error: Assertion failed: (.+)"
    failed_assertions: list[str] = list()
    error_lines = [line for line in error_msg.split("\n") if line.startswith("error: Assertion failed:")]
    for error_line in error_lines:
        match_result = re.search(assertion_failed_pattern, error_line)
        assert match_result != None, "error message changed or regex is wrong!"
        failed_assertions.append(match_result.group(1)) # 0 is the whole thing, 1 should be the name
    # NOTE: Currently noir is limited to only report the first assertion that fails!
    #       Since this might change, we assert this before we return.
    assert len(failed_assertions) <= 1, "sanity check on noir's implementation"
    return None if len(failed_assertions) == 0 else failed_assertions[0]


def random_input \
    ( input_signals: list[str]
    , curve: CurvePrime
    , boundary_probability: float
    , rng: Random
    ) -> dict[str, str]:
    """
    Generates an input map with random inputs given the input signals.
    """
    input_map: dict[str, str] = {}
    for variable in input_signals:
        sig_val = random_field_element(curve, rng, exclude_prime=True,
            boundary_prob=boundary_probability)
        # pack the values into a string to not lose precision!
        input_map[variable] = str(sig_val)
    return input_map

def is_failed_to_solve_opcode_error(status: ExecStatus) -> bool:
    """
    This function returns `True` if the "failed to solve opcode"
    error was triggered.
    """
    if status.returncode == FAILED_TO_SOLVE_PROGRAM_OPCODE_RETURNCODE:
        stderr = remove_ansi_escape_sequences(status.stderr)
        if FAILED_TO_SOLVE_PROGRAM_OPCODE_STDERR in stderr:
            return True
    return False

def check_for_ignored_errors(iteration: TestIteration, c1_exec: ExecStatus, c2_exec: ExecStatus) -> bool:
    """
    This function returns `True` if one of the executions contains an ignored error.
    Additionally, the error is marked as ignored in the passed iteration object.
    """

    found_ignored_error = False

    name_status_pairs = [("original", c1_exec), ("transformed", c2_exec)]
    for name, status in name_status_pairs:

        if is_failed_to_solve_opcode_error(status):
            logger.warning(f"Instance ignored because of 'Cannot solve opcode ...' error for {name}")
            iteration.c1_ignored_error = "cannot solve opcode"
            found_ignored_error = True

    return found_ignored_error


# ================================================================
#                  IR to Noir and Project Setup
# ================================================================

def prepare_project(root: Path, prefix: str, circuit: Circuit, curve: CurvePrime) -> Path:
    """
    Generates a default noir project for a given circuit.
    First the circuit is transformed into noir source code.
    Afterwards it is written into `main.noir` and placed into
    following file structure.
    ```
        PROJECT/
            |__ circuit.txt
            |__ Nargo.toml
            |__ src/
                 |__ main.noir
    ```
    """

    working_dir = root / prefix
    clean_or_create_dir(working_dir)
    source_dir = working_dir / "src"
    clean_or_create_dir(source_dir)

    nargo_version = get_system_nargo_verison()
    if nargo_version == None:
        raise RuntimeError("unable to retrieve noir version")

    # generate Nargo.toml
    nargo_toml = working_dir / "Nargo.toml"
    with open(nargo_toml, 'w') as file_handler:
        file_handler.write("\n".join(
            [ "[package]"
            , f"name = \"{PROJECT_NAME}\""
            , "type = \"bin\""
            , "authors = [\"\"]"
            , f"compiler_version = \"{nargo_version[0]}.{nargo_version[1]}.{nargo_version[2]}\""
            , ""
            , "[dependencies]"
            ]))

    # generate circuit.txt for debug purposes
    circuit_txt = working_dir / "circuit.txt"
    with open(circuit_txt, 'w') as file_handler:
        file_handler.write(str(circuit))

    # transform circuit into noir source code and
    # write it into src/main.nr
    noir_ast = IR2NoirVisitor(curve, nargo_version).transform(circuit)
    noir_source = EmitVisitor().emit(noir_ast)
    main_nr = source_dir / "main.nr"
    with open(main_nr, 'w') as file_handler:
        file_handler.write(noir_source)

    return working_dir

def normalize_output(output: str) -> str:
    lines = output.strip().splitlines()
    normalized = []
    for line in lines:
        if line.startswith("[Test] Witness saved to"):
            normalized.append("[Test] Witness saved to <some path>")
        else:
            normalized.append(line)
    return "\n"

# ================================================================
#                          Testing
# ================================================================

def analyze_metamorphic_relation \
    ( exec_orig: ExecStatus
    , exec_tf: ExecStatus
    , kind: MetamorphicKind
    ) -> NoirError | None:

    """
    This function takes two noir executions and checks for metamorphic violations
    regarding miss-matching returncode, output or assertions.
    """

    failed_assertion_orig_or_none = extract_assertion(exec_orig.stderr)
    failed_assertion_tf_or_none = extract_assertion(exec_tf.stderr)

    logger.info(f"checking for metamorphic violations ({kind}) of noir's execution states")

    match kind:
        case MetamorphicKind.WEAKER:
            if exec_tf.returncode == 0:
                return None # transformation did not fail so its fine
            if failed_assertion_tf_or_none == failed_assertion_orig_or_none:
                return None # failed assertions are equal
            if failed_assertion_tf_or_none != None and failed_assertion_orig_or_none != None:
                # NOTE: having multiple assertions would be optimal, but noir only gives you the first
                #       that fails, which is why instead of a subset we get the last assertion if present
                #       and check for the assertion (id: <number>)
                assertion_id_pattern = r"\(id: ([0-9]+)\)"
                match_origin = re.search(assertion_id_pattern, failed_assertion_orig_or_none)
                match_tf = re.search(assertion_id_pattern, failed_assertion_tf_or_none)
                assert match_origin != None and match_tf != None, "assertion had no id, generation error!"
                id_orig = int(match_origin.group(1))
                id_tf = int(match_tf.group(1))
                if id_orig < id_tf:
                    return None # weakened instance failed later than origin, which is ok
            # else: metamorphic weakening is violated
            logger.error(f"found metamorphic violation ({kind}) for noir execution state")
            logger.debug(exec_orig)
            logger.debug(exec_tf)
            return NoirError.METAMORPHIC_VIOLATION_EXECUTION
        case MetamorphicKind.EQUAL:
            if failed_assertion_orig_or_none != failed_assertion_tf_or_none or \
               exec_orig.returncode != exec_tf.returncode or \
               normalize_output(exec_orig.stdout) != normalize_output(exec_tf.stdout):
                logger.error(f"found metamorphic violation ({kind}) for noir execution state")
                logger.debug(exec_orig)
                logger.debug(exec_tf)
                return NoirError.METAMORPHIC_VIOLATION_EXECUTION
    return None


def prove_and_compare \
    ( original: Path
    , transformed: Path
    , iteration: TestIteration
    , online_tuning: OnlineTuning
    ):

    """
    Proves, verifies and compares two (executed) noir projects using `bb`.
    This functions expects following code structure:
    ```
        PROJECT/
            |__ circuit.txt
            |__ Nargo.toml
            |__ src/..
            |__ target/
                    |__ witness.gz
                    |__ Test.json
    ```
    where the `target` folder was a product of `noir execute`.
    """

    witness_orig = original / "target" / (WITNESS_NAME + ".gz")
    witness_tf = transformed / "target" / (WITNESS_NAME + ".gz")
    assert witness_orig.is_file(), "sanity check for available witness file"
    assert witness_tf.is_file(), "sanity check for available witness file"

    noir_json_orig = original / "target" / (PROJECT_NAME + ".json")
    noir_json_tf = transformed / "target" / (PROJECT_NAME + ".json")
    assert noir_json_orig.is_file(), "sanity check for available noir json file"
    assert noir_json_tf.is_file(), "sanity check for available noir json file"

    proof_orig = original / "proof"
    proof_tf = transformed / "proof"

    vk_orig = original / "target" / "vk"
    vk_tf = transformed / "target" / "vk"
    write_vk_exec_orig = bb_write_vk(noir_json_orig, vk_orig)
    write_vk_exec_tf = bb_write_vk(noir_json_tf, vk_tf)

    online_tuning.add_prove_or_verify_time(write_vk_exec_orig.delta_time)
    online_tuning.add_prove_or_verify_time(write_vk_exec_tf.delta_time)

    # use the key generation for verification as intermediate result
    iteration.c1_vk = write_vk_exec_orig.returncode == 0
    iteration.c1_vk_time = write_vk_exec_orig.delta_time
    iteration.c2_vk = write_vk_exec_tf.returncode == 0
    iteration.c2_vk_time = write_vk_exec_tf.delta_time

    # NOTE: currently vk generation is not expected to fail!
    if write_vk_exec_orig.returncode != 0:
        logger.error("unexpected error occurred during VK-key generation for the original project")
        logger.debug(write_vk_exec_orig.stderr)
        iteration.error = NoirError.UNKNOWN_VK_KEY_ERROR
        return # abort
    if write_vk_exec_tf.returncode != 0:
        logger.error("unexpected error occurred during VK-key generation for the transformed project")
        logger.debug(write_vk_exec_tf.stderr)
        iteration.error = NoirError.UNKNOWN_VK_KEY_ERROR
        return # abort
    
    # in older bb versions, the vk is dropped as a file at vk_orig/vk_tf.
    # in newer versions, vk_orig/vk_tf are directories containing the actual file.
    if vk_orig.is_dir():
        vk_orig = vk_orig / "vk"
    if vk_tf.is_dir():
        vk_tf = vk_tf / "vk"

    prove_exec_orig = bb_prove(noir_json_orig, witness_orig, vk_orig, proof_orig)
    prove_exec_tf = bb_prove(noir_json_tf, witness_tf, vk_tf, proof_tf)

    online_tuning.add_prove_or_verify_time(prove_exec_orig.delta_time)
    online_tuning.add_prove_or_verify_time(prove_exec_tf.delta_time)

    iteration.c1_bb_prove = prove_exec_orig.returncode == 0
    iteration.c1_bb_prove_time = prove_exec_orig.delta_time
    iteration.c2_bb_prove = prove_exec_tf.returncode == 0
    iteration.c2_bb_prove_time = prove_exec_tf.delta_time

    if check_for_ignored_errors(iteration, prove_exec_orig, prove_exec_tf):
        return # abort, without error

    # NOTE: currently vk generation is not expected to fail!
    if prove_exec_orig.returncode != 0:
        logger.error("unexpected error occurred during proof generation for the original project")
        logger.debug(prove_exec_orig)
        iteration.error = NoirError.UNKNOWN_PROOF_ERROR
        return # abort
    if prove_exec_tf.returncode != 0:
        logger.error("unexpected error occurred during proof generation for the transformed project")
        logger.debug(prove_exec_tf)
        iteration.error = NoirError.UNKNOWN_PROOF_ERROR
        return # abort

    inputs_orig = proof_orig
    inputs_tf = proof_tf

    # in older bb versions, the proof and inputs are bundled and dropped as a file at proof_orig/proof_tf.
    # in newer versions, proof_orig/proof_tf are directories containing the proof and input files.
    if proof_orig.is_dir():
        inputs_orig = proof_orig / "public_inputs"
        proof_orig = proof_orig / "proof"
    if proof_tf.is_dir():
        inputs_tf = proof_tf / "public_inputs"
        proof_tf = proof_tf / "proof"

    verify_exec_orig = bb_verify(vk_orig, proof_orig, inputs_orig)
    verify_exec_tf = bb_verify(vk_tf, proof_tf, inputs_tf)

    online_tuning.add_prove_or_verify_time(verify_exec_orig.delta_time)
    online_tuning.add_prove_or_verify_time(verify_exec_tf.delta_time)

    # override with actual verify value
    iteration.c1_bb_verify = verify_exec_orig.returncode == 0
    iteration.c1_bb_verify_time = verify_exec_orig.delta_time
    iteration.c2_bb_verify = verify_exec_tf.returncode == 0
    iteration.c2_bb_verify_time = verify_exec_tf.delta_time

    # NOTE: currently verification generation is not expected to fail!
    if verify_exec_orig.returncode != 0:
        logger.error("unexpected error occurred during verification of the original project")
        logger.debug(verify_exec_orig.stderr)
        iteration.error = NoirError.UNKNOWN_VERIFICATION_ERROR
        return # abort
    if verify_exec_tf.returncode != 0:
        logger.error("unexpected error occurred during verification of the transformed project")
        logger.debug(verify_exec_tf.stderr)
        iteration.error = NoirError.UNKNOWN_VERIFICATION_ERROR
        return # abort

    # proof and verification was a success!


def run_metamorphic_tests \
    ( metamorphic_pair: MetamorphicCircuitPair
    , seed: int
    , curve: CurvePrime
    , working_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> NoirResult:

    """
    Generates an runs noir on a metamorphic circuit pair. If a metamorphic violation
    is detected an error string is return, otherwise 'None' is returned
    """

    # check that only arithmetic generators are used!
    generatorKind = config.ir.generation.generator
    if generatorKind != GeneratorKind.ARITHMETIC:
        raise NotImplementedError(f"noir is unable to deal with '{generatorKind}' generator!")

    # sanity checks
    assert_circuit_compatibility([metamorphic_pair.fst, metamorphic_pair.snd])

    # start a new experiment
    rng = Random(seed)

    # extract information
    relation_kind = metamorphic_pair.kind
    circuit_orig = metamorphic_pair.fst
    circuit_tf = metamorphic_pair.snd
    input_signals = circuit_orig.inputs[::]
    output_signals = circuit_orig.outputs[::]

    # prepare noir projects
    clean_or_create_dir(working_dir)
    logger.info(f"cleaning working dir: {working_dir}")
    project_orig = prepare_project(working_dir, "origin", circuit_orig, curve)
    project_tf = prepare_project(working_dir, "transformed", circuit_tf, curve)

    noir_result = NoirResult()

    # main loop running for each input
    for _ in range(config.noir.test_iterations):

        iteration = TestIteration()
        noir_result.iterations.append(iteration)

        # get a new input map for current iteration
        input_map = random_input(input_signals, curve, config.noir.boundary_input_probability, rng)

        # update prover toml files
        update_prover_toml(project_orig, input_map)
        update_prover_toml(project_tf, input_map)

        # execute noir
        exec_orig = noir_execute(project_orig, WITNESS_NAME, EXPRESSION_WIDTH_DEFAULT)
        exec_tf = noir_execute(project_tf, WITNESS_NAME, EXPRESSION_WIDTH_DEFAULT)

        online_tuning.add_general_execution_time(exec_orig.delta_time)
        online_tuning.add_general_execution_time(exec_tf.delta_time)

        iteration.c1_execute = exec_orig.returncode == 0
        iteration.c1_execute_time = exec_orig.delta_time
        iteration.c2_execute = exec_tf.returncode == 0
        iteration.c2_execute_time = exec_tf.delta_time

        # check for unexpected errors
        expected_error_messages = \
            [ EXECUTION_ASSERTION_STDERR
            , EXECUTION_CONSTRAINED_FAILED_STDERR
            , FAILED_TO_SOLVE_PROGRAM_OPCODE_STDERR
            ]
        exec_orig_stderr = remove_ansi_escape_sequences(exec_orig.stderr)
        exec_tf_stderr = remove_ansi_escape_sequences(exec_tf.stderr)
        if exec_orig.returncode != 0:
            if not any([ e in exec_orig_stderr for e in expected_error_messages]):
                logger.error("unknown execution error for original noir project")
                logger.debug(exec_orig)
                iteration.error = NoirError.UNKNOWN_EXECUTION_ERROR
                return noir_result
        if exec_tf.returncode != 0:
            if not any([ e in exec_tf_stderr for e in expected_error_messages]):
                logger.error("unknown execution error for transformed noir project")
                logger.debug(exec_tf)
                iteration.error = NoirError.UNKNOWN_EXECUTION_ERROR
                return noir_result

        # check if we should ignore any occurred error
        if check_for_ignored_errors(iteration, exec_orig, exec_tf):
            break # ignore current setup

        # Check for difference in the debug output for signals.
        #
        # NOTE: This has always to hold as the only thing stopping an execution is a failing
        #       assertion. Since the statements are not moved, the debug statements for values,
        #       which are placed before the assertions, must always be executed! However, it must
        #       not contain ALL output signals.
        logger.info(f"comparing debug output signals")
        debug_signals_orig = parse_signal_from_debug_output(exec_orig.stdout)
        debug_signals_tf = parse_signal_from_debug_output(exec_tf.stdout)
        if debug_signals_orig != debug_signals_tf:
            logger.error("diverging witness signals for debugged output")
            logger.info(f"original signals: {debug_signals_orig}")
            logger.info(f"transformed signals: {debug_signals_tf}")
            logger.debug(exec_orig)
            logger.debug(exec_tf)
            iteration.error = NoirError.DIVERGING_SIGNALS_IN_DEBUG
            return noir_result

        # check a correct execution
        if exec_orig.returncode == 0 and exec_tf.returncode == 0:
            # TODO: also check the STDERR for warnings etc.

            # cross compare output signals of different executions
            # TODO: compare them also to the debug signals (WARNING: they can have different signs)
            logger.info(f"comparing noir execution output signals")
            output_orig = parse_signals_from_noir_output(exec_orig.stdout, PROJECT_NAME, output_signals)
            output_tf = parse_signals_from_noir_output(exec_tf.stdout, PROJECT_NAME, output_signals)
            if output_orig != output_tf:
                logger.error("diverging witness signals for noir execution output")
                logger.info(f"original signals: {output_orig}")
                logger.info(f"transformed signals: {output_tf}")
                logger.debug(exec_orig)
                logger.debug(exec_tf)
                iteration.error = NoirError.DIVERGING_SIGNALS_IN_OUTPUT
                return noir_result
            if any([not o in output_orig for o in output_signals]):
                logger.error("missing witness signals in noir execution output")
                signals = ", ".join([o for o in output_signals if not o in output_orig])
                logger.info(f"missing signal(s): {signals}")
                logger.debug(exec_orig)
                logger.debug(exec_tf)
                iteration.error = NoirError.MISSING_SIGNALS_IN_OUTPUT
                return noir_result

            # everything is setup for proving and verifying the circuit
            online_tuning.inc_prove_and_verify_ticks()

            # prove and verify the witnesses based on the online tuning strategy
            if online_tuning.is_prove_and_verify(rng):
                online_tuning.inc_prove_and_verify_exec()
                prove_and_compare(project_orig, project_tf, iteration, online_tuning)
                if iteration.is_error():
                    return noir_result
            continue # success, restart new loop
        else:
            # parse failed assertions from STDERR
            if rel_err := analyze_metamorphic_relation(exec_orig, exec_tf, relation_kind):
                iteration.error = rel_err
                return noir_result

    return noir_result # => all good if this is reached