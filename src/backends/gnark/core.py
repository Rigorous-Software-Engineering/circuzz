
from pathlib import Path
from random import Random
import time
from typing import Any

from experiment.data import DataEntry, TestResult

from circuzz.common.metamorphism import MetamorphicCircuitPair
from circuzz.common.helper import generate_metamorphic_related_circuit
from circuzz.common.helper import generate_random_circuit
from circuzz.common.helper import random_weighted_metamorphic_kind
from circuzz.common.colorlogs import get_color_logger

from experiment.config import Config, OnlineTuning

from .helper import run_metamorphic_tests
from .utils import GnarkCurve
from .utils import curve_to_prime

logger = get_color_logger()

def run_gnark_metamorphic_tests \
    ( seed: int | float
    , working_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> TestResult:

    """
    Runs a single metamorphic test with a given seed using the provided
    working directory and configuration.
    """

    start_time = time.time()
    logger.info(f"gnark metamorphic testing, seed: {seed}, working-dir: {working_dir}")

    rng = Random(seed)

    test_seed = rng.randint(1000000000, 9999999999)

    circuit_seed_set : set[int] = set()
    while len(circuit_seed_set) < config.gnark.bundle_size:
        circuit_seed_set.add(rng.randint(1000000000, 9999999999))

    circuit_lookup : dict[str, dict[str, Any]] = {} # dummy lookup to track circuits
    pair_and_curves = []
    for circuit_seed in list(circuit_seed_set):

        ir_tf_seed = rng.randint(1000000000, 9999999999)
        kind = random_weighted_metamorphic_kind(rng, config.ir.rewrite.weakening_probability)
        curve = rng.choice(list(GnarkCurve))
        prime = curve_to_prime(curve)

        ir_generation_start = time.time()
        ir = generate_random_circuit(prime, False, config.ir, circuit_seed)
        ir.name = f"C1_{circuit_seed}_{ir_tf_seed}"
        ir_generation_time = time.time() - ir_generation_start

        ir_rewrite_start = time.time()
        POIs, ir_tf = generate_metamorphic_related_circuit(kind, ir, prime, config.ir, ir_tf_seed)
        ir_tf.name = f"C2_{circuit_seed}_{ir_tf_seed}"
        ir_rewrite_time = time.time() - ir_rewrite_start

        # add to bundle
        metamorphic_pair = MetamorphicCircuitPair(kind, ir, ir_tf, POIs)
        pair_and_curves.append((metamorphic_pair, curve))

        # add to entries
        circuit_entry = \
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
            , "ir_generation_seed" : circuit_seed
            , "ir_generation_time" : ir_generation_time
            , "ir_rewrite_seed"    : ir_tf_seed
            , "ir_rewrite_time"    : ir_rewrite_time
            , "ir_rewrite_rules"   : [POI.rule.name for POI in POIs]
            , "curve"              : curve.value
            , "oracle"             : kind.value
            }
        circuit_lookup[ir.name] = circuit_entry

    gnark_result = run_metamorphic_tests(pair_and_curves, test_seed, working_dir, config, online_tuning)
    test_time = time.time() - start_time

    data_entries : list[DataEntry] = []
    for key in circuit_lookup:
        ir_info = circuit_lookup[key]
        for idx, iteration in enumerate(gnark_result.iterations[key]):

            data_entry = DataEntry \
                ( tool = "gnark"
                , test_time = test_time
                , seed = seed
                , curve = ir_info["curve"]
                , oracle = ir_info["oracle"]
                , iteration = idx
                , error = iteration.error
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
                , gnark_c1_compile = iteration.c1_compile
                , gnark_c1_compile_time = iteration.c1_compile_time
                , gnark_c2_compile = iteration.c2_compile
                , gnark_c2_compile_time = iteration.c2_compile_time
                , gnark_c1_new_witness = iteration.c1_new_witness
                , gnark_c1_new_witness_time = iteration.c1_new_witness_time
                , gnark_c2_new_witness = iteration.c2_new_witness
                , gnark_c2_new_witness_time = iteration.c2_new_witness_time
                , gnark_c1_witness_solved = iteration.c1_witness_solved
                , gnark_c1_witness_solved_time = iteration.c1_witness_solved_time
                , gnark_c2_witness_solved = iteration.c2_witness_solved
                , gnark_c2_witness_solved_time = iteration.c2_witness_solved_time
                , gnark_c1_witness_write = iteration.c1_witness_write
                , gnark_c1_witness_write_time = iteration.c1_witness_write_time
                , gnark_c2_witness_write = iteration.c2_witness_write
                , gnark_c2_witness_write_time = iteration.c2_witness_write_time
                , gnark_c1_new_srs = iteration.c1_new_srs
                , gnark_c2_new_srs = iteration.c2_new_srs
                , gnark_c1_proof_setup = iteration.c1_proof_setup
                , gnark_c1_proof_setup_time = iteration.c1_proof_setup_time
                , gnark_c2_proof_setup = iteration.c2_proof_setup
                , gnark_c2_proof_setup_time = iteration.c2_proof_setup_time
                , gnark_c1_prove = iteration.c1_prove
                , gnark_c1_prove_time = iteration.c1_prove_time
                , gnark_c2_prove = iteration.c2_prove
                , gnark_c2_prove_time = iteration.c2_prove_time
                , gnark_c1_witness_public = iteration.c1_witness_public
                , gnark_c1_witness_public_time = iteration.c1_witness_public_time
                , gnark_c2_witness_public = iteration.c2_witness_public
                , gnark_c2_witness_public_time = iteration.c2_witness_public_time
                , gnark_c1_verify = iteration.c1_verify
                , gnark_c1_verify_time = iteration.c1_verify_time
                , gnark_c2_verify = iteration.c2_verify
                , gnark_c2_verify_time = iteration.c2_verify_time
                , gnark_cs_engine = iteration.cs_engine
                , gnark_proof_system = iteration.proof_system
                , gnark_go_test_time = iteration.go_test_time
                , gnark_go_timeout = iteration.go_timeout
                , gnark_go_ignored_compiler_error = iteration.go_ignored_compiler_error
                )

            data_entries.append(data_entry)

    return TestResult(data_entries)