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
# Definitions
#

@dataclass
class CircuitStructField(ASTNode):
    """
    <name> frontend.Variable
    <name> frontend.Variable `gnark:",public"`
    """
    name      : str
    is_public : bool # currently only 'output' variables are public

    def copy(self) -> 'CircuitStructField':
        return CircuitStructField(self.name, self.is_public)

@dataclass
class CircuitStruct(ASTNode):
    """
    type <name> struct {
        <field-1>
        <field-2>
        ...
    }
    """
    name   : str
    fields : list[CircuitStructField]

    def copy(self) -> 'CircuitStruct':
        return CircuitStruct(self.name, [e.copy() for e in self.fields])

@dataclass
class CircuitDefineFunction(ASTNode):
    """
    func (circuit *<name>) Define(api frontend.API) error { ... }
    """
    name       : str
    statements : list[Statement]

    def copy(self) -> 'CircuitDefineFunction':
        return CircuitDefineFunction(self.name, [e.copy() for e in self.statements])

@dataclass
class CircuitDefinitionCollection(ASTNode):
    """
    type <name> struct { ... }

    func (circuit *<name>) Define(api frontend.API) error { ... }
    """
    name           : str
    circuit_struct : CircuitStruct
    circuit_define : CircuitDefineFunction

    def copy(self) -> 'CircuitDefinitionCollection':
        return CircuitDefinitionCollection(self.name, self.circuit_struct.copy(), self.circuit_define.copy())

#
# Statement
#

@dataclass
class CallStatement(Statement):
    expr : 'CallExpression'

    def copy(self) -> 'CallStatement':
        return CallStatement(self.expr.copy())

@dataclass
class AssignStatement(Statement):
    """
    <lhs> = <rhs>
    <lhs> := <rhs>
    """
    lhs : Expression
    rhs : Expression
    is_definition : bool = False

    def copy(self) -> 'AssignStatement':
        return AssignStatement(self.lhs.copy(), self.rhs.copy(), self.is_definition)

@dataclass
class ForLoop(Statement):
    """
    for i := <start>; i < <end>; i++ { <body> }
    """
    start     : Expression
    end       : Expression
    body      : list[Statement]
    index_var : str = "i"

    def copy(self) -> 'ForLoop':
        return ForLoop(self.start.copy(), self.end.copy(),
            [e.copy() for e in self.body], self.index_var)

#
# Expressions
#

@dataclass
class Identifier(Expression):
    name : str

    def copy(self) -> 'Identifier':
        return Identifier(self.name)

@dataclass
class FieldAccessExpression(Expression):
    """
    <expr>.<field>
    """
    expr  : Expression
    field : str

    def copy(self) -> 'FieldAccessExpression':
        return FieldAccessExpression(self.expr.copy(), self.field)

@dataclass
class CallExpression(Expression):
    """
    <expr>(<args>)
    """
    expr : Expression
    args : list[Expression]

    def copy(self) -> 'CallExpression':
        return CallExpression(self.expr.copy(), [e.copy() for e in self.args])

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
    value : int | bool | str

    def copy(self) -> 'Literal':
        return Literal(self.value)

    def is_bool(self) -> bool:
        return isinstance(self.value, bool)

    def is_int(self) -> bool:
        return not self.is_bool() and isinstance(self.value, int)

    def is_str(self) -> bool:
        return isinstance(self.value, str)
