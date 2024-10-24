from dataclasses import dataclass
from dataclasses import field

@dataclass
class DataEntry():

    #
    # General Test Information
    #

    tool      : str
    test_time : float
    seed      : float
    curve     : str
    oracle    : str
    iteration : int
    error     : str | None

    #
    # General IR
    #

    ir_generation_seed : int
    ir_generation_time : float
    ir_rewrite_seed    : int
    ir_rewrite_time    : float
    ir_rewrite_rules   : list[str]
    c1_node_size       : int
    c1_assignments     : int
    c1_assertions      : int
    c1_assumptions     : int
    c1_input_signals   : int
    c1_output_signals  : int
    c2_node_size       : int
    c2_assignments     : int
    c2_assertions      : int
    c2_assumptions     : int
    c2_input_signals   : int
    c2_output_signals  : int

    #
    # Circom
    #

    circom_c1_compilation                  : bool  | None = None
    circom_c1_compilation_time             : float | None = None
    circom_c1_compilation_optimization     : str   | None = None
    circom_c2_compilation                  : bool  | None = None
    circom_c2_compilation_time             : float | None = None
    circom_c2_compilation_optimization     : str   | None = None
    circom_c1_cpp_witness_preparation      : bool  | None = None
    circom_c1_cpp_witness_preparation_time : float | None = None
    circom_c1_cpp_witness_generation       : bool  | None = None
    circom_c1_cpp_witness_generation_time  : float | None = None
    circom_c1_js_witness_generation        : bool  | None = None
    circom_c1_js_witness_generation_time   : float | None = None
    circom_c1_snarkjs_witness_check        : bool  | None = None
    circom_c1_snarkjs_witness_check_time   : float | None = None
    circom_c2_cpp_witness_preparation      : bool  | None = None
    circom_c2_cpp_witness_preparation_time : float | None = None
    circom_c2_cpp_witness_generation       : bool  | None = None
    circom_c2_cpp_witness_generation_time  : float | None = None
    circom_c2_js_witness_generation        : bool  | None = None
    circom_c2_js_witness_generation_time   : float | None = None
    circom_c2_snarkjs_witness_check        : bool  | None = None
    circom_c2_snarkjs_witness_check_time   : float | None = None
    circom_proof_system                    : str   | None = None
    circom_c1_zkey_generation              : bool  | None = None
    circom_c1_zkey_generation_time         : float | None = None
    circom_c1_proof_generation             : bool  | None = None
    circom_c1_proof_generation_time        : float | None = None
    circom_c2_zkey_generation              : bool  | None = None
    circom_c2_zkey_generation_time         : float | None = None
    circom_c2_proof_generation             : bool  | None = None
    circom_c2_proof_generation_time        : float | None = None
    circom_c1_vkey_generation              : bool  | None = None
    circom_c1_vkey_generation_time         : float | None = None
    circom_c1_verification                 : bool  | None = None
    circom_c1_verification_time            : float | None = None
    circom_c2_vkey_generation              : bool  | None = None
    circom_c2_vkey_generation_time         : float | None = None
    circom_c2_verification                 : bool  | None = None
    circom_c2_verification_time            : float | None = None
    circom_c1_ignored_error                : str   | None = None
    circom_c2_ignored_error                : str   | None = None

    #
    # Corset
    #

    corset_rust_check           : bool      | None = None
    corset_rust_check_time      : float     | None = None
    corset_rust_compile         : bool      | None = None
    corset_rust_compile_time    : float     | None = None
    corset_go_compile           : bool      | None = None
    corset_go_compile_time      : float     | None = None
    corset_wizard_compile       : bool      | None = None
    corset_wizard_compile_time  : float     | None = None
    corset_wizard_prove         : bool      | None = None
    corset_wizard_prove_time    : float     | None = None
    corset_wizard_verify        : bool      | None = None
    corset_wizard_verify_time   : float     | None = None
    corset_go_custom_cli        : bool      | None = None
    corset_go_custom_cli_time   : float     | None = None
    corset_expansions           : int       | None = None
    corset_native               : bool      | None = None
    corset_auto_constraints     : list[str] | None = None
    corset_guard_variable       : bool      | None = None
    corset_timeout              : bool      | None = None
    corset_out_of_memory        : bool      | None = None
    corset_error_references     : list[int] | None = None
    corset_ignored_error        : str       | None = None

    #
    # Gnark
    #

    gnark_c1_compile                : bool  | None = None
    gnark_c1_compile_time           : float | None = None
    gnark_c2_compile                : bool  | None = None
    gnark_c2_compile_time           : float | None = None
    gnark_c1_new_witness            : bool  | None = None
    gnark_c1_new_witness_time       : float | None = None
    gnark_c2_new_witness            : bool  | None = None
    gnark_c2_new_witness_time       : float | None = None
    gnark_c1_witness_solved         : bool  | None = None
    gnark_c1_witness_solved_time    : float | None = None
    gnark_c2_witness_solved         : bool  | None = None
    gnark_c2_witness_solved_time    : float | None = None
    gnark_c1_witness_write          : bool  | None = None
    gnark_c1_witness_write_time     : float | None = None
    gnark_c2_witness_write          : bool  | None = None
    gnark_c2_witness_write_time     : float | None = None
    gnark_c1_new_srs                : bool  | None = None
    gnark_c2_new_srs                : bool  | None = None
    gnark_c1_proof_setup            : bool  | None = None
    gnark_c1_proof_setup_time       : float | None = None
    gnark_c2_proof_setup            : bool  | None = None
    gnark_c2_proof_setup_time       : float | None = None
    gnark_c1_prove                  : bool  | None = None
    gnark_c1_prove_time             : float | None = None
    gnark_c2_prove                  : bool  | None = None
    gnark_c2_prove_time             : float | None = None
    gnark_c1_witness_public         : bool  | None = None
    gnark_c1_witness_public_time    : float | None = None
    gnark_c2_witness_public         : bool  | None = None
    gnark_c2_witness_public_time    : float | None = None
    gnark_c1_verify                 : bool  | None = None
    gnark_c1_verify_time            : float | None = None
    gnark_c2_verify                 : bool  | None = None
    gnark_c2_verify_time            : float | None = None
    gnark_cs_engine                 : str   | None = None
    gnark_proof_system              : str   | None = None
    gnark_go_test_time              : float | None = None
    gnark_go_timeout                : bool  | None = None
    gnark_go_ignored_compiler_error : str   | None = None

    #
    # Noir
    #

    noir_c1_execute        : bool  | None = None
    noir_c1_execute_time   : float | None = None
    noir_c2_execute        : bool  | None = None
    noir_c2_execute_time   : float | None = None
    noir_c1_vk             : bool  | None = None
    noir_c1_vk_time        : float | None = None
    noir_c2_vk             : bool  | None = None
    noir_c2_vk_time        : float | None = None
    noir_c1_bb_prove       : bool  | None = None
    noir_c1_bb_prove_time  : float | None = None
    noir_c2_bb_prove       : bool  | None = None
    noir_c2_bb_prove_time  : float | None = None
    noir_c1_bb_verify      : bool  | None = None
    noir_c1_bb_verify_time : float | None = None
    noir_c2_bb_verify      : bool  | None = None
    noir_c2_bb_verify_time : float | None = None
    noir_c1_ignored_error  : str   | None = None
    noir_c2_ignored_error  : str   | None = None

    #
    # Special Entries for different modes
    #

    cycle        : int | None = None
    explore_time : float | None = None
    is_fixed     : bool | None = None

    #
    # Helper functions
    #

    def is_error(self) -> bool:
        return self.error != None

    def unique_id(self) -> str:
        # tool, seed and iteration is enough for identifying a unique line
        return f"{self.tool}-{self.seed}-{self.iteration}"

    def csv_line(self) -> str:
        return ",".join(
            [ self._custom_to_str(self.tool)
            , self._custom_to_str(self.test_time)
            , self._custom_to_str(self.seed)
            , self._custom_to_str(self.curve)
            , self._custom_to_str(self.oracle)
            , self._custom_to_str(self.iteration)
            , self._custom_to_str(self.error)
            , self._custom_to_str(self.ir_generation_seed)
            , self._custom_to_str(self.ir_generation_time)
            , self._custom_to_str(self.ir_rewrite_seed)
            , self._custom_to_str(self.ir_rewrite_time)
            , self._custom_list_to_str(self.ir_rewrite_rules)
            , self._custom_to_str(self.c1_node_size)
            , self._custom_to_str(self.c1_assignments)
            , self._custom_to_str(self.c1_assertions)
            , self._custom_to_str(self.c1_assumptions)
            , self._custom_to_str(self.c1_input_signals)
            , self._custom_to_str(self.c1_output_signals)
            , self._custom_to_str(self.c2_node_size)
            , self._custom_to_str(self.c2_assignments)
            , self._custom_to_str(self.c2_assertions)
            , self._custom_to_str(self.c2_assumptions)
            , self._custom_to_str(self.c2_input_signals)
            , self._custom_to_str(self.c2_output_signals)
            , self._custom_to_str(self.circom_c1_compilation)
            , self._custom_to_str(self.circom_c1_compilation_time)
            , self._custom_to_str(self.circom_c1_compilation_optimization)
            , self._custom_to_str(self.circom_c2_compilation)
            , self._custom_to_str(self.circom_c2_compilation_time)
            , self._custom_to_str(self.circom_c2_compilation_optimization)
            , self._custom_to_str(self.circom_c1_cpp_witness_preparation)
            , self._custom_to_str(self.circom_c1_cpp_witness_preparation_time)
            , self._custom_to_str(self.circom_c1_cpp_witness_generation)
            , self._custom_to_str(self.circom_c1_cpp_witness_generation_time)
            , self._custom_to_str(self.circom_c1_js_witness_generation)
            , self._custom_to_str(self.circom_c1_js_witness_generation_time)
            , self._custom_to_str(self.circom_c1_snarkjs_witness_check)
            , self._custom_to_str(self.circom_c1_snarkjs_witness_check_time)
            , self._custom_to_str(self.circom_c2_cpp_witness_preparation)
            , self._custom_to_str(self.circom_c2_cpp_witness_preparation_time)
            , self._custom_to_str(self.circom_c2_cpp_witness_generation)
            , self._custom_to_str(self.circom_c2_cpp_witness_generation_time)
            , self._custom_to_str(self.circom_c2_js_witness_generation)
            , self._custom_to_str(self.circom_c2_js_witness_generation_time)
            , self._custom_to_str(self.circom_c2_snarkjs_witness_check)
            , self._custom_to_str(self.circom_c2_snarkjs_witness_check_time)
            , self._custom_to_str(self.circom_proof_system)
            , self._custom_to_str(self.circom_c1_zkey_generation)
            , self._custom_to_str(self.circom_c1_zkey_generation_time)
            , self._custom_to_str(self.circom_c1_proof_generation)
            , self._custom_to_str(self.circom_c1_proof_generation_time)
            , self._custom_to_str(self.circom_c2_zkey_generation)
            , self._custom_to_str(self.circom_c2_zkey_generation_time)
            , self._custom_to_str(self.circom_c2_proof_generation)
            , self._custom_to_str(self.circom_c2_proof_generation_time)
            , self._custom_to_str(self.circom_c1_vkey_generation)
            , self._custom_to_str(self.circom_c1_vkey_generation_time)
            , self._custom_to_str(self.circom_c1_verification)
            , self._custom_to_str(self.circom_c1_verification_time)
            , self._custom_to_str(self.circom_c2_vkey_generation)
            , self._custom_to_str(self.circom_c2_vkey_generation_time)
            , self._custom_to_str(self.circom_c2_verification)
            , self._custom_to_str(self.circom_c2_verification_time)
            , self._custom_to_str(self.circom_c1_ignored_error)
            , self._custom_to_str(self.circom_c2_ignored_error)
            , self._custom_to_str(self.corset_rust_check)
            , self._custom_to_str(self.corset_rust_check_time)
            , self._custom_to_str(self.corset_rust_compile)
            , self._custom_to_str(self.corset_rust_compile_time)
            , self._custom_to_str(self.corset_go_compile)
            , self._custom_to_str(self.corset_go_compile_time)
            , self._custom_to_str(self.corset_wizard_compile)
            , self._custom_to_str(self.corset_wizard_compile_time)
            , self._custom_to_str(self.corset_wizard_prove)
            , self._custom_to_str(self.corset_wizard_prove_time)
            , self._custom_to_str(self.corset_wizard_verify)
            , self._custom_to_str(self.corset_wizard_verify_time)
            , self._custom_to_str(self.corset_go_custom_cli)
            , self._custom_to_str(self.corset_go_custom_cli_time)
            , self._custom_to_str(self.corset_expansions)
            , self._custom_to_str(self.corset_native)
            , self._custom_list_to_str(self.corset_auto_constraints)
            , self._custom_to_str(self.corset_guard_variable)
            , self._custom_to_str(self.corset_timeout)
            , self._custom_to_str(self.corset_out_of_memory)
            , self._custom_list_to_str(self.corset_error_references)
            , self._custom_to_str(self.corset_ignored_error)
            , self._custom_to_str(self.gnark_c1_compile)
            , self._custom_to_str(self.gnark_c1_compile_time)
            , self._custom_to_str(self.gnark_c2_compile)
            , self._custom_to_str(self.gnark_c2_compile_time)
            , self._custom_to_str(self.gnark_c1_new_witness)
            , self._custom_to_str(self.gnark_c1_new_witness_time)
            , self._custom_to_str(self.gnark_c2_new_witness)
            , self._custom_to_str(self.gnark_c2_new_witness_time)
            , self._custom_to_str(self.gnark_c1_witness_solved)
            , self._custom_to_str(self.gnark_c1_witness_solved_time)
            , self._custom_to_str(self.gnark_c2_witness_solved)
            , self._custom_to_str(self.gnark_c2_witness_solved_time)
            , self._custom_to_str(self.gnark_c1_witness_write)
            , self._custom_to_str(self.gnark_c1_witness_write_time)
            , self._custom_to_str(self.gnark_c2_witness_write)
            , self._custom_to_str(self.gnark_c2_witness_write_time)
            , self._custom_to_str(self.gnark_c1_new_srs)
            , self._custom_to_str(self.gnark_c2_new_srs)
            , self._custom_to_str(self.gnark_c1_proof_setup)
            , self._custom_to_str(self.gnark_c1_proof_setup_time)
            , self._custom_to_str(self.gnark_c2_proof_setup)
            , self._custom_to_str(self.gnark_c2_proof_setup_time)
            , self._custom_to_str(self.gnark_c1_prove)
            , self._custom_to_str(self.gnark_c1_prove_time)
            , self._custom_to_str(self.gnark_c2_prove)
            , self._custom_to_str(self.gnark_c2_prove_time)
            , self._custom_to_str(self.gnark_c1_witness_public)
            , self._custom_to_str(self.gnark_c1_witness_public_time)
            , self._custom_to_str(self.gnark_c2_witness_public)
            , self._custom_to_str(self.gnark_c2_witness_public_time)
            , self._custom_to_str(self.gnark_c1_verify)
            , self._custom_to_str(self.gnark_c1_verify_time)
            , self._custom_to_str(self.gnark_c2_verify)
            , self._custom_to_str(self.gnark_c2_verify_time)
            , self._custom_to_str(self.gnark_cs_engine)
            , self._custom_to_str(self.gnark_proof_system)
            , self._custom_to_str(self.gnark_go_test_time)
            , self._custom_to_str(self.gnark_go_timeout)
            , self._custom_to_str(self.gnark_go_ignored_compiler_error)
            , self._custom_to_str(self.noir_c1_execute)
            , self._custom_to_str(self.noir_c1_execute_time)
            , self._custom_to_str(self.noir_c2_execute)
            , self._custom_to_str(self.noir_c2_execute_time)
            , self._custom_to_str(self.noir_c1_vk)
            , self._custom_to_str(self.noir_c1_vk_time)
            , self._custom_to_str(self.noir_c2_vk)
            , self._custom_to_str(self.noir_c2_vk_time)
            , self._custom_to_str(self.noir_c1_bb_prove)
            , self._custom_to_str(self.noir_c1_bb_prove_time)
            , self._custom_to_str(self.noir_c2_bb_prove)
            , self._custom_to_str(self.noir_c2_bb_prove_time)
            , self._custom_to_str(self.noir_c1_bb_verify)
            , self._custom_to_str(self.noir_c1_bb_verify_time)
            , self._custom_to_str(self.noir_c2_bb_verify)
            , self._custom_to_str(self.noir_c2_bb_verify_time)
            , self._custom_to_str(self.noir_c1_ignored_error)
            , self._custom_to_str(self.noir_c2_ignored_error)
            , self._custom_to_str(self.cycle)
            , self._custom_to_str(self.explore_time)
            , self._custom_to_str(self.is_fixed)
            ])

    @classmethod
    def csv_header(cls) -> str:
        return ",".join(
        [ "tool"
        , "test_time"
        , "seed"
        , "curve"
        , "oracle"
        , "iteration"
        , "error"
        , "ir_generation_seed"
        , "ir_generation_time"
        , "ir_rewrite_seed"
        , "ir_rewrite_time"
        , "ir_rewrite_rules"
        , "c1_node_size"
        , "c1_assignments"
        , "c1_assertions"
        , "c1_assumptions"
        , "c1_input_signals"
        , "c1_output_signals"
        , "c2_node_size"
        , "c2_assignments"
        , "c2_assertions"
        , "c2_assumptions"
        , "c2_input_signals"
        , "c2_output_signals"
        , "circom_c1_compilation"
        , "circom_c1_compilation_time"
        , "circom_c1_compilation_optimization"
        , "circom_c2_compilation"
        , "circom_c2_compilation_time"
        , "circom_c2_compilation_optimization"
        , "circom_c1_cpp_witness_preparation"
        , "circom_c1_cpp_witness_preparation_time"
        , "circom_c1_cpp_witness_generation"
        , "circom_c1_cpp_witness_generation_time"
        , "circom_c1_js_witness_generation"
        , "circom_c1_js_witness_generation_time"
        , "circom_c1_snarkjs_witness_check"
        , "circom_c1_snarkjs_witness_check_time"
        , "circom_c2_cpp_witness_preparation"
        , "circom_c2_cpp_witness_preparation_time"
        , "circom_c2_cpp_witness_generation"
        , "circom_c2_cpp_witness_generation_time"
        , "circom_c2_js_witness_generation"
        , "circom_c2_js_witness_generation_time"
        , "circom_c2_snarkjs_witness_check"
        , "circom_c2_snarkjs_witness_check_time"
        , "circom_proof_system"
        , "circom_c1_zkey_generation"
        , "circom_c1_zkey_generation_time"
        , "circom_c1_proof_generation"
        , "circom_c1_proof_generation_time"
        , "circom_c2_zkey_generation"
        , "circom_c2_zkey_generation_time"
        , "circom_c2_proof_generation"
        , "circom_c2_proof_generation_time"
        , "circom_c1_vkey_generation"
        , "circom_c1_vkey_generation_time"
        , "circom_c1_verification"
        , "circom_c1_verification_time"
        , "circom_c2_vkey_generation"
        , "circom_c2_vkey_generation_time"
        , "circom_c2_verification"
        , "circom_c2_verification_time"
        , "circom_c1_ignored_error"
        , "circom_c2_ignored_error"
        , "corset_rust_check"
        , "corset_rust_check_time"
        , "corset_rust_compile"
        , "corset_rust_compile_time"
        , "corset_go_compile"
        , "corset_go_compile_time"
        , "corset_wizard_compile"
        , "corset_wizard_compile_time"
        , "corset_wizard_prove"
        , "corset_wizard_prove_time"
        , "corset_wizard_verify"
        , "corset_wizard_verify_time"
        , "corset_go_custom_cli"
        , "corset_go_custom_cli_time"
        , "corset_expansions"
        , "corset_native"
        , "corset_auto_constraints"
        , "corset_guard_variable"
        , "corset_timeout"
        , "corset_out_of_memory"
        , "corset_error_references"
        , "corset_ignored_error"
        , "gnark_c1_compile"
        , "gnark_c1_compile_time"
        , "gnark_c2_compile"
        , "gnark_c2_compile_time"
        , "gnark_c1_new_witness"
        , "gnark_c1_new_witness_time"
        , "gnark_c2_new_witness"
        , "gnark_c2_new_witness_time"
        , "gnark_c1_witness_solved"
        , "gnark_c1_witness_solved_time"
        , "gnark_c2_witness_solved"
        , "gnark_c2_witness_solved_time"
        , "gnark_c1_witness_write"
        , "gnark_c1_witness_write_time"
        , "gnark_c2_witness_write"
        , "gnark_c2_witness_write_time"
        , "gnark_c1_new_srs"
        , "gnark_c2_new_srs"
        , "gnark_c1_proof_setup"
        , "gnark_c1_proof_setup_time"
        , "gnark_c2_proof_setup"
        , "gnark_c2_proof_setup_time"
        , "gnark_c1_prove"
        , "gnark_c1_prove_time"
        , "gnark_c2_prove"
        , "gnark_c2_prove_time"
        , "gnark_c1_witness_public"
        , "gnark_c1_witness_public_time"
        , "gnark_c2_witness_public"
        , "gnark_c2_witness_public_time"
        , "gnark_c1_verify"
        , "gnark_c1_verify_time"
        , "gnark_c2_verify"
        , "gnark_c2_verify_time"
        , "gnark_cs_engine"
        , "gnark_proof_system"
        , "gnark_go_test_time"
        , "gnark_go_timeout"
        , "gnark_go_ignored_compiler_error"
        , "noir_c1_execute"
        , "noir_c1_execute_time"
        , "noir_c2_execute"
        , "noir_c2_execute_time"
        , "noir_c1_vk"
        , "noir_c1_vk_time"
        , "noir_c2_vk"
        , "noir_c2_vk_time"
        , "noir_c1_bb_prove"
        , "noir_c1_bb_prove_time"
        , "noir_c2_bb_prove"
        , "noir_c2_bb_prove_time"
        , "noir_c1_bb_verify"
        , "noir_c1_bb_verify_time"
        , "noir_c2_bb_verify"
        , "noir_c2_bb_verify_time"
        , "noir_c1_ignored_error"
        , "noir_c2_ignored_error"
        , "cycle"
        , "explore_time"
        , "is_fixed"
        ])

    def _custom_to_str(self, value: bool | int | float | str | None) -> str:
        if value == None:
            return ""
        else:
            return str(value)

    def _custom_list_to_str(self, values: list[int] | list[str] | None) -> str:
        if values == None or len(values) == 0:
            return ""
        else:
            return "|".join([self._custom_to_str(e) for e in values])

    @classmethod
    def parse_str_or_none(cls, value: str) -> str | None:
        if value == "":
            return None
        else:
            return value
    
    @classmethod
    def parse_int_or_none(cls, value: str) -> int | None:
        if value == "":
            return None
        else:
            return int(value)
    
    @classmethod
    def parse_float_or_none(cls, value: str) -> float | None:
        if value == "":
            return None
        else:
            return float(value)
    
    @classmethod
    def parse_bool_or_none(cls, value: str) -> bool | None:
        if value == "":
            return None
        else:
            return value == "True"
    
    @classmethod
    def parse_int_list_or_none(cls, values: str) -> list[int] | None:
        if values == "":
            return None
        else:
            return [int(e) for e in values.split("|")]

    @classmethod
    def parse_str_list_or_none(cls, values: str) -> list[str] | None:
        if values == "":
            return None
        else:
            return values.split("|")
    
    @classmethod
    def parse_str_list(cls, values: str) -> list[str]:
        if values == "":
            return []
        else:
            return values.split("|")

    @classmethod
    def from_csv_line(cls, value: str) -> 'DataEntry':
        tool, \
        test_time, \
        seed, \
        curve, \
        oracle, \
        iteration, \
        error, \
        ir_generation_seed, \
        ir_generation_time, \
        ir_rewrite_seed, \
        ir_rewrite_time, \
        ir_rewrite_rules, \
        c1_node_size, \
        c1_assignments, \
        c1_assertions, \
        c1_assumptions, \
        c1_input_signals, \
        c1_output_signals, \
        c2_node_size, \
        c2_assignments, \
        c2_assertions, \
        c2_assumptions, \
        c2_input_signals, \
        c2_output_signals, \
        circom_c1_compilation, \
        circom_c1_compilation_time, \
        circom_c1_compilation_optimization, \
        circom_c2_compilation, \
        circom_c2_compilation_time, \
        circom_c2_compilation_optimization, \
        circom_c1_cpp_witness_preparation, \
        circom_c1_cpp_witness_preparation_time, \
        circom_c1_cpp_witness_generation, \
        circom_c1_cpp_witness_generation_time, \
        circom_c1_js_witness_generation, \
        circom_c1_js_witness_generation_time, \
        circom_c1_snarkjs_witness_check, \
        circom_c1_snarkjs_witness_check_time, \
        circom_c2_cpp_witness_preparation, \
        circom_c2_cpp_witness_preparation_time, \
        circom_c2_cpp_witness_generation, \
        circom_c2_cpp_witness_generation_time, \
        circom_c2_js_witness_generation, \
        circom_c2_js_witness_generation_time, \
        circom_c2_snarkjs_witness_check, \
        circom_c2_snarkjs_witness_check_time, \
        circom_proof_system, \
        circom_c1_zkey_generation, \
        circom_c1_zkey_generation_time, \
        circom_c1_proof_generation, \
        circom_c1_proof_generation_time, \
        circom_c2_zkey_generation, \
        circom_c2_zkey_generation_time, \
        circom_c2_proof_generation, \
        circom_c2_proof_generation_time, \
        circom_c1_vkey_generation, \
        circom_c1_vkey_generation_time, \
        circom_c1_verification, \
        circom_c1_verification_time, \
        circom_c2_vkey_generation, \
        circom_c2_vkey_generation_time, \
        circom_c2_verification, \
        circom_c2_verification_time, \
        circom_c1_ignored_error, \
        circom_c2_ignored_error, \
        corset_rust_check, \
        corset_rust_check_time, \
        corset_rust_compile, \
        corset_rust_compile_time, \
        corset_go_compile, \
        corset_go_compile_time, \
        corset_wizard_compile, \
        corset_wizard_compile_time, \
        corset_wizard_prove, \
        corset_wizard_prove_time, \
        corset_wizard_verify, \
        corset_wizard_verify_time, \
        corset_go_custom_cli, \
        corset_go_custom_cli_time, \
        corset_expansions, \
        corset_native, \
        corset_auto_constraints, \
        corset_guard_variable, \
        corset_timeout, \
        corset_out_of_memory, \
        corset_error_references, \
        corset_ignored_error, \
        gnark_c1_compile, \
        gnark_c1_compile_time, \
        gnark_c2_compile, \
        gnark_c2_compile_time, \
        gnark_c1_new_witness, \
        gnark_c1_new_witness_time, \
        gnark_c2_new_witness, \
        gnark_c2_new_witness_time, \
        gnark_c1_witness_solved, \
        gnark_c1_witness_solved_time, \
        gnark_c2_witness_solved, \
        gnark_c2_witness_solved_time, \
        gnark_c1_witness_write, \
        gnark_c1_witness_write_time, \
        gnark_c2_witness_write, \
        gnark_c2_witness_write_time, \
        gnark_c1_new_srs, \
        gnark_c2_new_srs, \
        gnark_c1_proof_setup, \
        gnark_c1_proof_setup_time, \
        gnark_c2_proof_setup, \
        gnark_c2_proof_setup_time, \
        gnark_c1_prove, \
        gnark_c1_prove_time, \
        gnark_c2_prove, \
        gnark_c2_prove_time, \
        gnark_c1_witness_public, \
        gnark_c1_witness_public_time, \
        gnark_c2_witness_public, \
        gnark_c2_witness_public_time, \
        gnark_c1_verify, \
        gnark_c1_verify_time, \
        gnark_c2_verify, \
        gnark_c2_verify_time, \
        gnark_cs_engine, \
        gnark_proof_system, \
        gnark_go_test_time, \
        gnark_go_timeout, \
        gnark_go_ignored_compiler_error, \
        noir_c1_execute, \
        noir_c1_execute_time, \
        noir_c2_execute, \
        noir_c2_execute_time, \
        noir_c1_vk, \
        noir_c1_vk_time, \
        noir_c2_vk, \
        noir_c2_vk_time, \
        noir_c1_bb_prove, \
        noir_c1_bb_prove_time, \
        noir_c2_bb_prove, \
        noir_c2_bb_prove_time, \
        noir_c1_bb_verify, \
        noir_c1_bb_verify_time, \
        noir_c2_bb_verify, \
        noir_c2_bb_verify_time, \
        noir_c1_ignored_error, \
        noir_c2_ignored_error, \
        cycle, \
        explore_time, \
        is_fixed = value.split(",")

        return DataEntry \
            ( tool = tool
            , test_time = float(test_time)
            , seed = float(seed)
            , curve = curve
            , oracle = oracle
            , iteration = int(iteration)
            , error = cls.parse_str_or_none(error)
            , ir_generation_seed = int(ir_generation_seed)
            , ir_generation_time = float(ir_generation_time)
            , ir_rewrite_seed = int(ir_rewrite_seed)
            , ir_rewrite_time = float(ir_rewrite_time)
            , ir_rewrite_rules = cls.parse_str_list(ir_rewrite_rules)
            , c1_node_size = int(c1_node_size)
            , c1_assignments = int(c1_assignments)
            , c1_assertions = int(c1_assertions)
            , c1_assumptions = int(c1_assumptions)
            , c1_input_signals = int(c1_input_signals)
            , c1_output_signals = int(c1_output_signals)
            , c2_node_size = int(c2_node_size)
            , c2_assignments = int(c2_assignments)
            , c2_assertions = int(c2_assertions)
            , c2_assumptions = int(c2_assumptions)
            , c2_input_signals = int(c2_input_signals)
            , c2_output_signals = int(c2_output_signals)
            , circom_c1_compilation = cls.parse_bool_or_none(circom_c1_compilation)
            , circom_c1_compilation_time = cls.parse_float_or_none(circom_c1_compilation_time)
            , circom_c1_compilation_optimization = circom_c1_compilation_optimization
            , circom_c2_compilation = cls.parse_bool_or_none(circom_c2_compilation)
            , circom_c2_compilation_time = cls.parse_float_or_none(circom_c2_compilation_time)
            , circom_c2_compilation_optimization = circom_c2_compilation_optimization
            , circom_c1_cpp_witness_preparation = cls.parse_bool_or_none(circom_c1_cpp_witness_preparation)
            , circom_c1_cpp_witness_preparation_time = cls.parse_float_or_none(circom_c1_cpp_witness_preparation_time)
            , circom_c1_cpp_witness_generation = cls.parse_bool_or_none(circom_c1_cpp_witness_generation)
            , circom_c1_cpp_witness_generation_time = cls.parse_float_or_none(circom_c1_cpp_witness_generation_time)
            , circom_c1_js_witness_generation = cls.parse_bool_or_none(circom_c1_js_witness_generation)
            , circom_c1_js_witness_generation_time = cls.parse_float_or_none(circom_c1_js_witness_generation_time)
            , circom_c1_snarkjs_witness_check = cls.parse_bool_or_none(circom_c1_snarkjs_witness_check)
            , circom_c1_snarkjs_witness_check_time = cls.parse_float_or_none(circom_c1_snarkjs_witness_check_time)
            , circom_c2_cpp_witness_preparation = cls.parse_bool_or_none(circom_c2_cpp_witness_preparation)
            , circom_c2_cpp_witness_preparation_time = cls.parse_float_or_none(circom_c2_cpp_witness_preparation_time)
            , circom_c2_cpp_witness_generation = cls.parse_bool_or_none(circom_c2_cpp_witness_generation)
            , circom_c2_cpp_witness_generation_time = cls.parse_float_or_none(circom_c2_cpp_witness_generation_time)
            , circom_c2_js_witness_generation = cls.parse_bool_or_none(circom_c2_js_witness_generation)
            , circom_c2_js_witness_generation_time = cls.parse_float_or_none(circom_c2_js_witness_generation_time)
            , circom_c2_snarkjs_witness_check = cls.parse_bool_or_none(circom_c2_snarkjs_witness_check)
            , circom_c2_snarkjs_witness_check_time = cls.parse_float_or_none(circom_c2_snarkjs_witness_check_time)
            , circom_proof_system = circom_proof_system
            , circom_c1_zkey_generation = cls.parse_bool_or_none(circom_c1_zkey_generation)
            , circom_c1_zkey_generation_time = cls.parse_float_or_none(circom_c1_zkey_generation_time)
            , circom_c1_proof_generation = cls.parse_bool_or_none(circom_c1_proof_generation)
            , circom_c1_proof_generation_time = cls.parse_float_or_none(circom_c1_proof_generation_time)
            , circom_c2_zkey_generation = cls.parse_bool_or_none(circom_c2_zkey_generation)
            , circom_c2_zkey_generation_time = cls.parse_float_or_none(circom_c2_zkey_generation_time)
            , circom_c2_proof_generation = cls.parse_bool_or_none(circom_c2_proof_generation)
            , circom_c2_proof_generation_time = cls.parse_float_or_none(circom_c2_proof_generation_time)
            , circom_c1_vkey_generation = cls.parse_bool_or_none(circom_c1_vkey_generation)
            , circom_c1_vkey_generation_time = cls.parse_float_or_none(circom_c1_vkey_generation_time)
            , circom_c1_verification = cls.parse_bool_or_none(circom_c1_verification)
            , circom_c1_verification_time = cls.parse_float_or_none(circom_c1_verification_time)
            , circom_c2_vkey_generation = cls.parse_bool_or_none(circom_c2_vkey_generation)
            , circom_c2_vkey_generation_time = cls.parse_float_or_none(circom_c2_vkey_generation_time)
            , circom_c2_verification = cls.parse_bool_or_none(circom_c2_verification)
            , circom_c2_verification_time = cls.parse_float_or_none(circom_c2_verification_time)
            , circom_c1_ignored_error = cls.parse_str_or_none(circom_c1_ignored_error)
            , circom_c2_ignored_error = cls.parse_str_or_none(circom_c2_ignored_error)
            , corset_rust_check = cls.parse_bool_or_none(corset_rust_check)
            , corset_rust_check_time = cls.parse_float_or_none(corset_rust_check_time)
            , corset_rust_compile = cls.parse_bool_or_none(corset_rust_compile)
            , corset_rust_compile_time = cls.parse_float_or_none(corset_rust_compile_time)
            , corset_go_compile = cls.parse_bool_or_none(corset_go_compile)
            , corset_go_compile_time = cls.parse_float_or_none(corset_go_compile_time)
            , corset_wizard_compile = cls.parse_bool_or_none(corset_wizard_compile)
            , corset_wizard_compile_time = cls.parse_float_or_none(corset_wizard_compile_time)
            , corset_wizard_prove = cls.parse_bool_or_none(corset_wizard_prove)
            , corset_wizard_prove_time = cls.parse_float_or_none(corset_wizard_prove_time)
            , corset_wizard_verify = cls.parse_bool_or_none(corset_wizard_verify)
            , corset_wizard_verify_time = cls.parse_float_or_none(corset_wizard_verify_time)
            , corset_go_custom_cli = cls.parse_bool_or_none(corset_go_custom_cli)
            , corset_go_custom_cli_time = cls.parse_float_or_none(corset_go_custom_cli_time)
            , corset_expansions = cls.parse_int_or_none(corset_expansions)
            , corset_native = cls.parse_bool_or_none(corset_native)
            , corset_auto_constraints = cls.parse_str_list_or_none(corset_auto_constraints)
            , corset_guard_variable = cls.parse_bool_or_none(corset_guard_variable)
            , corset_timeout = cls.parse_bool_or_none(corset_timeout)
            , corset_out_of_memory = cls.parse_bool_or_none(corset_out_of_memory)
            , corset_error_references = cls.parse_int_list_or_none(corset_error_references)
            , corset_ignored_error = cls.parse_str_or_none(corset_ignored_error)
            , gnark_c1_compile = cls.parse_bool_or_none(gnark_c1_compile)
            , gnark_c1_compile_time = cls.parse_float_or_none(gnark_c1_compile_time)
            , gnark_c2_compile = cls.parse_bool_or_none(gnark_c2_compile)
            , gnark_c2_compile_time = cls.parse_float_or_none(gnark_c2_compile_time)
            , gnark_c1_new_witness = cls.parse_bool_or_none(gnark_c1_new_witness)
            , gnark_c1_new_witness_time = cls.parse_float_or_none(gnark_c1_new_witness_time)
            , gnark_c2_new_witness = cls.parse_bool_or_none(gnark_c2_new_witness)
            , gnark_c2_new_witness_time = cls.parse_float_or_none(gnark_c2_new_witness_time)
            , gnark_c1_witness_solved = cls.parse_bool_or_none(gnark_c1_witness_solved)
            , gnark_c1_witness_solved_time = cls.parse_float_or_none(gnark_c1_witness_solved_time)
            , gnark_c2_witness_solved = cls.parse_bool_or_none(gnark_c2_witness_solved)
            , gnark_c2_witness_solved_time = cls.parse_float_or_none(gnark_c2_witness_solved_time)
            , gnark_c1_witness_write = cls.parse_bool_or_none(gnark_c1_witness_write)
            , gnark_c1_witness_write_time = cls.parse_float_or_none(gnark_c1_witness_write_time)
            , gnark_c2_witness_write = cls.parse_bool_or_none(gnark_c2_witness_write)
            , gnark_c2_witness_write_time = cls.parse_float_or_none(gnark_c2_witness_write_time)
            , gnark_c1_new_srs = cls.parse_bool_or_none(gnark_c1_new_srs)
            , gnark_c2_new_srs = cls.parse_bool_or_none(gnark_c2_new_srs)
            , gnark_c1_proof_setup = cls.parse_bool_or_none(gnark_c1_proof_setup)
            , gnark_c1_proof_setup_time = cls.parse_float_or_none(gnark_c1_proof_setup_time)
            , gnark_c2_proof_setup = cls.parse_bool_or_none(gnark_c2_proof_setup)
            , gnark_c2_proof_setup_time = cls.parse_float_or_none(gnark_c2_proof_setup_time)
            , gnark_c1_prove = cls.parse_bool_or_none(gnark_c1_prove)
            , gnark_c1_prove_time = cls.parse_float_or_none(gnark_c1_prove_time)
            , gnark_c2_prove = cls.parse_bool_or_none(gnark_c2_prove)
            , gnark_c2_prove_time = cls.parse_float_or_none(gnark_c2_prove_time)
            , gnark_c1_witness_public = cls.parse_bool_or_none(gnark_c1_witness_public)
            , gnark_c1_witness_public_time = cls.parse_float_or_none(gnark_c1_witness_public_time)
            , gnark_c2_witness_public = cls.parse_bool_or_none(gnark_c2_witness_public)
            , gnark_c2_witness_public_time = cls.parse_float_or_none(gnark_c2_witness_public_time)
            , gnark_c1_verify = cls.parse_bool_or_none(gnark_c1_verify)
            , gnark_c1_verify_time = cls.parse_float_or_none(gnark_c1_verify_time)
            , gnark_c2_verify = cls.parse_bool_or_none(gnark_c2_verify)
            , gnark_c2_verify_time = cls.parse_float_or_none(gnark_c2_verify_time)
            , gnark_cs_engine = cls.parse_str_or_none(gnark_cs_engine)
            , gnark_proof_system = cls.parse_str_or_none(gnark_proof_system)
            , gnark_go_test_time = cls.parse_float_or_none(gnark_go_test_time)
            , gnark_go_timeout = cls.parse_bool_or_none(gnark_go_timeout)
            , gnark_go_ignored_compiler_error = cls.parse_str_or_none(gnark_go_ignored_compiler_error)
            , noir_c1_execute = cls.parse_bool_or_none(noir_c1_execute)
            , noir_c1_execute_time = cls.parse_float_or_none(noir_c1_execute_time)
            , noir_c2_execute = cls.parse_bool_or_none(noir_c2_execute)
            , noir_c2_execute_time = cls.parse_float_or_none(noir_c2_execute_time)
            , noir_c1_vk = cls.parse_bool_or_none(noir_c1_vk)
            , noir_c1_vk_time = cls.parse_float_or_none(noir_c1_vk_time)
            , noir_c2_vk = cls.parse_bool_or_none(noir_c2_vk)
            , noir_c2_vk_time = cls.parse_float_or_none(noir_c2_vk_time)
            , noir_c1_bb_prove = cls.parse_bool_or_none(noir_c1_bb_prove)
            , noir_c1_bb_prove_time = cls.parse_float_or_none(noir_c1_bb_prove_time)
            , noir_c2_bb_prove = cls.parse_bool_or_none(noir_c2_bb_prove)
            , noir_c2_bb_prove_time = cls.parse_float_or_none(noir_c2_bb_prove_time)
            , noir_c1_bb_verify = cls.parse_bool_or_none(noir_c1_bb_verify)
            , noir_c1_bb_verify_time = cls.parse_float_or_none(noir_c1_bb_verify_time)
            , noir_c2_bb_verify = cls.parse_bool_or_none(noir_c2_bb_verify)
            , noir_c2_bb_verify_time = cls.parse_float_or_none(noir_c2_bb_verify_time)
            , noir_c1_ignored_error = cls.parse_str_or_none(noir_c1_ignored_error)
            , noir_c2_ignored_error = cls.parse_str_or_none(noir_c2_ignored_error)
            , cycle = cls.parse_int_or_none(cycle)
            , explore_time = cls.parse_float_or_none(explore_time)
            , is_fixed = cls.parse_bool_or_none(is_fixed)
            )

@dataclass
class TestResult():
    entries : list[DataEntry] = field(default_factory=list)

    def is_error(self) -> bool:
        return any([e.is_error() for e in self.entries])

    def filter_errors(self) -> list[DataEntry]:
        return [e for e in self.entries if e.is_error()]

    def has_entries(self) -> bool:
        return len(self.entries) > 0

    def csv_lines(self) -> list[str]:
        return [e.csv_line() for e in self.entries]

    def csv_error_lines(self) -> list[str]:
        return [e.csv_line() for e in self.filter_errors()]

    @classmethod
    def csv_header(cls) -> str:
        return DataEntry.csv_header()