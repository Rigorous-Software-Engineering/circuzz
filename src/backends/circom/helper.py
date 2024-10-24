from dataclasses import dataclass, field
from enum import StrEnum
import filecmp
import json
from pathlib import Path
from random import Random

from circuzz.common.command import ExecStatus
from circuzz.common.probability import bernoulli
from circuzz.common.field import CurvePrime
from circuzz.common.helper import remove_ansi_escape_sequences
from circuzz.common.helper import assert_circuit_compatibility
from circuzz.common.field import random_field_element
from circuzz.common.filesystem import clean_or_create_dir
from circuzz.common.filesystem import remove_file_if_exists
from circuzz.common.filesystem import remove_files_if_exists

from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.metamorphism import MetamorphicKind

from circuzz.common.colorlogs import get_color_logger

from circuzz.ir.config import GeneratorKind
from circuzz.ir.nodes import Circuit

from experiment.config import Config, OnlineTuning

from .command import CircomOptimization
from .command import circom_build_witness_preparation_using_cpp
from .command import circom_compile
from .command import circom_generate_witness_using_cpp
from .command import circom_generate_witness_using_js
from .command import snarkjs_check_witness
from .command import snarkjs_generate_vkey
from .command import snarkjs_generate_zkey
from .command import snarkjs_prove
from .command import snarkjs_verify

from .utils import CircomCurve, curve_to_prime
from .utils import ProofSystem
from .utils import PTAU_FILEPATH_2POW17
from .utils import CIRCOMLIB_DIR

from .emitter import EmitVisitor
from .ir2circom import IR2CircomVisitor

logger = get_color_logger()

#
# Return Result
#

@dataclass
class TestIteration():
    # Compilation Phase
    compilation              : dict[str, bool]  = field(default_factory=dict)
    compilation_time         : dict[str, float] = field(default_factory=dict)
    compilation_optimization : dict[str, str]   = field(default_factory=dict)

    # Witness Phase
    cpp_witness_preparation      : dict[str, bool]  = field(default_factory=dict)
    cpp_witness_preparation_time : dict[str, float] = field(default_factory=dict)
    cpp_witness_generation       : dict[str, bool]  = field(default_factory=dict)
    cpp_witness_generation_time  : dict[str, float] = field(default_factory=dict)
    js_witness_generation        : dict[str, bool]  = field(default_factory=dict)
    js_witness_generation_time   : dict[str, float] = field(default_factory=dict)
    snarkjs_witness_check        : dict[str, bool]  = field(default_factory=dict)
    snarkjs_witness_check_time   : dict[str, float] = field(default_factory=dict)

    # Proof Phase
    proof_system              : str | None = None
    zkey_generation           : dict[str, bool]  = field(default_factory=dict)
    zkey_generation_time      : dict[str, float] = field(default_factory=dict)
    proof_generation          : dict[str, bool]  = field(default_factory=dict)
    proof_generation_time     : dict[str, float] = field(default_factory=dict)

    # Verification Phase
    vkey_generation           : dict[str, bool]  = field(default_factory=dict)
    vkey_generation_time      : dict[str, float] = field(default_factory=dict)
    verification              : dict[str, bool]  = field(default_factory=dict)
    verification_time         : dict[str, float] = field(default_factory=dict)

    # individual ignores
    ignored_error : dict[str, str] = field(default_factory=dict)

    # Overall error handling (stopping reason)
    error         : str | None = None

    def update(self, manager: 'CircomManager', proof_system: ProofSystem | None):
        circuit_name = manager.circuit_name()
        if manager.compile_exec != None:
            self.compilation[circuit_name] = manager.compile_exec.returncode == 0
            self.compilation_time[circuit_name] = manager.compile_exec.delta_time
            self.compilation_optimization[circuit_name] = manager.compile_optimization()
        if manager.cpp_wtns_build_exec != None:
            self.cpp_witness_preparation[circuit_name] = manager.cpp_wtns_build_exec.returncode == 0
            self.cpp_witness_preparation_time[circuit_name] = manager.cpp_wtns_build_exec.delta_time
        if manager.cpp_wtns_gen_exec != None:
            self.cpp_witness_generation[circuit_name] = manager.cpp_wtns_gen_exec.returncode == 0
            self.cpp_witness_generation_time[circuit_name] = manager.cpp_wtns_gen_exec.delta_time
        if manager.js_wtns_gen_exec != None:
            self.js_witness_generation[circuit_name] = manager.js_wtns_gen_exec.returncode == 0
            self.js_witness_generation_time[circuit_name] = manager.js_wtns_gen_exec.delta_time
        if manager.prove_exec != None:
            self.proof_generation[circuit_name] = manager.prove_exec.returncode == 0
            self.proof_generation_time[circuit_name] = manager.prove_exec.delta_time
            if proof_system != None and manager.is_groth16_proof_scala_error(proof_system, manager.prove_exec):
                self.ignored_error[circuit_name] = "proof groth16 scalar error"
        if manager.verify_exec != None:
            self.verification[circuit_name] = manager.verify_exec.returncode == 0
            self.verification_time[circuit_name] = manager.verify_exec.delta_time
            if proof_system != None and manager.is_groth16_verify_scalar_error(proof_system, manager.verify_exec):
                self.ignored_error[circuit_name] = "verify groth16 scalar error"
        if manager.wtns_check_exec != None:
            self.snarkjs_witness_check[circuit_name] = manager.wtns_check_exec.returncode == 0
            self.snarkjs_witness_check_time[circuit_name] = manager.wtns_check_exec.delta_time
        if proof_system != None:
            self.proof_system = proof_system
            if proof_system in manager.zkey_exec_map:
                self.zkey_generation[circuit_name] = manager.zkey_exec_map[proof_system].returncode == 0
                self.zkey_generation_time[circuit_name] = manager.zkey_exec_map[proof_system].delta_time
                if manager.is_groth16_zkey_scalar_error(proof_system, manager.zkey_exec_map[proof_system]):
                    self.ignored_error[circuit_name] = "zkey groth16 scalar error"
                if manager.is_plonk_zkey_too_big_for_tau_error(proof_system, manager.zkey_exec_map[proof_system]):
                    self.ignored_error[circuit_name] = "zkey plonk too big for tau"
            if proof_system in  manager.vkey_exec_map:
                self.vkey_generation[circuit_name] = manager.vkey_exec_map[proof_system].returncode == 0
                self.vkey_generation_time[circuit_name] = manager.vkey_exec_map[proof_system].delta_time

