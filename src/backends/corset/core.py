
from pathlib import Path
from random import Random
import time
from typing import Any

from circuzz.common.metamorphism import MetamorphicCircuitBundle
from circuzz.common.metamorphism import MetamorphicKind

from circuzz.common.field import CurvePrime
from circuzz.common.field import get_curve_name

from circuzz.common.helper import generate_metamorphic_related_circuit
from circuzz.common.helper import generate_random_circuit
from circuzz.common.helper import random_weighted_metamorphic_kind

from circuzz.common.colorlogs import get_color_logger

from experiment.config import Config, OnlineTuning
from experiment.data import DataEntry, TestResult

from .helpers import run_metamorphic_tests

logger = get_color_logger()

def run_corset_metamorphic_tests \
    ( seed: float
    , working_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> TestResult:

    """
    Runs a single metamorphic test with a given seed using the provided
    working directory and configuration.
    """

    start_time = time.time()
    logger.info(f"corset metamorphic testing, seed: {seed}, working-dir: {working_dir}")

    rng = Random(seed)
    ir_gen_seed = rng.randint(1000000000, 9999999999)
    test_seed = rng.randint(1000000000, 9999999999)

    prime = CurvePrime.BLS12_377

    ir_generation_start = time.time()
    ir = generate_random_circuit(prime, False, config.ir, ir_gen_seed)
    ir.name = "Circuit"
    ir_generation_time = time.time() - ir_generation_start

    bundle_size = config.corset.bundle_size
    rewrite_seed_set : set[int] = set()
    while len(rewrite_seed_set) < bundle_size:
        rewrite_seed_set.add(rng.randint(1000000000, 9999999999))
    rewrite_seed_list = sorted(list(rewrite_seed_set))

    ir_entry_lookup : dict[str, dict[str, Any]] = {} # dummy test entry just for lookup 
    bundle = MetamorphicCircuitBundle([], ir, [], []) # create an empty bundle
    for ir_tf_seed in rewrite_seed_list:
        kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)

        ir_rewrite_start = time.time()
        POIs, ir_tf = generate_metamorphic_related_circuit(kind, ir, prime, config.ir, ir_tf_seed)
        postfix = f"_eq_{ir_tf_seed}" if kind == MetamorphicKind.EQUAL else f"_wk_{ir_tf_seed}"
        ir_tf.name = f"{ir.name}{postfix}"
        ir_rewrite_time = time.time() - ir_rewrite_start

        # add to bundle
        bundle.kinds.append(kind)
        bundle.bundle.append(ir_tf)
        bundle.transformations.append(POIs)

        # reuse the test entry to save the IR specifics
        ir_entry_lookup[ir_tf.name] = \
            { "c1_node_size"       : ir.node_size()
            , "c1_assignments"     : len(ir.assignments())
            , "c1_assertions"      : len(ir.assertions())
            , "c1_assumptions"     : len(ir.assumptions())
            , "c1_input_signals"   : len(ir.inputs)
            , "c1_output_signals"  : len(ir.outputs)
            , "c2_node_size"       : ir_tf.node_size()
            , "c2_assignments"     : len(ir_tf.assignments())
            , "c2_assertions"      : len(ir_tf.assertions())
            , "c2_assumptions"     : len(ir_tf.assumptions())
            , "c2_input_signals"   : len(ir_tf.inputs)
            , "c2_output_signals"  : len(ir_tf.outputs)
            , "ir_generation_seed" : ir_gen_seed
            , "ir_generation_time" : ir_generation_time
            , "ir_rewrite_seed"    : ir_tf_seed
            , "ir_rewrite_time"    : ir_rewrite_time
            , "ir_rewrite_rules"   : [POI.rule.name for POI in POIs]
            , "curve"              : get_curve_name(CurvePrime.BLS12_377)
            , "oracle"             : kind.value
            }

    corset_test_result = run_metamorphic_tests(bundle, test_seed, working_dir, config, online_tuning)
    test_time = time.time() - start_time

    data_entries : list[DataEntry] = []
    for idx, iteration in enumerate(corset_test_result.iterations): # every execution
        for key in ir_entry_lookup: # every constraint
            # copy the basics
            ir_info = ir_entry_lookup[key]

            # generate entry
            data_entry = DataEntry \
                ( tool = "corset"
                , test_time = test_time
                , seed = seed
                , curve = ir_info["curve"]
                , oracle = ir_info["oracle"]
                , iteration = idx
                , error = None # this is set later
                , ir_generation_seed = ir_info["ir_generation_seed"]
                , ir_generation_time = ir_info["ir_generation_time"]
                , ir_rewrite_seed = ir_info["ir_rewrite_seed"]
                , ir_rewrite_time = ir_info["ir_rewrite_time"]
                , ir_rewrite_rules = ir_info["ir_rewrite_rules"]
                , c1_node_size = ir_info["c1_node_size"]
                , c1_assignments = ir_info["c1_assignments"]
                , c1_assertions = ir_info["c1_assertions"]
                , c1_assumptions = ir_info["c1_assumptions"]
                , c1_input_signals = ir_info["c1_input_signals"]
                , c1_output_signals = ir_info["c1_output_signals"]
                , c2_node_size = ir_info["c2_node_size"]
                , c2_assignments = ir_info["c2_assignments"]
                , c2_assertions = ir_info["c2_assertions"]
                , c2_assumptions = ir_info["c2_assumptions"]
                , c2_input_signals = ir_info["c2_input_signals"]
                , c2_output_signals = ir_info["c2_output_signals"]
                , corset_rust_check = iteration.rust_corset_check
                , corset_rust_check_time = iteration.rust_corset_check_time
                , corset_rust_compile = iteration.rust_corset_compile
                , corset_rust_compile_time = iteration.rust_corset_compile_time
                , corset_go_compile = iteration.go_corset_compile
                , corset_go_compile_time = iteration.go_corset_compile_time
                , corset_wizard_compile = iteration.wizard_compile
                , corset_wizard_compile_time = iteration.wizard_compile_time
                , corset_wizard_prove = iteration.wizard_prove
                , corset_wizard_prove_time = iteration.wizard_prove_time
                , corset_wizard_verify = iteration.wizard_verify
                , corset_wizard_verify_time = iteration.wizard_verify_time
                , corset_go_custom_cli = iteration.go_custom_cli
                , corset_go_custom_cli_time = iteration.go_custom_cli_time
                , corset_ignored_error = iteration.ignored_error
                , corset_expansions = iteration.expansions
                , corset_native = iteration.native
                , corset_auto_constraints = iteration.auto_constraints
                , corset_guard_variable = iteration.guard_variable
                , corset_timeout = iteration.timeout
                , corset_out_of_memory = iteration.out_of_memory
                , corset_error_references = iteration.error_references
                )

            if iteration.constraints != None and len(iteration.constraints) > 0:
                if key in iteration.constraints: # if the constraint was the culprit save error
                    data_entry.error = iteration.error
            else:
                # no specific constraint caused the error so we add it to all
                data_entry.error = iteration.error

            data_entries.append(data_entry)

    return TestResult(data_entries)