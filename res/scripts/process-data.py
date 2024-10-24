import sys
from pathlib import Path
from typing import Any
import statistics

# manual set the source root to access data
if not __package__:
    package_root_path = Path(__file__).parent.parent.parent.absolute()
    package_source_path = (package_root_path / "src").absolute().as_posix()
    sys.path.insert(0, package_source_path)

from experiment.data import DataEntry

#
# Hardcoded experiment values
#

BUG_LIST = [
    # circom
      "operator ~ (1/2)"
    , "operator ~ (2/2)"
    , "inconsistent prime"
    , "wrong '~' evaluation on small curves"
    # corset
    , "expansion and native flags"
    , "wrong constraint for expansion"
    , "reworked ifs"
    , "wrong evaluation of normalized loobean"
    # gnark
    , "api.Or"
    , "api.AssertIsLessOrEqual"
    , "min 1 bit for binary decompose"
    , "unchecked casted branch"
    # noir
    , "wrong assert"
    , "bb prover error in MemBn254CrsFactory"
    , "stack overflow for lt-expressions"
    ]

REPETITIONS = 10
TIME_LIMIT = 60 * 60 * 24 + 1 # 1 sec tolerance

#
# Helper Functions
#

def tabulate(rows: list[list[Any]], sep=",") -> str:
    assert len(rows) > 0, "unable to print empty table"

    columns = len(rows[0])
    max_column_sizes: list[int] = []

    for column in range(columns):
        tmp_max = 0
        for row in rows:
            tmp_max = max(tmp_max, len(str(row[column])))
        max_column_sizes.append(tmp_max)

    result = ""
    for row_idx, row in enumerate(rows):
        for col_idx, value in enumerate(row):
            value_str = str(value)
            postfix = ""

            if (col_idx + 1) != len(row):
                column_size = max_column_sizes[col_idx]
                size = len(value_str)
                size_diff = column_size - size
                padding = " " * size_diff
                postfix = f"{padding} {sep} "

            result += f"{value_str}{postfix}"

        if (row_idx + 1) != len(rows):
            result += "\n"

    return result

def bug_to_tool(bug: str) -> str:
    # NOTE: This will AND SHOULD fail if the bug is not in the dictionary!
    return {
    # circom
      "operator ~ (1/2)"                     : "circom"
    , "operator ~ (2/2)"                     : "circom"
    , "inconsistent prime"                   : "circom"
    , "wrong '~' evaluation on small curves" : "circom"
    # corset
    , "expansion and native flags"             : "corset"
    , "wrong constraint for expansion"         : "corset"
    , "reworked ifs"                           : "corset"
    , "wrong evaluation of normalized loobean" : "corset"
    # gnark
    , "api.Or"                         : "gnark"
    , "api.AssertIsLessOrEqual"        : "gnark"
    , "min 1 bit for binary decompose" : "gnark"
    , "unchecked casted branch"        : "gnark"
    # noir
    , "wrong assert"                          : "noir"
    , "bb prover error in MemBn254CrsFactory" : "noir"
    , "stack overflow for lt-expressions"     : "noir"
    }[bug]

def collect_csv_data(csv_file: Path) -> list[DataEntry]:
    """
    Parses a CSV file and returns the result as DataEntry list
    """
    if not csv_file.is_file():
        raise RuntimeError(f"unable to find {csv_file}")

    # extract lines from csv file
    lines : list[str] = []
    with open(csv_file, "r") as file_handle:
        lines = file_handle.readlines()

    # prepare the result data
    entries : list[DataEntry] = []
    for line in lines[1:]: # skip csv header line
        stripped_line = line.rstrip() # remove trailing newline
        entries.append(DataEntry.from_csv_line(stripped_line))

    return entries

def remove_timeout_data(entries: list[DataEntry], timeout: float) -> list[DataEntry]:
    """
    Remove all entries with a higher explore time than the timeout limit.
    """
    return [e for e in entries if e.explore_time != None and e.explore_time <= timeout]

def patch_circom_cached_exec_times(entries: list[DataEntry]) -> list[DataEntry]:
    """
    Sets the time for stage entries to 0 if they were cached in previous iteration.
    Cached entries are for example circuit compilation or witness compilation,
    that are done only once.

    NOTE: This function assumes the entries to be in proper order, i.e., iterations are
          ascending and in sequence.
    """

    outer_idx = 0
    inner_idx = 0
    while outer_idx < len(entries):
        entry1 = entries[outer_idx]
        inner_idx = outer_idx + 1
        while inner_idx < len(entries):
            entry2 = entries[inner_idx]

            # check if entry2 is an iteration of entry1
            if entry1.seed == entry2.seed and \
               entry1.iteration < entry2.iteration:

                if entry1.circom_c1_compilation_time != None and \
                   entry2.circom_c1_compilation_time != None:
                    entry2.circom_c1_compilation_time = 0
                if entry1.circom_c2_compilation_time != None and \
                   entry2.circom_c2_compilation_time != None:
                    entry2.circom_c2_compilation_time = 0

                if entry1.circom_c1_cpp_witness_preparation_time != None and \
                   entry2.circom_c1_cpp_witness_preparation_time != None:
                    entry2.circom_c1_cpp_witness_preparation_time = 0
                if entry1.circom_c2_cpp_witness_preparation_time != None and \
                   entry2.circom_c2_cpp_witness_preparation_time != None:
                    entry2.circom_c2_cpp_witness_preparation_time = 0

                if entry1.circom_c1_zkey_generation_time != None and \
                   entry2.circom_c1_zkey_generation_time != None:
                    entry2.circom_c1_zkey_generation_time = 0
                if entry1.circom_c2_zkey_generation_time != None and \
                   entry2.circom_c2_zkey_generation_time != None:
                    entry2.circom_c2_zkey_generation_time = 0
                if entry1.circom_c1_vkey_generation_time != None and \
                   entry2.circom_c1_vkey_generation_time != None:
                    entry2.circom_c1_vkey_generation_time = 0
                if entry1.circom_c2_vkey_generation_time != None and \
                   entry2.circom_c2_vkey_generation_time != None:
                    entry2.circom_c2_vkey_generation_time = 0

                inner_idx += 1 # look at next entry if it is also a iteration of the current seed
            else:
                break # no more iterations available

        outer_idx += 1

    return entries

def filter_first_iterations(entries: list[DataEntry]):
    """
    Returns only the first iteration of a test case. This is helpful if we want to
    get the overall test time or the circuit structure.
    """
    return [e for e in entries if e.iteration == 0]

def from_s_to_hms(seconds_raw: float) -> str:
    """
    Returns seconds in a (rounded) hms format.
    If the seconds would result in 0, a "<1s" is returned.
    """
    seconds_rounded = int(round(seconds_raw))
    hours   = seconds_rounded // 3600
    minutes = (seconds_rounded % 3600) // 60
    seconds = seconds_rounded % 60

    result = ""
    if hours > 0:
        result += f"{hours}h"
    if minutes > 0:
        result += f"{minutes}m"
    if seconds > 0:
        result += f"{seconds}s"

    if result == "": # nothing was > 0
        result = "0s" if seconds_raw == 0 else "<1s"

    return result

def update_count_lookup(lookup: dict[str, int], values: list[str]):
    for value in values:
        if not value in lookup:
            lookup[value] = 0
        lookup[value] += 1

