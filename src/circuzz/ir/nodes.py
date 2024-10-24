"""
This file contains a possible IR for the zkProof circuits.
It is a good compromise to model rank-1-constrained-systems (R1CS),
as every polynomial can be modeled as a R1CS by introducing intermediates.
"""

from enum import StrEnum
from dataclasses import dataclass
from dataclasses import field
from itertools import count
from typing import Any

class Operator(StrEnum):
    MUL = "*"
    SUB = "-"
    ADD = "+"
    POW = "**"
    DIV = "/"
    REM = "%"

    EQU = "=="
    NEQ = "!="
    LTH = "<"
    LEQ = "<="
    GTH = ">"
    GEQ = ">="

    LAND = "&&"
    LOR = "||"
    LXOR = "^^"
    NOT = "!"

    AND = "&"
    OR = "|"
    XOR = "^"
    COMP = "~"

    @classmethod
    def unary_operations(cls) -> list['Operator']:
        return [cls.SUB, cls.NOT, cls.COMP]

    @classmethod
    def binary_operations(cls) -> list['Operator']:
        return [cls.LAND, cls.LOR, cls.EQU, cls.NEQ, cls.LTH, \
                cls.LEQ, cls.GTH, cls.GEQ, cls.ADD, cls.SUB, \
                cls.MUL, cls.POW, cls.DIV, cls.REM, cls.AND, \
                cls.OR, cls.XOR, cls.LXOR]

    @classmethod
    def logic_connectives(cls) -> list['Operator']:
        return [cls.LAND, cls.LOR, cls.LXOR]

    @classmethod
    def relation_connectives(cls) -> list['Operator']:
        return [cls.EQU, cls.NEQ, cls.LTH, cls.LEQ, cls.GTH, cls.GEQ]

    @classmethod
    def arithmetic_connectives(cls) -> list['Operator']:
        return [cls.ADD, cls.SUB, cls.MUL, cls.POW, cls.DIV, cls.REM, \
                cls.AND, cls.OR, cls.XOR]

@dataclass
class IRNode():
    node_id: int = field(default_factory=count().__next__, init=False)
    meta_info: dict[str, Any] = field(default_factory=dict, init=False)
    def copy(self) -> 'IRNode':
        raise NotImplementedError()

    def __eq__(self, obj: Any) -> bool:
        return not obj == None and \
               isinstance(obj, IRNode) and \
               obj.node_id == self.node_id

    def node_size(self) -> int:
        raise NotImplementedError()

@dataclass
class Statement(IRNode):
    def copy(self) -> 'Statement':
        raise NotImplementedError()

    def node_size(self) -> int:
        raise NotImplementedError()

@dataclass
class Expression(IRNode):
    def copy(self) -> 'Expression':
        raise NotImplementedError()

    def is_constant(self) -> bool:
        raise NotImplementedError()

    def contains_variables(self) -> bool:
        raise NotImplementedError()

    def is_boolean_expression(self) -> bool:
        raise NotImplementedError()

    def is_arithmetic_expression(self) -> bool:
        raise NotImplementedError()

    def node_size(self) -> int:
        raise NotImplementedError()

@dataclass
class Variable(Expression):
    name: str
    is_boolean: bool = False

    def copy(self) -> 'Variable':
        return Variable(self.name, self.is_boolean)

    def __str__(self):
        return self.name

    def is_constant(self) -> bool:
        return False

    def contains_variables(self) -> bool:
        return True

    def is_boolean_expression(self) -> bool:
        return self.is_boolean

    def is_arithmetic_expression(self) -> bool:
        return True

    def node_size(self) -> int:
        return 1

@dataclass
class Integer(Expression):
    value: int

    def copy(self) -> 'Integer':
        return Integer(self.value)

    def __str__(self):
            return str(self.value)

    def is_constant(self) -> bool:
        return True

    def contains_variables(self) -> bool:
        return False

    def is_boolean_expression(self) -> bool:
        return False

    def is_arithmetic_expression(self) -> bool:
        return True

    def node_size(self) -> int:
        return 1

@dataclass
class Boolean(Expression):
    value: bool

    def copy(self) -> 'Boolean':
        return Boolean(self.value)

    def __str__(self):
        return "T" if self.value else "F"

    def is_constant(self) -> bool:
        return True

    def contains_variables(self) -> bool:
        return False

    def is_boolean_expression(self) -> bool:
        return True

    def is_arithmetic_expression(self) -> bool:
        return False

    def node_size(self) -> int:
        return 1

