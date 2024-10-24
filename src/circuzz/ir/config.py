from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .nodes import Operator
from .rewrite.rules import RewriteRule

class GeneratorKind(StrEnum):
    ARITHMETIC = "arithmetic" # see ArithmeticCircuitGenerator
    BOOLEAN    = "boolean"    # see BooleanCircuitGenerator

@dataclass(frozen=True)
class IROpsConfig():
    """
    ir configuration for supported operators
    """

    relations                   : list[Operator]
    boolean_unary_operators     : list[Operator]
    boolean_binary_operators    : list[Operator]
    arithmetic_unary_operators  : list[Operator]
    arithmetic_binary_operators : list[Operator]

    is_arithmetic_ternary_supported : bool
    is_boolean_ternary_supported    : bool

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> 'IROpsConfig':
        relations                   = [Operator(e) for e in value["relations"]]
        boolean_unary_operators     = [Operator(e) for e in value["boolean_unary_operators"]]
        boolean_binary_operators    = [Operator(e) for e in value["boolean_binary_operators"]]
        arithmetic_unary_operators  = [Operator(e) for e in value["arithmetic_unary_operators"]]
        arithmetic_binary_operators = [Operator(e) for e in value["arithmetic_binary_operators"]]

        is_arithmetic_ternary_supported = bool(value["is_arithmetic_ternary_supported"])
        is_boolean_ternary_supported    = bool(value["is_boolean_ternary_supported"])

        return IROpsConfig \
            ( relations = relations
            , boolean_unary_operators = boolean_unary_operators
            , boolean_binary_operators = boolean_binary_operators
            , arithmetic_unary_operators = arithmetic_unary_operators
            , arithmetic_binary_operators = arithmetic_binary_operators
            , is_arithmetic_ternary_supported = is_arithmetic_ternary_supported
            , is_boolean_ternary_supported = is_boolean_ternary_supported
            )

@dataclass(frozen=True)
class IRGenConfig():
    """
    ir configuration for generator
    """

    # specifies which generator to use. This mostly impacts
    # how input signals are treated.
    generator : GeneratorKind

    # weighted probability for generation nodes
    constant_probability_weight : float
    variable_probability_weight : float
    unary_probability_weight    : float
    binary_probability_weight   : float
    relation_probability_weight : float
    ternary_probability_weight  : float

    # generation limits
    max_expression_depth           : int
    min_number_of_assertions       : int
    max_number_of_assertions       : int
    min_number_of_input_variables  : int
    max_number_of_input_variables  : int
    min_number_of_output_variables : int
    max_number_of_output_variables : int

    # random max values
    max_exponent_value : int

    # probability for boundary values
    boundary_value_probability: float

    # probability for using small numbers if it is not a boundary value
    small_upper_bound_probability: float

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> 'IRGenConfig':

        generator = GeneratorKind(str(value["generator"]))

        constant_probability_weight = float(value["constant_probability_weight"])
        variable_probability_weight = float(value["variable_probability_weight"])
        unary_probability_weight    = float(value["unary_probability_weight"])
        binary_probability_weight   = float(value["binary_probability_weight"])
        relation_probability_weight = float(value["relation_probability_weight"])
        ternary_probability_weight  = float(value["ternary_probability_weight"])

        max_expression_depth           = int(value["max_expression_depth"])
        min_number_of_assertions       = int(value["min_number_of_assertions"])
        max_number_of_assertions       = int(value["max_number_of_assertions"])
        min_number_of_input_variables  = int(value["min_number_of_input_variables"])
        max_number_of_input_variables  = int(value["max_number_of_input_variables"])
        min_number_of_output_variables = int(value["min_number_of_output_variables"])
        max_number_of_output_variables = int(value["max_number_of_output_variables"])

        max_exponent_value = int(value["max_exponent_value"])

        boundary_value_probability = float(value["boundary_value_probability"])

        # currently this makes no sense so it is no longer required and defaults to 0
        small_upper_bound_probability = float(value.get("small_upper_bound_probability", 0))

        return IRGenConfig \
            ( generator=generator
            , constant_probability_weight = constant_probability_weight
            , variable_probability_weight = variable_probability_weight
            , unary_probability_weight = unary_probability_weight
            , binary_probability_weight = binary_probability_weight
            , relation_probability_weight = relation_probability_weight
            , ternary_probability_weight = ternary_probability_weight
            , max_expression_depth = max_expression_depth
            , min_number_of_assertions = min_number_of_assertions
            , max_number_of_assertions = max_number_of_assertions
            , min_number_of_input_variables = min_number_of_input_variables
            , max_number_of_input_variables = max_number_of_input_variables
            , min_number_of_output_variables = min_number_of_output_variables
            , max_number_of_output_variables = max_number_of_output_variables
            , max_exponent_value = max_exponent_value
            , boundary_value_probability = boundary_value_probability
            , small_upper_bound_probability = small_upper_bound_probability
            )

@dataclass(frozen=True)
class IRRewriteConfig():

    # probability to apply weakening
    weakening_probability : float

    # number of rewrites
    min_rewrites : int
    max_rewrites : int

    # rewrite rules
    equivalence : list[RewriteRule]
    weakening   : list[RewriteRule]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> 'IRRewriteConfig':
        weakening_probability = float(value["weakening_probability"])
        min_rewrites = int(value["min_rewrites"])
        max_rewrites = int(value["max_rewrites"])
        equivalence = [RewriteRule(r["name"], r["match"], r["rewrite"]) for r in value["rules"]["equivalence"]]
        weakening   = [RewriteRule(r["name"], r["match"], r["rewrite"]) for r in value["rules"]["weakening"]]

        # checks if names rules are occurring multiple times
        rule_names = [r.name for r in equivalence] + [r.name for r in weakening]
        if len(rule_names) != len(set(rule_names)):
            # something is not right, find the colliding names:
            collisions = []
            for name in rule_names:
                if rule_names.count(name) != 1 and not name in collisions:
                    collisions.append(name)
            collisions_str = ", ".join(collisions)
            raise ValueError(f"Rule name collision detected for: {collisions_str}!")
        assert len(rule_names) == len(set(rule_names)), "sanity check"

        return IRRewriteConfig \
            ( weakening_probability = weakening_probability
            , min_rewrites = min_rewrites
            , max_rewrites = max_rewrites
            , equivalence = equivalence
            , weakening = weakening
            )

@dataclass(frozen=True)
class IRConfig():
    rewrite    : IRRewriteConfig
    generation : IRGenConfig
    operators  : IROpsConfig

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> 'IRConfig':
        rewrite    = IRRewriteConfig.from_dict(value["rewrite"])
        generation = IRGenConfig.from_dict(value["generation"])
        operators  = IROpsConfig.from_dict(value["operators"])

        return IRConfig \
            ( rewrite = rewrite
            , generation = generation
            , operators = operators
            )