def sorted_by_value(x: dict[Any, Any], reverse: bool = False) -> dict[Any, Any]:
    return {k: v for k, v in sorted(x.items(), key=lambda item: item[1], reverse=reverse)}

def compute_min_med_max(data: list[int] | list[float]) -> tuple[float, float, float]:
    min_data = round(min(data), ndigits=2)
    max_data = round(max(data), ndigits=2)
    med_data = round(statistics.median(data), ndigits=2)
    return min_data, med_data, max_data

def init_circuit_structure_lookups() -> dict[str, list[int]]:
    lookup : dict[str, list[int]] = dict()
    lookup["assertions"] = []
    lookup["assignments"] = []
    lookup["assumptions"] = []
    lookup["input_signals"] = []
    lookup["output_signals"] = []
    lookup["node_size"] = []
    return lookup

def update_circuit_structure_lookups(c1_lookup: dict[str, list[int]], c2_lookup: dict[str, list[int]], entry: DataEntry):
    c1_lookup["assertions"].append(entry.c1_assertions)
    c1_lookup["assignments"].append(entry.c1_assignments)
    c1_lookup["assumptions"].append(entry.c1_assumptions)
    c1_lookup["input_signals"].append(entry.c1_input_signals)
    c1_lookup["output_signals"].append(entry.c1_output_signals)
    c1_lookup["node_size"].append(entry.c1_node_size)
    c2_lookup["assertions"].append(entry.c2_assertions)
    c2_lookup["assignments"].append(entry.c2_assignments)
    c2_lookup["assumptions"].append(entry.c2_assumptions)
    c2_lookup["input_signals"].append(entry.c2_input_signals)
    c2_lookup["output_signals"].append(entry.c2_output_signals)
    c2_lookup["node_size"].append(entry.c2_node_size)

def get_circuit_structures(entries: list[DataEntry]) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    c1_info : dict[str, list[int]] = init_circuit_structure_lookups()
    c2_info : dict[str, list[int]] = init_circuit_structure_lookups()
    for entry in entries:
        update_circuit_structure_lookups(c1_info, c2_info, entry)
    return c1_info, c2_info

def init_pipeline_lookup_for_tool(tool: str) -> dict[str, tuple[int, int, list[float]]]:
    result : dict[str, tuple[int, int, list[float]]] = {}
    match tool:
        case "circom":
            result["compile"] = 0, 0, []
            result["witness"] = 0, 0, []
            result["prove"] = 0, 0, []
            result["verify"] = 0, 0, []
        case "corset":
            result["check"] = 0, 0, []
            result["compile"] = 0, 0, []
            result["witness"] = 0, 0, []
            result["prove"] = 0, 0, []
            result["verify"] = 0, 0, []
        case "gnark":
            result["compile"] = 0, 0, []
            result["witness"] = 0, 0, []
            result["prove"] = 0, 0, []
            result["verify"] = 0, 0, []
        case "noir":
            result["execute"] = 0, 0, []
            result["prove"] = 0, 0, []
            result["verify"] = 0, 0, []
        case _:
            raise RuntimeError(f"unsupported tool '{tool}'")
    return result

def update_pipeline_lookup(lookup: dict[str, tuple[int, int, list[float]]], value: dict[str, tuple[bool, float]]):
    for key in value:
        assert key in lookup, f"pipeline key '{key}' not in lookup" # should be there by init
        acc_suc, acc_exec, time_list = lookup[key]
        status, time = value[key]
        success_offset = 1 if status else 0
        time_list.append(time)
        lookup[key] = acc_suc + success_offset, acc_exec + 1, time_list

