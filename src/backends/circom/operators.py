from enum import StrEnum

class SignalKind(StrEnum):
    OUTPUT = "output"
    INPUT = "input"
    INTERMEDIATE = ""

class Operator(StrEnum):

    """
    Operator presedence:
        https://doc.rust-lang.org/1.22.1/reference/expressions/operator-expr.html#operator-precedence
    """

    """
    boolean operators:
    """
    LAND   = "&&"
    LOR    = "||"
    NOT = "!"

    """
    relational operators:
    """
    EQU = "=="
    NEQ = "!="
    LEQ = "<="
    LTH = "<"
    GEQ = ">="
    GTH = ">"

    """
    arithmetic operators:
    """
    ADD = "+"   #  a + b   Arithmetic addition modulo p
    SUB = "-"   #  a - b   Arithmetic subtraction modulo p
    MUL = "*"   #  a * b   Arithmetic multiplication modulo p
    POW = "**"  #  a ** b  Power modulo p
    DIV = "/"   #  a / b   Multiplication by the inverse modulo p
    QUO = "\\"  #  a \ b   Quotient of the integer division
    REM = "%"   #  a % b   Remainder of the integer division

    """
    arithmetic final assignment operators:
    """
    ADD_ASSIGN = "+="   #  a += b  Arithmetic addition modulo p and assignment
    SUB_ASSIGN = "-="   #  a -= b  Arithmetic subtraction modulo p and assignment
    MUL_ASSIGN = "*="   #  a *= b  Arithmetic multiplication modulo p and assignment
    POW_ASSIGN = "**="  #  a ** b  Power modulo p and assignment
    DIV_ASSIGN = "/="   #  a /= b  Multiplication by the inverse modulo p and assignment
    QUO_ASSIGN = "\\="  #  a \= b  Quotient of the integer division and assignment
    REM_ASSIGN = "%="   #  a %= b  Remainder of the integer division and assignment
    INC        = "++"   #  a++     Unit increment. Syntactic sugar for a += 1
    DEC        = "--"   #  a--     Unit decrement. Syntactic sugar for a -= 1

    """
    bitwise operators:
    """
    AND  = "&"   #  a & b   Bitwise AND
    OR   = "|"   #  a | b   Bitwise OR
    COMP = "~"   #  ~a      Complement 254 bits
    XOR  = "^"   #  a ^ b   XOR 254 bits
    SHR  = ">>"  #  a >> 4  Right shift operator
    SHL  = "<<"  #  a << 4  Left shift operator

    """
    bitwise final assignment operators:
    """
    AND_ASSIGN  = "&="  #  a &= b      Bitwise AND and assignment
    OR_ASSIGN   = "|="  #  a |= b      Bitwise OR and assignment
    COMP_ASSIGN = "~="  #  ~=a         Complement 254 bits and assignment
    XOR_ASSIGN  = "^="  #  a ^= b      XOR 254 bits and assignment
    SHR_ASSIGN  = ">>=" #  a >>= 4     Right shift operator and assignment
    SHL_ASSIGN  = "<<=" #  a <<= 4     Left shift operator and assignment

    """
    assign operator:
    """
    ASSIGN = "="  #  b = a   simple assignment

    """
    constraint operators:
    """
    EQU_CONSTRAINT = "==="                      # creates the simplified form of the given equality constraint.
    EQU_CONSTRAINT_SIGNAL_ASSIGN_LEFT = "<=="   # combination of equivalent constraint wth signal assign
    SIGNAL_ASSIGN_LEFT = "<--"                  # signal assignment
    EQU_CONSTRAINT_SIGNAL_ASSIGN_RIGHT = "==>"  # combination of equivalent constraint wth signal assign
    SIGNAL_ASSIGN_RIGHT = "-->"                 # signal assignment

    @staticmethod
    def linear_connectors():
        return [Operator.ADD, Operator.SUB]

    @staticmethod
    def constant_wrapper_connectors():
        return [Operator.ADD, Operator.SUB, Operator.MUL]