@dataclass
class UnaryExpression(Expression):
    op : Operator
    value : Expression

    def copy(self) -> 'UnaryExpression':
        return UnaryExpression(self.op, self.value.copy())

    def __str__(self):
        return f"({self.op.value} {self.value})"

    def is_constant(self) -> bool:
        return self.value.is_constant()

    def contains_variables(self) -> bool:
        return self.value.contains_variables()

    def is_boolean_expression(self) -> bool:
        return self.op == Operator.NOT

    def is_arithmetic_expression(self) -> bool:
        return not self.op == Operator.NOT

    def node_size(self) -> int:
        return 1 + self.value.node_size()

@dataclass
class BinaryExpression(Expression):
    op : Operator
    lhs : Expression
    rhs : Expression

    def copy(self) -> 'BinaryExpression':
        return BinaryExpression(self.op, self.lhs.copy(), self.rhs.copy())

    def __str__(self):
        return f"({self.lhs} {self.op.value} {self.rhs})"

    def is_constant(self) -> bool:
        return self.lhs.is_constant() and self.rhs.is_constant()

    def contains_variables(self) -> bool:
        return self.lhs.contains_variables() or self.rhs.contains_variables()

    def is_boolean_expression(self) -> bool:
        return self.op in Operator.relation_connectives() or self.op in Operator.logic_connectives()

    def is_arithmetic_expression(self) -> bool:
        return self.op in Operator.arithmetic_connectives()

    def node_size(self) -> int:
        return 1 + self.lhs.node_size() + self.rhs.node_size()

@dataclass
class TernaryExpression(Expression):
    condition : Expression
    if_expr : Expression
    else_expr : Expression

    def copy(self) -> 'TernaryExpression':
        return TernaryExpression(self.condition.copy(), self.if_expr.copy(), self.else_expr.copy())

    def __str__(self):
        return f"({self.condition} ? {self.if_expr} : {self.else_expr})"

    def is_constant(self) -> bool:
        return self.condition.is_constant() and self.if_expr.is_constant() and self.else_expr.is_constant()

    def contains_variables(self) -> bool:
        return self.condition.contains_variables() \
            or self.if_expr.contains_variables() \
            or self.else_expr.contains_variables()

    def is_boolean_expression(self) -> bool:
        return self.if_expr.is_boolean_expression() \
            or self.else_expr.is_boolean_expression()

    def is_arithmetic_expression(self) -> bool:
        return self.if_expr.is_arithmetic_expression() \
            or self.else_expr.is_arithmetic_expression()

    def node_size(self) -> int:
        return 1 + \
            self.condition.node_size() + \
            self.if_expr.node_size() + \
            self.else_expr.node_size()

@dataclass
class Assertion(Statement):
    identifier: str
    value: Expression

    def copy(self) -> 'Assertion':
        return Assertion(self.identifier, self.value.copy())

    def __str__(self):
        return f"assert({self.value}, \"{self.identifier}\")"

    def node_size(self) -> int:
        return 1 + self.value.node_size()

@dataclass
class Assignment(Statement):
    lhs: Variable
    rhs: Expression

    def copy(self) -> 'Assignment':
        return Assignment(self.lhs.copy(), self.rhs.copy())

    def __str__(self):
        return f"{self.lhs} = {self.rhs}"

    def node_size(self) -> int:
        return 1 + self.lhs.node_size() + self.rhs.node_size()

@dataclass
class Assume(Statement):
    condition: Expression
    identifier: str

    def copy(self) -> 'Assume':
        return Assume(self.condition.copy(), self.identifier)

    def __str__(self):
        return f"assume({self.condition}, \"{self.identifier}\")"

    def node_size(self) -> int:
        return 1 + self.condition.node_size()

@dataclass
class Circuit(IRNode):
    name: str
    inputs: list[str]
    outputs: list[str]
    statements: list[Statement]

    def copy(self) -> 'Circuit':
        return Circuit( \
            self.name,
            [x for x in self.inputs],
            [x for x in self.outputs],
            [x.copy() for x in self.statements])

    def __str__(self):
        return \
"""
==========================================================
Circuit: {0}
----------------------------------------------------------
inputs : {1}
outputs: {2}
----------------------------------------------------------
{3}
==========================================================
""".format( self.name
          , ", ".join([str(e) for e in self.inputs])
          , ", ".join([str(e) for e in self.outputs])
          , "\n".join([str(e) for e in self.statements]))

    def assignments(self) -> list[Assignment]:
        return [s for s in self.statements if isinstance(s, Assignment)]

    def assertions(self) -> list[Assertion]:
        return [s for s in self.statements if isinstance(s, Assertion)]

    def assumptions(self) -> list[Assume]:
        return [s for s in self.statements if isinstance(s, Assume)]

    def node_size(self) -> int:
        return sum([s.node_size() for s in self.statements])