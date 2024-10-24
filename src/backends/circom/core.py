from pathlib import Path
from random import Random
import time
from typing import Any

from experiment.data import DataEntry, TestResult

from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.metamorphism import MetamorphicKind
from circuzz.common.helper import generate_metamorphic_related_circuit
from circuzz.common.helper import generate_random_circuit
from circuzz.common.helper import random_weighted_metamorphic_kind
from circuzz.common.colorlogs import get_color_logger

from experiment.config import Config, OnlineTuning

from .helper import run_metamorphic_tests
from .utils import curve_to_prime
from .utils import random_circom_curve

logger = get_color_logger()

def run_circom_metamorphic_tests \
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
    logger.info(f"circom metamorphic testing, seed: {seed}, working-dir: {working_dir}")

    #
    # Start Of Test
    #

    rng = Random(seed)
    ir_gen_seed = rng.randint(1000000000, 9999999999)
    ir_tf_seed = rng.randint(1000000000, 9999999999)
    test_seed = rng.randint(1000000000, 9999999999)
    kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)
    curve = random_circom_curve(rng)
    prime = curve_to_prime(curve)

    ir_generation_start = time.time()
    ir = generate_random_circuit(prime, False, config.ir, ir_gen_seed)
    ir.name = f"Circuit_{curve}"
    ir_generation_time = time.time() - ir_generation_start

    ir_rewrite_start = time.time()
    POIs, ir_tf = generate_metamorphic_related_circuit(kind, ir, prime, config.ir, ir_tf_seed)
    postfix = "_eq" if kind == MetamorphicKind.EQUAL else "_wk"
    ir_tf.name = f"{ir.name}{postfix}"
    ir_rewrite_time = time.time() - ir_rewrite_start

    metamorphic_pair = MetamorphicCircuitPair(kind, ir, ir_tf, POIs)
    circom_result = run_metamorphic_tests(metamorphic_pair, test_seed, curve, working_dir, config, online_tuning)
    test_time = time.time() - start_time

    #
    # Report Result
    #

    # report each iteration outcome
    data_entries : list[DataEntry] = []
    c1_name = ir.name
    c2_name = ir_tf.name

    for idx, iteration in enumerate(circom_result.iterations):

        data_entry = DataEntry \
            ( tool = "circom"
            , test_time = test_time
            , seed = seed
            , curve = curve.value
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
            , circom_c1_compilation = iteration.compilation.get(c1_name, None)
            , circom_c1_compilation_time = iteration.compilation_time.get(c1_name, None)
            , circom_c1_compilation_optimization = iteration.compilation_optimization.get(c1_name, None)
            , circom_c2_compilation = iteration.compilation.get(c2_name, None)
            , circom_c2_compilation_time = iteration.compilation_time.get(c2_name, None)
            , circom_c2_compilation_optimization = iteration.compilation_optimization.get(c2_name, None)
            , circom_c1_cpp_witness_preparation = iteration.cpp_witness_preparation.get(c1_name, None)
            , circom_c1_cpp_witness_preparation_time = iteration.cpp_witness_preparation_time.get(c1_name, None)
            , circom_c1_cpp_witness_generation = iteration.cpp_witness_generation.get(c1_name, None)
            , circom_c1_cpp_witness_generation_time = iteration.cpp_witness_generation_time.get(c1_name, None)
            , circom_c1_js_witness_generation = iteration.js_witness_generation.get(c1_name, None)
            , circom_c1_js_witness_generation_time = iteration.js_witness_generation_time.get(c1_name, None)
            , circom_c1_snarkjs_witness_check = iteration.snarkjs_witness_check.get(c1_name, None)
            , circom_c1_snarkjs_witness_check_time = iteration.snarkjs_witness_check_time.get(c1_name, None)
            , circom_c2_cpp_witness_preparation = iteration.cpp_witness_preparation.get(c2_name, None)
            , circom_c2_cpp_witness_preparation_time = iteration.cpp_witness_preparation_time.get(c2_name, None)
            , circom_c2_cpp_witness_generation = iteration.cpp_witness_generation.get(c2_name, None)
            , circom_c2_cpp_witness_generation_time = iteration.cpp_witness_generation_time.get(c2_name, None)
            , circom_c2_js_witness_generation = iteration.js_witness_generation.get(c2_name, None)
            , circom_c2_js_witness_generation_time = iteration.js_witness_generation_time.get(c2_name, None)
            , circom_c2_snarkjs_witness_check = iteration.snarkjs_witness_check.get(c2_name, None)
            , circom_c2_snarkjs_witness_check_time = iteration.snarkjs_witness_check_time.get(c2_name, None)
            , circom_proof_system = iteration.proof_system
            , circom_c1_zkey_generation = iteration.zkey_generation.get(c1_name, None)
            , circom_c1_zkey_generation_time = iteration.zkey_generation_time.get(c1_name, None)
            , circom_c1_proof_generation = iteration.proof_generation.get(c1_name, None)
            , circom_c1_proof_generation_time = iteration.proof_generation_time.get(c1_name, None)
            , circom_c2_zkey_generation = iteration.zkey_generation.get(c2_name, None)
            , circom_c2_zkey_generation_time = iteration.zkey_generation_time.get(c2_name, None)
            , circom_c2_proof_generation = iteration.proof_generation.get(c2_name, None)
            , circom_c2_proof_generation_time = iteration.proof_generation_time.get(c2_name, None)
            , circom_c1_vkey_generation = iteration.vkey_generation.get(c1_name, None)
            , circom_c1_vkey_generation_time = iteration.vkey_generation_time.get(c1_name, None)
            , circom_c1_verification = iteration.verification.get(c1_name, None)
            , circom_c1_verification_time = iteration.verification_time.get(c1_name, None)
            , circom_c2_vkey_generation = iteration.vkey_generation.get(c2_name, None)
            , circom_c2_vkey_generation_time = iteration.vkey_generation_time.get(c2_name, None)
            , circom_c2_verification = iteration.verification.get(c2_name, None)
            , circom_c2_verification_time = iteration.verification_time.get(c2_name, None)
            , circom_c1_ignored_error = iteration.ignored_error.get(c1_name, None)
            , circom_c2_ignored_error = iteration.ignored_error.get(c2_name, None)
            )

        # append to test entry list
        data_entries.append(data_entry)

    return TestResult(data_entries)