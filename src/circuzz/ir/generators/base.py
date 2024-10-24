from datetime import datetime
from enum import StrEnum
from random import Random

from ...common.probability import weighted_select
from ..config import IRConfig
from ..nodes import *
from ...common.field import CurvePrime
from ...common.field import random_field_element
from ...common.field import random_non_zero_field_element

class ExpressionKind(StrEnum):
    CONSTANT = "constant"
    VARIABLE = "variable"
    UNARY = "unary"
    BINARY = "binary"
    RELATION = "relation"
    TERNARY = "ternary"

class BaseCircuitGenerator():
    """
    This abstract class is the base of an IR generator
    """

    #
    # Randomness
    #

    _seed : int | float
    _rng  : Random

    #
    # Generation specific settings
    #

    # configurations for probability weights
    _constant_probability_weight : float
    _variable_probability_weight : float
    _unary_probability_weight    : float
    _binary_probability_weight   : float
    _relation_probability_weight : float
    _ternary_probability_weight  : float

    # configurations for circuit shape
    _max_expression_depth           : int
    _min_number_of_assertions       : int
    _max_number_of_assertions       : int
    _min_number_of_input_variables  : int
    _max_number_of_input_variables  : int
    _min_number_of_output_variables : int
    _max_number_of_output_variables : int

    # configurations for random values
    _max_exponent_value : int

    # probability to use boundary elements
    _boundary_value_probability : float
    _curve_prime   : CurvePrime
    _exclude_prime : bool

    # probability to use small integers
    _small_upper_bound_probability : float

    #
    # Supported Operators
    #

    _relations                   : list[Operator]
    _boolean_unary_operators     : list[Operator]
    _boolean_binary_operators    : list[Operator]
    _arithmetic_unary_operators  : list[Operator]
    _arithmetic_binary_operators : list[Operator]

    _is_arithmetic_ternary_supported : bool
    _is_boolean_ternary_supported    : bool

    #
    # Available Variables
    #
    # NOTE: these are managed by the specific generators as they depend on
    #       the input.
    #

    _boolean_variables    : list[str]
    _arithmetic_variables : list[str]


    def __init__(self, curve_prime: CurvePrime, config: IRConfig, seed: float | int | None = None, exclude_prime = False):

        # prepare randomness
        self._seed = int(datetime.now().timestamp()) if seed == None else seed
        self._rng = Random(self._seed)

        #
        # flatten config by copying it to locals
        #

        self._constant_probability_weight = config.generation.constant_probability_weight
        self._variable_probability_weight = config.generation.variable_probability_weight
        self._unary_probability_weight    = config.generation.unary_probability_weight
        self._binary_probability_weight   = config.generation.binary_probability_weight
        self._relation_probability_weight = config.generation.relation_probability_weight
        self._ternary_probability_weight  = config.generation.ternary_probability_weight

        #
        # NOTE: Some backends require at least one input or/and one output.
        #       But this should be controlled by the configuration file.
        #

        self._max_expression_depth           = config.generation.max_expression_depth
        self._min_number_of_assertions       = config.generation.min_number_of_assertions
        self._max_number_of_assertions       = config.generation.max_number_of_assertions
        self._min_number_of_input_variables  = config.generation.min_number_of_input_variables
        self._max_number_of_input_variables  = config.generation.max_number_of_input_variables
        self._min_number_of_output_variables = config.generation.min_number_of_output_variables
        self._max_number_of_output_variables = config.generation.max_number_of_output_variables

        self._boundary_value_probability = config.generation.boundary_value_probability
        self._curve_prime = curve_prime
        self._exclude_prime = exclude_prime

        self._small_upper_bound_probability = config.generation.small_upper_bound_probability

        self._max_exponent_value = config.generation.max_exponent_value

        self._relations                   = config.operators.relations
        self._boolean_unary_operators     = config.operators.boolean_unary_operators
        self._boolean_binary_operators    = config.operators.boolean_binary_operators
        self._arithmetic_unary_operators  = config.operators.arithmetic_unary_operators
        self._arithmetic_binary_operators = config.operators.arithmetic_binary_operators

        self._is_arithmetic_ternary_supported = config.operators.is_arithmetic_ternary_supported
        self._is_boolean_ternary_supported    = config.operators.is_boolean_ternary_supported

        #
        # validation of configurations
        #

        assert self._max_number_of_assertions >= self._min_number_of_assertions, \
            "number of maximal and minimal input variables are inconsistent"
        assert self._max_number_of_input_variables >= self._min_number_of_input_variables, \
            "number of maximal and minimal input variables are inconsistent"
        assert self._max_number_of_output_variables >= self._min_number_of_output_variables, \
            "number of maximal and minimal output variables are inconsistent"
        assert self._min_number_of_input_variables >= 0, \
            "number of minimal input variables must not be negative"
        assert self._min_number_of_output_variables >= 0, \
            "number of minimal output variables must not be negative"

        assert (self._constant_probability_weight + self._variable_probability_weight) > 0, \
            "sum of weighted probabilities for leaf nodes must not be 0"

        assert self._max_exponent_value >= 2, "constant number for exponent cannot be smaller than 2"

        #
        # default init of variable lists
        #

        self._boolean_variables     = []
        self._arithmetic_variables  = []


    def run(self) -> Circuit:
        raise NotImplementedError("calling run on the abstract generator class")

    def _random_id(self, size: int) -> str:
        name = ""
        for _ in range(size):
            name += self._rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890")
        return name

    def _random_expr_kind_with_weight(self, allowed_exprs: list[ExpressionKind]) -> ExpressionKind:
        weight_lookup = \
            { ExpressionKind.CONSTANT : self._constant_probability_weight
            , ExpressionKind.VARIABLE : self._variable_probability_weight
            , ExpressionKind.UNARY    : self._unary_probability_weight
            , ExpressionKind.BINARY   : self._binary_probability_weight
            , ExpressionKind.RELATION : self._relation_probability_weight
            , ExpressionKind.TERNARY  : self._ternary_probability_weight
            }
        return weighted_select(allowed_exprs, weight_lookup, self._rng)

    def _random_number_for_pow(self) -> Integer:
        return Integer(self._rng.randint(2, self._max_exponent_value))

    def _random_number(self) -> Integer:
        return Integer(random_field_element(self._curve_prime, self._rng,
            exclude_prime=self._exclude_prime,
            boundary_prob=self._boundary_value_probability,
            small_upper_bound_prob=self._small_upper_bound_probability))

    def _random_non_zero_number(self) -> Integer:
        return Integer(random_non_zero_field_element(self._curve_prime, self._rng,
            boundary_prob=self._boundary_value_probability,
            small_upper_bound_prob=self._small_upper_bound_probability))

    def _random_boolean(self) -> Boolean:
        return Boolean(self._rng.choice([True, False]))

    def _random_boolean_variable(self) -> Variable:
        assert len(self._boolean_variables) > 0, "no boolean variables available"
        return Variable(self._rng.choice(self._boolean_variables))

    def _random_arithmetic_variable(self) -> Variable:
        assert len(self._arithmetic_variables) > 0, "no arithmetic variables available"
        return Variable(self._rng.choice(self._arithmetic_variables))

    def _random_relation(self) -> Operator:
        return self._rng.choice(self._relations)

    def _random_boolean_unary_operation(self) -> Operator:
        return self._rng.choice(self._boolean_unary_operators)

    def _random_boolean_binary_operation(self) -> Operator:
        return self._rng.choice(self._boolean_binary_operators)

    def _random_arithmetic_unary_operation(self) -> Operator:
        return self._rng.choice(self._arithmetic_unary_operators)

    def _random_arithmetic_binary_operation(self) -> Operator:
        return self._rng.choice(self._arithmetic_binary_operators)

    def _allowed_boolean_expression_kinds(self, depth : int) -> list[ExpressionKind]:
        allowed_expr = list()
        allowed_expr.append(ExpressionKind.CONSTANT)
        if len(self._boolean_variables) > 0:
            allowed_expr.append(ExpressionKind.VARIABLE)
        if depth < self._max_expression_depth:
            if len(self._relations) > 0:
                allowed_expr.append(ExpressionKind.RELATION)
            if len(self._boolean_unary_operators):
                allowed_expr.append(ExpressionKind.UNARY)
            if len(self._boolean_binary_operators):
                allowed_expr.append(ExpressionKind.BINARY)
            if self._is_boolean_ternary_supported:
                allowed_expr.append(ExpressionKind.TERNARY)
        return allowed_expr

    def _allowed_arithmetic_expression_kinds(self, depth : int) -> list[ExpressionKind]:
        allowed_expr = list()
        allowed_expr.append(ExpressionKind.CONSTANT)
        if len(self._arithmetic_variables) > 0:
            allowed_expr.append(ExpressionKind.VARIABLE)
        if depth < self._max_expression_depth:
            if len(self._arithmetic_unary_operators):
                allowed_expr.append(ExpressionKind.UNARY)
            if len(self._arithmetic_binary_operators):
                allowed_expr.append(ExpressionKind.BINARY)
            if self._is_arithmetic_ternary_supported:
                allowed_expr.append(ExpressionKind.TERNARY)
        return allowed_expr