def generate_pipeline_stages(data: DataEntry) -> tuple[dict[str, tuple[bool, float]], dict[str, tuple[bool, float]]]:

    # We only look ate following stages:
    #   * check          (only check is available, i.e. corset)
    #   * execute        (combination of compile, check, witness generation, i.e. noir's execution)
    #   * compile        (compilation of the constraint system)
    #   * witness        (generation of a witness file)
    #   * prove          (generation of a proof)
    #   * verify         (verifying the generated proof)
    #   * prove & verify (prove and verification are combined)
    # For each stages we track status and execution time for c1 and c2.

    def combine_status(s1: bool | None, s2: bool | None) -> bool | None:
        if s1 == None:
            return s2
        if s2 == None:
            return s1
        return s1 and s2

    c1_stages : dict[str, tuple[bool, float]] = {}
    c2_stages : dict[str, tuple[bool, float]] = {}

    match data.tool:
        case "circom":

            #
            # Compilation
            #

            if data.circom_c1_compilation != None and data.circom_c1_compilation_time != None:
                c1_stages["compile"] = data.circom_c1_compilation, data.circom_c1_compilation_time
            else:
                assert data.circom_c1_compilation == None and data.circom_c1_compilation_time == None

            if data.circom_c2_compilation != None and data.circom_c2_compilation_time != None:
                c2_stages["compile"] = data.circom_c2_compilation, data.circom_c2_compilation_time
            else:
                assert data.circom_c2_compilation == None and data.circom_c2_compilation_time == None

            #
            # Witness Generation
            #

            c1_acc_witness_time : float = 0
            c1_acc_witness_status : bool | None = None

            if data.circom_c1_cpp_witness_preparation != None and data.circom_c1_cpp_witness_preparation_time != None:
                c1_acc_witness_time += data.circom_c1_cpp_witness_preparation_time
                c1_acc_witness_status = combine_status(c1_acc_witness_status, data.circom_c1_cpp_witness_preparation)
            else:
                assert data.circom_c1_cpp_witness_preparation == None and data.circom_c1_cpp_witness_preparation_time == None

            if data.circom_c1_cpp_witness_generation != None and data.circom_c1_cpp_witness_generation_time != None:
                c1_acc_witness_time += data.circom_c1_cpp_witness_generation_time
                c1_acc_witness_status = combine_status(c1_acc_witness_status, data.circom_c1_cpp_witness_generation)
            else:
                assert data.circom_c1_cpp_witness_generation == None and data.circom_c1_cpp_witness_generation_time == None

            if data.circom_c1_js_witness_generation != None and data.circom_c1_js_witness_generation_time != None:
                c1_acc_witness_time += data.circom_c1_js_witness_generation_time
                c1_acc_witness_status = combine_status(c1_acc_witness_status, data.circom_c1_js_witness_generation)
            else:
                assert data.circom_c1_js_witness_generation == None and data.circom_c1_js_witness_generation_time == None

            if data.circom_c1_snarkjs_witness_check != None and data.circom_c1_snarkjs_witness_check_time != None:
                c1_acc_witness_time += data.circom_c1_snarkjs_witness_check_time
                c1_acc_witness_status = combine_status(c1_acc_witness_status, data.circom_c1_snarkjs_witness_check)
            else:
                assert data.circom_c1_snarkjs_witness_check == None and data.circom_c1_snarkjs_witness_check_time == None

            if c1_acc_witness_status != None:
                c1_stages["witness"] = c1_acc_witness_status, c1_acc_witness_time

            c2_acc_witness_time : float = 0
            c2_acc_witness_status : bool | None = None

            if data.circom_c2_cpp_witness_preparation != None and data.circom_c2_cpp_witness_preparation_time != None:
                c2_acc_witness_time += data.circom_c2_cpp_witness_preparation_time
                c2_acc_witness_status = combine_status(c2_acc_witness_status, data.circom_c2_cpp_witness_preparation)
            else:
                assert data.circom_c2_cpp_witness_preparation == None and data.circom_c2_cpp_witness_preparation_time == None

            if data.circom_c2_cpp_witness_generation != None and data.circom_c2_cpp_witness_generation_time != None:
                c2_acc_witness_time += data.circom_c2_cpp_witness_generation_time
                c2_acc_witness_status = combine_status(c2_acc_witness_status, data.circom_c2_cpp_witness_generation)
            else:
                assert data.circom_c2_cpp_witness_generation == None and data.circom_c2_cpp_witness_generation_time == None

            if data.circom_c2_js_witness_generation != None and data.circom_c2_js_witness_generation_time != None:
                c2_acc_witness_time += data.circom_c2_js_witness_generation_time
                c2_acc_witness_status = combine_status(c2_acc_witness_status, data.circom_c2_js_witness_generation)
            else:
                assert data.circom_c2_js_witness_generation == None and data.circom_c2_js_witness_generation_time == None

            if data.circom_c2_snarkjs_witness_check != None and data.circom_c2_snarkjs_witness_check_time != None:
                c2_acc_witness_time += data.circom_c2_snarkjs_witness_check_time
                c2_acc_witness_status = combine_status(c2_acc_witness_status, data.circom_c2_snarkjs_witness_check)
            else:
                assert data.circom_c2_snarkjs_witness_check == None and data.circom_c2_snarkjs_witness_check_time == None

            if c2_acc_witness_status != None:
                c2_stages["witness"] = c2_acc_witness_status, c2_acc_witness_time

            #
            # Proof Generation
            #

            c1_acc_prove_time : float = 0
            c1_acc_prove_status : bool | None = None

            if data.circom_c1_zkey_generation != None and data.circom_c1_zkey_generation_time != None:
                c1_acc_prove_time += data.circom_c1_zkey_generation_time
                c1_acc_prove_status = combine_status(c1_acc_prove_status, data.circom_c1_zkey_generation)
            else:
                assert data.circom_c1_zkey_generation == None and data.circom_c1_zkey_generation_time == None

            if data.circom_c1_proof_generation != None and data.circom_c1_proof_generation_time != None:
                c1_acc_prove_time += data.circom_c1_proof_generation_time
                c1_acc_prove_status = combine_status(c1_acc_prove_status, data.circom_c1_proof_generation)
            else:
                assert data.circom_c1_proof_generation == None and data.circom_c1_proof_generation_time == None

            if c1_acc_prove_status != None:
                c1_stages["prove"] = c1_acc_prove_status, c1_acc_prove_time

            c2_acc_prove_time : float = 0
            c2_acc_prove_status : bool | None = None

            if data.circom_c2_zkey_generation != None and data.circom_c2_zkey_generation_time != None:
                c2_acc_prove_time += data.circom_c2_zkey_generation_time
                c2_acc_prove_status = combine_status(c2_acc_prove_status, data.circom_c2_zkey_generation)
            else:
                assert data.circom_c2_zkey_generation == None and data.circom_c2_zkey_generation_time == None

            if data.circom_c2_proof_generation != None and data.circom_c2_proof_generation_time != None:
                c2_acc_prove_time += data.circom_c2_proof_generation_time
                c2_acc_prove_status = combine_status(c2_acc_prove_status, data.circom_c2_proof_generation)
            else:
                assert data.circom_c2_proof_generation == None and data.circom_c2_proof_generation_time == None

            if c2_acc_prove_status != None:
                c2_stages["prove"] = c2_acc_prove_status, c2_acc_prove_time

            #
            # Verification
            #

            c1_acc_verify_time : float = 0
            c1_acc_verify_status : bool | None = None

            if data.circom_c1_vkey_generation != None and data.circom_c1_vkey_generation_time != None:
                c1_acc_verify_time += data.circom_c1_vkey_generation_time
                c1_acc_verify_status = combine_status(c1_acc_verify_status, data.circom_c1_vkey_generation)
            else:
                assert data.circom_c1_vkey_generation == None and data.circom_c1_vkey_generation_time == None

            if data.circom_c1_verification != None and data.circom_c1_verification_time != None:
                c1_acc_verify_time += data.circom_c1_verification_time
                c1_acc_verify_status = combine_status(c1_acc_verify_status, data.circom_c1_verification)
            else:
                assert data.circom_c1_verification == None and data.circom_c1_verification_time == None

            if c1_acc_verify_status != None:
                c1_stages["verify"] = c1_acc_verify_status, c1_acc_verify_time

            c2_acc_verify_time : float = 0
            c2_acc_verify_status : bool | None = None

            if data.circom_c2_vkey_generation != None and data.circom_c2_vkey_generation_time != None:
                c2_acc_verify_time += data.circom_c2_vkey_generation_time
                c2_acc_verify_status = combine_status(c2_acc_verify_status, data.circom_c2_vkey_generation)
            else:
                assert data.circom_c2_vkey_generation == None and data.circom_c2_vkey_generation_time == None

            if data.circom_c2_verification != None and data.circom_c2_verification_time != None:
                c2_acc_verify_time += data.circom_c2_verification_time
                c2_acc_verify_status = combine_status(c2_acc_verify_status, data.circom_c2_verification)
            else:
                assert data.circom_c2_verification == None and data.circom_c2_verification_time == None

            if c2_acc_verify_status != None:
                c2_stages["verify"] = c2_acc_verify_status, c2_acc_verify_time

        case "corset":

            #
            # Check
            #

            if data.corset_rust_check != None and data.corset_rust_check_time != None:
                c1_stages["check"] = data.corset_rust_check, data.corset_rust_check_time
                c2_stages["check"] = data.corset_rust_check, data.corset_rust_check_time
            else:
                assert data.corset_rust_check == None and data.corset_rust_check_time == None

            #
            # Compile
            #

            corset_compile_time : float = 0
            corset_compile_status : bool | None = None

            if data.corset_rust_compile != None and data.corset_rust_compile_time != None:
                corset_compile_time += data.corset_rust_compile_time
                corset_compile_status = combine_status(corset_compile_status, data.corset_rust_compile)
            else:
                assert data.corset_rust_compile == None and data.corset_rust_compile_time == None

            if data.corset_go_compile != None and data.corset_go_compile_time != None:
                corset_compile_time += data.corset_go_compile_time
                corset_compile_status = combine_status(corset_compile_status, data.corset_go_compile)
            else:
                assert data.corset_go_compile == None and data.corset_go_compile_time == None

            if corset_compile_status != None:
                c1_stages["compile"] = corset_compile_status, corset_compile_time
                c2_stages["compile"] = corset_compile_status, corset_compile_time

            #
            # Witness Generation
            #

            if data.corset_wizard_compile != None and data.corset_wizard_compile_time:
                c1_stages["witness"] = data.corset_wizard_compile, data.corset_wizard_compile_time
                c2_stages["witness"] = data.corset_wizard_compile, data.corset_wizard_compile_time
            else:
                assert data.corset_wizard_compile == None and data.corset_wizard_compile_time == None

            #
            # Prove
            #

            if data.corset_wizard_prove != None and data.corset_wizard_prove_time:
                c1_stages["prove"] = data.corset_wizard_prove, data.corset_wizard_prove_time
                c2_stages["prove"] = data.corset_wizard_prove, data.corset_wizard_prove_time
            else:
                assert data.corset_wizard_prove == None and data.corset_wizard_prove_time == None

            #
            # Verify
            #

            if data.corset_wizard_verify != None and data.corset_wizard_verify_time:
                c1_stages["verify"] = data.corset_wizard_verify, data.corset_wizard_verify_time
                c2_stages["verify"] = data.corset_wizard_verify, data.corset_wizard_verify_time
            else:
                assert data.corset_wizard_verify == None and data.corset_wizard_verify_time == None

        case "gnark":

            #
            # Compilation
            #

            if data.gnark_c1_compile != None and data.gnark_c1_compile_time != None:
                c1_stages["compile"] = data.gnark_c1_compile, data.gnark_c1_compile_time
            else:
                assert data.gnark_c1_compile == None and data.gnark_c1_compile_time == None

            if data.gnark_c2_compile != None and data.gnark_c2_compile_time != None:
                c2_stages["compile"] = data.gnark_c2_compile, data.gnark_c2_compile_time
            else:
                assert data.gnark_c2_compile == None and data.gnark_c2_compile_time == None

            #
            # Witness Generation
            #

            c1_acc_witness_time : float = 0
            c1_acc_witness_status : bool | None = None

            if data.gnark_c1_new_witness != None and data.gnark_c1_new_witness_time != None:
                c1_acc_witness_time += data.gnark_c1_new_witness_time
                c1_acc_witness_status = combine_status(c1_acc_witness_status, data.gnark_c1_new_witness)
            else:
                assert data.gnark_c1_new_witness == None and data.gnark_c1_new_witness_time == None

            if data.gnark_c1_witness_solved != None and data.gnark_c1_witness_solved_time != None:
                c1_acc_witness_time += data.gnark_c1_witness_solved_time
                c1_acc_witness_status = combine_status(c1_acc_witness_status, data.gnark_c1_witness_solved)
            else:
                assert data.gnark_c1_witness_solved == None and data.gnark_c1_witness_solved_time == None

            if data.gnark_c1_witness_write != None and data.gnark_c1_witness_write_time != None:
                c1_acc_witness_time += data.gnark_c1_witness_write_time
                c1_acc_witness_status = combine_status(c1_acc_witness_status, data.gnark_c1_witness_write)
            else:
                assert data.gnark_c1_witness_write == None and data.gnark_c1_witness_write_time == None

            if c1_acc_witness_status != None:
                c1_stages["witness"] = c1_acc_witness_status, c1_acc_witness_time

            c2_acc_witness_time : float = 0
            c2_acc_witness_status : bool | None = None

            if data.gnark_c2_new_witness != None and data.gnark_c2_new_witness_time != None:
                c2_acc_witness_time += data.gnark_c2_new_witness_time
                c2_acc_witness_status = combine_status(c2_acc_witness_status, data.gnark_c2_new_witness)
            else:
                assert data.gnark_c2_new_witness == None and data.gnark_c2_new_witness_time == None

            if data.gnark_c2_witness_solved != None and data.gnark_c2_witness_solved_time != None:
                c2_acc_witness_time += data.gnark_c2_witness_solved_time
                c2_acc_witness_status = combine_status(c2_acc_witness_status, data.gnark_c2_witness_solved)
            else:
                assert data.gnark_c2_witness_solved == None and data.gnark_c2_witness_solved_time == None

            if data.gnark_c2_witness_write != None and data.gnark_c2_witness_write_time != None:
                c2_acc_witness_time += data.gnark_c2_witness_write_time
                c2_acc_witness_status = combine_status(c2_acc_witness_status, data.gnark_c2_witness_write)
            else:
                assert data.gnark_c2_witness_write == None and data.gnark_c2_witness_write_time == None

            if c2_acc_witness_status != None:
                c2_stages["witness"] = c2_acc_witness_status, c2_acc_witness_time

            #
            # Proof Generation
            #

            c1_acc_prove_time : float = 0
            c1_acc_prove_status : bool | None = None

            if data.gnark_c1_proof_setup != None and data.gnark_c1_proof_setup_time != None:
                c1_acc_prove_time += data.gnark_c1_proof_setup_time
                c1_acc_prove_status = combine_status(c1_acc_prove_status, data.gnark_c1_proof_setup)
            else:
                assert data.gnark_c1_proof_setup == None and data.gnark_c1_proof_setup_time == None

            if data.gnark_c1_new_srs != None:
                c1_acc_prove_status = combine_status(c1_acc_prove_status, data.gnark_c1_new_srs)

            if data.gnark_c1_prove != None and data.gnark_c1_prove_time != None:
                c1_acc_prove_time += data.gnark_c1_prove_time
                c1_acc_prove_status = combine_status(c1_acc_prove_status, data.gnark_c1_prove)
            else:
                assert data.gnark_c1_prove == None and data.gnark_c1_prove_time == None

            if c1_acc_prove_status != None:
                c1_stages["prove"] = c1_acc_prove_status, c1_acc_prove_time

            c2_acc_prove_time : float = 0
            c2_acc_prove_status : bool | None = None

            if data.gnark_c2_proof_setup != None and data.gnark_c2_proof_setup_time != None:
                c2_acc_prove_time += data.gnark_c2_proof_setup_time
                c2_acc_prove_status = combine_status(c2_acc_prove_status, data.gnark_c2_proof_setup)
            else:
                assert data.gnark_c2_proof_setup == None and data.gnark_c2_proof_setup_time == None

            if data.gnark_c2_new_srs != None:
                c2_acc_prove_status = combine_status(c2_acc_prove_status, data.gnark_c2_new_srs)

            if data.gnark_c2_prove != None and data.gnark_c2_prove_time != None:
                c2_acc_prove_time += data.gnark_c2_prove_time
                c2_acc_prove_status = combine_status(c2_acc_prove_status, data.gnark_c2_prove)
            else:
                assert data.gnark_c2_prove == None and data.gnark_c2_prove_time == None

            if c2_acc_prove_status != None:
                c2_stages["prove"] = c2_acc_prove_status, c2_acc_prove_time

            #
            # Verification
            #

            c1_acc_verify_time : float = 0
            c1_acc_verify_status : bool | None = None

            if data.gnark_c1_witness_public != None and data.gnark_c1_witness_public_time != None:
                c1_acc_verify_time += data.gnark_c1_witness_public_time
                c1_acc_verify_status = combine_status(c1_acc_verify_status, data.gnark_c1_witness_public)
            else:
                assert data.gnark_c1_witness_public == None and data.gnark_c1_witness_public_time == None

            if data.gnark_c1_verify != None and data.gnark_c1_verify_time != None:
                c1_acc_verify_time += data.gnark_c1_verify_time
                c1_acc_verify_status = combine_status(c1_acc_verify_status, data.gnark_c1_verify)
            else:
                assert data.gnark_c1_verify == None and data.gnark_c1_verify_time == None

            if c1_acc_verify_status != None:
                c1_stages["verify"] = c1_acc_verify_status, c1_acc_verify_time

            c2_acc_verify_time : float = 0
            c2_acc_verify_status : bool | None = None

            if data.gnark_c2_witness_public != None and data.gnark_c2_witness_public_time != None:
                c2_acc_verify_time += data.gnark_c2_witness_public_time
                c2_acc_verify_status = combine_status(c2_acc_verify_status, data.gnark_c2_witness_public)
            else:
                assert data.gnark_c2_witness_public == None and data.gnark_c2_witness_public_time == None

            if data.gnark_c2_verify != None and data.gnark_c2_verify_time != None:
                c2_acc_verify_time += data.gnark_c2_verify_time
                c2_acc_verify_status = combine_status(c2_acc_verify_status, data.gnark_c2_verify)
            else:
                assert data.gnark_c2_verify == None and data.gnark_c2_verify_time == None

            if c2_acc_verify_status != None:
                c2_stages["verify"] = c2_acc_verify_status, c2_acc_verify_time

        case "noir":

            #
            # Execution
            #

            if data.noir_c1_execute != None and data.noir_c1_execute_time != None:
                c1_stages["execute"] = data.noir_c1_execute, data.noir_c1_execute_time

            if data.noir_c2_execute != None and data.noir_c2_execute_time != None:
                c2_stages["execute"] = data.noir_c2_execute, data.noir_c2_execute_time

            #
            # Proof Generation
            #

            if data.noir_c1_bb_prove != None and data.noir_c1_bb_prove_time != None:
                c1_stages["prove"] = data.noir_c1_bb_prove, data.noir_c1_bb_prove_time

            if data.noir_c2_bb_prove != None and data.noir_c2_bb_prove_time != None:
                c2_stages["prove"] = data.noir_c2_bb_prove, data.noir_c2_bb_prove_time

            #
            # Verification
            #

            c1_acc_verify_time : float = 0
            c1_acc_verify_status : bool | None = None

            if data.noir_c1_vk != None and data.noir_c1_vk_time != None:
                c1_acc_verify_time += data.noir_c1_vk_time
                c1_acc_verify_status = combine_status(c1_acc_verify_status, data.noir_c1_vk)
            else:
                assert data.noir_c1_vk == None and data.noir_c1_vk_time == None

            if data.noir_c1_bb_verify != None and data.noir_c1_bb_verify_time != None:
                c1_acc_verify_time += data.noir_c1_bb_verify_time
                c1_acc_verify_status = combine_status(c1_acc_verify_status, data.noir_c1_bb_verify)
            else:
                assert data.noir_c1_bb_verify == None and data.noir_c1_bb_verify_time == None

            if c1_acc_verify_status != None:
                c1_stages["verify"] = c1_acc_verify_status, c1_acc_verify_time

            c2_acc_verify_time : float = 0
            c2_acc_verify_status : bool | None = None

            if data.noir_c2_vk != None and data.noir_c2_vk_time != None:
                c2_acc_verify_time += data.noir_c2_vk_time
                c2_acc_verify_status = combine_status(c2_acc_verify_status, data.noir_c2_vk)
            else:
                assert data.noir_c2_vk == None and data.noir_c2_vk_time == None

            if data.noir_c2_bb_verify != None and data.noir_c2_bb_verify_time != None:
                c2_acc_verify_time += data.noir_c2_bb_verify_time
                c2_acc_verify_status = combine_status(c2_acc_verify_status, data.noir_c2_bb_verify)
            else:
                assert data.noir_c2_bb_verify == None and data.noir_c2_bb_verify_time == None

            if c2_acc_verify_status != None:
                c2_stages["verify"] = c2_acc_verify_status, c2_acc_verify_time

    return c1_stages, c2_stages

