from circuzz.ir import nodes as IRNodes

from .nodes import *

class IR2CorsetVisitor():

    """
    Transforms the IR to a corset program.

    NOTE: To ignore corset's zero-padding we add an additional column to the
          defined columns, i.e. input signals, which needs a non zero value for all
          desired rows we want to check. To achieve the behavior, every constraint is
          then prefixed by an "if-not-zero-then" statement using this column as argument.
          This is also IMPORTANT to be reflected in the trace file. As default name we use
          ST for STAMP.
    """

    # guards the constraints with a if-non-zero, to exclude zero padding
    GUARD_VARIABLE = "ST"

    __use_guard_variable: bool

    def __init__(self, use_guard_variable: bool):
        self.__use_guard_variable = use_guard_variable

    def transform(self, system: IRNodes.Circuit) -> Module:
       return self.visit_circuit(system)

    def constraint(self, system: IRNodes.Circuit) -> ListStatement:
       return self._circuit_to_constraint(system.name, system)

    def columns(self, system: IRNodes.Circuit) -> ListStatement:
       return self._circuit_to_columns(system)

    def visit_expression(self, node: IRNodes.IRNode) -> Expression:
        match node:
            case IRNodes.Variable():
                return self.visit_variable(node)
            case IRNodes.Boolean():
                return self.visit_boolean(node)
            case IRNodes.Integer():
                return self.visit_integer(node)
            case IRNodes.UnaryExpression():
                return self.visit_unary_expression(node)
            case IRNodes.BinaryExpression():
                return self.visit_binary_expression(node)
            case IRNodes.TernaryExpression():
                return self.visit_ternary_expression(node)
            case _:
                raise NotImplementedError()

    def visit_statement(self, node: IRNodes.IRNode, previous: Expression | None) -> Expression:
        match node:
            case IRNodes.Assertion():
                return self.visit_assertion(node, previous)
            case IRNodes.Assignment():
                return self.visit_assignment(node, previous)
            # case IRNodes.Assume():
            #     return self.visit_assume(node)
            case _:
                raise NotImplementedError()

    def visit_variable(self, node: IRNodes.Variable) -> Expression:
        return Identifier(node.name)

    def visit_boolean(self, node: IRNodes.Boolean) -> Expression:
        # treat every boolean as loobean which is why 0 and 1 is switched
        return Literal(0) if node.value else Literal(1)

    def visit_integer(self, node: IRNodes.Integer) -> Expression:
        return Literal(node.value)

    def visit_unary_expression(self, node: IRNodes.UnaryExpression) -> Expression:
        expr = self.visit_expression(node.value)
        if node.op == IRNodes.Operator.NOT and node.is_boolean_expression():
            return self._is_not_zero_as_loob(expr)
        raise NotImplementedError(f"Unary expression is not supported '{node}'")

    def visit_binary_expression(self, node: IRNodes.BinaryExpression) -> Expression:
        lhs = self.visit_expression(node.lhs)
        rhs = self.visit_expression(node.rhs)

        match node.op:
            case IRNodes.Operator.EQU:
                return self._eq(lhs, rhs)
            case IRNodes.Operator.NEQ:
                return self._neq(lhs, rhs)
            case IRNodes.Operator.LAND:
                return self._and_normalized(lhs, rhs)
            case IRNodes.Operator.LOR:
                return self._or_normalized(lhs, rhs)
            case _:
                raise NotImplementedError(f"binary operator {node.op.value}")

    def visit_ternary_expression(self, node: IRNodes.TernaryExpression) -> Expression:
        cond = self._is_zero_as_bool(self.visit_expression(node.condition))
        if_expr = self.visit_expression(node.if_expr)
        else_expr = self.visit_expression(node.else_expr)
        return self._if_else(cond, if_expr, else_expr)

    def visit_assertion(self, node: IRNodes.Assertion, previous: Expression | None) -> Expression:
        value = self.visit_expression(node.value)
        if previous == None:
            return value
        else:
            return self._and(value, previous)

    def visit_assignment(self, node: IRNodes.Assignment, previous: Expression | None) -> Expression:
        lhs = self.visit_expression(node.lhs)
        rhs = self.visit_expression(node.rhs)

        binding : list[ASTNode] = []
        binding.append(Identifier("let"))
        binding.append(Literal([Literal([lhs, rhs])]))
        binding.append(self._vanishes(Literal(0)) if previous == None else previous) # vanish is required for loobean

        return Literal(binding)

    def visit_assume(self, node: IRNodes.Assume) -> Expression:
        raise NotImplementedError("assumptions are not supported for corset")

    def visit_circuit(self, node: IRNodes.Circuit) -> Module:
        module_stmts : list[Statement] = []
        if len(node.inputs) > 0:
            module_stmts.append(self._circuit_to_columns(node))
        module_stmts.append(self._circuit_to_constraint("main-constraint", node))
        module = Module(node.name, module_stmts)
        return module

    #
    # Helper
    #

    def _circuit_to_columns(self, node: IRNodes.Circuit) -> ListStatement:
        columns : list[ASTNode] = []
        columns.append(Identifier("defcolumns"))
        for e in node.inputs:
            columns.append(Identifier(e))
        if self.__use_guard_variable:
            columns.append(Identifier(self.GUARD_VARIABLE)) # NOTE: this is used to ignore the zero padding
        return ListStatement(Literal(columns))

    def _circuit_to_constraint(self, constraint_name: str, node: IRNodes.Circuit) -> ListStatement:
        previous = None
        for stmt in reversed(node.statements):
            previous = self.visit_statement(stmt, previous)
        if previous == None:
            previous = Literal(0) # true (0) if no constraints
        previous = self._vanishes(previous) # always vanish

        constraint : list[ASTNode] = []
        constraint.append(Identifier("defconstraint"))
        constraint.append(Identifier(constraint_name))
        constraint.append(Literal([]))

        if self.__use_guard_variable:
            constraint.append(self._constraint_guard(previous))
        else:
            constraint.append(previous)

        return ListStatement(Literal(constraint))


    def _func_call(self, func: str, args: list[Expression]) -> Expression:
        _list = []
        _list.append(Identifier(func))
        _list += args
        return Literal(_list)

    def _is_not_zero_as_loob(self, value: Expression) -> Expression:
        return self._func_call("is-not-zero!", [value])

    def _is_zero_as_bool(self, value: Expression) -> Expression:
        return self._func_call("is-zero", [value])

    def _eq(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._func_call("eq!", [lhs, rhs])

    def _neq(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._func_call("neq!", [lhs, rhs])

    def _and(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._func_call("and!", [lhs, rhs])

    def _or(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._func_call("or!", [lhs, rhs])

    def _and_normalized(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._func_call("~and!", [lhs, rhs])

    def _or_normalized(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._func_call("~or!", [lhs, rhs])

    def _if_else(self, cond: Expression, if_expr: Expression, else_expr: Expression) -> Expression:
        return self._func_call("if", [cond, if_expr, else_expr])

    def _let(self, var: Expression, value: Expression, expr: Expression) -> Expression:
        return self._func_call("let", [Literal([Literal([var, value]), expr])])

    def _chain_stmts(self, stmts: list[Expression]) -> Expression:
        return self._func_call("begin", stmts)

    def _vanishes(self, value: Expression) -> Expression:
        return self._func_call("vanishes!", [value])
   
    def _if_not_zero(self, cond: Expression, if_expr: Expression) -> Expression:
        return self._func_call("if-not-zero", [cond, if_expr])

    def _constraint_guard(self, expr: Expression) -> Expression:
        return self._if_not_zero(Identifier(self.GUARD_VARIABLE), expr)