from enum import Enum
from typing import cast
from random import Random

from circuzz.ir import nodes as IRNodes
from circuzz.common.probability import bernoulli

from .nodes import *
from .operators import *

class NameDispenser():
    def __init__(self):
        self.__unique_var_counter = 0
    def next(self, prefix: str = "") -> Identifier:
        identifier = Identifier(f"{prefix}_{self.__unique_var_counter}")
        self.__unique_var_counter += 1
        return identifier

class ImportDependency(Enum):
    COMPARATORS = "comparators.circom"
    GATES = "gates.circom"
    MUX = "mux1.circom"

@dataclass
class ImportDependencyManager():
    dependencies : set[ImportDependency] = field(default_factory=set)


class IR2CircomVisitor():

    """
    # Transformer from IR to Circom

    Transforms a valid IR to a circom source program. It also takes a probability and a random
    number generator as argument. The probability indicates if an assignment should be treated as
    constraining assignment, i.e. "<==" instead of "<--".

    #### Limitations and semantic changes

    Following list holds limitations of the generation based on the documentation
    and found bugs:
        * Ternary expression must be a top level element, otherwise the compiler or
          later generation fails.
            - LINKS:
                - (https://github.com/iden3/circom/issues/263)
                - (https://docs.circom.io/circom-language/basic-operators/)
            - SOLUTION:
                - we generate temporary variables or signals
        * Using libraries to model constraint relations
            - Constraint relations are currently modeled using the Circomlib library.
              This enables easy constraint management, but it has the limitation of
              only being able to support 252 bit value integers.
            - LINKS:
                - (https://github.com/iden3/circomlib/tree/master/circuits)
            - SOLUTION:
                - we can have a guarding if to check the bitsize and if it cannot be guaranteed,
                  then we simply do not constraint the relation check.
                  NOTE: we are TESTING and we are not in PRODUCTION!
        * Bug regarding division by zero during runtime
            - Sometimes division by zero (especially when the denominator is not a constant)
              is ignored to runtime, which results in failures later on.
            - LINKS:
                - (https://github.com/iden3/circom/issues/206)
            - SOLUTION:
                - to be able to handle this we add a flag, which if it is set to true,
                  creates an assertion statement out of the the denominator assumption. This
                  should not compromise the correction. (see __assert_divisor_non_zero_assumption)
            - INFO:
                - The division in general is tough to properly check as optimizations sometimes
                  optimizes it away resulting in a correct program (no div by zero).
                  Therefore it is best to keep the __assert_divisor_non_zero_assumption flag on
                  to prevent false-positives.

    NOTE: Circom relation reminder, that relations are applied based on the "val" function:
        - val(z) = z-p   if p/2 +1 <= z < p
        - val(z) = z,    otherwise.
        - TODO: FIXME: We use current only the default prime number
            - 21888242871839275222246405745257275088548364400416034343698204186575808495617

    TODO:
        - always move non top level ternary expression to temporary variable or signal.
        - implement some sort of guard in the constraint visitor for relations.
    """

    __name_dispenser              : NameDispenser
    __dependency_manager          : ImportDependencyManager

    # probability to create a constraint "<==" assignment
    # instead of a normal one "<--"
    __constraint_assignment_probability : float
    __rng : Random

    def __init__(self, constraint_assignment_probability: float, rng: Random):
        self.__name_dispenser = NameDispenser()
        self.__dependency_manager = ImportDependencyManager()

        self.__assert_divisor_non_zero_assumption = True
        self.__constraint_assignment_probability = constraint_assignment_probability
        self.__rng = rng

    def transform(self, system: IRNodes.Circuit) -> Document:
        return self.visit_circuit(system)

    def visit_operator(self, ir_op: IRNodes.Operator) -> Operator:
        mapping = \
            { IRNodes.Operator.MUL : Operator.MUL
            , IRNodes.Operator.SUB : Operator.SUB
            , IRNodes.Operator.ADD : Operator.ADD
            , IRNodes.Operator.POW : Operator.POW
            , IRNodes.Operator.EQU : Operator.EQU
            , IRNodes.Operator.LTH : Operator.LTH
            , IRNodes.Operator.LEQ : Operator.LEQ
            , IRNodes.Operator.GTH : Operator.GTH
            , IRNodes.Operator.GEQ : Operator.GEQ
            , IRNodes.Operator.NEQ : Operator.NEQ
            , IRNodes.Operator.LAND : Operator.LAND
            , IRNodes.Operator.LOR : Operator.LOR
            , IRNodes.Operator.NOT : Operator.NOT
            , IRNodes.Operator.DIV : Operator.DIV
            , IRNodes.Operator.REM : Operator.REM
            , IRNodes.Operator.COMP : Operator.COMP
            , IRNodes.Operator.AND : Operator.AND
            , IRNodes.Operator.OR : Operator.OR
            , IRNodes.Operator.XOR : Operator.XOR
            , IRNodes.Operator.LXOR : Operator.XOR
            }
        ast_op = mapping.get(ir_op, None)
        if ast_op == None:
            raise NotImplementedError(f"unimplemented IR operator {ir_op.value}")
        return ast_op

    def visit_expression(self, node: IRNodes.IRNode) -> tuple[Expression, list[Statement]]:
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

    def visit_statement(self, node: IRNodes.IRNode) -> tuple[Statement, list[Statement]]:
        match node:
            case IRNodes.Assertion():
                return self.visit_assertion(node)
            case IRNodes.Assignment():
                return self.visit_assignment(node)
            case IRNodes.Assume():
                return self.visit_assume(node)
            case _:
                raise NotImplementedError()

    def visit_variable(self, node: IRNodes.Variable) -> tuple[Expression, list[Statement]]:
        return Identifier(node.name), []

    def visit_boolean(self, node: IRNodes.Boolean) -> tuple[Expression, list[Statement]]:
        return IntegerLiteral(1 if node.value else 0), []
   
    def visit_integer(self, node: IRNodes.Integer) -> tuple[Expression, list[Statement]]:
        return IntegerLiteral(node.value), []

    def visit_unary_expression(self, node: IRNodes.UnaryExpression) -> tuple[Expression, list[Statement]]:
        expression, statements = self.visit_expression(node.value)
        op = self.visit_operator(node.op)
        return UnaryExpression(op, expression), statements

    def visit_binary_expression(self, node: IRNodes.BinaryExpression) -> tuple[Expression, list[Statement]]:
        expression = None
        statements = []

        lhs, lhs_tail = self.visit_expression(node.lhs)
        statements += lhs_tail
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements += rhs_tail

        op = self.visit_operator(node.op)
        expression = BinaryExpression(op, lhs, rhs)
        return expression, statements

    def visit_ternary_expression(self, node: IRNodes.TernaryExpression) -> tuple[Expression, list[Statement]]:
        expression = None
        statements = []
        cond, cond_tail = self.visit_expression(node.condition)
        statements += cond_tail
        if_expr, if_expr_tail = self.visit_expression(node.if_expr)
        statements += if_expr_tail
        else_expr, else_expr_tail = self.visit_expression(node.else_expr)
        statements += else_expr_tail
        expression = ConditionalExpression(cond, if_expr, else_expr)

        # always move ternary to a tmp variable
        variable_name = self.__name_dispenser.next("var")
        statements.append(VariableDefinition(variable_name, [], expression))

        return variable_name.copy(), statements

    def visit_assertion(self, node: IRNodes.Assertion) -> tuple[Statement, list[Statement]]:
        expression, statements = self.visit_expression(node.value)
        return AssertStatement(expression), statements

    def visit_assignment(self, node: IRNodes.Assignment) -> tuple[Statement, list[Statement]]:
        assignment = None
        statements = []
        if bernoulli(self.__constraint_assignment_probability, self.__rng):
            assignment, statements = \
                IR2ConstraintCircomVisitor \
                    ( self.__name_dispenser
                    , self.__dependency_manager
                    ).visit_assignment(node)
        else:
            lhs, lhs_tail = self.visit_expression(node.lhs)
            statements += lhs_tail
            rhs, rhs_tail = self.visit_expression(node.rhs)
            statements += rhs_tail
            assignment = AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, lhs, rhs)
        return assignment, statements

    def visit_assume(self, node: IRNodes.Assume) -> tuple[Statement, list[Statement]]:
        if self.__assert_divisor_non_zero_assumption:
            condition, stmts = self.visit_expression(node.condition)
            assert_stmt = AssertStatement(condition, f"{node.identifier} violation detected!")
            return assert_stmt, stmts
        else:
            condition, stmts = self.visit_expression(node.condition)
            log_stmt = LogStatement([StringLiteral("<!> assume: "), condition])
            return log_stmt, stmts

    def visit_circuit(self, node: IRNodes.Circuit) -> Document:

        # generate main template

        circuit_template_name = Identifier("main_template")
        circuit_statements = []
        circuit_statements += [SignalDefinition(Identifier(v), SignalKind.INPUT) for v in node.inputs]
        circuit_statements += [SignalDefinition(Identifier(v), SignalKind.OUTPUT) for v in node.outputs]

        for statement in node.statements:
            assign, tail = self.visit_statement(statement) # : tuple[Statement, list[Statement]]
            circuit_statements += tail
            circuit_statements.append(assign)
       
        # add log statements to see the output signals
        log_statements = self._log_statements_for_signals(node.outputs)
        circuit_statements += log_statements

        circuit_block = BasicBlock(circuit_statements)
        circuit_template = TemplateDefinition(circuit_template_name, [], circuit_block)

        # generate main component

        main_component_name = Identifier("main")
        main_template_ref = Identifier("main_template")
        main_template_inst = CallExpression(main_template_ref)
        main_component = ComponentDefinition(main_component_name,  [], main_template_inst)

        # add dependency imports
        document_definitions = []
        for dependency in self.__dependency_manager.dependencies:
            document_definitions.append(IncludeStatement(StringLiteral(dependency.value)))

        # add main circuit template
        document_definitions.append(circuit_template)

        # generate and return document

        return Document(document_definitions, main_component)

    def _assert_not_zero(self, value: Expression, msg: str | None = None) -> Statement:
        zero_lit = IntegerLiteral(0)
        is_not_zero_expr = BinaryExpression(Operator.NEQ, value.copy(), zero_lit)
        return AssertStatement(is_not_zero_expr, msg)

    def _log_statements_for_signals(self, names: list[str]) -> list[Statement]:
        statements = []
        for name in names:
            identifier = Identifier(name)
            # dedicated debug symbol at line start
            debug_str = StringLiteral(f"<@> {name} = ")
            log_stmt = LogStatement([debug_str, identifier])
            statements.append(log_stmt)
        return statements


