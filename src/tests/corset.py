from circuzz.common.field import CurvePrime
from circuzz.common.helper import generate_random_circuit
from backends.corset.nodes import Module
from backends.corset.emitter import EmitVisitor
from backends.corset.ir2corset import IR2CorsetVisitor
from circuzz.ir.config import GeneratorKind, IRConfig

def test_corset_generator(seed: int):

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
            "generator": GeneratorKind.BOOLEAN,

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
            "relations"                   : ["==", "!="],
            "boolean_unary_operators"     : ["!"],
            "boolean_binary_operators"    : ["&&", "||"],
            "arithmetic_unary_operators"  : [],
            "arithmetic_binary_operators" : [],

            "is_arithmetic_ternary_supported" : False,
            "is_boolean_ternary_supported"    : True
        }
    })

    circuit = generate_random_circuit(CurvePrime.BLS12_377, False, irConfig, seed)
    circuit.name = "original"

    transformer = IR2CorsetVisitor(use_guard_variable=True)

    # build up the base module
    corset_module = Module("corset-test", [])
    columns = transformer.columns(circuit)
    corset_module.statements.append(columns)

    # start constraints
    original_constraint = transformer.constraint(circuit)
    corset_module.statements.append(original_constraint)

    circuit_comment = ";; " + str(circuit).replace("\n", "\n;; ")
    print(circuit_comment)
    print()
    print(EmitVisitor().emit(corset_module))