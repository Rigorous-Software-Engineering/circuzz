from .operators import Operator
from .operators import SignalKind

from itertools import count

from dataclasses import dataclass
from dataclasses import field

#
#
# Abstract nodes
#

@dataclass
class ASTNode():
    node_id: int = field(default_factory=count().__next__, init=False)

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

@dataclass
class Literal(Expression):
    def copy(self) -> 'Literal':
        raise NotImplementedError()

#
#
# Document Node (Root)
#

@dataclass
class Document(ASTNode):
    """
    pragma circom <version>
    pragma ...

    template ...

    function ...

    component {public <public>} main = ...
    """

    statements : list['Statement']
    main : 'ComponentDefinition'
    public_inputs: list['Expression'] = field(default_factory=list)
    version : str = "2.0.6"
    custom : bool = False

    def copy(self) -> 'Document':
        return Document([s.copy() for s in self.statements], self.main.copy(), [i.copy() for i in self.public_inputs], self.version, self.custom)

#
#
# Basic Blocks
#

@dataclass
class BasicBlock(ASTNode):
    """
    {
        <stmt1>
        <stmt2>
        ...
    }
    """
    statements : list[Statement]

    def copy(self) -> 'BasicBlock':
        return BasicBlock([s.copy() for s in self.statements])


#
#
# Expressions
#

@dataclass
class Identifier(Expression):
    """
    <name>
    """
    name : str

    def copy(self) -> 'Identifier':
        return Identifier(self.name)


@dataclass
class ConditionalExpression(Expression):
    """
    (<condition> ? <true> : <false>)

    This conditional expression is not allowed in a nested form,
    hence can only be used at the top level.
    """
    condition : Expression
    trueVal : Expression
    falseVal : Expression

    def copy(self) -> 'ConditionalExpression':
        return ConditionalExpression(self.condition.copy(), self.trueVal.copy(), self.falseVal.copy())


@dataclass
class BinaryExpression(Expression):
    """
    (<lhs> <operator> <rhs>)
    """
    operator : Operator
    lhs : Expression
    rhs : Expression

    def copy(self) -> 'BinaryExpression':
        return BinaryExpression(self.operator, self.lhs.copy(), self.rhs.copy())

@dataclass
class UnaryExpression(Expression):
    """
    (<operator> <value>)
    """
    operator : Operator
    value : Expression

    def copy(self) -> 'UnaryExpression':
        return UnaryExpression(self.operator, self.value.copy())

@dataclass
class CallExpression(Expression):
    """
    <reference>(<arguments>)
    """
    reference : Expression
    arguments : list[Expression] = field(default_factory=list)

    def copy(self) -> 'CallExpression':
        return CallExpression(self.reference.copy(), [e.copy() for e in self.arguments])

@dataclass
class IndexAccessExpression(Expression):
    """
    <reference>[<index>]
    """
    reference : Expression
    index : Expression

    def copy(self) -> 'IndexAccessExpression':
        return IndexAccessExpression(self.reference.copy(), self.index.copy())

@dataclass
class FieldAccessExpression(Expression):
    """
    <reference>.<field>
    """
    reference : Expression
    field : Identifier

    def copy(self) -> 'FieldAccessExpression':
        return FieldAccessExpression(self.reference.copy(), self.field.copy())

#
#
# Statements
#

@dataclass
class TemplateDefinition(Statement):
    """
    template <name>(<parameter>) <block>
    """
    name : Identifier
    parameters : list[Identifier]
    block : BasicBlock
    custom : bool = False

    def copy(self) -> 'TemplateDefinition':
        return TemplateDefinition(self.name.copy(), [p.copy() for p in self.parameters], self.block.copy(), self.custom)

@dataclass
class IncludeStatement(Statement):
    """
    include 'foo_bar.circom';
    """
    dependency: 'StringLiteral'

    def copy(self) -> 'IncludeStatement':
        return IncludeStatement(self.dependency.copy())