def has_duplicates(entries: list[DataEntry]) -> bool:
    original_length = len(entries)
    unique_id_set_length = len({e.unique_id() for e in entries})
    return original_length == unique_id_set_length

def flat_first_iterations_from_repetitions(data: dict[int, list[DataEntry]]) -> list[DataEntry]:
    result : list[DataEntry] = []
    for rep_key in data:
        result += filter_first_iterations(data[rep_key])
    return result

def flat_first_iterations_from_experiments(data: dict[str, dict[int, list[DataEntry]]]) -> dict[str, list[DataEntry]]:
    result : dict[str, list[DataEntry]] = {}
    for bug_key in data:
        tool_name = bug_to_tool(bug_key)
        if not tool_name in result:
            result[tool_name] = []
        result[tool_name] += flat_first_iterations_from_repetitions(data[bug_key])
    return result

def flat_iterations_from_repetitions(data: dict[int, list[DataEntry]]) -> list[DataEntry]:
    result : list[DataEntry] = []
    for rep_key in data:
        result += data[rep_key]
    return result

def flat_iterations_from_experiments(data: dict[str, dict[int, list[DataEntry]]]) -> dict[str, list[DataEntry]]:
    result : dict[str, list[DataEntry]] = {}
    for bug_key in data:
        tool_name = bug_to_tool(bug_key)
        if not tool_name in result:
            result[tool_name] = []
        result[tool_name] += flat_iterations_from_repetitions(data[bug_key])
    return result