@dataclass
class CircomResult():
    iterations : list[TestIteration] = field(default_factory=list)

#
# Error strings
#

COMPILATION_FALSE_ASSERT_STDERR = "False assert reached"
COMPILATION_FALSE_ASSERT_RETURNCODE = 1

WITNESS_GENERATION_JS_FALSE_ASSERT_STDERR = "Error: Assert Failed."
WITNESS_GENERATION_JS_FALSE_ASSERT_RETURNCODE = 1

WITNESS_GENERATION_CPP_FALSE_ASSERT_STDERR = "Assertion `Fr_isTrue("
WITNESS_GENERATION_CPP_FALSE_ASSERT_RETURNCODE = -6

SNARK_JS_GROTH16_PROOF_SCALAR_SIZE_ERROR_STDOUT = "Error: Scalar size does not match"
SNARK_JS_GROTH16_PROOF_SCALAR_SIZE_ERROR_RETURNCODE = 1

SNARK_JS_GROTH16_ZKEY_SCALAR_SIZE_ERROR_STDOUT = "Error: Scalar size does not match"
SNARK_JS_GROTH16_ZKEY_SCALAR_SIZE_ERROR_RETURNCODE = 1

SNARK_JS_GROTH16_VERIFY_SCALAR_SIZE_ERROR_STDOUT = "Error: Scalar size does not match"
SNARK_JS_GROTH16_VERIFY_SCALAR_SIZE_ERROR_RETURNCODE = 1

SNARK_JS_PLONK_ZKEY_TOO_BIG_FOR_TAU_ERROR_STDOUT = "circuit too big for this power of tau ceremony. 0 >"
SNARK_JS_PLONK_ZKEY_TOO_BIG_FOR_TAU_ERROR_RETURNCODE = 255

COMPILE_HINT_FOR_NOT_USING_GROTH16 = "(none belong to witness)"

class WitnessChoice(StrEnum):
    JS_ONLY = "js"
    CPP_ONLY = "cpp"
    BOTH = "both"

class CircomError(StrEnum):
    UNKNOWN_COMPILATION_ERROR = "unknown compilation error"
    CPP_WITNESS_GENERATION_BUILD_ERROR = "CPP witness generation build error"
    UNKNOWN_CPP_WITNESS_GENERATION_ERROR = "unknown CPP witness generation error"
    UNKNOWN_JS_WITNESS_GENERATION_ERROR = "unknown JS witness generation error"
    DIVERGING_WTNS_GEN_EXIT_STATUS = "diverging witness exit status for JS and CPP"
    DIVERGING_WTNS_GEN_OUTPUT_SIGNALS = "diverging witness output signals for JS and CPP"
    DIVERGING_WTNS_GEN_FILES = "diverging witness file for JS and CPP"
    UNKNOWN_ZKEY_GENERATION_ERROR = "unknown zkey generation error"
    UNKNOWN_PROVE_ERROR = "unknown prove error"
    UNKNOWN_VKEY_GENERATION_ERROR = "unknown vkey generation error"
    UNKNOWN_VERIFICATION_ERROR = "unknown verification error"
    UNKNOWN_WITNESS_CHECK_ERROR = "unknown witness check error"

    METAMORPHIC_VIOLATION_FOR_WTNS_GEN_STATUS = "metamorphic violation for the witness generation status"
    METAMORPHIC_VIOLATION_FOR_WTNS_GEN_SIGNALS = "metamorphic violation for the witness generation output signals"
    METAMORPHIC_VIOLATION_FOR_PROOF = "metamorphic violation for proof"
    METAMORPHIC_VIOLATION_FOR_VERIFICATION = "metamorphic violation for verification"

    MISSING_OUTPUT_SIGNAL = "missing output signal"

# =====================================================
#     Compile, Witness Generation, Prove, Verify
# =====================================================

