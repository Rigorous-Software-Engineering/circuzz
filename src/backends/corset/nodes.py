from dataclasses import dataclass

@dataclass
class ASTNode():
    def copy(self) -> 'ASTNode':
        raise NotImplementedError()
@dataclass
class Statement(ASTNode):
    def copy(self) -> 'Statement':
        raise NotImplementedError()
@dataclass
class Expression(ASTNode):
    def copy(self) -> 'Expression':
        raise NotImplementedError()

#
# Definition
#

@dataclass
class Module(ASTNode):
    """
    (module <name>)
    <statements>
    """

    name : str
    statements : list[Statement]

    def copy(self) -> 'Module':
        return Module(self.name, [e.copy() for e in self.statements])

#
# Statement
#

@dataclass
class ListStatement(Statement):
    expr : 'Literal'

    def copy(self) -> 'ListStatement':
        return ListStatement(self.expr.copy())

#
# Expressions
#

@dataclass
class Identifier(Expression):
    name : str

    def copy(self) -> 'Identifier':
        return Identifier(self.name)

@dataclass
class FieldAccess(Expression):
    """
    <expr>.<field>
    """
    expr  : Expression
    field : str

    def copy(self) -> 'FieldAccess':
        return FieldAccess(self.expr.copy(), self.field)


@dataclass
class IndexAccessExpression(Expression):
    """
    <expr>[<index>]
    """
    expr  : Expression
    index : Expression

    def copy(self) -> 'IndexAccessExpression':
        return IndexAccessExpression(self.expr.copy(), self.index.copy())

@dataclass
class Literal(Expression):
    value : int | bool | str | list[ASTNode]

    def copy(self) -> 'Literal':
        if isinstance(self.value, list):
            return Literal([e.copy() for e in self.value])
        return Literal(self.value)

    def is_bool(self) -> bool:
        return isinstance(self.value, bool)

    def is_int(self) -> bool:
        return not self.is_bool() and isinstance(self.value, int)

    def is_str(self) -> bool:
        return isinstance(self.value, str)

    def is_list(self) -> bool:
        return isinstance(self.value, list)
