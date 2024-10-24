from ..config import IRConfig
from ..generators.base import BaseCircuitGenerator
from ..generators.base import ExpressionKind
from ..nodes import *
from ...common.field import CurvePrime

class ArithmeticCircuitGenerator(BaseCircuitGenerator):
    """
    The arithmetic circuit generator treats all input and output variables
    as arithmetic variables. Besides that, all the different expression kinds
    are implemented for boolean and arithmetic expressions.

    Furthermore, relations are only supported for arithmetic expressions.

    All assertions and assumptions are ordered by occurrence, i.e. the first assertion / assumption
    has id "... (id: 0)", the second "... (id: 1)", and so on. This makes it possible to distinguish
    them in the backend.
    """

    # internal generation variable tracker
    _assertion_ordering   : int # NOTE: some backends depend on assertion numbering (e.g. noir)
    _assertion_budget     : int
    _unassigned_variables : list[str]
    _preconditions        : list[Assume]

    def __init__ \
        ( self
        , curve_prime: CurvePrime
        , config: IRConfig
        , seed: float | int | None = None
        , exclude_prime : bool = False
        ):

        super().__init__(curve_prime, config, seed, exclude_prime)

        # init internal variable
        self._assertion_budget = 0
        self._assertion_ordering = 0
        self._unassigned_variables = []
        self._preconditions = []

    def run(self) -> Circuit:
        input_variables_amount = self._rng.randint(
            self._min_number_of_input_variables, self._max_number_of_input_variables)
        output_variables_amount = self._rng.randint(
            self._min_number_of_output_variables, self._max_number_of_output_variables)
        input_variables = ["in" + str(i) for i in range(input_variables_amount)]
        output_variables = ["out" + str(i) for i in range(output_variables_amount)]
        self._arithmetic_variables = input_variables[::]
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

    def _random_boolean_logic_ternary_expression(self, depth: int = 0) -> Expression:
        condition = self._random_boolean_expression(depth + 1)
        true_val = self._random_boolean_expression(depth + 1)
        false_val = self._random_boolean_expression(depth + 1)
        return TernaryExpression(condition, true_val, false_val)

    def _random_relation_expression(self, depth: int = 0) -> BinaryExpression:
        op = self._random_relation()
        lhs = self._random_arithmetic_expression(depth + 1)
        rhs = self._random_arithmetic_expression(depth + 1)
        return BinaryExpression(op, lhs, rhs)

    def _random_boolean_expression(self, depth: int = 0) -> Expression:
        kinds = self._allowed_boolean_expression_kinds(depth)
        kind = self._random_expr_kind_with_weight(kinds)
        match kind:
            case ExpressionKind.CONSTANT:
                return self._random_boolean()
            case ExpressionKind.RELATION:
                return self._random_relation_expression(depth)
            case ExpressionKind.UNARY:
                return self._random_boolean_logic_unary_expression(depth)
            case ExpressionKind.BINARY:
                return self._random_boolean_logic_binary_expression(depth)
            case ExpressionKind.TERNARY:
                return self._random_boolean_logic_ternary_expression(depth)
            case _:
                raise NotImplementedError(f"Unimplemented Boolean Expression {kind}")

    def _random_arithmetic_unary_expression(self, depth: int = 0) -> Expression:
        op = self._random_arithmetic_unary_operation()
        return UnaryExpression(op, self._random_arithmetic_expression(depth + 1))

    def _random_arithmetic_binary_expression(self, depth: int = 0) -> Expression:
        op = self._random_arithmetic_binary_operation()

        # special handling for power (**), right side is constant and limited
        if op == Operator.POW:
            return BinaryExpression(op, self._random_arithmetic_expression(depth + 1), self._random_number_for_pow())

        # special handling for remainder (%) and division (/),
        # right side is either non zero constant or expression with an assumption.
        if op in [Operator.REM, Operator.DIV]:
            if self._rng.choice([True, False]):
                divisor = self._random_non_zero_number()
            else:
                divisor = self._random_arithmetic_expression(depth + 1)
                # if divisor is an expression we need to be careful of div by zero -> precondition
                precondition = BinaryExpression(Operator.NEQ, divisor, Integer(0))
                self._preconditions.append(Assume(precondition, f"division-by-zero (id: {self._assertion_ordering})"))
                self._assertion_ordering += 1
            return BinaryExpression(op, self._random_arithmetic_expression(depth + 1), divisor)

        # default operator
        return BinaryExpression(op, self._random_arithmetic_expression(depth + 1), self._random_arithmetic_expression(depth + 1))

    def _random_arithmetic_ternary_expression(self, depth: int = 0) -> Expression:
        condition = self._random_boolean_expression(depth + 1)
        true_val = self._random_arithmetic_expression(depth + 1)
        false_val = self._random_arithmetic_expression(depth + 1)
        return TernaryExpression(condition, true_val, false_val)

    def _random_arithmetic_expression(self, depth: int = 0) -> Expression:
        kinds = self._allowed_arithmetic_expression_kinds(depth)
        kind = self._random_expr_kind_with_weight(kinds)
        match kind:
            case ExpressionKind.CONSTANT:
                return self._random_number()
            case ExpressionKind.VARIABLE:
                return self._random_arithmetic_variable()
            case ExpressionKind.UNARY:
                return self._random_arithmetic_unary_expression(depth)
            case ExpressionKind.BINARY:
                return self._random_arithmetic_binary_expression(depth)
            case ExpressionKind.TERNARY:
                return self._random_arithmetic_ternary_expression(depth)
            case _:
                raise NotImplementedError(f"Unimplemented Arithmetic Expression {kind}")

    def _random_assignment(self) -> Assignment:
        assert self.__is_unassigned_variable_available(), \
            "no unassigned variables left to create an assignment"
        name = self._unassigned_variables.pop(0)
        assignment = Assignment(Variable(name), self._random_arithmetic_expression())
        self._arithmetic_variables.append(name)
        return assignment

    def _random_assertion(self) -> Assertion:
        assert self._assertion_budget > 0, "no budget left to create an assertion"
        self._assertion_budget -= 1
        condition = self._random_boolean_expression() # visit this first to have a correct assertion id ordering
        assertion_id = self._assertion_ordering
        self._assertion_ordering += 1
        return Assertion(f"assertion (id: {assertion_id})", condition)

    def _random_statements(self) -> list[Statement]:
        statements = []

        for _ in range(len(self._unassigned_variables)):
            assignment = self._random_assignment()
            statements += self._preconditions
            statements.append(assignment)
            self._preconditions = []

        for _ in range(self._assertion_budget):
            assertion = self._random_assertion()
            statements += self._preconditions
            statements.append(assertion)
            self._preconditions = []

        # sanity check
        assert self._assertion_budget == 0, "still available budget for assertions"
        assert len(self._unassigned_variables) == 0, "still pending variable assignments"

        return statements

    def __is_unassigned_variable_available(self) -> bool:
        return len(self._unassigned_variables) > 0