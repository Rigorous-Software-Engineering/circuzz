import io

from .nodes import *

class EmitVisitor():

    def __init__(self):
        self.indent = 0
        self.buffer = io.StringIO()

    def emit(self, node : ASTNode) -> str:
        self.indent = 0
        self.buffer = io.StringIO()
        self.visit(node)
        return self.buffer.getvalue()

    def visit(self, node: ASTNode):
        match node:
            case Identifier():
                self.visit_identifier(node)
            case BinaryExpression():
                self.visit_binary_expression(node)
            case UnaryExpression():
                self.visit_unary_expression(node)
            case CallExpression():
                self.visit_call_expression(node)
            case IndexAccessExpression():
                self.visit_index_access_expression(node)
            case FieldAccessExpression():
                self.visit_field_access_expression(node)
            case BasicBlock():
                self.visit_basic_block(node)
            case IfStatement():
                self.visit_if_statement(node)
            case ForStatement():
                self.visit_for_statement(node)
            case LetStatement():
                self.visit_let_statement(node)
            case AssignStatement():
                self.visit_assign_statement(node)
            case AssertStatement():
                self.visit_assert_statement(node)
            case ExpressionStatement():
                self.visit_expression_statement(node)
            case ReturnStatement():
                self.visit_return_statement(node)
            case StringLiteral():
                self.visit_string_literal(node)
            case BooleanLiteral():
                self.visit_boolean_literal(node)
            case IntegerLiteral():
                self.visit_integer_literal(node)
            case ListLiteral():
                self.visit_list_literal(node)
            case TupleLiteral():
                self.visit_tuple_literal(node)
            case FunctionDefinition():
                self.visit_function_definition(node)
            case VariableDefinition():
                self.visit_variable_definition(node)
            case Document():
                self.visit_document(node)

    def visit_identifier(self, node: Identifier):
        self.buffer.write(node.name)

    def visit_binary_expression(self, node: BinaryExpression):
        self.buffer.write("(")
        self.visit(node.lhs)
        self.buffer.write(f" {node.operator.value} ")
        self.visit(node.rhs)
        self.buffer.write(")")

    def visit_unary_expression(self, node: UnaryExpression):
        self.buffer.write("(")
        self.buffer.write(f"{node.operator.value} ")
        self.visit(node.value)
        self.buffer.write(")")

    def visit_call_expression(self, node: CallExpression):
        self.visit(node.reference)
        self.buffer.write("(")
        self._print_comma_separated(node.arguments)
        self.buffer.write(")")
   
    def visit_index_access_expression(self, node: IndexAccessExpression):
        self.visit(node.reference)
        self.buffer.write("[")
        self.visit(node.index)
        self.buffer.write("]")

    def visit_field_access_expression(self, node: FieldAccessExpression):
        self.visit(node.reference)
        self.buffer.write(".")
        self.visit(node.field)

    def visit_basic_block(self, node: BasicBlock):
        self.buffer.write(self.current_indent + "{\n")
        self.indent += 4
        for s in node.statements:
            self.visit(s)
            self.buffer.write("\n")
        self.indent -= 4
        self.buffer.write(self.current_indent + "}")

    def visit_if_statement(self, node: IfStatement):
        self.buffer.write(self.current_indent + "if ")
        self.visit(node.condition)
        self.buffer.write("\n")
        self.visit(node.true_stmt)
        self.buffer.write("\n")
        if node.false_stmt:
            self.buffer.write(self.current_indent + "else\n")
            self.visit(node.false_stmt)

    def visit_for_statement(self, node: ForStatement):
        self.buffer.write(self.current_indent + "for ")
        self.visit(node.index)
        self.buffer.write(" in ")
        self.visit(node.start)
        self.buffer.write("..")
        self.visit(node.end)
        self.buffer.write(" {\n")
        self.indent += 4
        for stmt in node.statements:
            self.visit(stmt)
            self.buffer.write("\n")
        self.indent -= 4
        self.buffer.write(self.current_indent + "}")
       

    def visit_let_statement(self, node: LetStatement):
        self.buffer.write(self.current_indent + "let ")
        if node.is_mutable:
            self.buffer.write("mut ")
        self.visit(node.name)
        if node.type_:
            self.buffer.write(" : ")
            self.buffer.write(str(node.type_))
        if node.expr:
            self.buffer.write(" = ")
            self.visit(node.expr)
        self.buffer.write(";")
   
    def visit_assign_statement(self, node: AssignStatement):
        self.buffer.write(self.current_indent)
        self.visit(node.lhs)
        self.buffer.write(" = ")
        self.visit(node.rhs)
        self.buffer.write(";")

    def visit_assert_statement(self, node: AssertStatement):
        self.buffer.write(self.current_indent + "assert(")
        self.visit(node.condition)
        if node.message:
            self.buffer.write(", ")
            self.visit(node.message)
        self.buffer.write(");")

    def visit_expression_statement(self, node: ExpressionStatement):
        self.buffer.write(self.current_indent)
        self.visit(node.expr)
        if node.is_semicolon:
            self.buffer.write(";")

    def visit_return_statement(self, node: ReturnStatement):
        self.buffer.write(self.current_indent + "return ")
        self.visit(node.value)
        self.buffer.write(";")

    def visit_string_literal(self, node: StringLiteral):
        self.buffer.write(f'"{node.value}"')

    def visit_boolean_literal(self, node: BooleanLiteral):
        self.buffer.write("true" if node.value else "false")

    def visit_integer_literal(self, node: IntegerLiteral):
        self.buffer.write(str(node.value))

    def visit_list_literal(self, node: ListLiteral):
        self.buffer.write("[")
        self._print_comma_separated(node.value)
        self.buffer.write("]")

    def visit_tuple_literal(self, node: TupleLiteral):
        self.buffer.write("(")
        self._print_comma_separated(node.value)
        self.buffer.write(")")

    def visit_function_definition(self, node: FunctionDefinition):
        if node.is_public:
            self.buffer.write("pub ")
        self.buffer.write(self.current_indent + "fn ")
        self.visit(node.name)
        self.buffer.write("(")
        self._print_comma_separated(node.arguments)
        self.buffer.write(")")
        if node.type_:
            if node.is_public_return:
                self.buffer.write(f" -> pub {str(node.type_)}")
            else:
                self.buffer.write(f" -> pub {str(node.type_)}")
        if isinstance(node.body, BasicBlock):
            self.buffer.write(" ")
            self.visit(node.body)
        else:
            self.buffer.write("\n")
            self.indent += 4
            self.visit(node.body)
            self.indent -= 4

    def visit_variable_definition(self, node: VariableDefinition):
        self.visit(node.name)
        self.buffer.write(f" : {node.type_}")

    def visit_document(self, node: Document):
        self.buffer.write("use dep::std;")
        self.buffer.write("\n\n")
        self.visit(node.main)

    @property
    def current_indent(self):
        return " " * self.indent

    def _print_comma_separated(self, arguments: list):
        argument_count = len(arguments)
        argument_index = 0
        for argument in arguments:
            self.visit(argument)
            argument_index += 1
            if argument_index < argument_count:
                self.buffer.write(", ")