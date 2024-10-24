
from .parser import RewriteUtil
from .rules import RewriteRule

from ..config import IRConfig
from ..nodes import *
from ..visitors.replace import NodeReplacer
from ...common.field import CurvePrime

from typing import cast
from random import Random

@dataclass
class PointOfInterest():
    rule: RewriteRule
    target: IRNode
    parent: IRNode | None = None
    replacement: IRNode | None = None

    def has_parent(self) -> bool:
        return not self.parent == None

    def apply_rule(self, rewrite_util: RewriteUtil) -> IRNode:
        self.replacement = self.rule.rewrite(self.target, rewrite_util)
        assert self.replacement, f"unable to apply {self.rule.name} to {self.target}"
        return self.replacement


class RuleBasedRewriter():
    """
    This rewriter takes a list of rewrite rules and applies them
    a given number of times on a node in random fashion.

    Limitations:
        - statements
        - left hand side of assignment
        - right hand side of power
    """

    def __init__(self, prime: CurvePrime, config: IRConfig, rules: list[RewriteRule], seed: int | float):
        self.__config = config
        self.__rules = rules
        self.__points_of_interest: dict[str, list[PointOfInterest]] = {}
        self.__seed = seed
        self.__rng = Random(self.__seed)
        self.__rewrite_rewrite_util = RewriteUtil(0, prime, self.__rng)

    def run(self, node: IRNode, amount: int | None = None) -> tuple[list[PointOfInterest], IRNode]:
        root = node.copy()
        applied_rules = []
        replacer = NodeReplacer()
        if amount == None:
            amount = self.__rng.randint(self.__config.rewrite.min_rewrites, self.__config.rewrite.max_rewrites)
        for _ in range(amount):
            self.__points_of_interest = {}
            self.collect_rules(root, None)
            if len(self.__points_of_interest) > 0:
                rule_identifier = self.__rng.choice(list(self.__points_of_interest.keys()))
                POI = self.__rng.choice(self.__points_of_interest[rule_identifier])
                applied_rules.append(POI)

                # we are targeting the root
                if POI.target == root:
                    assert POI.has_parent() == False, "unexpected parent for starting node"
                    root = POI.apply_rule(self.__rewrite_rewrite_util).copy() # use copy to not taint POI
                    continue # early, abort after whole root replacement

                # we are targeting a sub node and need a replacement run
                assert POI.has_parent(), "unexpected orphan target for point of interest"
                replacement = POI.apply_rule(self.__rewrite_rewrite_util)
                is_replaced = replacer.replace(cast(IRNode, POI.parent), POI.target, replacement)
                assert is_replaced, "unable to find origin node"
            else:
                break # unable to find a rule
        return applied_rules, root

    def collect_rules(self, node: IRNode, parent: IRNode | None):
        for rule in self.__rules:
            if rule.is_applicable(node):
                if not rule.name in self.__points_of_interest:
                    self.__points_of_interest[rule.name] = []
                self.__points_of_interest[rule.name].append(PointOfInterest(rule, node, parent))

        match node:
            case Variable():
                return self.visit_variable(node)
            case Boolean():
                return self.visit_boolean(node)
            case Integer():
                return self.visit_integer(node)
            case UnaryExpression():
                return self.visit_unary_expression(node)
            case BinaryExpression():
                return self.visit_binary_expression(node)
            case TernaryExpression():
                return self.visit_ternary_expression(node)
            case Assignment():
                return self.visit_assignment(node)
            case Assertion():
                return self.visit_assertion(node)
            case Assume():
                return self.visit_assume(node)
            case Circuit():
                return self.visit_circuit(node)
            case _:
                raise NotImplementedError(f"unexpected node with class '{node.__class__}'")

    def visit_variable(self, node: Variable):
        pass

    def visit_boolean(self, node: Boolean):
        pass

    def visit_integer(self, node: Integer):
        pass

    def visit_binary_expression(self, node: BinaryExpression):
        self.collect_rules(node.lhs, node)
        if not node.op == Operator.POW: # do not mess with exponent
            self.collect_rules(node.rhs, node)

    def visit_unary_expression(self, node: UnaryExpression):
        self.collect_rules(node.value, node)

    def visit_ternary_expression(self, node: TernaryExpression):
        self.collect_rules(node.condition, node)
        self.collect_rules(node.if_expr, node)
        self.collect_rules(node.else_expr, node)

    def visit_assignment(self, node: Assignment):
        # self.collect_rules(node.lhs, node) # only allow the expressions part of an assignment for now
        self.collect_rules(node.rhs, node)

    def visit_assertion(self, node: Assertion):
        self.collect_rules(node.value, node)

    def visit_assume(self, node: Assume):
        pass # do not rewrite assumptions

    def visit_circuit(self, node: Circuit):
        for e in node.statements:
            self.collect_rules(e, node)