#
# Bug Specific Prints
#

def print_bugs_specific_data \
        ( data: dict[str, dict[int, DataEntry]]
        , bug_sat_circuits: dict[str, tuple[int, int]]
        , repetitions: int
        ):

    #
    # Collection Of Data
    #

    # list of all circuits for all bugs combined
    all_circuits : list[int] = []

    # count of all rules used to find all bugs combined
    all_rules_count : dict[str, int] = {}

    # time spend in exploration before bug was found
    all_exploration_times : list[float] = []

    # list of all circuits for a specific bug
    bug_circuits : dict[str, list[int]] = {}

    # count of all rules used to find a specific bug
    bug_rules_count : dict[str, dict[str, int]] = {}

    # intersection of rules
    bug_rule_intersection : dict[str, set[str] | None] = {}

    # time spend in exploration before bug was found per bug
    bug_exploration_times : dict[str, list[float]] = {}

    # tracks the amount of timeouts during bug finding per bug
    bug_timeout_count : dict[str, int] = {}

    # tracks the amount of error that occurred per bug
    bug_error_lookup : dict[str, dict[str, int]] = {}

    # structure of the IR for the original circuit per bug
    bug_c1_structure : dict[str, dict[str, list[int]]] = {}

    # structure of the IR for the transformed circuit per bug
    bug_c2_structure : dict[str, dict[str, list[int]]] = {}

    # pipeline stage for the original circuit per bug
    bug_c1_pipelines : dict[str, dict[str, tuple[int, int, list[float]]]] = {}

    # pipeline stage for the transformed circuit per bug
    bug_c2_pipelines : dict[str, dict[str, tuple[int, int, list[float]]]] = {}

    for bug in data:

        # get the repetition entries for current bug
        bug_data = data[bug]

        # insert default entry
        bug_circuits[bug] = []
        bug_rules_count[bug] = {}
        bug_rule_intersection[bug] = None # undefined
        bug_exploration_times[bug] = []
        bug_timeout_count[bug] = 0
        bug_error_lookup[bug] = {}
        bug_c1_structure[bug] = init_circuit_structure_lookups()
        bug_c2_structure[bug] = init_circuit_structure_lookups()
        bug_c1_pipelines[bug] = init_pipeline_lookup_for_tool(bug_to_tool(bug))
        bug_c2_pipelines[bug] = init_pipeline_lookup_for_tool(bug_to_tool(bug))

        for rep in range(1, repetitions + 1):

            if not rep in bug_data:
                bug_timeout_count[bug] += 1 # mark timeout
                continue # go to next repetition

            rep_data = bug_data[rep]

            # assert possible None fields to contain values
            assert rep_data.cycle != None, "field for 'cycle' was 'None'"
            assert rep_data.explore_time != None, "field for 'explore_time' was 'None'"
            assert rep_data.error != None, "field for 'error' was 'None'"

            # update local and global data
            bug_circuits[bug].append(rep_data.cycle + 1) # +1 for 0 offset of cycles
            all_circuits.append(rep_data.cycle + 1) # +1 for 0 offset of cycles
            bug_exploration_times[bug].append(rep_data.explore_time)
            all_exploration_times.append(rep_data.explore_time)
            update_count_lookup(bug_error_lookup[bug], [rep_data.error])
            update_count_lookup(bug_rules_count[bug], rep_data.ir_rewrite_rules)

            tmp_rule_set = bug_rule_intersection[bug]
            if tmp_rule_set == None:
                bug_rule_intersection[bug] = set(rep_data.ir_rewrite_rules)
            else:
                tmp_rule_set = tmp_rule_set.intersection(set(rep_data.ir_rewrite_rules))
                bug_rule_intersection[bug] = tmp_rule_set

            update_count_lookup(all_rules_count, rep_data.ir_rewrite_rules)
            update_circuit_structure_lookups(bug_c1_structure[bug], bug_c2_structure[bug], rep_data)

            # update abstracted stage data
            c1_stages, c2_stages = generate_pipeline_stages(rep_data)
            update_pipeline_lookup(bug_c1_pipelines[bug], c1_stages)
            update_pipeline_lookup(bug_c2_pipelines[bug], c2_stages)

    #
    # Display of Data
    #

    # print individual bug reports
    for bug_idx, bug in enumerate(data, start=1):
        tool_name = bug_to_tool(bug)

        print()
        print(f" == Bug Nr {bug_idx}: '{bug}', {tool_name} == ")
        print()

        # check if we even have data on the specific bug, if not print
        # a message and move on to the next
        if bug_timeout_count[bug] >= repetitions:
            print("    -> No information available as all instances timed out!")
            print()
            continue # go to next bug

        curr_circuits          : list[int]                               = bug_circuits[bug]
        curr_rules_count       : dict[str, int]                          = bug_rules_count[bug]
        curr_rule_intersection : set[str] | None                         = bug_rule_intersection[bug]
        curr_exploration_times : list[float]                             = bug_exploration_times[bug]
        curr_timeout_count     : int                                     = bug_timeout_count[bug]
        curr_error_lookup      : dict[str, int]                          = bug_error_lookup[bug]
        curr_c1_structure      : dict[str, list[int]]                    = bug_c1_structure[bug]
        curr_c2_structure      : dict[str, list[int]]                    = bug_c2_structure[bug]
        curr_c1_pipelines      : dict[str, tuple[int, int, list[float]]] = bug_c1_pipelines[bug]
        curr_c2_pipelines      : dict[str, tuple[int, int, list[float]]] = bug_c2_pipelines[bug]

        # circuits generated for current bug
        circ_min, circ_med, circ_max = compute_min_med_max(curr_circuits)
        print("circuits:")
        print(f"    - min: {circ_min}, median: {circ_med}, max: {circ_max}")
        print()

        # exploration time in general for current bug
        exp_min, exp_med, exp_max = compute_min_med_max(curr_exploration_times)
        print(f"exploration time:")
        print(f"    - min: {exp_min}, median: {exp_med}, max: {exp_max}")
        print()

        # timeouts of current bug
        print(f"timeouts: {curr_timeout_count}")
        print()

        ## # rewrite rules for current bug
        ## print("rewrite rules:")
        ## for rule_name, rule_amount in sorted_by_value(curr_rules_count, reverse=True).items():
        ##     print(f"    - {rule_name} : {rule_amount}")

        # rule intersection
        assert curr_rule_intersection != None, "no rule intersection found"
        if len(curr_rule_intersection) > 0:
            print("rewrite rules intersection:")
            for rule_name in sorted(list(curr_rule_intersection)):
                print(f"    - {rule_name} ({curr_rules_count.get(rule_name, 0)})")
        else:
            print("rewrite rules intersection: EMPTY SET")
        print()

        # errors for current bug
        print("errors:")
        for err_name, err_amount in sorted_by_value(curr_error_lookup, reverse=True).items():
            print(f"    - {err_name} : {err_amount}")
        print()

        # structure of c1 and c2 for current bug
        print("structural information:")
        structure_rows: list[list[Any]] = [["circuit", "property", "min", "median", "max"]]
        for structure_key in curr_c1_structure:
            c1_vals = curr_c1_structure[structure_key]
            c1_val_min, c1_val_med, c1_val_max = compute_min_med_max(c1_vals)
            c2_vals = curr_c2_structure[structure_key] # should exist by construction
            c2_val_min, c2_val_med, c2_val_max = compute_min_med_max(c2_vals)
            structure_rows.append(["c1", structure_key, c1_val_min, c1_val_med, c1_val_max])
            structure_rows.append(["c2", structure_key, c2_val_min, c2_val_med, c2_val_max])
        structure_table = tabulate(structure_rows)
        print(structure_table)
        print()

        # pipeline information of c1 and c2 for current bug
        print("pipelines:")
        pipeline_rows: list[list[Any]] = [["circuit", "stage",
            "executions", "success", "time-min", "time-median", "time-max"]]
        for pipeline_key in curr_c1_pipelines:
            c1_suc, c1_exec, c1_times = curr_c1_pipelines[pipeline_key]
            if len(c1_times) > 0:
                c1_t_min, c1_t_med, c1_t_max = compute_min_med_max(c1_times)
                pipeline_rows.append(["c1", pipeline_key, c1_exec, c1_suc, c1_t_min, c1_t_med, c1_t_max])
            else:
                pipeline_rows.append(["c1", pipeline_key, "-", "-", "-", "-", "-"])
            c2_suc, c2_exec, c2_times = curr_c2_pipelines[pipeline_key] # should exist by construction
            if len(c2_times) > 0:
                c2_t_min, c2_t_med, c2_t_max = compute_min_med_max(c2_times)
                pipeline_rows.append(["c2", pipeline_key, c2_exec, c2_suc, c2_t_min, c2_t_med, c2_t_max])
            else:
                pipeline_rows.append(["c2", pipeline_key, "-", "-", "-", "-", "-"])
        pipeline_table = tabulate(pipeline_rows)
        print(pipeline_table)
        print()

        # pipeline info like table 2
        overall_time: float = 0
        if tool_name == "corset": # corset pipelines are duplicated
            overall_time += sum([sum(v) for _, _, v in curr_c1_pipelines.values()])
        else:
            overall_time += sum([sum(v) for _, _, v in curr_c1_pipelines.values()])
            overall_time += sum([sum(v) for _, _, v in curr_c2_pipelines.values()])

        pipeline_rows: list[list[Any]] = [["stage", "executions", "success", "time", "percent"]]
        for stage_key in curr_c1_pipelines:
            success : int = 0
            execs   : int = 0
            times   : list[float] = []

            if tool_name == "corset": # corset pipelines are duplicated
                success, execs, times = curr_c1_pipelines[stage_key]
            else:
                c1_success, c1_execs, c1_times = curr_c1_pipelines[stage_key]
                c2_success, c2_execs, c2_times = curr_c2_pipelines[stage_key]
                success, execs, times = (c1_success + c2_success), \
                    (c1_execs + c2_execs), (c1_times + c2_times)

            if len(times) > 0: # if no time is available we can skip
                time_sum = sum(times)
                time_percent = round((time_sum / overall_time) * 100, 2)
                pipeline_rows.append([stage_key, execs, success, \
                    from_s_to_hms(time_sum), f"{time_percent}%"])
            else:
                pipeline_rows.append([stage_key, "-", "-", "-", "-"])

        pipeline_table = tabulate(pipeline_rows)
        print(pipeline_table)
        print()
    print()

    # print information over all bugs
    print(" == All Bugs ==")
    print()

    # exploration time over all bugs
    if len(all_exploration_times) > 0:
        exp_min, exp_med, exp_max = compute_min_med_max(all_exploration_times)
        print("exploration time:")
        print(f"    - min: {exp_min}, median: {exp_med}, max: {exp_max}")
        print()

    # generated circuits over all bugs
    if len(all_circuits) > 0:
        cir_min, cir_med, cir_max = compute_min_med_max(all_circuits)
        print("circuits:")
        print(f"    - min: {cir_min}, median: {cir_med}, max: {cir_max}")
        print()

    ## # list of rules used by all bugs
    ## if len(all_rules_count) > 0:
    ##     print("rewrite rules:")
    ##     for rule_name, rule_amount in sorted_by_value(all_rules_count, reverse=True).items():
    ##         print(f"    - {rule_name} : {rule_amount}")

    #
    # Summary table (figure 2), Effectiveness table
    #

    print("Summary (Paper Table 2):")
    summary_table_data : list[list[Any]] = [["tool", "bug-id", "seeds", "circ-SAT", \
        "time-min", "time-median", "time-max", "circ-min", "circ-median", "circ-max"]]
    for bug_idx, bug in enumerate(data, start=1):
        tool = bug_to_tool(bug)
        seeds = repetitions - bug_timeout_count[bug]

        sat_circuits = "-"
        if bug in bug_sat_circuits:
            sat_circuits, unique_circuits = bug_sat_circuits[bug]
            sat_circuits_percent = round((sat_circuits / unique_circuits) * 100, 2)
            sat_circuits = f"{sat_circuits_percent}%"

        if bug_timeout_count[bug] < repetitions:
            exp_min, exp_med, exp_max = compute_min_med_max(bug_exploration_times[bug])
            circ_min, circ_med, circ_max = compute_min_med_max(bug_circuits[bug])
            summary_table_data.append([tool, bug_idx, seeds, sat_circuits, from_s_to_hms(exp_min),
                from_s_to_hms(exp_med), from_s_to_hms(exp_max), circ_min, circ_med, circ_max])
        else:
            summary_table_data.append([tool, bug_idx, bug, seeds, "-", "-", "-", "-", "-", "-"])
    summary_table = tabulate(summary_table_data, sep="&")
    print(summary_table)
    print()

    print("Effectiveness Comparison Table:")
    summary_table_data : list[list[Any]] = [["tool", "bug-id", "seeds", "time-median","circ-median"]]
    for bug_idx, bug in enumerate(data, start=1):
        tool = bug_to_tool(bug)
        seeds = repetitions - bug_timeout_count[bug]
        if bug_timeout_count[bug] < repetitions:
            exp_min, exp_med, exp_max = compute_min_med_max(bug_exploration_times[bug])
            circ_min, circ_med, circ_max = compute_min_med_max(bug_circuits[bug])
            summary_table_data.append([tool, bug_idx, seeds, exp_med, circ_med])
        else:
            summary_table_data.append([tool, bug_idx, seeds, "-", "-"])
    summary_table = tabulate(summary_table_data, sep="&")
    print(summary_table)
    print()

    # new line
    print()


