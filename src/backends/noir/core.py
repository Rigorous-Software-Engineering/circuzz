from pathlib import Path
from random import Random
import time

from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.metamorphism import MetamorphicKind
from circuzz.common.helper import generate_metamorphic_related_circuit
from circuzz.common.field  import CurvePrime, get_curve_name
from circuzz.common.helper import generate_random_circuit
from circuzz.common.helper import random_weighted_metamorphic_kind
from circuzz.common.colorlogs import get_color_logger

from experiment.config import Config, OnlineTuning
from experiment.data import DataEntry, TestResult

from .helper import run_metamorphic_tests

logger = get_color_logger()

def run_noir_metamorphic_tests \
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
    logger.info(f"noir metamorphic testing, seed: {seed}, working-dir: {working_dir}")

    rng = Random(seed)
    ir_gen_seed = rng.randint(1000000000, 9999999999)
    ir_tf_seed = rng.randint(1000000000, 9999999999)
    test_seed = rng.randint(1000000000, 9999999999)
    kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)

    curve_prime = CurvePrime.BN254 # noir only supports the bn254 curve natively 
    curve_name = get_curve_name(curve_prime)

    ir_generation_start = time.time()
    ir = generate_random_circuit(curve_prime, True, config.ir, ir_gen_seed)
    ir.name = f"Circuit_{curve_name}"
    ir_generation_time = time.time() - ir_generation_start

    ir_rewrite_start = time.time()
    POIs, ir_tf = generate_metamorphic_related_circuit(kind, ir, curve_prime, config.ir, ir_tf_seed)
    postfix = "_eq" if kind == MetamorphicKind.EQUAL else "_wk"
    ir_tf.name = f"{ir.name}{postfix}"
    ir_rewrite_time = time.time() - ir_rewrite_start

    metamorphic_pair = MetamorphicCircuitPair(kind, ir, ir_tf, POIs)
    noir_result = run_metamorphic_tests(metamorphic_pair, test_seed, curve_prime, working_dir, config, online_tuning)
    test_time = time.time() - start_time

    data_entries : list[DataEntry] = []
    for idx, iteration in enumerate(noir_result.iterations):

        data_entry = DataEntry \
            ( tool = "noir"
            , test_time = test_time
            , seed = seed
            , curve = curve_name
            , oracle = kind.value
            , iteration = idx
            , error = iteration.error
            , ir_generation_seed = ir_gen_seed
            , ir_generation_time = ir_generation_time
            , ir_rewrite_seed = ir_tf_seed
            , ir_rewrite_time = ir_rewrite_time
            , ir_rewrite_rules = [POI.rule.name for POI in POIs]
            , c1_node_size = ir.node_size()
            , c1_assignments = len(ir.assignments())
            , c1_assertions = len(ir.assertions())
            , c1_assumptions = len(ir.assumptions())
            , c1_input_signals = len(ir.inputs)
            , c1_output_signals = len(ir.outputs)
            , c2_node_size = ir_tf.node_size()
            , c2_assignments = len(ir_tf.assignments())
            , c2_assertions = len(ir_tf.assertions())
            , c2_assumptions = len(ir_tf.assumptions())
            , c2_input_signals = len(ir_tf.inputs)
            , c2_output_signals = len(ir_tf.outputs)
            , noir_c1_execute = iteration.c1_execute
            , noir_c1_execute_time = iteration.c1_execute_time
            , noir_c2_execute = iteration.c2_execute
            , noir_c2_execute_time = iteration.c2_execute_time
            , noir_c1_vk =  iteration.c1_vk
            , noir_c1_vk_time = iteration.c1_vk_time
            , noir_c2_vk =  iteration.c2_vk
            , noir_c2_vk_time = iteration.c2_vk_time
            , noir_c1_bb_prove = iteration.c1_bb_prove
            , noir_c1_bb_prove_time = iteration.c1_bb_prove_time
            , noir_c2_bb_prove = iteration.c2_bb_prove
            , noir_c2_bb_prove_time = iteration.c2_bb_prove_time
            , noir_c1_bb_verify = iteration.c1_bb_verify
            , noir_c1_bb_verify_time = iteration.c1_bb_verify_time
            , noir_c2_bb_verify = iteration.c2_bb_verify
            , noir_c2_bb_verify_time = iteration.c2_bb_verify_time
            , noir_c1_ignored_error = iteration.c1_ignored_error
            , noir_c2_ignored_error = iteration.c2_ignored_error
            )

        data_entries.append(data_entry)

    return TestResult(data_entries)