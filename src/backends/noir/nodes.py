from dataclasses import dataclass
from dataclasses import field

from .types import NoirType
from .operators import NoirOperator

@dataclass
class ASTNode():
    def copy(self) -> 'ASTNode':
        raise NotImplementedError()

#
# Expressions
#

@dataclass
class Expression(ASTNode):
    def copy(self) -> 'Expression':
        raise NotImplementedError()

@dataclass
class Identifier(Expression):
    """
    identifier for any kind of variable or reference
    """
    name: str

    def copy(self) -> 'Identifier':
        return Identifier(self.name)

@dataclass
class BinaryExpression(Expression):
    """
    (<lhs> <op> <rhs>)
    """
    operator: NoirOperator
    lhs: Expression
    rhs: Expression

    def copy(self) -> 'BinaryExpression':
        return BinaryExpression(self.operator, self.lhs.copy(), self.rhs.copy())

@dataclass
class UnaryExpression(Expression):
    """
    (<op> <value>)
    """
    operator: NoirOperator
    value: Expression

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
# Statements
#

@dataclass
class Statement(ASTNode):
    def copy(self) -> 'Statement':
        raise NotImplementedError()

@dataclass
class BasicBlock(Statement):
    """
    { <statements> }
    """
    statements: list[Statement]

    def copy(self) -> 'BasicBlock':
        return BasicBlock([e.copy() for e in self.statements])

@dataclass
class IfStatement(Statement):
    """
    if <condition>
        <true_stmt>
    else
        <false_stmt>
    , where the else part and `false_stmt` is optional
    """
    condition: Expression
    true_stmt: Statement
    false_stmt: Statement | None

    def copy(self) -> 'IfStatement':
        return IfStatement \
            ( self.condition.copy()
            , self.true_stmt.copy()
            , self.false_stmt.copy() if self.false_stmt else None
            )

@dataclass
class ForStatement(Statement):
    """
    for <index> in <start> .. <end> {
        <stmts>
    }
    """
    index: Identifier
    start: Expression
    end: Expression
    statements: list[Statement]

    def copy(self) -> 'ForStatement':
        return ForStatement \
            ( self.index.copy()
            , self.start.copy()
            , self.end.copy()
            , [e.copy() for e in self.statements]
            )

@dataclass
class LetStatement(Statement):
    """
    let <name>;
    let <name> : <type>;
    let mut <name>;
    let mut <name> : <type>;
    let <name> = <expr>;
    let <name> : <type> = <expr>;
    let mut <name> = <expr>;
    let mut <name> : <type> = <expr>;
    """
    name: Identifier
    expr: Expression | None = None
    type_: NoirType | None = None
    is_mutable: bool = False

    def copy(self) -> 'LetStatement':
        return LetStatement \
            ( self.name.copy()
            , self.expr.copy() if self.expr else None
            , self.type_.copy() if self.type_ else None
            , self.is_mutable
            )

@dataclass
class AssignStatement(Statement):
    """
    <name> = <expr>;
    """
    lhs: Expression
    rhs: Expression

    def copy(self) -> 'AssignStatement':
        return AssignStatement(self.lhs.copy(), self.rhs.copy())

@dataclass
class AssertStatement(Statement):
    """
    assert(<condition>, <message>);
    assert(<condition>);
    """
    condition : Expression
    message : 'StringLiteral | None' = None

    def copy(self) -> 'AssertStatement':
        return AssertStatement(self.condition.copy(), self.message)

@dataclass
class ExpressionStatement(Statement):
    """
    This expression is mostly used to model calls without return values
    or to model the return values at the end of a function.

    <expr>;
    <expr>
    """
    expr : Expression
    is_semicolon : bool = True

    def copy(self) -> 'ExpressionStatement':
        return ExpressionStatement(self.expr.copy(), self.is_semicolon)

@dataclass
class ReturnStatement(Statement):
    """
    return <value>;
    """
    value : Expression

    def copy(self) -> 'ReturnStatement':
        return ReturnStatement(self.value.copy())

#
# Literals
#

@dataclass
class Literal(Expression):
    def copy(self) -> 'Literal':
        raise NotImplementedError()

@dataclass
class StringLiteral(Expression):
    value: str

    def copy(self) -> 'StringLiteral':
        return StringLiteral(self.value)

@dataclass
class BooleanLiteral(Expression):
    value: bool

    def copy(self) -> 'BooleanLiteral':
        return BooleanLiteral(self.value)

@dataclass
class IntegerLiteral(Expression):
    value: int

    def copy(self) -> 'IntegerLiteral':
        return IntegerLiteral(self.value)

@dataclass
class ListLiteral(Expression):
    value: list[Expression]

    def copy(self) -> 'ListLiteral':
        return ListLiteral([e.copy() for e in self.value])

@dataclass
class TupleLiteral(Expression):
    value: list[Expression]

    def copy(self) -> 'TupleLiteral':
        return TupleLiteral([e.copy() for e in self.value])

#
# Definitions
#

@dataclass
class VariableDefinition(ASTNode):
    name: Identifier
    type_: NoirType
   
    def copy(self) -> 'VariableDefinition':
        return VariableDefinition(self.name.copy(), self.type_.copy())

@dataclass
class FunctionDefinition(ASTNode):
    """
    fn pub <name>( <arguments> ) -> <type_> <body>
    , where `pub`, `type_` and field annotation is optional.
    """
    name: Identifier
    arguments: list[VariableDefinition]
    body: Statement
    is_public: bool = False
    is_public_return: bool = False
    type_: NoirType | None = None

    def copy(self) -> 'FunctionDefinition':
        return FunctionDefinition \
            ( self.name.copy()
            , [v.copy() for v in self.arguments]
            , self.body.copy()
            , self.is_public
            , self.is_public_return
            , self.type_.copy() if self.type_ else None
            )

@dataclass
class Document(ASTNode):
    """
    fn main( ... ) {
        // ...
    }
    """
    main: FunctionDefinition

    def copy(self) -> 'Document':
        return Document(self.main.copy())