class IR2ConstraintCircomVisitor(IR2CircomVisitor):

    """
    Special transformer to focus on producing quadratic expression such that they can be
    used for circom constraints. This works similar to the IR2CircomVisitor. See the
    IR2CircomVisitor for more information on limitations.
    """

    __name_dispenser     : NameDispenser
    __dependency_manager : ImportDependencyManager

    def __init__ \
        ( self
        , name_dispenser: NameDispenser
        , import_manager: ImportDependencyManager
        ):
        self.__name_dispenser = name_dispenser
        self.__dependency_manager = import_manager

    def visit_unary_expression(self, node: IRNodes.UnaryExpression) -> tuple[Expression, list[Statement]]:
        match node.op:
            case IRNodes.Operator.NOT:
                value, statements = self.visit_expression(node.value)
                not_expr, not_stmts = self._constrained_not(value)
                statements += not_stmts
                return not_expr, statements
            case IRNodes.Operator.COMP: # TODO: FIXME: compliment is not constrained!
                value, statements = self.visit_expression(node.value) # try to constraint child
                comp_expr = UnaryExpression(Operator.COMP, value)
                signal = self._next_intermediate_signal()
                statements.append(signal)
                # no constraint for comp, which is why we simply write it into a signal
                assignment = AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, signal.name.copy(), comp_expr)
                statements.append(assignment)
                return signal.name.copy(), statements
            case IRNodes.Operator.SUB:
                return super().visit_unary_expression(node) # use default
            case _:
                raise NotImplementedError(f"unimplemented simplification for unary operator {node.op}")

    def visit_binary_expression(self, node: IRNodes.BinaryExpression) -> tuple[Expression, list[Statement]]:
        expression = None
        statements = []

        lhs, lhs_tail = self.visit_expression(node.lhs)
        statements += lhs_tail
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements += rhs_tail

        match node.op:
            case IRNodes.Operator.POW:
                expression, expression_tail = self.simplify_pow_expression(node, lhs, rhs)
            case IRNodes.Operator.MUL:
                expression, expression_tail = self.simplify_mul_expression(node, lhs, rhs)
            case IRNodes.Operator.ADD | IRNodes.Operator.SUB:
                expression, expression_tail = self.simplify_add_or_sub_expression(node, lhs, rhs)
            case IRNodes.Operator.EQU | IRNodes.Operator.LTH | IRNodes.Operator.LEQ | IRNodes.Operator.GTH | IRNodes.Operator.GEQ | IRNodes.Operator.NEQ:
                expression, expression_tail = self.simplify_relation_expression(node, lhs, rhs)
            case IRNodes.Operator.LAND | IRNodes.Operator.LOR | IRNodes.Operator.LXOR:
                expression, expression_tail = self.simplify_binary_boolean_logic_expression(node, lhs, rhs)
            case IRNodes.Operator.DIV:
                expression, expression_tail = self.simplify_div_expression(node, lhs, rhs)
            case IRNodes.Operator.REM:
                expression, expression_tail = self.simplify_rem_expression(node, lhs, rhs)
            case IRNodes.Operator.AND | IRNodes.Operator.OR | IRNodes.Operator.XOR:
                expression, expression_tail = self.simplify_bitwise_expression(node, lhs, rhs)
            case _:
                raise NotImplementedError(f"binary operator {node.op.value}")
        statements += expression_tail

        return expression, statements

    def visit_ternary_expression(self, node: IRNodes.TernaryExpression) -> tuple[Expression, list[Statement]]:
        expression = None
        statements = []

        cond, cond_tail = self.visit_expression(node.condition)
        statements += cond_tail
        if_expr, if_expr_tail = self.visit_expression(node.if_expr)
        statements += if_expr_tail
        else_expr, else_expr_tail = self.visit_expression(node.else_expr)
        statements += else_expr_tail

        expression, expression_tail = self.simplify_ternary_expression(node, cond, if_expr, else_expr)
        statements += expression_tail

        return expression, statements

    def visit_assignment(self, node: IRNodes.Assignment) -> tuple[Statement, list[Statement]]:
        statements = []
        signal_reference, reference_tail= self.visit_expression(node.lhs)
        statements += reference_tail
        constraint_expression, tail_stmts = self.visit_expression(node.rhs)
        statements += tail_stmts
        statement = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, signal_reference, constraint_expression)
        return statement, statements

    def simplify_pow_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        assert node.op == IRNodes.Operator.POW, "unexpected operator for IR expression"
        statements = []
        constraint_op = Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT

        # TODO: FIXME: This is way too strict and could be loosened but otherwise the random
        # generator keeps finding instances where it is possible to violate the compilation.
        #
        # no need to simplify if the power is applied to a constant number
        if self._is_constant(lhs):
            return BinaryExpression(Operator.POW, lhs, rhs), statements # early return

        # else: split 1 exponent from pow expressions
        assert isinstance(rhs, IntegerLiteral), "unexpected non integer value for exponent"
        exponent = cast(IntegerLiteral, rhs).value
        assert exponent >= 2, "unexpected exponent value, expected: '>=2' but was '" + str(exponent) + "'"

        """
        a^n, where n >= 2 and a is linear or quadratic
        s0 = a
        sn = sn-1 * s0
        """
        s0 = self._next_intermediate_signal()
        statements.append(s0)
        statements.append(AssignmentOrConstraint(constraint_op, s0.name.copy(), lhs.copy()))

        reference_to_last = s0.name.copy()
        for _ in range(exponent-1):
            sn = self._next_intermediate_signal()
            statements.append(sn)
            mul_sn = BinaryExpression(Operator.MUL, reference_to_last, s0.name.copy())
            statements.append(AssignmentOrConstraint(constraint_op, sn.name.copy(), mul_sn))
            reference_to_last = sn.name.copy()

        return reference_to_last, statements

    def simplify_mul_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        assert node.op == IRNodes.Operator.MUL, "unexpected operator for IR expression"
        statements = []
        constraint_op = Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT
        if self._is_at_least_quadratic(lhs) and self._contains_variable(rhs):
            inter_sig = self._next_intermediate_signal()
            statements.append(inter_sig)
            isc = AssignmentOrConstraint(constraint_op, inter_sig.name.copy(), lhs)
            statements.append(isc)
            lhs = inter_sig.name.copy() # override left hand side
        if self._contains_variable(lhs) and self._is_at_least_quadratic(rhs):
            inter_sig = self._next_intermediate_signal()
            statements.append(inter_sig)
            isc = AssignmentOrConstraint(constraint_op, inter_sig.name.copy(), rhs)
            statements.append(isc)
            rhs = inter_sig.name.copy() # override right hand side
        return BinaryExpression(Operator.MUL, lhs, rhs), statements

    def simplify_add_or_sub_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        assert node.op in [IRNodes.Operator.ADD, IRNodes.Operator.SUB], "unexpected operator for IR expression"
        statements = []
        constraint_op = Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT
        if self._is_at_least_quadratic(lhs) and self._is_at_least_quadratic(rhs):
            """
            s <= a <op> b, where a and b are quadratic
            s0 <= a
            s <= s0 <op> b
            """
            inter_sig = self._next_intermediate_signal()
            statements.append(inter_sig)
            isc = AssignmentOrConstraint(constraint_op, inter_sig.name.copy(), lhs)
            statements.append(isc)
            lhs = inter_sig.name.copy() # override lhs

        if node.op == IRNodes.Operator.ADD:
            return BinaryExpression(Operator.ADD, lhs, rhs), statements
        else:
            return BinaryExpression(Operator.SUB, lhs, rhs), statements

    def simplify_relation_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:

        expression = None
        statements = []

        if node.op in [IRNodes.Operator.EQU, IRNodes.Operator.NEQ]:
            expression, equ_stmts = self._constrained_equ(lhs, rhs)
            statements += equ_stmts
            # in-equality is done by negating the equality
            if node.op == IRNodes.Operator.NEQ:
                expression, not_stmts = self._constrained_not(expression) # reassign expression
                statements += not_stmts
        else: # op was not equ or neq
            # NOTE: WARNING: this is NOT CONSTRAINING but the default implementation with a temporary signal
            # TODO: FIXME: use another circom library or guard and split everything

            ALLOWED_RELATIONS = [IRNodes.Operator.LTH, IRNodes.Operator.LEQ, IRNodes.Operator.GTH, IRNodes.Operator.GEQ]
            assert node.op in ALLOWED_RELATIONS, f"Unexpected operator {node.op} for relation simplification"

            op = self.visit_operator(node.op)
            relation_expression = BinaryExpression(op, lhs, rhs)

            intermediate_signal = self._next_intermediate_signal()
            statements.append(intermediate_signal)
            assignment = AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, intermediate_signal.name.copy(), relation_expression)
            statements.append(assignment)
            expression = intermediate_signal.name.copy()

        return expression, statements

    def simplify_binary_boolean_logic_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        self.__dependency_manager.dependencies.add(ImportDependency.GATES)

        expression = None
        statements = []

        match node.op:
            case IRNodes.Operator.LAND:
                gate = self._next_component([], CallExpression(Identifier("AND")))
            case IRNodes.Operator.LOR:
                gate = self._next_component([], CallExpression(Identifier("OR")))
            case IRNodes.Operator.LXOR:
                gate = self._next_component([], CallExpression(Identifier("XOR")))
            case _:
                raise NotImplementedError(f"Unexpected operator {node.op} for binary boolean logic simplification")

        statements.append(gate)

        gate_a = FieldAccessExpression(gate.name.copy(), Identifier("a"))
        gate_a_assign = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, gate_a, lhs)
        statements.append(gate_a_assign)

        gate_b = FieldAccessExpression(gate.name.copy(), Identifier("b"))
        gate_b_assign = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, gate_b, rhs)
        statements.append(gate_b_assign)

        expression = FieldAccessExpression(gate.name.copy(), Identifier("out"))

        return expression, statements

    def simplify_ternary_expression(self, node: IRNodes.TernaryExpression, cond: Expression, if_expr: Expression, else_expr: Expression) -> tuple[Expression, list[Statement]]:
        self.__dependency_manager.dependencies.add(ImportDependency.MUX)
        mux = self._next_component([], CallExpression(Identifier("Mux1")))
        mux_c0 = IndexAccessExpression(FieldAccessExpression(mux.name.copy(), Identifier("c")), IntegerLiteral(0))
        mux_c1 = IndexAccessExpression(FieldAccessExpression(mux.name.copy(), Identifier("c")), IntegerLiteral(1))
        mux_s = FieldAccessExpression(mux.name.copy(), Identifier("s"))
        mux_out = FieldAccessExpression(mux.name.copy(), Identifier("out"))
        mux_c0_assign = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, mux_c0, else_expr) # in mux 0 is the first element but 0 is false -> else-expr
        mux_c1_assign = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, mux_c1, if_expr)   # in mux 1 is the second element but 1 is true -> if-expr
        mux_s_assign = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, mux_s, cond)
        return mux_out, [mux, mux_c0_assign, mux_c1_assign, mux_s_assign]

    def simplify_div_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        # transforming: b / a
        #
        # sig <-- b / a;
        # sig * a === b;

        statements = []

        # if lhs is quadratic we need an intermediate
        if self._is_at_least_quadratic(lhs):
            lhs_sig = self._next_intermediate_signal()
            statements.append(lhs_sig)
            lhs_assign = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, lhs_sig.name.copy(), lhs.copy())
            statements.append(lhs_assign)
            lhs = lhs_sig.name.copy()

        # if rhs is quadratic we need an intermediate
        if self._is_at_least_quadratic(rhs):
            rhs_sig = self._next_intermediate_signal()
            statements.append(rhs_sig)
            rhs_assign = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, rhs_sig.name.copy(), rhs.copy())
            statements.append(rhs_assign)
            rhs = rhs_sig.name.copy()

        inter_sig = self._next_intermediate_signal()
        statements.append(inter_sig)

        # sig <-- b / a;
        div_expression = BinaryExpression(Operator.DIV, lhs, rhs)
        div_assignment = AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, inter_sig.name.copy(), div_expression)
        statements.append(div_assignment)

        # sig * a === b;
        mul_expression = BinaryExpression(Operator.MUL, inter_sig.name.copy(), rhs.copy())
        mul_constraint = AssignmentOrConstraint(Operator.EQU_CONSTRAINT, mul_expression, lhs.copy())
        statements.append(mul_constraint)

        return inter_sig.name.copy(), statements

    def simplify_rem_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        # TODO: FIXME: this is not constraint yet!
        #              constrain it using "\" "/" and "%" ?
        statements = []
        signal = self._next_intermediate_signal()
        statements.append(signal)
        rem_expression = BinaryExpression(Operator.REM, lhs, rhs)
        rem_assignment = AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, signal.name.copy(), rem_expression)
        statements.append(rem_assignment)
        return signal.name.copy(), statements

    def simplify_bitwise_expression(self, node: IRNodes.BinaryExpression, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        # TODO: FIXME: this is not constraint yet!
        assert node.op in [IRNodes.Operator.AND, IRNodes.Operator.OR, IRNodes.Operator.XOR], \
            "unexpected bitwise operator {node.op}"
        statements = []
        operator = super().visit_operator(node.op)
        signal = self._next_intermediate_signal()
        statements.append(signal)
        expression = BinaryExpression(operator, lhs, rhs)
        assignment = AssignmentOrConstraint(Operator.SIGNAL_ASSIGN_LEFT, signal.name.copy(), expression)
        statements.append(assignment)
        return signal.name.copy(), statements

    def _is_constant(self, node: Expression) -> bool:
        """
        Helper function to see if a circom expression can be labeled as constant
        expression. This is necessary to determine if we have to split complex
        expressions to preserve the quadratic nature of constraints.
        """

        # TODO: FIXME: add other cases and refine this
        match node:
            case Identifier():
                return False # for now this is always false
            case ConditionalExpression():
                return False # for now this is always false (we want to be super strict with conditional expressions, e.g. see power expression)
            case BinaryExpression():
                return self._is_constant(node.lhs) and self._is_constant(node.rhs)
            case UnaryExpression():
                return self._is_constant(node.value)
            case CallExpression():
                return False # for now this is always false
            case IndexAccessExpression():
                return False # for now this is always false
            case FieldAccessExpression():
                return False # for now this is always false
            case IntegerLiteral():
                return True
            case StringLiteral():
                return True
            case ListLiteral():
                return all(map(self._is_constant, node.value))
            case _:
                raise NotImplementedError(f"Unexpected Expression '{node.__class__.__name__}'")

    def _contains_variable(self, node: Expression) -> bool:
        """
        Helper function to see if a circom expression contains a symbol.
        This is necessary to determine if we have to split complex
        expressions to preserve the quadratic nature of constraints.
        """

        # TODO: FIXME: add other cases and refine this
        match node:
            case Identifier():
                return True # for now this is always true
            case ConditionalExpression():
                return self._contains_variable(node.condition) or self._contains_variable(node.trueVal) or self._contains_variable(node.falseVal)
            case BinaryExpression():
                return self._contains_variable(node.lhs) or self._contains_variable(node.rhs)
            case UnaryExpression():
                return self._contains_variable(node.value)
            case CallExpression():
                return True # for now this is always true
            case IndexAccessExpression():
                return True # for now this is always true
            case FieldAccessExpression():
                return True # for now this is always true
            case IntegerLiteral():
                return False
            case StringLiteral():
                return False
            case ListLiteral():
                return any(map(self._contains_variable, node.value))
            case _:
                raise NotImplementedError(f"Unexpected Expression '{node.__class__.__name__}'")

    def _is_at_least_quadratic(self, node: Expression) -> bool:
        """
        Helper function to see if a circom expression is at least quadratic.
        This is necessary to determine if we have to split complex
        expressions to preserve the quadratic nature of constraints.
        """

        # TODO: FIXME: add other cases and refine this
        match node:
            case Identifier():
                return False # for now this is always False
            case ConditionalExpression():
                return self._is_at_least_quadratic(node.condition) \
                    or self._is_at_least_quadratic(node.trueVal) \
                    or self._is_at_least_quadratic(node.falseVal)
            case BinaryExpression():
                return self._is_at_least_quadratic(node.lhs) \
                    or self._is_at_least_quadratic(node.rhs) \
                    or (node.operator in [Operator.MUL, Operator.DIV, Operator.QUO, Operator.REM]  and \
                        self._contains_variable(node.lhs) and \
                        self._contains_variable(node.rhs))
            case UnaryExpression():
                if node.operator == Operator.COMP:
                    return False
                return self._is_at_least_quadratic(node.value)
            case CallExpression():
                return False # for now this is always False
            case IndexAccessExpression():
                return False # for now this is always False
            case FieldAccessExpression():
                return False # for now this is always False
            case IntegerLiteral():
                return False # for now this is always False
            case StringLiteral():
                return False # for now this is always False
            case ListLiteral():
                return any(map(self._is_at_least_quadratic, node.value))
            case _:
                raise NotImplementedError(f"Unexpected Expression '{node.__class__.__name__}'")

    def _next_intermediate_signal(self) -> SignalDefinition:
        identifier = self.__name_dispenser.next("sig")
        return SignalDefinition(identifier, SignalKind.INTERMEDIATE)

    def _next_component(self, sizes: list[Expression], value: Expression) -> ComponentDefinition:
        identifier = self.__name_dispenser.next("comp")
        return ComponentDefinition(identifier, sizes, value)

    def _constrained_not(self, value: Expression) -> tuple[Expression, list[Statement]]:
        self.__dependency_manager.dependencies.add(ImportDependency.GATES)
        not_gate = self._next_component([], CallExpression(Identifier("NOT")))
        not_gate_in = FieldAccessExpression(not_gate.name.copy(), Identifier("in"))
        not_gate_out = FieldAccessExpression(not_gate.name.copy(), Identifier("out"))
        assignment = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, not_gate_in, value)
        return not_gate_out, [not_gate, assignment]

    def _constrained_equ(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        self.__dependency_manager.dependencies.add(ImportDependency.COMPARATORS)
        comparator = self._next_component([], CallExpression(Identifier("IsEqual")))
        comparator_in0 = IndexAccessExpression(FieldAccessExpression(comparator.name.copy(), Identifier("in")), IntegerLiteral(0))
        comparator_in0_assign = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, comparator_in0, lhs)
        comparator_in1 = IndexAccessExpression(FieldAccessExpression(comparator.name.copy(), Identifier("in")), IntegerLiteral(1))
        comparator_in1_assign = AssignmentOrConstraint(Operator.EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT, comparator_in1, rhs)
        comparator_out = FieldAccessExpression(comparator.name.copy(), Identifier("out"))
        return comparator_out, [comparator, comparator_in0_assign, comparator_in1_assign]