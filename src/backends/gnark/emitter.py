import io

from .nodes import *

class EmitVisitor():

    def __init__(self):
        self.tabs = 0
        self.buffer = io.StringIO()

    def emit(self, node: ASTNode) -> str:
        self.tabs = 0
        self.buffer = io.StringIO()
        self.visit(node)
        return self.buffer.getvalue()

    def emit_to_buffer(self, buffer: io.StringIO, node: ASTNode):
        self.tabs = 0
        _buffer = self.buffer
        self.buffer = buffer
        self.visit(node)
        self.buffer = _buffer # reset such that it cannot be misused

    def visit(self, node: ASTNode):
        match node:
            case CircuitStructField():
                self.visit_circuit_struct_field(node)
            case CircuitStruct():
                self.visit_circuit_struct(node)
            case CircuitDefineFunction():
                self.visit_circuit_define_function(node)
            case CircuitDefinitionCollection():
                self.visit_circuit_definition_collection(node)
            case CallStatement():
                self.visit_call_statement(node)
            case AssignStatement():
                self.visit_assign_statement(node)
            case ForLoop():
                self.visit_for_loop(node)
            case Identifier():
                self.visit_identifier(node)
            case FieldAccessExpression():
                self.visit_field_access_expression(node)
            case CallExpression():
                self.visit_call_expression(node)
            case IndexAccessExpression():
                self.visit_index_access_expression(node)
            case Literal():
                self.visit_literal(node)
            case _:
                raise NotImplementedError(f"unsupported node type '{node.__class__}'")

    def visit_circuit_struct_field(self, node: CircuitStructField):
        self.buffer.write(self.current_tabs)
        self.buffer.write(f"{node.name} frontend.Variable")
        if node.is_public:
            self.buffer.write(" `gnark:\",public\"`")

    def visit_circuit_struct(self, node: CircuitStruct):
        self.buffer.write(self.current_tabs)
        self.buffer.write(f"type {node.name} struct {{\n")
        self.tabs += 1
        for field in node.fields:
            self.visit_circuit_struct_field(field)
            self.buffer.write("\n")
        self.tabs -= 1
        self.buffer.write("}")

    def visit_circuit_define_function(self, node: CircuitDefineFunction):
        self.buffer.write(f"func (circuit *{node.name}) Define(api frontend.API) error {{\n")
        self.tabs += 1
        for stmt in node.statements:
            self.visit(stmt)
            self.buffer.write("\n")
        # finally return nil (no error)
        self.buffer.write(f"{self.current_tabs}return nil // no error\n")
        self.tabs -= 1
        self.buffer.write("}")

    def visit_circuit_definition_collection(self, node: CircuitDefinitionCollection):
        self.visit_circuit_struct(node.circuit_struct)
        self.buffer.write("\n\n")
        self.visit_circuit_define_function(node.circuit_define)

    def visit_call_statement(self, node: CallStatement):
        self.buffer.write(self.current_tabs)
        self.visit_call_expression(node.expr)

    def visit_assign_statement(self, node: AssignStatement):
        self.buffer.write(self.current_tabs)
        self.visit(node.lhs)
        self.buffer.write(" := " if node.is_definition else " = ")
        self.visit(node.rhs)

    def visit_for_loop(self, node: ForLoop):
        self.buffer.write(self.current_tabs)
        self.buffer.write(f"for {node.index_var} := ")
        self.visit(node.start)
        self.buffer.write(f"; {node.index_var} < ")
        self.visit(node.end)
        self.buffer.write(f"; {node.index_var}++ {{\n")
        self.tabs += 1
        for e in node.body:
            self.visit(e)
            self.buffer.write("\n")
        self.tabs -= 1
        self.buffer.write(self.current_tabs)
        self.buffer.write("}")

    def visit_identifier(self, node: Identifier):
        self.buffer.write(node.name)

    def visit_field_access_expression(self, node: FieldAccessExpression):
        self.visit(node.expr)
        self.buffer.write(".")
        self.buffer.write(node.field)

    def visit_call_expression(self, node: CallExpression):
        self.visit(node.expr)
        self.buffer.write("(")
        for idx, arg in enumerate(node.args):
            self.visit(arg)
            if idx+1 != len(node.args): # if not the last
                self.buffer.write(", ")
        self.buffer.write(")")

    def visit_index_access_expression(self, node: IndexAccessExpression):
        self.visit(node.expr)
        self.buffer.write("[")
        self.visit(node.index)
        self.buffer.write("]")

    def visit_literal(self, node: Literal):
        if node.is_bool():
            self.buffer.write("true" if node.value else "false")
        elif node.is_int():
            self.buffer.write(str(node.value))
        else: # string
            assert node.is_str(), "unexpected literal"
            self.buffer.write(f"\"{node.value}\"")

    @property
    def current_tabs(self):
        return "\t" * self.tabs