@dataclass
class VariableDefinition(Statement):
    """
    var <name> = <value>;
    var <name>; # if <value> == None
    var <name>[<size>] = <value>;
    var <name>[<size>]; # if <value> == None
    """
    name : Identifier
    sizes : list[Expression] = field(default_factory=list)
    value : Expression | None = None

    def copy(self) -> 'VariableDefinition':
        return VariableDefinition(self.name.copy(), [s.copy() for s in self.sizes], None if self.value == None else self.value.copy())

    @property
    def is_array(self) -> bool:
        return len(self.sizes) > 0

@dataclass
class SignalDefinition(Statement):
    """
    signal <kind> <name> = <operator> <value>;
    signal <kind> <name>;
    """
    name : Identifier
    kind : SignalKind
    sizes : list[Expression] = field(default_factory=list)
    value : Expression | None = None

    def copy(self) -> 'SignalDefinition':
        return SignalDefinition(self.name.copy(), self.kind, [s.copy() for s in self.sizes], None if self.value == None else self.value.copy())

    @property
    def is_array(self) -> bool:
        return len(self.sizes) > 0

    @property
    def is_input(self) -> bool:
        return self.kind == SignalKind.INPUT


@dataclass
class ComponentDefinition(Statement):
    """
    component <name> = <value>;
    component <name>;
    """
    name : Identifier
    sizes : list[Expression] = field(default_factory=list)
    value : Expression | None = None

    def copy(self) -> 'ComponentDefinition':
        return ComponentDefinition(self.name.copy(), [s.copy() for s in self.sizes], None if self.value == None else self.value.copy())

    @property
    def is_array(self) -> bool:
        return len(self.sizes) > 0

@dataclass
class AssignmentOrConstraint(Statement):
    """
    <name> <operator> <value>;
    """
    operator : Operator
    name : Expression
    value : Expression

    def copy(self) -> 'AssignmentOrConstraint':
        return AssignmentOrConstraint(self.operator, self.name.copy(), self.value.copy())

@dataclass
class IfStatement(Statement):
    """
    if (<condition>) <block>
    """
    condition : Expression
    ifBlock : BasicBlock
    elseBlock : BasicBlock | None = None

    def copy(self) -> 'IfStatement':
        return IfStatement(self.condition.copy(), self.ifBlock.copy(), None if self.elseBlock == None else self.elseBlock.copy())

@dataclass
class ForStatement(Statement):
    """
    for (<init>; <condition>; <step>) <block>
    """
    init : Statement
    condition : Expression
    step : Statement
    block : BasicBlock

    def copy(self) -> 'ForStatement':
        return ForStatement(self.init.copy(), self.condition.copy(), self.step.copy(), self.block.copy())


@dataclass
class WhileStatement(Statement):
    """
    while (<condition>)<block>
    """
    condition : Expression
    block : BasicBlock

    def copy(self) -> 'WhileStatement':
        return WhileStatement(self.condition.copy(), self.block.copy())


@dataclass
class AssertStatement(Statement):
    """
    assert(<condition>)
    """
    condition : Expression
    message : str | None = None

    def copy(self) -> 'AssertStatement':
        return AssertStatement(self.condition.copy())

@dataclass
class LogStatement(Statement):
    """
    log(<arguments>)
    """
    arguments : list[Expression]

    def copy(self) -> 'LogStatement':
        return LogStatement(self.arguments.copy())

#
#
# Literals
#

@dataclass
class IntegerLiteral(Literal):
    value : int

    def copy(self) -> 'IntegerLiteral':
        return IntegerLiteral(self.value)

@dataclass
class StringLiteral(Literal):
    value : str

    def copy(self) -> 'StringLiteral':
        return StringLiteral(self.value)

@dataclass
class ListLiteral(Literal):
    value : list[Expression] = field(default_factory=list)

    def copy(self) -> 'ListLiteral':
        return ListLiteral([v.copy() for v in self.value])