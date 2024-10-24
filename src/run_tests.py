#!/bin/python3

from random import Random
import time

from tests.circom import test_circom_generator as circom_generator_test
from tests.corset import test_corset_generator as corset_generator_test
from tests.gnark import test_gnark_generator as gnark_generator_test
from tests.ir import test_ir_generator as ir_generator_test
from tests.noir import test_noir_generator as noir_generator_test
from tests.rule import test_rule_rewrites as rule_rewrites_test

def main(seed: int):
    rng = Random(seed)
    circom_generator_test(rng.randint(0, 10000000))
    corset_generator_test(rng.randint(0, 10000000))
    gnark_generator_test(rng.randint(0, 10000000))
    ir_generator_test(rng.randint(0, 10000000))
    noir_generator_test(rng.randint(0, 10000000))
    rule_rewrites_test(rng.randint(0, 10000000), 10)

if __name__ == "__main__":
    main(seed=int(time.time() * 1000))