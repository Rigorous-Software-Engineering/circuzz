from circuzz.ir import nodes as IRNodes
from circuzz.common.field import CurvePrime

from .operators import *
from .nodes import *
from .types import *
from .emitter import EmitVisitor

class NameDispenser():
    def __init__(self):
        self.__unique_var_counter = 0
    def next(self, prefix: str = "") -> Identifier:
        identifier = Identifier(f"{prefix}_{self.__unique_var_counter}")
        self.__unique_var_counter += 1
        return identifier

class IR2NoirVisitor():

    """
    Transforms IR to noir.

    TODO: Noir dev supports new functionalities
    """

    FIELD_POW = "pow_32"
    FIELD_LT = "lt"
    FIELD_BIT_WIDTH = 256
    FIELD_BYTE_WIDTH = 32
    BYTE_BITS_WIDTH = 8

    SIGNAL_DEBUG_PREFIX = "<@> "
    SIGNAL_DEBUG_SEPARATOR = " => "

    _noir_version : tuple[int, int, int]

    __name_dispenser : NameDispenser
    __curve : CurvePrime

    def __init__(self, curve: CurvePrime, noir_version: tuple[int,int,int]):
        self._noir_version = noir_version
        self.__name_dispenser = NameDispenser()
        self.__curve = curve

    def transform(self, system: IRNodes.Circuit) -> Document:
       return self.visit_circuit(system)

    def visit_operator(self, ir_op: IRNodes.Operator) -> NoirOperator:
        mapping = \
            { IRNodes.Operator.MUL : NoirOperator.MUL
            , IRNodes.Operator.SUB : NoirOperator.SUB
            , IRNodes.Operator.ADD : NoirOperator.ADD
            # , IRNodes.Operator.EQU : NoirOperator.EQU # modeled using field functions
            # , IRNodes.Operator.LTH : NoirOperator.LTH # modeled using field functions
            # , IRNodes.Operator.LEQ : NoirOperator.LEQ # modeled using field functions
            # , IRNodes.Operator.GTH : NoirOperator.GTH # modeled using field functions
            # , IRNodes.Operator.GEQ : NoirOperator.GEQ # modeled using field functions
            # , IRNodes.Operator.NEQ : NoirOperator.NEQ # modeled using field functions
            , IRNodes.Operator.LAND : NoirOperator.AND  # no logic so we map to bit
            , IRNodes.Operator.LOR : NoirOperator.OR    # no logic so we map to bit
            , IRNodes.Operator.LXOR : NoirOperator.XOR  # no logic so we map to bit
            , IRNodes.Operator.NOT : NoirOperator.NOT
            , IRNodes.Operator.DIV : NoirOperator.DIV
            # , IRNodes.Operator.REM : NoirOperator.REM
            # , IRNodes.Operator.COMP : NoirOperator.COMP
            # , IRNodes.Operator.AND : NoirOperator.AND
            # , IRNodes.Operator.OR : NoirOperator.OR
            # , IRNodes.Operator.XOR : NoirOperator.XOR
            }
        # Operator.POW
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

    def visit_statement(self, node: IRNodes.IRNode) -> list[Statement]:
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
        return BooleanLiteral(node.value == True), []
   
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

        match node.op:
            case IRNodes.Operator.POW:
                expression = self._field_pow(lhs, rhs)
            case IRNodes.Operator.EQU:
                expression = self._field_equ(lhs, rhs)
            case IRNodes.Operator.NEQ:
                expression = self._field_neq(lhs, rhs)
            case IRNodes.Operator.LTH:
                expression = self._field_lth(lhs, rhs)
            case IRNodes.Operator.LEQ:
                expression = self._field_leq(lhs, rhs)
            case IRNodes.Operator.GTH:
                expression = self._field_gth(lhs, rhs)
            case IRNodes.Operator.GEQ:
                expression = self._field_geq(lhs, rhs)
            case IRNodes.Operator.AND:
                expression, op_stmts = self._field_and(lhs, rhs)
                statements += op_stmts
            case IRNodes.Operator.OR:
                expression, op_stmts = self._field_or(lhs, rhs)
                statements += op_stmts
            case IRNodes.Operator.XOR:
                expression, op_stmts = self._field_xor(lhs, rhs)
                statements += op_stmts
            case _:
                op = self.visit_operator(node.op)
                expression = BinaryExpression(op, lhs, rhs)
        return expression, statements

    def visit_ternary_expression(self, node: IRNodes.TernaryExpression) -> tuple[Expression, list[Statement]]:
        statements = []

        condition, condition_tail = self.visit_expression(node.condition)
        statements += condition_tail

        result_name = self.__name_dispenser.next("var")
        result_let = LetStatement(result_name, IntegerLiteral(0), FieldType(), True)
        statements.append(result_let)

        true_expression, true_tail = self.visit_expression(node.if_expr)
        true_statements = true_tail
        true_assign = AssignStatement(result_name.copy(), true_expression)
        true_statements.append(true_assign)
        true_basic_block = BasicBlock(true_statements)

        false_expression, false_tail = self.visit_expression(node.else_expr)
        false_statements = false_tail
        false_assign = AssignStatement(result_name.copy(), false_expression)
        false_statements.append(false_assign)
        false_basic_block = BasicBlock(false_statements)

        if_stmt = IfStatement(condition, true_basic_block, false_basic_block)
        statements.append(if_stmt)

        return result_name.copy(), statements

    def visit_assertion(self, node: IRNodes.Assertion) -> list[Statement]:
        statements = []
        value, value_tail = self.visit_expression(node.value)
        statements += value_tail
        statements.append(AssertStatement(value, StringLiteral(node.identifier)))
        return statements

    def visit_assignment(self, node: IRNodes.Assignment) -> list[Statement]:
        statements = []
        lhs, lhs_tail = self.visit_expression(node.lhs)
        statements += lhs_tail
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements += rhs_tail
        statements.append(AssignStatement(lhs.copy(), rhs.copy()))

        # at the end of the assignment print the value
        statements += self._debug_expr(lhs.copy())

        return statements

    def visit_assume(self, node: IRNodes.Assume) -> list[Statement]:
        condition, statements = self.visit_expression(node.condition)
        statements.append(AssertStatement(condition, StringLiteral(node.identifier)))
        return statements

    def visit_circuit(self, node: IRNodes.Circuit) -> Document:
        main_function_name = Identifier("main")
        main_function_parameters : list[VariableDefinition] = \
            [ VariableDefinition(Identifier(n), FieldType()) for n in node.inputs ]
        main_function_stmts : list[Statement] = \
            [ LetStatement(Identifier(n), IntegerLiteral(0), FieldType(), True) for n in node.outputs ]

        if len(node.outputs) == 1:
            main_last_expr_stmt = ExpressionStatement(Identifier(node.outputs[0]), False)
            main_function_return_type : NoirType = FieldType()
        else:
            main_last_expr_stmt = \
                ExpressionStatement(TupleLiteral([ Identifier(n) for n in node.outputs ]), False)
            main_function_return_type : NoirType = \
                TupleType([ FieldType() for _ in node.outputs ])

        for statement in node.statements:
            stmts = self.visit_statement(statement)
            main_function_stmts += stmts

        main_function_stmts.append(main_last_expr_stmt)

        main_function_body = BasicBlock(main_function_stmts)
        main_function = FunctionDefinition \
            ( main_function_name
            , main_function_parameters
            , main_function_body
            , True
            , True
            , main_function_return_type
            )

        return Document(main_function)

    #
    # operation helper
    #

    def _field_pow(self, base: Expression, exponent: Expression) -> Expression:
        assert isinstance(exponent, IntegerLiteral), "unexpected rhs (exponent) for power operator (**)"
        field_access = FieldAccessExpression(base, Identifier("pow_32"))
        return CallExpression(field_access, [exponent])

    def _field_equ(self, lhs: Expression, rhs: Expression) -> Expression:
        return BinaryExpression(NoirOperator.EQU, lhs, rhs)

    def _field_neq(self, lhs: Expression, rhs: Expression) -> Expression:
        equ_expr = self._field_equ(lhs, rhs)
        return UnaryExpression(NoirOperator.NOT, equ_expr)

    def _field_lth(self, lhs: Expression, rhs: Expression) -> Expression:
        field_access = FieldAccessExpression(lhs, Identifier("lt"))
        return CallExpression(field_access, [rhs])

    def _field_leq(self, lhs: Expression, rhs: Expression) -> Expression:
        equ_expr = self._field_equ(lhs, rhs)
        lth_expr = self._field_lth(lhs.copy(), rhs.copy())
        return BinaryExpression(NoirOperator.OR, equ_expr, lth_expr)

    def _field_gth(self, lhs: Expression, rhs: Expression) -> Expression:
        # TODO: FIXME: might be possible model this using a "gt" function in BN256
        return self._field_lth(rhs, lhs)

    def _field_geq(self, lhs: Expression, rhs: Expression) -> Expression:
        # TODO: FIXME: might be possible model this using a "gt" function in BN256
        return self._field_leq(rhs, lhs)

    def _debug_expr(self, value: Expression) -> list[Statement]:
        # NOTE: returns a list of statements to be more generic, uses the emitter for debugging.
        value_str = EmitVisitor().emit(value)
        prefix_literal = StringLiteral(f"{self.SIGNAL_DEBUG_PREFIX}{value_str}{self.SIGNAL_DEBUG_SEPARATOR}")
        prefix_print_expr = CallExpression(Identifier("print"), [prefix_literal])
        prefix_print_stmt = ExpressionStatement(prefix_print_expr)

        value_print_expr = CallExpression(Identifier("println"), [value])
        value_print_stmt = ExpressionStatement(value_print_expr)

        return [prefix_print_stmt, value_print_stmt]

    #
    # more expansive helper
    #

    def _to_be_bytes(self, value: Expression) -> tuple[Expression, list[Statement]]:
        statements : list[Statement] = []

        # if the field is already a symbol we can reuse it, otherwise we need to
        # save it into an intermediate variable.
        field_sym = value.copy()
        if not isinstance(field_sym, Identifier):
            field_name = self.__name_dispenser.next("var")
            field_assign = LetStatement(field_name, field_sym)
            statements.append(field_assign)
            field_sym = field_name.copy()

        # TODO: FIXME: find out why the assertions keeps failing!
        #
        # 254 bits should be enough to represent most useful prime fields, but
        # if it is not, this assertion should catch the edge cases.
        # assert_max_bit_method = FieldAccessExpression(field_sym.copy(), Identifier("assert_max_bit_size"))
        # bit_size_literal = IntegerLiteral(self.FIELD_BIT_WIDTH)
        # assert_max_bit_call = CallExpression(assert_max_bit_method, [bit_size_literal])
        # assert_max_bit_stmt = ExpressionStatement(assert_max_bit_call)
        # statements.append(assert_max_bit_stmt)

        # now we can split everything into bits in big-endian manner and save it into
        # another temporary variable.
        to_be_bytes_method = FieldAccessExpression(field_sym.copy(), Identifier("to_be_bytes"))

        if self._is_version_ge(0, 34, 0):
            to_be_bytes_call = CallExpression(to_be_bytes_method, [])
        else:
            byte_size_literal = IntegerLiteral(self.FIELD_BYTE_WIDTH)
            to_be_bytes_call = CallExpression(to_be_bytes_method, [byte_size_literal])

        bytes_name = self.__name_dispenser.next("bytes")

        if self._is_version_ge(0, 34, 0):
            fixed_sized_byte_array_type = ListType(IntType(False, self.BYTE_BITS_WIDTH), self.FIELD_BYTE_WIDTH)
            to_be_bytes_assign = LetStatement(bytes_name, to_be_bytes_call, type_=fixed_sized_byte_array_type)
        else:
            to_be_bytes_assign = LetStatement(bytes_name, to_be_bytes_call)

        statements.append(to_be_bytes_assign)

        # return the name of the new bit vector
        return bytes_name.copy(), statements

    def _field_bit_op(self, lhs: Expression, rhs: Expression, op: NoirOperator) -> tuple[Expression, list[Statement]]:
        statements: list[Statement] = []
        lhs_bytes, lhs_stmts = self._to_be_bytes(lhs)
        statements += lhs_stmts
        rhs_bytes, rhs_stmts = self._to_be_bytes(rhs)
        statements += rhs_stmts

        value_name = self.__name_dispenser.next("bytes")
        value_bytes = LetStatement \
            ( value_name
            , ListLiteral([IntegerLiteral(0) for _ in range(self.FIELD_BYTE_WIDTH)])
            , ListType(IntType(False, 8), self.FIELD_BYTE_WIDTH)
            , True
            )
        statements.append(value_bytes)

        for_body: list[Statement] = []
        index_name = self.__name_dispenser.next("i")
        start_index = IntegerLiteral(0)
        end_index = IntegerLiteral(32) # <- doc says its exclusive
       
        lhs_index = IndexAccessExpression(lhs_bytes, index_name.copy())
        rhs_index = IndexAccessExpression(rhs_bytes, index_name.copy())
        value_index = IndexAccessExpression(value_name.copy(), index_name.copy())
        iter_expr = BinaryExpression(op, lhs_index, rhs_index)
        iter_assign = AssignStatement(value_index, iter_expr)
        for_body.append(iter_assign)

        for_stmt = ForStatement(index_name.copy(), start_index, end_index, for_body)
        statements.append(for_stmt)

        value_field = CallExpression(Identifier("std::field::bytes32_to_field"), [value_name.copy()])

        return value_field, statements

    def _field_and(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        return self._field_bit_op(lhs, rhs, NoirOperator.AND)

    def _field_or(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        return self._field_bit_op(lhs, rhs, NoirOperator.OR)

    def _field_xor(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        return self._field_bit_op(lhs, rhs, NoirOperator.XOR)
    
    #
    # Version helper Checks
    #

    def _is_version_ge(self, test_big: int, test_mid: int, test_small: int) -> bool:
        curr_big, curr_mid, curr_small = self._noir_version
        if curr_big > test_big:
            return True
        elif curr_big < test_big:
            return False
        else: # curr_big == test_big
            if curr_mid > test_mid:
                return True
            elif curr_mid < test_mid:
                return False
            else: # curr_mid == test_mid
                if curr_small > test_small:
                    return True
                elif curr_small < test_small:
                    return False
                else: # curr_small == test_small
                    return True