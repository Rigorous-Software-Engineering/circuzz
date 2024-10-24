
from ..nodes import IRNode
from ..nodes import Assume
from ..nodes import Variable
from ..nodes import Boolean
from ..nodes import Integer
from ..nodes import UnaryExpression
from ..nodes import BinaryExpression
from ..nodes import TernaryExpression
from ..nodes import Assertion
from ..nodes import Assignment
from ..nodes import Assume
from ..nodes import Circuit

class EmptyVisitor():
    def visit(self, node: IRNode):
        match node:
            case Variable():
                self.visit_variable(node)
            case Boolean():
                self.visit_boolean(node)
            case Integer():
                self.visit_integer(node)
            case UnaryExpression():
                self.visit_unary_expression(node)
            case BinaryExpression():
                self.visit_binary_expression(node)
            case TernaryExpression():
                self.visit_ternary_expression(node)
            case Assertion():
                self.visit_assertion(node)
            case Assignment():
                self.visit_assignment(node)
            case Assume():
                self.visit_assume(node)
            case Circuit():
                self.visit_circuit(node)
            case _:
                raise NotImplementedError()
    def visit_variable(self, node: Variable):
        pass
    def visit_boolean(self, node: Boolean):
        pass
    def visit_integer(self, node: Integer):
        pass
    def visit_unary_expression(self, node: UnaryExpression):
        pass
    def visit_binary_expression(self, node: BinaryExpression):
        pass
    def visit_ternary_expression(self, node: TernaryExpression):
        pass
    def visit_assertion(self, node: Assertion):
        pass
    def visit_assignment(self, node: Assignment):
        pass
    def visit_assume(self, node: Assume):
        pass
    def visit_circuit(self, node: Circuit):
        pass

class ASTWalker(EmptyVisitor):
    def visit_variable(self, node: Variable):
        pass
    def visit_boolean(self, node: Boolean):
        pass
    def visit_integer(self, node: Integer):
        pass
    def visit_unary_expression(self, node: UnaryExpression):
        self.visit(node.value)
    def visit_binary_expression(self, node: BinaryExpression):
        self.visit(node.lhs)
        self.visit(node.rhs)
    def visit_ternary_expression(self, node: TernaryExpression):
        self.visit(node.condition)
        self.visit(node.if_expr)
        self.visit(node.else_expr)
    def visit_assertion(self, node: Assertion):
        self.visit(node.value)
    def visit_assignment(self, node: Assignment):
        self.visit(node.lhs)
        self.visit(node.rhs)
    def visit_assume(self, node: Assume):
        self.visit(node.condition)
    def visit_circuit(self, node: Circuit):
        for statement in node.statements:
            self.visit(statement)
