from ..config import IRConfig
from ..generators.base import BaseCircuitGenerator
from ..generators.base import ExpressionKind
from ..nodes import *
from ...common.field import CurvePrime

class BooleanCircuitGenerator(BaseCircuitGenerator):
    """
    The Boolean circuit generator treats all input and output variables
    as boolean variables. Even if arithmetic operations are available,
    this generator will only produce boolean expressions.

    Furthermore, relations are only supported for boolean expressions.

    All assertions and assumptions are ordered by occurrence, i.e. the first assertion / assumption
    has id "... (id: 0)", the second "... (id: 1)", and so on. This makes it possible to distinguish
    them in the backend.
    """

    # internal generation variable tracker
    _assertion_ordering   : int # NOTE: some backends depend on assertion numbering (e.g. noir)
    _assertion_budget     : int
    _unassigned_variables : list[str]

    def __init__ \
        ( self
        , curve_prime: CurvePrime
        , config: IRConfig
        , seed: float | int | None = None
        , exclude_prime: bool = False
        ):

        super().__init__(curve_prime, config, seed, exclude_prime)

        # internal variable
        self._assertion_budget = 0
        self._assertion_ordering = 0
        self._unassigned_variables = []

    def run(self) -> Circuit:
        input_variables_amount = self._rng.randint(
            self._min_number_of_input_variables, self._max_number_of_input_variables)
        output_variables_amount = self._rng.randint(
            self._min_number_of_output_variables, self._max_number_of_output_variables)
        input_variables = ["in" + str(i) for i in range(input_variables_amount)]
        output_variables = ["out" + str(i) for i in range(output_variables_amount)]
        self._boolean_variables = input_variables[::]
        self._assertion_budget = self._rng.randint(self._min_number_of_assertions, self._max_number_of_assertions)
        self._assertion_ordering = 0
        self._unassigned_variables = output_variables[::]

        statements = self._random_statements()

        circuit_name = f"circuit_{self._random_id(10)}"
        return Circuit(circuit_name, input_variables, output_variables, statements)

    def _random_boolean_logic_unary_expression(self, depth: int = 0) -> Expression:
        op = self._random_boolean_unary_operation()
        return UnaryExpression(op, self._random_boolean_expression(depth + 1))

    def _random_boolean_logic_binary_expression(self, depth: int = 0) -> Expression:
        op = self._random_boolean_binary_operation()
        lhs = self._random_boolean_expression(depth + 1)
        rhs = self._random_boolean_expression(depth + 1)
        return BinaryExpression(op, lhs, rhs)

    def _random_boolean_logic_relation_expression(self, depth: int = 0) -> Expression:
        op = self._random_relation()
        lhs = self._random_boolean_expression(depth + 1)
        rhs = self._random_boolean_expression(depth + 1)
        return BinaryExpression(op, lhs, rhs)

    def _random_boolean_logic_ternary_expression(self, depth: int = 0) -> Expression:
        cond = self._random_boolean_expression(depth + 1)
        if_expr = self._random_boolean_expression(depth + 1)
        else_expr = self._random_boolean_expression(depth + 1)
        return TernaryExpression(cond, if_expr, else_expr)

    def _random_boolean_expression(self, depth: int = 0) -> Expression:
        kinds = self._allowed_boolean_expression_kinds(depth)
        kind = self._random_expr_kind_with_weight(kinds)
        match kind:
            case ExpressionKind.CONSTANT:
                return self._random_boolean()
            case ExpressionKind.VARIABLE:
                return self._random_boolean_variable()
            case ExpressionKind.UNARY:
                return self._random_boolean_logic_unary_expression(depth)
            case ExpressionKind.BINARY:
                return self._random_boolean_logic_binary_expression(depth)
            case ExpressionKind.RELATION:
                return self._random_boolean_logic_relation_expression(depth)
            case ExpressionKind.TERNARY:
                return self._random_boolean_logic_ternary_expression(depth)
            case _:
                raise NotImplementedError(f"Unimplemented Boolean Expression {kind}")

    def _random_assignment(self) -> Assignment:
        assert self.__is_unassigned_variable_available(), \
            "no unassigned variables left to create an assignment"
        name = self._unassigned_variables.pop(0)
        assignment = Assignment(Variable(name), self._random_boolean_expression())
        self._boolean_variables.append(name)
        return assignment

    def _random_assertion(self) -> Assertion:
        assert self._assertion_budget > 0, "no budget left to create an assertion"
        self._assertion_budget -= 1
        assertion = Assertion(f"assertion-{self._assertion_ordering}", self._random_boolean_expression())
        self._assertion_ordering += 1
        return assertion

    def _random_statements(self) -> list[Statement]:
        statements = []

        for _ in range(len(self._unassigned_variables)):
            statements.append(self._random_assignment())

        for _ in range(self._assertion_budget):
            statements.append(self._random_assertion())

        # sanity check
        assert self._assertion_budget == 0, "still available budget for assertions"
        assert len(self._unassigned_variables) == 0, "still pending variable assignments"

        return statements

    def __is_unassigned_variable_available(self) -> bool:
        return len(self._unassigned_variables) > 0