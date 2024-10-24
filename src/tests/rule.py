import json
import time
from pathlib import Path
from random import Random

from circuzz.common.field import CurvePrime
from circuzz.ir.rewrite.rewriter import RuleBasedRewriter
from circuzz.ir.rewrite.rules import RewriteRule
from circuzz.ir.config import GeneratorKind, IRConfig
from circuzz.ir.generators.arithmetic import ArithmeticCircuitGenerator

RULES_JSON = Path(__file__).parent / ".." / ".." / "res" / "configs" / "rules" / "rules.json"

def ir_to_python(content: str):
    return content \
        .replace("F"  , "False") \
        .replace("T"  , "True" ) \
        .replace("||" , "or"   ) \
        .replace("&&" , "and"  ) \
        .replace("^^" , "!="   ) \
        .replace("! "  , "not "  ) \
        .replace("/"  , "//"   ) # only division will be by 1

def test_rule_rewrites(seed: int, test_rounds: int):

    irConfig = IRConfig.from_dict({ \
        "rewrite" : {
            "weakening_probability" : 0,
            "min_rewrites" : test_rounds,
            "max_rewrites" : test_rounds,
            "rules"     : {
                "equivalence" : [], # empty because we load it from the rules file
                "weakening"   : []  # empty because we load it from the rules file
            }
        },
        "generation": {
            "generator": GeneratorKind.ARITHMETIC,

            "constant_probability_weight" : 1,
            "variable_probability_weight" : 0, # do not use variables inside of expressions
            "unary_probability_weight"    : 1,
            "binary_probability_weight"   : 1,
            "relation_probability_weight" : 1,
            "ternary_probability_weight"  : 0, # do not use ternary as there are no rules

            "max_expression_depth"           : 20,
            "min_number_of_assertions"       : 0,
            "max_number_of_assertions"       : 0,
            "min_number_of_input_variables"  : 0,
            "max_number_of_input_variables"  : 0,
            "min_number_of_output_variables" : 0,
            "max_number_of_output_variables" : 0,

            "max_exponent_value" : 3,
            "boundary_value_probability" : 0.5
        },
        "operators" : {
            "relations"                   : ["<", ">", "<=", ">=", "==", "!="],
            "boolean_unary_operators"     : ["!"],
            "boolean_binary_operators"    : ["&&", "||", "^^"],
            "arithmetic_unary_operators"  : ["-", "~"],
            "arithmetic_binary_operators" : ["+", "-", "*", "**", "^", "&", "|"], # no "/"" and "%"

            "is_arithmetic_ternary_supported" : True,
            "is_boolean_ternary_supported"    : False
        }
    })

    with open(RULES_JSON, "r") as fp:
        rules = [RewriteRule(e["name"], e["match"], e["rewrite"]) \
            for e in json.load(fp)["rules"]["equivalence"]]

    # remove division rule as we cannot be certain that divisor is not 0
    # RULE: inv-div-des: (?a / ?a) --> 1
    rules = list(filter(lambda x: x.name != "inv-div-des", rules))

    rng = Random(seed)

    for test_id in range(test_rounds):
        gen_seed = rng.randint(1000000000,9999999999)
        rew_seed = rng.randint(1000000000,9999999999)

        start = time.time()

        generator = ArithmeticCircuitGenerator(CurvePrime.BN128, irConfig, gen_seed)

        # pick random boolean or integer expression
        if rng.choice([True, False]):
            expression = generator._random_arithmetic_binary_expression()
        else:
            expression = generator._random_boolean_expression()

        rewriter = RuleBasedRewriter(CurvePrime.BN128, irConfig, rules, rew_seed)
        _, transformed = rewriter.run(expression)

        e1 = ir_to_python(str(expression))
        e2 = ir_to_python(str(transformed))

        is_passed = eval(e1) == eval(e2)

        duration = time.time() - start

        if is_passed:
            print(f"test {test_id + 1}: PASSED, time: {round(duration, 3)}s")
        else:
            print(f"test {test_id + 1}: FAILED, time: {round(duration, 3)}s")
            print("---------")
            print(e1)
            print()
            print(e2)
            print("---------")