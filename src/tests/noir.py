import random
from circuzz.common.field import CurvePrime
from circuzz.common.helper import generate_random_circuit
from backends.noir.emitter import EmitVisitor
from backends.noir.ir2noir import IR2NoirVisitor
from circuzz.ir.config import GeneratorKind, IRConfig

def test_noir_generator(seed: int):
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
            "arithmetic_unary_operators"  : ["-"],
            "arithmetic_binary_operators" : ["+", "-", "*", "/", "^", "&", "|"],

            "is_arithmetic_ternary_supported" : True,
            "is_boolean_ternary_supported"    : False
        }
    })

    circuit = generate_random_circuit(CurvePrime.BN128, True, irConfig, seed)

    print(circuit)
    print()

    if random.random() > 0.5:
        nargo_version = (0, 30, 0)
    else:
        nargo_version = (0, 34, 0)

    circom = IR2NoirVisitor(CurvePrime.BN128, nargo_version).transform(circuit)
    emitter = EmitVisitor()

    print(emitter.emit(circom))