#
# Summary Prints
#

def print_test_time_experiment_summary(data: dict[str, dict[int, list[DataEntry]]]):
    """
    Prints test time per tool for a experiment
    """

    # process data

    tool_test_times : dict[str, list[float]] = dict()
    flat_data = flat_first_iterations_from_experiments(data)
    for tool_name in flat_data:
        tool_test_times[tool_name] = [e.test_time for e in flat_data[tool_name]]

    # print data

    print("+------------------------------+")
    print("| Test Time Summary")
    print("+------------------------------+")
    print()

    table_rows = []
    table_rows.append(["tool", "mean", "median", "stdev", "min", "max", "count"])

    for tool_name in tool_test_times:
        test_times        = tool_test_times[tool_name]
        test_times_mean   = round(statistics.mean(test_times), ndigits=3)
        test_times_median = round(statistics.median(test_times), ndigits=3)
        test_times_stdev  = round(statistics.stdev(test_times), ndigits=3)
        test_times_min    = round(min(test_times), ndigits=3)
        test_times_max    = round(max(test_times), ndigits=3)
        test_times_count  = len(test_times)

        table_rows.append(
            [ tool_name
            , test_times_mean
            , test_times_median
            , test_times_stdev
            , test_times_min
            , test_times_max
            , test_times_count
            ])

    table = tabulate(table_rows)
    print(table)

    print()

