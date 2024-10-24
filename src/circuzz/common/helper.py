import re
from random import Random

from .probability import bernoulli
from .metamorphism import MetamorphicKind
from ..ir.config import GeneratorKind
from ..ir.config import IRConfig
from ..ir.nodes import Circuit
from ..ir.rewrite.rewriter import PointOfInterest
from ..ir.rewrite.rewriter import RuleBasedRewriter
from ..ir.generators.arithmetic import ArithmeticCircuitGenerator
from ..ir.generators.boolean import BooleanCircuitGenerator
from .field import CurvePrime

#
# Defines
#

MAX_256_BITS_INTEGER = (1 << 256) - 1
MAX_64_BITS_INTEGER  = (1 << 64) - 1
MAX_32_BITS_INTEGER  = (1 << 32) - 1

#
# Generation Helper
#

def generate_random_circuit \
    ( curve: CurvePrime
    , exclude_prime: bool
    , config: IRConfig
    , seed: int
    ) -> Circuit:

    match config.generation.generator:
        case GeneratorKind.ARITHMETIC:
            generator = ArithmeticCircuitGenerator(curve, config, seed, exclude_prime)
        case GeneratorKind.BOOLEAN:
            generator = BooleanCircuitGenerator(curve, config, seed, exclude_prime)
        case _:
            raise NotImplementedError(f"unknown generator kind '{config.generation.generator}'")
    circuit = generator.run()
    return circuit

def generate_metamorphic_related_circuit \
    ( kind: MetamorphicKind
    , circuit: Circuit
    , curve: CurvePrime
    , config: IRConfig
    , seed: int
    ) -> tuple[list[PointOfInterest], Circuit]:

    match kind:
        case MetamorphicKind.EQUAL:
            rules = config.rewrite.equivalence
        case MetamorphicKind.WEAKER:
            rules = config.rewrite.equivalence + config.rewrite.weakening
        case _:
            raise NotImplementedError(f"unknown metamorphic kind '{kind}'")
    rewriter = RuleBasedRewriter(curve, config, rules, seed)
    POIs, transformed_circuit = rewriter.run(circuit)
    assert isinstance(transformed_circuit, Circuit), "unexpected root node after rewrite"
    return POIs, transformed_circuit

def random_weighted_metamorphic_kind(rng: Random, weak_pro: float) -> MetamorphicKind:
    if bernoulli(weak_pro, rng):
        return MetamorphicKind.WEAKER
    else:
        return MetamorphicKind.EQUAL

#
# defensive programming helper
#

def assert_circuit_compatibility(circuits: list[Circuit]):
    """
    asserts that the circuits inside the given list
        - DO NOT share the same name
        - share the same amount of output signals
        - share the same amount of input signals
    """

    if len(circuits) < 2:
        return # unable to say anything

    head_element = circuits[0]
    expected_input_size = len(head_element.inputs)
    expected_output_size = len(head_element.outputs)

    seen_names_set = set()
    for element in circuits:
        assert not element.name in seen_names_set, \
            "circuits are not allowed to share the same name"
        assert expected_input_size == len(element.inputs), \
            "miss-matching input vectors"
        assert expected_output_size == len(element.outputs), \
            "miss-matching output vectors"
        seen_names_set.add(element.name)

    # everything was ok!

#
# Terminal Helper
#

def remove_ansi_escape_sequences(string: str) -> str:
    ansi_escape_pattern = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape_pattern.sub('', string)