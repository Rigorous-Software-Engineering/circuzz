from circuzz.common.field import CurvePrime
from circuzz.common.helper import generate_random_circuit
from backends.circom.emitter import EmitVisitor
from backends.circom.ir2circom import IR2CircomVisitor
from circuzz.ir.config import GeneratorKind, IRConfig

from random import Random

def test_circom_generator(seed: int):

    irConfig = IRConfig.from_dict({ \
        "rewrite"  : {
            "weakening_probability" : 0,
            "min_rewrites" : 0,
            "max_rewrites" : 0,
            "rules" : {
                "equivalence" : [],
                "weakening" :[]
            }
        },
        "generation": {
            "generator": GeneratorKind.ARITHMETIC,

            "constant_probability_weight" : 1,
            "variable_probability_weight" : 1,
            "unary_probability_weight"    : 1,
            "binary_probability_weight"   : 1,
            "relation_probability_weight" : 1,
            "ternary_probability_weight"  : 1,

            "max_expression_depth"           : 2,
            "min_number_of_assertions"       : 1,
            "max_number_of_assertions"       : 2,
            "min_number_of_input_variables"  : 1,
            "max_number_of_input_variables"  : 2,
            "min_number_of_output_variables" : 1,
            "max_number_of_output_variables" : 2,

            "max_exponent_value" : 2,
            "boundary_value_probability" : 0.5
        },
        "operators" : {
            "relations"                   : ["<", ">", "<=", ">=", "==", "!="],
            "boolean_unary_operators"     : ["!"],
            "boolean_binary_operators"    : ["&&", "||", "^^"],
            "arithmetic_unary_operators"  : ["-", "~"],
            "arithmetic_binary_operators" : ["+", "-", "*", "**", "/", "%", "^", "&", "|"],

            "is_arithmetic_ternary_supported" : True,
            "is_boolean_ternary_supported"    : False
        }
    })

    circuit = generate_random_circuit(CurvePrime.BN128, False, irConfig, seed)

    print(circuit)
    print()

    rng = Random(seed)
    constraint_assignment_probability = 0.5
    circom = IR2CircomVisitor(constraint_assignment_probability, rng).transform(circuit)
    emitter = EmitVisitor()

    print(emitter.emit(circom))