def print_circuit_experiment_summary(data: dict[str, dict[int, list[DataEntry]]]):
    """
    Prints circuit information per tool for a experiment
    """
    # process data

    tool_c1_circuit_info : dict[str, dict[str, list[int]]] = dict()
    tool_c2_circuit_info : dict[str, dict[str, list[int]]] = dict()
    flat_data = flat_first_iterations_from_experiments(data)
    for tool_name in flat_data:
        c1_info, c2_info = get_circuit_structures(flat_data[tool_name])
        tool_c1_circuit_info[tool_name] = c1_info
        tool_c2_circuit_info[tool_name] = c2_info

    # print data

    print("+------------------------------+")
    print("| Circuit Info Summary")
    print("+------------------------------+")
    print()

    table_rows = []
    table_rows.append(["tool", "circuit", "property", "min", "median", "mean", "max"])

    for tool_name in tool_c1_circuit_info:
        c1_info = tool_c1_circuit_info[tool_name]
        c2_info = tool_c2_circuit_info[tool_name]
        for circuit, info in [("c1", c1_info), ("c2",c2_info )]:
            for key in info:
                values = info[key]
                if len(values) == 0:
                    table_rows.append([tool_name, circuit, key, "-", "-", "-", "-"])
                else:
                    val_min  = min(values)
                    val_med  = round(statistics.median(values))
                    val_mean = round(statistics.mean(values))
                    val_max  = max(values)
                    table_rows.append([ tool_name, circuit, key, val_min, val_med, val_mean, val_max])

    table = tabulate(table_rows)
    print(table)
    print()