class CircomManager():

    circuit : Circuit | None = None

    # keeping track of files
    unsafe_project        : Path
    unsafe_circuit_circom : Path
    unsafe_circuit_txt    : Path
    unsafe_r1cs           : Path
    unsafe_sym            : Path
    unsafe_input_json     : Path
    unsafe_cpp_wtns       : Path
    unsafe_js_wtns        : Path
    unsafe_cpp_dir        : Path
    unsafe_circuit_exe    : Path
    unsafe_js_dir         : Path
    unsafe_circuit_wasm   : Path
    unsafe_gen_wtns_js    : Path
    unsafe_proof_json     : Path
    unsafe_public_json    : Path

    # keeping track of executions
    compile_exec        : ExecStatus | None = None
    cpp_wtns_build_exec : ExecStatus | None = None
    cpp_wtns_gen_exec   : ExecStatus | None = None
    js_wtns_gen_exec    : ExecStatus | None = None
    prove_exec          : ExecStatus | None = None
    verify_exec         : ExecStatus | None = None
    wtns_check_exec     : ExecStatus | None = None # (optional)

    # these execution can stay longer
    zkey_exec_map       : dict[ProofSystem, ExecStatus]
    vkey_exec_map       : dict[ProofSystem, ExecStatus]

    # generation values
    cpp_output_signals : dict[str, int] | None = None
    js_output_signals  : dict[str, int] | None = None

    # main controls
    error   : CircomError | None = None

    # setting info
    optimization : CircomOptimization | None = None

    # shared online tuning object
    online_tuning: OnlineTuning

    def __init__(self, project : Path, online_tuning: OnlineTuning):
        self.unsafe_project = project
        self.unsafe_circuit_circom = project / "circuit.circom"
        self.unsafe_circuit_txt = project / "circuit.txt"
        self.unsafe_r1cs = project / "circuit.r1cs"
        self.unsafe_sym = project / "circuit.sym"
        self.unsafe_input_json = project / "input.json"
        self.unsafe_cpp_wtns = project / "witness.cpp.wtns"
        self.unsafe_js_wtns = project / "witness.js.wtns"
        self.unsafe_cpp_dir = project / "circuit_cpp"
        self.unsafe_circuit_exe = self.unsafe_cpp_dir / "circuit"
        self.unsafe_js_dir = project / "circuit_js"
        self.unsafe_circuit_wasm = self.unsafe_js_dir / "circuit.wasm"
        self.unsafe_gen_wtns_js = self.unsafe_js_dir / "generate_witness.js"
        self.unsafe_proof_json = project / "proof.json"
        self.unsafe_public_json = project / "public.json"

        self.zkey_exec_map = {}
        self.vkey_exec_map = {}

        self.online_tuning = online_tuning

    def setup(self, circuit: Circuit, constraint_assignment_probability: float, rng: Random):
        self.circuit = circuit
        self.error = None

        # clean up directory
        clean_or_create_dir(self.unsafe_project)

        # transforms the given circuit into a circom representation
        circom = IR2CircomVisitor(constraint_assignment_probability, rng).transform(circuit)

        # write circuit.circom source file
        circom_source = EmitVisitor().emit(circom)
        with open(self.unsafe_circuit_circom, 'w') as file_handler:
            file_handler.write(circom_source)

        # write a circuit.txt debug file
        with open(self.unsafe_circuit_txt, 'w') as file_handler:
            file_handler.write(str(circuit))

    def update(self, inputs: dict[str, int]):
        stringified_inputs = {k: str(v) for k, v in inputs.items()}
        input_source = json.dumps(stringified_inputs, indent=4)
        with open(self.unsafe_input_json, 'w') as file_handler:
            file_handler.write(input_source)

        # reset outdated executions status
        # NOTE: 'compile_exec' and 'cpp_wtns_build_exec' are kept
        self.cpp_wtns_gen_exec = None
        self.js_wtns_gen_exec = None
        self.prove_exec = None
        self.verify_exec = None
        self.wtns_check_exec = None

        # reset outdated files
        outdated = \
            [ self.unsafe_cpp_wtns
            , self.unsafe_js_wtns
            , self.unsafe_proof_json
            , self.unsafe_public_json
            ]
        remove_files_if_exists(outdated)

    def compile(self, curve: CircomCurve, optimization: CircomOptimization):
        self.optimization = optimization
        if not CIRCOMLIB_DIR.is_dir():
            raise RuntimeError(f"unable to find {CIRCOMLIB_DIR}! Is it not called from container?")
        self.compile_exec = circom_compile(self.circuit_circom, \
            self.project, CIRCOMLIB_DIR, optimization, curve)
        self.online_tuning.add_general_execution_time(self.compile_exec.delta_time)
        if self.compile_exec.returncode != 0:
            if not self.is_compile_assertion_error(self.compile_exec):
                self.abort(CircomError.UNKNOWN_COMPILATION_ERROR)
            return # stop

    def generate_witness(self, choice: WitnessChoice):
        # execute the witness generation using the CPP generator
        if choice in [WitnessChoice.CPP_ONLY, WitnessChoice.BOTH]:
            if not self.unsafe_circuit_exe.is_file():
                self.cpp_wtns_build_exec = circom_build_witness_preparation_using_cpp(self.cpp_dir)
                self.online_tuning.add_general_execution_time(self.cpp_wtns_build_exec.delta_time)
                if self.cpp_wtns_build_exec.returncode != 0:
                    self.abort(CircomError.UNKNOWN_COMPILATION_ERROR)
                    return # stop
            self.cpp_wtns_gen_exec = circom_generate_witness_using_cpp(self.circuit_exe, self.input_json, self.unsafe_cpp_wtns)
            self.online_tuning.add_general_execution_time(self.cpp_wtns_gen_exec.delta_time)
            if self.cpp_wtns_gen_exec.returncode == 0:
                self.cpp_output_signals = parse_output_from_stdout(self.cpp_wtns_gen_exec.stdout)
            else:
                if not self.is_cpp_wtns_gen_assertion_error(self.cpp_wtns_gen_exec) :
                    self.abort(CircomError.UNKNOWN_CPP_WITNESS_GENERATION_ERROR)
                return # stop

        # execute the witness generation using the JS generator
        if choice in [WitnessChoice.JS_ONLY, WitnessChoice.BOTH]:
            self.js_wtns_gen_exec = circom_generate_witness_using_js(self.gen_wtns_js, \
                self.circuit_wasm, self.input_json, self.unsafe_js_wtns)
            self.online_tuning.add_general_execution_time(self.js_wtns_gen_exec.delta_time)
            if self.js_wtns_gen_exec.returncode == 0:
                self.js_output_signals = parse_output_from_stdout(self.js_wtns_gen_exec.stdout)
            else:
                if not self.is_js_wtns_gen_assertion_error(self.js_wtns_gen_exec):
                    self.abort(CircomError.UNKNOWN_JS_WITNESS_GENERATION_ERROR)
                return # stop

        if choice == WitnessChoice.BOTH:
            # sanity check
            assert self.cpp_wtns_gen_exec != None, "CPP witness generation status is 'None'"
            assert self.js_wtns_gen_exec != None, "JS witness generation status is 'None'"

            if self.cpp_wtns_gen_exec.is_failure() != self.js_wtns_gen_exec.is_failure():
                self.abort(CircomError.DIVERGING_WTNS_GEN_EXIT_STATUS)
                return # stop

            if self.cpp_wtns_gen_exec.returncode == 0:
                # sanity check
                assert self.cpp_output_signals != None, "CPP output signals are 'None'"
                assert self.js_output_signals != None, "JS output signals are 'None'"

                if self.cpp_output_signals != self.js_output_signals:
                    self.abort(CircomError.DIVERGING_WTNS_GEN_OUTPUT_SIGNALS)
                    return # stop

                if not filecmp.cmp(self.js_wtns, self.cpp_wtns, shallow=False):
                    self.abort(CircomError.DIVERGING_WTNS_GEN_FILES)
                    return # stop

    def check_witness(self):
        self.wtns_check_exec = snarkjs_check_witness(self.r1cs, self.witness_wtns)
        self.online_tuning.add_general_execution_time(self.wtns_check_exec.delta_time)
        if self.wtns_check_exec.returncode != 0:
            self.abort(CircomError.UNKNOWN_WITNESS_CHECK_ERROR)
            return # stop

    def prove(self, system: ProofSystem):
        unsafe_zkey = self.unsafe_zkey(system)
        if not unsafe_zkey.is_file():
            # check if hardcoded precomputed ptau-file is available
            if not PTAU_FILEPATH_2POW17.is_file():
                raise RuntimeError(f"unable to find {PTAU_FILEPATH_2POW17}! Is it not called from container?")
            zkey_exec = snarkjs_generate_zkey(system, self.r1cs, PTAU_FILEPATH_2POW17, unsafe_zkey)
            self.online_tuning.add_prove_or_verify_time(zkey_exec.delta_time)
            self.zkey_exec_map[system] = zkey_exec
            if zkey_exec.returncode != 0:
                if not self.is_groth16_zkey_scalar_error(system, zkey_exec) and \
                   not self.is_plonk_zkey_too_big_for_tau_error(system, zkey_exec):
                    self.abort(CircomError.UNKNOWN_ZKEY_GENERATION_ERROR)
                else:
                    # NOTE: since we are not aborting we have to clean
                    # up the invalid zkey or it is used
                    remove_file_if_exists(unsafe_zkey)
                return # stop

        self.prove_exec = snarkjs_prove(system, self.zkey(system), self.witness_wtns, \
            self.unsafe_proof_json, self.unsafe_public_json)
        self.online_tuning.add_prove_or_verify_time(self.prove_exec.delta_time)
        if self.prove_exec.returncode != 0:
            if not self.is_groth16_proof_scala_error(system, self.prove_exec):
                self.abort(CircomError.UNKNOWN_PROVE_ERROR)
            return # stop

    def verify(self, system: ProofSystem):
        zkey = self.zkey(system)
        unsafe_vkey = self.unsafe_vkey(system)
        if not unsafe_vkey.is_file():
            vkey_exec = snarkjs_generate_vkey(zkey, unsafe_vkey)
            self.online_tuning.add_prove_or_verify_time(vkey_exec.delta_time)
            self.vkey_exec_map[system] = vkey_exec
            if vkey_exec.returncode != 0:
                self.abort(CircomError.UNKNOWN_VKEY_GENERATION_ERROR)
                return # stop

        self.verify_exec = snarkjs_verify(system, self.vkey(system), \
            self.public_json, self.proof_json)
        self.online_tuning.add_prove_or_verify_time(self.verify_exec.delta_time)
        if self.verify_exec.returncode != 0:
            if not self.is_groth16_verify_scalar_error(system, self.verify_exec):
                self.abort(CircomError.UNKNOWN_VERIFICATION_ERROR)
            return # stop

    def abort(self, error: CircomError):
        logger.error(f"{error.value}")

        self.error = error
        self.dump_commands()

    #
    # progress information
    #

    def is_compiled(self) -> bool:
        if self.compile_exec != None:
            return self.compile_exec.returncode == 0
        return False

    def is_witness_generated(self) -> bool:
        if self.js_wtns_gen_exec != None and \
           self.js_wtns_gen_exec.returncode == 0:
            return True
        if self.cpp_wtns_gen_exec != None and \
           self.cpp_wtns_gen_exec.returncode == 0:
            return True
        return False

    def is_proved(self) -> bool:
        if self.prove_exec != None:
            return self.prove_exec.returncode == 0
        return False

    def is_verified(self) -> bool:
        if self.verify_exec != None:
            return self.verify_exec.returncode == 0
        return False

    def is_stop(self) -> bool:
        return self.error != None

    #
    # Error
    #

    def is_groth16_proof_scala_error(self, system: ProofSystem, status: ExecStatus) -> bool:
        return system == ProofSystem.GROTH16 and \
            SNARK_JS_GROTH16_PROOF_SCALAR_SIZE_ERROR_STDOUT in status.stdout and \
            SNARK_JS_GROTH16_PROOF_SCALAR_SIZE_ERROR_RETURNCODE == status.returncode

    def is_groth16_zkey_scalar_error(self, system: ProofSystem, status: ExecStatus) -> bool:
        return system == ProofSystem.GROTH16 and \
            SNARK_JS_GROTH16_ZKEY_SCALAR_SIZE_ERROR_STDOUT in status.stdout and \
            SNARK_JS_GROTH16_ZKEY_SCALAR_SIZE_ERROR_RETURNCODE == status.returncode

    def is_groth16_verify_scalar_error(self, system: ProofSystem, status: ExecStatus) -> bool:
        return system == ProofSystem.GROTH16 and \
            SNARK_JS_GROTH16_VERIFY_SCALAR_SIZE_ERROR_STDOUT in status.stdout and \
            SNARK_JS_GROTH16_VERIFY_SCALAR_SIZE_ERROR_RETURNCODE == status.returncode

    def is_plonk_zkey_too_big_for_tau_error(self, system: ProofSystem, status: ExecStatus) -> bool:
        return system == ProofSystem.PLONK and \
            SNARK_JS_PLONK_ZKEY_TOO_BIG_FOR_TAU_ERROR_STDOUT in status.stdout and \
            SNARK_JS_PLONK_ZKEY_TOO_BIG_FOR_TAU_ERROR_RETURNCODE == status.returncode

    def is_compile_assertion_error(self, status: ExecStatus) -> bool:
        return COMPILATION_FALSE_ASSERT_STDERR in status.stderr or \
            COMPILATION_FALSE_ASSERT_RETURNCODE == status.returncode

    def is_cpp_wtns_gen_assertion_error(self, status: ExecStatus) -> bool:
        return WITNESS_GENERATION_CPP_FALSE_ASSERT_STDERR in status.stderr and \
            WITNESS_GENERATION_CPP_FALSE_ASSERT_RETURNCODE == status.returncode

    def is_js_wtns_gen_assertion_error(self, status: ExecStatus) -> bool:
        return WITNESS_GENERATION_JS_FALSE_ASSERT_STDERR in status.stderr and \
            WITNESS_GENERATION_JS_FALSE_ASSERT_RETURNCODE == status.returncode

    def should_skip_groth16(self) -> bool:
        if self.compile_exec:
            if self.compile_exec.returncode == 0:
                return COMPILE_HINT_FOR_NOT_USING_GROTH16 in self.compile_exec.stdout
        return False

    def is_tainted_by_groth16_or_plonk_error(self, system: ProofSystem) -> bool:
        if self.prove_exec:
            if self.is_groth16_proof_scala_error(system, self.prove_exec):
                return True
        if self.verify_exec:
            if self.is_groth16_verify_scalar_error(system, self.verify_exec):
                return True
        if system in self.zkey_exec_map:
            if self.is_groth16_zkey_scalar_error(system, self.zkey_exec_map[system]):
                return True
            if self.is_plonk_zkey_too_big_for_tau_error(system, self.zkey_exec_map[system]):
                return True
        return False

    #
    # Debug / Report
    #

    def dump_commands(self):
        result = ""
        if self.compile_exec:
            result += self.compile_exec.as_markdown()
            result += "\n"
        if self.cpp_wtns_build_exec:
            result += self.cpp_wtns_build_exec.as_markdown()
            result += "\n"
        if self.cpp_wtns_gen_exec:
            result += self.cpp_wtns_gen_exec.as_markdown()
            result += "\n"
        if self.js_wtns_gen_exec:
            result += self.js_wtns_gen_exec.as_markdown()
            result += "\n"
        if self.zkey_exec_map:
            for value in self.zkey_exec_map.values():
                result += value.as_markdown()
                result += "\n"
        if self.vkey_exec_map:
            for value in self.vkey_exec_map.values():
                result += value.as_markdown()
                result += "\n"
        if self.prove_exec:
            result += self.prove_exec.as_markdown()
            result += "\n"
        if self.verify_exec:
            result += self.verify_exec.as_markdown()
            result += "\n"
        if self.wtns_check_exec:
            result += self.wtns_check_exec.as_markdown()
            result += "\n"

        commands_md = self.project / "commands.md"
        commands_md_source = remove_ansi_escape_sequences(result)
        with open(commands_md, 'w') as file_handler:
            file_handler.write(commands_md_source)

        logger.info(f"wrote commands into {commands_md}")

    #
    # (Safe) File Access
    #

    @property
    def circuit_circom(self) -> Path:
        assert self.unsafe_circuit_circom.is_file(), \
                f"unable to access {self.unsafe_circuit_circom}"
        return self.unsafe_circuit_circom

    @property
    def project(self) -> Path:
        assert self.unsafe_project.is_dir(), \
                f"unable to access {self.unsafe_project}"
        return self.unsafe_project

    @property
    def r1cs(self) -> Path:
        assert self.unsafe_r1cs.is_file(), \
            f"unable to access {self.unsafe_r1cs}"
        return self.unsafe_r1cs

    @property
    def sym(self) -> Path:
        assert self.unsafe_sym.is_file(), \
            f"unable to access {self.unsafe_sym}"
        return self.unsafe_sym

    @property
    def input_json(self) -> Path:
        assert self.unsafe_input_json.is_file(), \
            f"unable to access {self.unsafe_input_json}"
        return self.unsafe_input_json

    @property
    def cpp_wtns(self) -> Path:
        assert self.unsafe_cpp_wtns.is_file(), \
            f"unable to access {self.unsafe_cpp_wtns}"
        return self.unsafe_cpp_wtns

    @property
    def js_wtns(self) -> Path:
        assert self.unsafe_js_wtns.is_file(), \
            f"unable to access {self.unsafe_js_wtns}"
        return self.unsafe_js_wtns

    @property
    def cpp_dir(self) -> Path:
        assert self.unsafe_cpp_dir.is_dir(), \
            f"unable to access {self.unsafe_cpp_dir}"
        return self.unsafe_cpp_dir

    @property
    def circuit_exe(self) -> Path:
        assert self.unsafe_circuit_exe.is_file(), \
            f"unable to access {self.unsafe_circuit_exe}"
        return self.unsafe_circuit_exe

    @property
    def js_dir(self) -> Path:
        assert self.unsafe_js_dir.is_dir(), \
            f"unable to access {self.unsafe_js_dir}"
        return self.unsafe_js_dir

    @property
    def circuit_wasm(self) -> Path:
        assert self.unsafe_circuit_wasm.is_file(), \
            f"unable to access {self.unsafe_circuit_wasm}"
        return self.unsafe_circuit_wasm

    @property
    def gen_wtns_js(self) -> Path:
        assert self.unsafe_gen_wtns_js.is_file(), \
            f"unable to access {self.unsafe_gen_wtns_js}"
        return self.unsafe_gen_wtns_js

    @property
    def proof_json(self) -> Path:
        assert self.unsafe_proof_json.is_file(), \
            f"unable to access {self.unsafe_proof_json}"
        return self.unsafe_proof_json

    @property
    def public_json(self) -> Path:
        assert self.unsafe_public_json.is_file(), \
            f"unable to access {self.unsafe_public_json}"
        return self.unsafe_public_json

    @property
    def witness_wtns(self) -> Path:
        if self.unsafe_js_wtns.is_file():
            return self.unsafe_js_wtns
        if self.unsafe_cpp_wtns.is_file():
            return self.unsafe_cpp_wtns
        assert False, f"unable to access {self.unsafe_js_wtns} or {self.unsafe_cpp_wtns}"

    @property
    def output_signals(self) -> dict[str, int]:
        if self.js_output_signals != None:
            return self.js_output_signals
        if self.cpp_output_signals != None:
            return self.cpp_output_signals
        assert False, f"no output signals available"

    def unsafe_zkey(self, system: ProofSystem) -> Path:
        return self.project / f"{system.value}_final.zkey"

    def zkey(self, system: ProofSystem) -> Path:
        zkey_file = self.unsafe_zkey(system)
        assert zkey_file.is_file(), \
            f"unable to access {zkey_file}"
        return zkey_file

    def unsafe_vkey(self, system: ProofSystem) -> Path:
        return self.project / f"{system.value}_vkey.json"

    def vkey(self, system: ProofSystem) -> Path:
        vkey_file = self.unsafe_vkey(system)
        assert vkey_file.is_file(), \
            f"unable to access {vkey_file}"
        return vkey_file

    def circuit_name(self) -> str:
        assert self.circuit != None, "no circuit available"
        return self.circuit.name

    def compile_optimization(self) -> str:
        assert self.optimization != None, "no circuit available"
        return self.optimization.value


