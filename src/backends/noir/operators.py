
from enum import StrEnum

class NoirOperator(StrEnum):
    ADD = "+"  # Adds two private input types together Types must be private input
    SUB = "-"  # Subtracts two private input types together Types must be private input
    MUL = "*"  # Multiplies two private input types together Types must be private input
    DIV = "/"  # Divides two private input types together Types must be private input
    XOR = "^"  # XOR two private input types together Types must be integer
    AND = "&"  # AND two private input types together Types must be integer
    OR = "|"   # OR two private input types together Types must be integer
    SHL = "<<" # Left shift an integer by another integer amount Types must be integer, shift must be u8
    SHR = ">>" # Right shift an integer by another integer amount Types must be integer, shift must be u8
    NOT = "!"  # Bitwise not of a value Type must be integer or boolean
    LTH = "<"  # returns a bool if one value is less than the other Upper bound must have a known bit size
    LEQ = "<=" # returns a bool if one value is less than or equal to the other Upper bound must have a known bit size
    GTH = ">"  # returns a bool if one value is more than the other Upper bound must have a known bit size
    GEQ = ">=" # returns a bool if one value is more than or equal to the other Upper bound must have a known bit size
    EQU = "==" # returns a bool if one value is equal to the other Both types must not be constants
    NEQ = "!=" # returns a bool if one value is not equal to the other Both types must not be constants
    REM = "%"
    COMP = "~"