def get_sat_circuit_experiment_summary(data: dict[str, dict[int, list[DataEntry]]]) -> dict[str, tuple[int, int]]:
    # key is the tool and the tuple is SAT-Circuits, Overall-Circuits
    bug_sat_circuits : dict[str, tuple[int, int]] = {}
    for bug in data:
        flat_bug_data = flat_iterations_from_repetitions(data[bug])
        tool_name = bug_to_tool(bug)
        visited_entries   : set[str] = set()
        visited_seeds     : set[float] = set()
        satisfiable_seeds : set[float] = set()
        for entry in flat_bug_data:
            entry_id   = entry.unique_id()
            entry_seed = entry.seed

            assert not entry_id in visited_entries, "duplicate entry for bug"
            visited_entries.add(entry_id)
            visited_seeds.add(entry_seed) # multiple adds are fine for a set

            if entry.is_error():
                continue # we skip error entries

            if entry_seed in satisfiable_seeds:
                continue # we already have a sat instance for this circuit

            match tool_name:
                case "circom":
                    if entry.circom_c1_js_witness_generation == True or \
                       entry.circom_c1_cpp_witness_generation == True or \
                       entry.circom_c2_js_witness_generation == True or \
                       entry.circom_c2_cpp_witness_generation == True:
                        # we say that it is sat if any of the witness generations are
                        # successful. If they disagree we would have an error!
                        satisfiable_seeds.add(entry_seed)
                case "corset":
                    if entry.corset_wizard_verify != None:
                        if entry.corset_wizard_verify == True:
                            # if the verification is available to take its output
                            # to check if the circuits are valid
                            satisfiable_seeds.add(entry_seed)
                    else:
                        if entry.corset_rust_check == True:
                            # if the verification is not available we
                            # check if the corset check succeeded
                            satisfiable_seeds.add(entry_seed)
                case "gnark":
                    if entry.gnark_c1_witness_solved == True or \
                       entry.gnark_c2_witness_solved == True:
                        # we say that it is sat if any of the witness solved checks are
                        # successful. If they disagree we would have an error!
                        satisfiable_seeds.add(entry_seed)
                case "noir":
                    if entry.noir_c1_execute == True or \
                       entry.noir_c2_execute == True:
                        # if we have a successful noir execution the circuit
                        # is satisfiable with the given input
                        satisfiable_seeds.add(entry_seed)
        bug_sat_circuits[bug] = len(satisfiable_seeds), len(visited_seeds)
    return bug_sat_circuits

def print_sat_circuit_experiment_summary(data : dict[str, tuple[int, int]]):
    print("+------------------------------+")
    print("| Satisfiability of Circuits")
    print("+------------------------------+")
    print()

    table_rows = []
    table_rows.append(["bug", "circuit seeds", "SAT circuits", "SAT percentage"])
    for bug in data:
        sat_circuits, all_circuits = data[bug]
        sat_percent = round((sat_circuits / all_circuits) * 100, 2)
        table_rows.append([bug, all_circuits, sat_circuits, f"{sat_percent}%"])
    table = tabulate(table_rows)
    print(table)
    print()

def print_pipeline_summary(data: dict[str, dict[int, list[DataEntry]]]):

    pipelines : dict[str, dict[str, tuple[int, int, list[float]]]] = {}
    flat_data = flat_iterations_from_experiments(data)
    for tool_name in flat_data:
        # warning circom data is patched here!
        if tool_name == "circom":
            flat_data[tool_name] = patch_circom_cached_exec_times(flat_data[tool_name])
        pipelines[tool_name] = init_pipeline_lookup_for_tool(tool_name)
        for entry in flat_data[tool_name]:
            c1_stages, c2_stages = generate_pipeline_stages(entry)
            update_pipeline_lookup(pipelines[tool_name], c1_stages)
            update_pipeline_lookup(pipelines[tool_name], c2_stages)

    print("+------------------------------+")
    print("| Pipeline Info Summary")
    print("+------------------------------+")
    print()

    overall_times: dict[str, float] = {}
    for tool_name in pipelines:
        overall_times[tool_name] = sum([sum(v) for _, _, v in pipelines[tool_name].values()])

    pipeline_rows: list[list[Any]] = [["tool", "stage", "executions", "success", "time", "percent"]]
    for tool_name in pipelines:
        stages = pipelines[tool_name]
        overall_time = overall_times[tool_name]

        # circuits are executed at the same time
        if tool_name == "corset":
            overall_time /= 2

        for stage_key in stages:
            success, execs, times = stages[stage_key]
            if len(times) > 0:
                time_sum = sum(times)

                # circuits are executed at the same time
                if tool_name == "corset":
                    time_sum /= 2

                time_percent = round((time_sum / overall_time) * 100, 2)
                pipeline_rows.append([tool_name, stage_key, execs, success, from_s_to_hms(time_sum), f"{time_percent}%"])
            else:
                pipeline_rows.append([tool_name, stage_key, "-", "-", "-", "-"])
    pipeline_table = tabulate(pipeline_rows)
    print(pipeline_table)
    print()

#
# Main Function / Entry Point
#

def main(data_root: Path, repetitions: int, ordered_bug_list: list[str], timeout_limit: float):

    explore_data_lookup : dict[str, dict[int, list[DataEntry]]] = {}
    observe_data_lookup : dict[str, dict[int, list[DataEntry]]] = {}
    buggy_line_lookup   : dict[str, dict[int, DataEntry]] = {}

    # iterate over each bug and each iteration
    for bug_idx, bug in enumerate(ordered_bug_list, start=1):
        explore_data_lookup[bug] = {}
        observe_data_lookup[bug] = {}
        buggy_line_lookup[bug] = {}
        for rep in range(1, repetitions + 1):

            # gather explore csv data
            explorer_csv = data_root / f"bug-{bug_idx}-rep-{rep}" / "explore" / "report" / "summary.csv"
            explore_data = collect_csv_data(explorer_csv)

            # gather observe csv data
            observe_csv = data_root / f"bug-{bug_idx}-rep-{rep}" / "observe" / "report" / "summary.csv"
            observe_data = collect_csv_data(observe_csv)

            # remove any row that succeeds the timeout and report it
            old_explore_len = len(explore_data)
            explore_data = remove_timeout_data(explore_data, timeout_limit)
            new_explore_len = len(explore_data)
            if new_explore_len < old_explore_len:
                print("WARNING: explore data did not respect the set time limit!")
                print(f"Removed {old_explore_len - new_explore_len} entries for '{bug}' in repetition {rep}")

            # parse row that holds the fix from observation data
            fixed_row_or_none : DataEntry | None = None
            for entry in observe_data:
                if entry.is_fixed == True:
                    fixed_row_or_none = entry

            # if a fixed row is present, collect the exploring counter part
            if fixed_row_or_none != None:
                for entry in explore_data:
                    if fixed_row_or_none.unique_id() == entry.unique_id():
                        explore_time = entry.explore_time # get explore time to fix
                        assert explore_time != None, "unexpected 'None' value for explore time field"
                        explore_data = remove_timeout_data(explore_data, explore_time) # remove everything after
                        buggy_line_lookup[bug][rep] = entry

            explore_data_lookup[bug][rep] = explore_data
            observe_data_lookup[bug][rep] = observe_data

    # TODO:
    #   - Data validation:
    #       - for every stage status there has to be time available
    #           => check that both are 'None' or none is 'None'
    #       - for every stage status the followup stages should fail!
    #           => e.g. if the compilation failed, there cannot be a witness generation!
    #       - check that all cycles are available for every repetition
    #           => 0 - "number of found bug"

    #
    # Pre-compute some data
    #

    bug_sat_circuits = get_sat_circuit_experiment_summary(explore_data_lookup)

    #
    # Print data
    #

    # bug specifics
    print_bugs_specific_data(buggy_line_lookup, bug_sat_circuits, repetitions)

    # summary data
    print_test_time_experiment_summary(explore_data_lookup)
    print_circuit_experiment_summary(explore_data_lookup)
    print_sat_circuit_experiment_summary(bug_sat_circuits)

    # NOTE: 'print_pipeline_summary' patches circom data!
    print_pipeline_summary(explore_data_lookup)


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("ERROR: no data root provided!")
        print("USAGE:")
        print(f"    {sys.argv[0]} <DATA ROOT>")
        exit(1)

    data_root = Path(sys.argv[1])

    if not data_root.is_dir():
        raise RuntimeError(f"unable to locate {data_root}")

    main(data_root, REPETITIONS, BUG_LIST, TIME_LIMIT)