# =====================================================
#                      Helpers
# =====================================================


def parse_output_from_stdout(stdout: str) -> dict[str, int]:
    """
    Each output signal is printed after its assigned using
    following format "<@> NAME = VALUE", where NAME represents an output
    signal and VALUE a field value. If the witness generation was
    successful and the logs have the given form, this functions returns a
    map from variable to value.
    """

    outputs = dict()
    lines = stdout.split("\n")
    for line in lines:
        if line.startswith("<@>"): # dedicated debug symbol at line start
            line = line.replace(" ", "").replace("<@>", "")
            name, value = line.split("=")
            outputs[name] = int(value)
    return outputs

def random_inputs \
    ( input_signals: list[str]
    , prime: CurvePrime
    , boundary_input_probability: float
    , rng: Random
    ) -> dict[str, int]:

    input_map: dict[str, int] = {}
    for variable in input_signals:
        input_map[variable] = random_field_element(prime, rng,
            boundary_prob=boundary_input_probability)
    return input_map


# =====================================================
#                     Testing
# =====================================================

def run_metamorphic_tests \
    ( metamorphic_pair: MetamorphicCircuitPair
    , seed: int
    , curve: CircomCurve
    , working_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> CircomResult:

    # start a new experiment
    rng = Random(seed)

    # check that only arithmetic generators are used!
    generatorKind = config.ir.generation.generator
    if generatorKind != GeneratorKind.ARITHMETIC:
        raise NotImplementedError(f"circom is unable to deal with '{generatorKind}' generator!")

    # sanity checks
    assert_circuit_compatibility([metamorphic_pair.fst, metamorphic_pair.snd])

    # add circom folder
    clean_or_create_dir(working_dir)
    project_orig = working_dir / "origin"
    project_tf = working_dir / "transformed"

    # retrieve information
    circuit_orig = metamorphic_pair.fst
    circuit_tf = metamorphic_pair.snd
    input_signals = circuit_orig.inputs[:]
    relation_kind = metamorphic_pair.kind
    output_signals = circuit_orig.outputs[:]

    # ------------------------------------------------------
    #           Project Setup and Compilation
    # ------------------------------------------------------

    circom_result = CircomResult()
    current_iteration = TestIteration()
    circom_result.iterations.append(current_iteration)

    # project setup and circuit compilation
    circom_managers : list[CircomManager] = []
    for project, circuit in [(project_orig, circuit_orig), (project_tf, circuit_tf)]:
        manager = CircomManager(project, online_tuning)
        circom_managers.append(manager)
        manager.setup(circuit, config.circom.constraint_assignment_probability, rng)
        opt = rng.choice(list(CircomOptimization))
        manager.compile(curve, opt)

        # update iteration
        current_iteration.update(manager, proof_system=None)

        # something happened during compilation
        if manager.is_stop():
            current_iteration.error = manager.error
            return circom_result

    # no circuit compiled
    if all([not e.is_compiled() for e in circom_managers]):
        return circom_result

    # ------------------------------------------------------
    #           Preparation for Main-Loop
    # ------------------------------------------------------

    # NOTE: If we choose to use cpp gen even just once, it is only reasonable to
    # keep using it all the time for the instance due to its speed advantage.
    # Therefore we either only use js or a combination of both / only cpp.
    WITNESS_GEN_CHOICES = [WitnessChoice.JS_ONLY]
    if bernoulli(config.circom.likelihood_cpp_witness_generation, rng):
        WITNESS_GEN_CHOICES = [WitnessChoice.CPP_ONLY, WitnessChoice.BOTH]

    # build up usable proof system list
    available_proof_systems: list[ProofSystem] = list(ProofSystem)
    # TODO: HACK: Investigate the error and why it occurs for some instances.
    #             The commented section below can help to remove some instances
    # if any([e.should_skip_groth16() for e in circom_managers]):
    #     available_proof_systems.remove(ProofSystem.GROTH16)

    # ------------------------------------------------------
    #      Main-Loop with Witness, Proof, Verify Loop
    # ------------------------------------------------------

    for iter_idx in range(config.circom.test_iterations):

        # NOTE: snarkjs only supports BLS12_381 and BN128 at the moment: https://github.com/iden3/snarkjs
        #       and the precomputed power of tau uses the BN128 curve.
        #       This could be extended to BLS12_381 by computing the power of tau
        #       OR the likelihood could have an impact on the curve selection.

        # if current iteration is not available, create it
        if iter_idx > (len(circom_result.iterations) - 1):
            current_iteration = TestIteration()
            circom_result.iterations.append(current_iteration)

        # generate new random input
        input_map = random_inputs(input_signals, curve_to_prime(curve),
            config.circom.boundary_input_probability, rng)

        # randomly select what witness generation should be used
        witness_choice = rng.choice(WITNESS_GEN_CHOICES)

        # randomly select what proof system should be used
        proof_system = rng.choice(available_proof_systems)

        # update both managers first so that the error
        # report is more clear.
        for manager in circom_managers:
            if not manager.is_compiled():
                # no need to update as this was done previously
                continue # skip not compiled projects

            # input update and witness generation
            manager.update(input_map)

        # after updating run witness generation phases
        for manager in circom_managers:
            if not manager.is_compiled():
                # no need to update as this was done previously
                continue # skip not compiled projects

            # witness generation
            manager.generate_witness(witness_choice)

        # if witness generation was successful for both circuits we can
        # continue with other actions and phases:
        if all([x.is_witness_generated() for x in circom_managers]):

            # compute if we perform an optional witness check
            is_bn128 = curve == CircomCurve.BN128
            wtns_check_prob = config.circom.likelihood_snark_witness_check
            is_wtns_check = is_bn128 and bernoulli(wtns_check_prob, rng)

            # optional witness check for both circuits
            if is_wtns_check:
                for manager in circom_managers:
                    logger.info(f"check witnesses for {manager.circuit_name()} ...")
                    manager.check_witness()
                    if manager.is_stop():
                        # update current iteration before error is reported
                        current_iteration.update(manager, proof_system=proof_system)
                        current_iteration.error = manager.error
                        return circom_result # early stop for wtns check

            # We have the opportunity to execute the circom prove and verify process.
            # Although, the curve might be wrong, we should count a tick here
            online_tuning.inc_prove_and_verify_ticks()

            # Flag indicating if we execute prover and verifier.
            # The decision is based on the online tuning strategy and curve.
            is_prove_and_verify = is_bn128 and online_tuning.is_prove_and_verify(rng)

            # proof and verification steps
            if is_prove_and_verify:
                online_tuning.inc_prove_and_verify_exec()
                for manager in circom_managers:
                    logger.info(f"start proving and verifying for {manager.circuit_name()} ...")
                    manager.prove(proof_system)
                    if manager.is_proved():
                        manager.verify(proof_system)

                    # check for any errors during the different phases
                    if manager.is_stop():
                        # update current iteration before error is reported
                        current_iteration.update(manager, proof_system=proof_system)
                        current_iteration.error = manager.error
                        return circom_result # early stop if any error occurred

        # else: witness generation failed so we can skip this

        # update current iteration after all phases
        for manager in circom_managers:
            current_iteration.update(manager, proof_system=proof_system)

        #
        # check for metamorphic violations
        #

        manager_orig, manager_tf = circom_managers
        if manager_orig.is_witness_generated() != manager_tf.is_witness_generated():
            # possible violation detected, check if it was weakening
            if manager_orig.is_witness_generated() or relation_kind != MetamorphicKind.WEAKER:
                manager_orig.dump_commands()
                manager_tf.dump_commands()
                logger.error("metamorphic violation for the witness generation status")
                current_iteration.error = CircomError.METAMORPHIC_VIOLATION_FOR_WTNS_GEN_STATUS
                return circom_result
        else: # witness generation is equivalent
            if manager_orig.is_witness_generated():
                if manager_orig.output_signals != manager_tf.output_signals:
                    manager_orig.dump_commands()
                    manager_tf.dump_commands()
                    logger.error("metamorphic violation for the witness generation output signals")
                    current_iteration.error = CircomError.METAMORPHIC_VIOLATION_FOR_WTNS_GEN_SIGNALS
                    return circom_result
                if len(input_signals) > 0:
                    # It seems that in older versions of circom the, instances with no
                    # input_signals where essentially not executed / optimized away.
                    # Which is why we have no outputs for them. (This is fine AS LONG
                    # AS THE METAMORPHIC COUNTER PART ALSO HAS NO OUTPUT, which was
                    # already checked above.)
                    if any([not o in manager_orig.output_signals for o in output_signals]):
                        manager_orig.dump_commands()
                        manager_tf.dump_commands()
                        logger.critical("missing output signal")
                        current_iteration.error = CircomError.MISSING_OUTPUT_SIGNAL
                        return circom_result
                if manager_orig.is_proved() != manager_tf.is_proved():
                    # do not consider violations that fall under the groth16 or plonk limitations
                    if not manager_orig.is_tainted_by_groth16_or_plonk_error(proof_system) and \
                       not manager_tf.is_tainted_by_groth16_or_plonk_error(proof_system):
                        manager_orig.dump_commands()
                        manager_tf.dump_commands()
                        logger.error("metamorphic violation for proof")
                        current_iteration.error =  CircomError.METAMORPHIC_VIOLATION_FOR_PROOF
                        return circom_result
                    else:
                        continue # we must stop here and go to the next iteration
                if manager_orig.is_verified() != manager_tf.is_verified():
                    # do not consider violations that fall under the groth16 or plonk limitations
                    if not manager_orig.is_tainted_by_groth16_or_plonk_error(proof_system) and \
                       not manager_tf.is_tainted_by_groth16_or_plonk_error(proof_system):
                        manager_orig.dump_commands()
                        manager_tf.dump_commands()
                        logger.error("metamorphic violation for verification")
                        current_iteration.error = CircomError.METAMORPHIC_VIOLATION_FOR_VERIFICATION
                        return circom_result

        # Possible TODOs:
        # TODO: symbol and witness export + compare
        # TODO: compare proof output json files

    return circom_result