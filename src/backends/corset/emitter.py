import io

from .nodes import *

class EmitVisitor():

    def __init__(self):
        self.indent = 0
        self.buffer = io.StringIO()

    def emit(self, node: ASTNode) -> str:
        self.indent = 0
        self.buffer = io.StringIO()
        self.visit(node)
        return self.buffer.getvalue()

    def visit(self, node: ASTNode):
        match node:
            case Module():
                self.visit_module(node)
            case ListStatement():
                self.visit_list_statement(node)
            case Identifier():
                self.visit_identifier(node)
            case FieldAccess():
                self.visit_field_access(node)
            case IndexAccessExpression():
                self.visit_index_access_expression(node)
            case Literal():
                self.visit_literal(node)
            case _:
                raise NotImplementedError(f"unsupported node type '{node.__class__}'")

    def visit_module(self, node: Module):
        self.buffer.write(self.current_indent)
        self.buffer.write(f"(module {node.name})\n")
        last_idx = len(node.statements) - 1
        for idx, statement in enumerate(node.statements):
            self.buffer.write(self.current_indent)
            self.visit(statement)
            if idx < last_idx:
                self.buffer.write("\n")

    def visit_list_statement(self, node: ListStatement):
        self.buffer.write(self.current_indent)
        self.visit_literal(node.expr)

    def visit_identifier(self, node: Identifier):
        self.buffer.write(node.name)

    def visit_field_access(self, node: FieldAccess):
        self.visit(node.expr)
        self.buffer.write(".")
        self.buffer.write(node.field)

    def visit_index_access_expression(self, node: IndexAccessExpression):
        self.buffer.write("[")
        self.visit(node.expr)
        self.buffer.write(" ")
        self.visit(node.index)
        self.buffer.write("]")

    def visit_literal(self, node: Literal):
        if node.is_bool():
            self.buffer.write("true" if node.value else "false")
        elif node.is_int():
            self.buffer.write(str(node.value))
        elif node.is_list():
            assert isinstance(node.value, list)
            self.buffer.write("(")
            last_idx = len(node.value) - 1
            for idx, e in enumerate(node.value):
                self.visit(e)
                if last_idx > idx:
                    self.buffer.write(" ")
            self.buffer.write(")")
        else: # string
            assert node.is_str(), "unexpected literal"
            self.buffer.write(f"\"{node.value}\"")

    @property
    def current_indent(self):
        return " " * self.indent