
from ..visitors.base import ASTWalker
from ..nodes import *

class NodeReplacer(ASTWalker):

    """
    Given a parent node, it traverses the ir and tries to replace
    a unique origin node with its replacement. If the replacement
    was successful function returns true. If the replacement was
    unsuccessful due to not finding the origin it returns false.

    IMPORTANT:
        - the origin node MUST NOT be the parent!
        - this only works on a proper initialized IR as
          the node id is taken for comparison
        - once the replacement is done, it tries to break out
          of the recursive visit.
    """

    def replace(self, parent: IRNode, origin: IRNode, replacement: IRNode) -> bool:
        self.__origin = origin
        self.__replacement = replacement
        self.__replaced = False
        super().visit(parent)
        return self.__replaced

    def visit_binary_expression(self, node: BinaryExpression):
        if self.__replaced:
            return # abort

        if node.lhs == self.__origin and isinstance(self.__replacement, Expression):
            node.lhs = self.__replacement
            self.__replaced = True
            return # abort

        if node.rhs == self.__origin and isinstance(self.__replacement, Expression):
            node.rhs = self.__replacement
            self.__replaced = True
            return # abort

        super().visit(node.lhs)
        super().visit(node.rhs)

    def visit_unary_expression(self, node: UnaryExpression):
        if self.__replaced:
            return # abort

        if node.value == self.__origin and isinstance(self.__replacement, Expression):
            node.value = self.__replacement
            self.__replaced = True
            return # abort

        super().visit(node.value)

    def visit_ternary_expression(self, node: TernaryExpression):
        if self.__replaced:
            return # abort

        if node.condition == self.__origin and isinstance(self.__replacement, Expression):
            node.condition = self.__replacement
            self.__replaced = True
            return # abort

        if node.if_expr == self.__origin and isinstance(self.__replacement, Expression):
            node.if_expr = self.__replacement
            self.__replaced = True
            return # abort

        if node.else_expr == self.__origin and isinstance(self.__replacement, Expression):
            node.else_expr = self.__replacement
            self.__replaced = True
            return # abort

        super().visit(node.condition)
        super().visit(node.if_expr)
        super().visit(node.else_expr)

    def visit_assignment(self, node: Assignment):
        if self.__replaced:
            return # abort

        if node.lhs == self.__origin and isinstance(self.__replacement, Variable):
            node.lhs = self.__replacement
            self.__replaced = True
            return # abort

        if node.rhs == self.__origin and isinstance(self.__replacement, Expression):
            node.rhs = self.__replacement
            self.__replaced = True
            return # abort

        super().visit(node.lhs)
        super().visit(node.rhs)

    def visit_assertion(self, node: Assertion):
        if self.__replaced:
            return # abort

        if node.value == self.__origin and isinstance(self.__replacement, Expression):
            node.value = self.__replacement
            self.__replaced = True
            return # abort

        super().visit(node.value)

    def visit_assume(self, node: Assume):
        pass # skip over assume statements

    def visit_circuit(self, node: Circuit):
        replacement_index = None
        for idx, s in enumerate(node.statements):
            if s == self.__origin:
                replacement_index = idx
                break
            super().visit(s)
            if self.__replaced:
                return # abort

        if not replacement_index == None and isinstance(self.__replacement, Statement):
            node.statements[replacement_index] = self.__replacement
            self.__replaced = True
