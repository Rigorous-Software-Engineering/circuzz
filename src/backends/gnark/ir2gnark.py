from circuzz.common.helper import MAX_64_BITS_INTEGER

from circuzz.ir import nodes as IRNodes

from .nodes import *

class IR2GnarkVisitor():

    """
    NOTE:
        - circuit variables are replaced by "FVar_{name}"
        - circuit names are manipulated to contain a starting "C"
        - relations are implemented using a subset of relations
        - output signals are treated as normal variables (:= assign, no circuit member)

        - TODO: enable AssertIsDifferent again
        - TODO: think about modeling integers as big.NewInt(...)
        - TODO: deal with different assertion types
    """

    # output signals should be treated as normal variables
    __output_signals : set[str]

    # temporary variables count
    __temporary_variables : int

    def __init__(self):
        self.__output_signals = set()
        self.__temporary_variables = 0

    def transform(self, system: IRNodes.Circuit) -> CircuitDefinitionCollection:
       return self.visit_circuit(system)

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

    def visit_statement(self, node: IRNodes.IRNode) -> tuple[Statement | None, list[Statement]]:
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
        if node.name in self.__output_signals:
            return Identifier(node.name), []
        else:
            return FieldAccessExpression(Identifier("circuit"), f"FVar_{node.name}"), []

    def visit_boolean(self, node: IRNodes.Boolean) -> tuple[Expression, list[Statement]]:
        return Literal(1) if node.value else Literal(0), []

    def visit_integer(self, node: IRNodes.Integer) -> tuple[Expression, list[Statement]]:
        return self._new_big_int(node.value)

    def visit_unary_expression(self, node: IRNodes.UnaryExpression) -> tuple[Expression, list[Statement]]:
        expr, statements = self.visit_expression(node.value)
        if node.op == IRNodes.Operator.SUB:
            return self._neg(expr), statements
        if node.op == IRNodes.Operator.NOT and node.is_boolean_expression():
            return self._is_zero(expr), statements
        raise NotImplementedError(f"Unary expression is not supported '{node}'")

    def visit_binary_expression(self, node: IRNodes.BinaryExpression) -> tuple[Expression, list[Statement]]:
        statements = []
        lhs, lhs_tail = self.visit_expression(node.lhs)
        statements += lhs_tail
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements += rhs_tail

        match node.op:
            case IRNodes.Operator.MUL:
                return self._mul(lhs, rhs), statements
            case IRNodes.Operator.ADD:
                return self._add(lhs, rhs), statements
            case IRNodes.Operator.SUB:
                return self._sub(lhs, rhs), statements
            case IRNodes.Operator.EQU:
                return self._eq(lhs, rhs), statements
            case IRNodes.Operator.LTH:
                return self._lth(lhs, rhs), statements
            case IRNodes.Operator.LEQ:
                return self._leq(lhs, rhs), statements
            case IRNodes.Operator.GTH:
                return self._gth(lhs, rhs), statements
            case IRNodes.Operator.GEQ:
                return self._geq(lhs, rhs), statements
            case IRNodes.Operator.NEQ:
                return self._neq(lhs, rhs), statements
            case IRNodes.Operator.LAND:
                return self._and(lhs, rhs), statements
            case IRNodes.Operator.LOR:
                return self._or(lhs, rhs), statements
            case IRNodes.Operator.LXOR:
                return self._xor(lhs, rhs), statements
            case IRNodes.Operator.DIV:
                return self._div(lhs, rhs), statements
            case IRNodes.Operator.AND:
                bitwise_expr, bitwise_stmts = self._bitwise_and(lhs, rhs)
                statements += bitwise_stmts
                return bitwise_expr, statements
            case IRNodes.Operator.OR:
                bitwise_expr, bitwise_stmts = self._bitwise_or(lhs, rhs)
                statements += bitwise_stmts
                return bitwise_expr, statements
            case IRNodes.Operator.XOR:
                bitwise_expr, bitwise_stmts = self._bitwise_xor(lhs, rhs)
                statements += bitwise_stmts
                return bitwise_expr, statements
            case _:
                raise NotImplementedError(f"binary operator {node.op.value}")

    def visit_ternary_expression(self, node: IRNodes.TernaryExpression) -> tuple[Expression, list[Statement]]:
        statements = []
        cond, cond_tail = self.visit_expression(node.condition)
        statements += cond_tail
        if_expr, if_expr_tail = self.visit_expression(node.if_expr)
        statements += if_expr_tail
        else_expr, else_expr_tail = self.visit_expression(node.else_expr)
        statements += else_expr_tail
        return self._select(cond, if_expr, else_expr), statements

    def visit_assertion(self, node: IRNodes.Assertion) -> tuple[Statement, list[Statement]]:
        return self._visit_as_assertion_content(node.value)

    def visit_assignment(self, node: IRNodes.Assignment) -> tuple[Statement, list[Statement]]:
        statements = []
        lhs, lhs_tail = self.visit_expression(node.lhs)
        statements += lhs_tail
        rhs, rhs_tail = self.visit_expression(node.rhs)
        statements += rhs_tail

        is_definition = False
        if isinstance(node.lhs, IRNodes.Variable):
            if node.lhs.name in self.__output_signals:
                is_definition = True

        assignment = AssignStatement(lhs, rhs, is_definition)
        return assignment, statements

    def visit_assume(self, node: IRNodes.Assume) -> tuple[Statement, list[Statement]]:
        return self._visit_as_assertion_content(node.condition)

    def visit_circuit(self, node: IRNodes.Circuit) -> CircuitDefinitionCollection:
        # populate the circuit fields with input signals
        circuit_fields = [ CircuitStructField(f"FVar_{e}", False) for e in node.inputs ]
        # register all output signals for special handling
        self.__output_signals = set(node.outputs)

        circuit_struct = CircuitStruct(node.name, circuit_fields)

        # iterate over statements to build up definition function
        circuit_function_stmts = []
        for statement in node.statements:
            stmt, tail = self.visit_statement(statement)
            if stmt: # only if statement was parsed
                circuit_function_stmts += tail
                circuit_function_stmts.append(stmt)
        # add print statement for output signals (debug and make the compiler happy)
        for e in node.outputs:
            debug_stmt = self._print([Literal(f"{e}:"), Identifier(e)])
            circuit_function_stmts.append(debug_stmt)
        circuit_define = CircuitDefineFunction(node.name, circuit_function_stmts)

        # create circuit definition (bundle)
        return CircuitDefinitionCollection(node.name, circuit_struct, circuit_define)

    #
    # Helper
    #

    def _assert(self, value: Expression) -> Statement:
        return self._assert_eq(value, Literal(1))

    def _eq(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._is_zero(self._cmp(lhs, rhs))

    def _neq(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._is_zero(self._eq(lhs, rhs))

    def _gth(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._eq(self._cmp(lhs, rhs), Literal(1))

    def _geq(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._is_zero(self._lth(lhs, rhs))

    def _visit_as_assertion_content(self, value: IRNodes.Expression) -> tuple[Statement, list[Statement]]:
        if isinstance(value, IRNodes.BinaryExpression):
            # try to use the build in assertions
            statements = []
            lhs_expr, lhs_stmts = self.visit_expression(value.lhs)
            statements += lhs_stmts
            rhs_expr, rhs_stmts = self.visit_expression(value.rhs)
            statements += rhs_stmts
            match value.op:
                case IRNodes.Operator.EQU:
                    return self._assert_eq(lhs_expr, rhs_expr), statements
                case IRNodes.Operator.LEQ:
                    return self._assert_le(lhs_expr, rhs_expr), statements
                case IRNodes.Operator.GEQ:
                    return self._assert_le(rhs_expr, lhs_expr), statements
                case IRNodes.Operator.NEQ:
                    return self._assert_ne(lhs_expr, rhs_expr), statements
                case _:
                    pass # not possible to use default assertions

        # use api.Cmp to deal with boolean expressions
        expr, statements = self.visit_expression(value)
        return self._assert(expr), statements

    #
    # API wrapper functions
    #

    def _api_expr(self, func: str, args: list[Expression]) -> CallExpression:
        return CallExpression(FieldAccessExpression(Identifier("api"), func), args)

    def _api_stmt(self, func: str, args: list[Expression]) -> CallStatement:
        return CallStatement(self._api_expr(func, args))

    # Arithmetic wrappers

    def _add(self, lhs: Expression, rhs: Expression) ->  Expression:
        return self._api_expr("Add", [lhs, rhs])

    def _mulacc(self, a: Expression, b: Expression, c: Expression) ->  Expression:
        return self._api_expr("MulAcc", [a, b, c])

    def _neg(self, value: Expression) ->  Expression:
        return self._api_expr("Neg", [value])

    def _sub(self, lhs: Expression, rhs: Expression) ->  Expression:
        return self._api_expr("Sub", [lhs, rhs])

    def _mul(self, lhs: Expression, rhs: Expression) ->  Expression:
        return self._api_expr("Mul", [lhs, rhs])

    def _div_unchecked(self, lhs: Expression, rhs: Expression) ->  Expression:
        return self._api_expr("DivUnchecked", [lhs, rhs])

    def _div(self, lhs: Expression, rhs: Expression) ->  Expression:
        return self._api_expr("Div", [lhs, rhs])

    def _inv(self, value: Expression) -> Expression:
        return self._api_expr("Inverse", [value])

    # Bit Operations Wrapper (variable must be 0 or 1)

    def _xor(self, lhs: Expression, rhs: Expression) ->  Expression:
        return self._api_expr("Xor", [lhs, rhs])

    def _or(self, lhs: Expression, rhs: Expression) ->  Expression:
        return self._api_expr("Or", [lhs, rhs])

    def _and(self, lhs: Expression, rhs: Expression) ->  Expression:
        return self._api_expr("And", [lhs, rhs])

    # Conditionals Wrapper

    def _select(self, cond: Expression, if_expr: Expression, else_expr: Expression) -> Expression:
        return self._api_expr("Select", [cond, if_expr, else_expr])

    # Is Zero Wrapper

    def _is_zero(self, value: Expression) -> Expression:
        return self._api_expr("IsZero", [value])

    # Comparator Wrapper

    def _cmp(self, lhs: Expression, rhs: Expression) ->  Expression:
        """
        The result is
            -)  1 if i1>i2,
            -)  0 if i1=i2,
            -) -1 if i1<i2.
        """
        return self._api_expr("Cmp", [lhs, rhs])

    # Assertion Wrapper

    def _assert_eq(self, lhs: Expression, rhs: Expression) ->  Statement:
        return self._api_stmt("AssertIsEqual", [lhs, rhs])

    def _assert_ne(self, lhs: Expression, rhs: Expression) ->  Statement:
        return self._api_stmt("AssertIsDifferent", [lhs, rhs])

    def _assert_le(self, lhs: Expression, rhs: Expression) ->  Statement:
        return self._api_stmt("AssertIsLessOrEqual", [lhs, rhs])

    # Helper wrapper

    def _print(self, values: list[Expression]) -> Statement:
        return self._api_stmt("Println", values)

    def _compiler(self) -> Statement:
        return self._api_stmt("Compiler", [])

    #
    # cmp package functions
    #

    def _cmp_expr(self, func: str, args: list[Expression]) -> CallExpression:
        return CallExpression(FieldAccessExpression(Identifier("cmp"), func), [Identifier("api")] + args)

    def _lth(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._cmp_expr("IsLess", [lhs, rhs])

    def _leq(self, lhs: Expression, rhs: Expression) -> Expression:
        return self._cmp_expr("IsLessOrEqual", [lhs, rhs])

    #
    # bits package
    #

    def _bits_expr(self, func: str, args: list[Expression]) -> Expression:
        return CallExpression(FieldAccessExpression(Identifier("bits"), func), [Identifier("api")] + args)

    def _to_binary(self, value: Expression) -> Expression:
        return self._bits_expr("ToBinary", [value])

    def _from_binary(self, value: Expression) -> Expression:
        return self._bits_expr("FromBinary", [value])

    #
    # bitwise helper
    #

    def _to_binary_as_stmt(self, value: Expression) -> tuple[Identifier, list[Statement]]:
        name = self._dispense_tmp_identifier("bits")
        expr = self._to_binary(value)
        stmt = AssignStatement(name, expr, is_definition=True)
        return name.copy(), [stmt]

    def _from_binary_as_stmt(self, value: Expression) -> tuple[Identifier, list[Statement]]:
        name = self._dispense_tmp_identifier("res")
        expr = self._from_binary(value)
        stmt = AssignStatement(name, expr, is_definition=True)
        return name.copy(), [stmt]

    def _field_bit_len(self) -> Expression:
        compiler = CallExpression(FieldAccessExpression(Identifier("api"), "Compiler"), [])
        fieldBitLen = CallExpression(FieldAccessExpression(compiler, "FieldBitLen"), [])
        return fieldBitLen

    def _bitwise_wrapper(self, lhs: Expression, rhs: Expression, api_func: str) -> tuple[Expression, list[Statement]]:
        """
        bits_1 := api.ToBinary(lhs)
        bits_2 := api.ToBinary(rhs)
        for i := 0; i < fieldBitLen; i++ {
            bits_lhs[i] = api.<BIT_OPERATION>(bits_lhs[i], bits_rhs[i])
        }
        expr_3 := api.FromBinary(bits_1)
        """
        # prolog
        statements = []
        lhs2bin_var, lhs2bin_stmt = self._to_binary_as_stmt(lhs)
        statements += lhs2bin_stmt
        rhs2bin_var, rhs2bin_stmt = self._to_binary_as_stmt(rhs)
        statements += rhs2bin_stmt

        # body
        body = []
        lhs_bit = IndexAccessExpression(lhs2bin_var, Identifier("i"))
        rhs_bit = IndexAccessExpression(rhs2bin_var, Identifier("i"))
        bit_expr = self._api_expr(api_func,[lhs_bit, rhs_bit])
        bit_assign = AssignStatement(lhs_bit.copy(), bit_expr, is_definition=False)
        body.append(bit_assign)

        # loop
        loop_stmt = ForLoop(Literal(0), self._field_bit_len(), body, "i")
        statements.append(loop_stmt)

        # epilog
        result, from_bin_stmt = self._from_binary_as_stmt(lhs2bin_var.copy())
        statements += from_bin_stmt

        return result, statements

    def _bitwise_or(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        return self._bitwise_wrapper(lhs, rhs, "Or")

    def _bitwise_and(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        return self._bitwise_wrapper(lhs, rhs, "And")

    def _bitwise_xor(self, lhs: Expression, rhs: Expression) -> tuple[Expression, list[Statement]]:
        return self._bitwise_wrapper(lhs, rhs, "Xor")

    #
    # temporary helpers
    #

    def _dispense_tmp_name(self, prefix : str = "tmp") -> str:
        name = f"{prefix}_{self.__temporary_variables}"
        self.__temporary_variables += 1
        return name

    def _dispense_tmp_identifier(self, prefix : str = "tmp") -> Identifier:
        return Identifier(self._dispense_tmp_name(prefix=prefix))
    
    #
    # big int helpers
    #

    def _new_big_int(self, value : int) -> tuple[Identifier, list[Statement]]:
        identifier = self._dispense_tmp_identifier("cons")

        intId = FieldAccessExpression(Identifier("big"), "Int")
        newExpr = CallExpression(Identifier("new"), [intId])
        declaration = AssignStatement(identifier, newExpr, True)

        if value <= MAX_64_BITS_INTEGER: # fits uint64
            setMethod = FieldAccessExpression(identifier.copy(), "SetUint64")
            setMethodExpr = CallExpression(setMethod, [Literal(value)])
        else: # needs decoding from string
            setMethod = FieldAccessExpression(identifier.copy(), "SetString")
            setMethodExpr = CallExpression(setMethod, [Literal(str(value)), Literal(10)])

        definition = CallStatement(setMethodExpr)

        return identifier.copy(), [declaration, definition]