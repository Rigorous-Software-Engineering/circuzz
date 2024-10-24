from dataclasses import dataclass

@dataclass
class NoirType():
    def __str__(self):
        raise NotImplementedError()
    def copy(self) -> 'NoirType':
        raise NotImplementedError()

@dataclass
class ListType(NoirType):
    base: NoirType
    size: int | None = None
    def __str__(self):
        return f"[{self.base}; {self.size}]" if self.size else f"[{self.base}]"
    def copy(self) -> 'ListType':
        return ListType(self.base.copy(), self.size)

@dataclass
class TupleType(NoirType):
    elems: list[NoirType]
    def __str__(self):
        return "(" + ", ".join(map(str, self.elems)) + ")"
    def copy(self) -> 'TupleType':
        return TupleType([e.copy() for e in self.elems])

@dataclass
class StringType(NoirType):
    size: int | None = None
    def __str__(self):
        return f"str<{self.size}>" if self.size else "str"
    def copy(self) -> 'StringType':
        return StringType(self.size)

@dataclass
class FieldType(NoirType):
    def __str__(self):
        return "Field"
    def copy(self) -> 'FieldType':
        return FieldType()

@dataclass
class IntType(NoirType):
    signed: bool = False
    size: int = 64
    def __str__(self):
        return f"i{self.size}" if self.signed else f"u{self.size}"
    def copy(self) -> 'IntType':
        return IntType(self.signed, self.size)

@dataclass
class BoolType(NoirType):
    def __str__(self):
        return "bool"
    def copy(self) -> 'BoolType':
        return BoolType()