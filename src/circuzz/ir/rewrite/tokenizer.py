from .error import RuleParserException
from ..nodes import *

class TokenKind(StrEnum):
    OPERATOR = "<operator>"
    IDENTIFIER = "<identifier>"
    NUMBER = "<number>"
    BOOLEAN = "<boolean>"
    PARENTHESIS_LEFT = "'('"
    PARENTHESIS_RIGHT = "')'"
    CURLY_PARENTHESIS_LEFT = "'{'"
    CURLY_PARENTHESIS_RIGHT = "'}'"
    SEMICOLON = "';'"
    COLON = "':'"
    QUESTION_MARK = "'?'"
    DOLLAR = "'$'"

@dataclass
class Token():
    value: str | int | bool | Operator | None
    kind: TokenKind
    pos_start: int
    pos_end: int

    def __str__(self):
        return f"{self.kind.value}({self.value}, {self.pos_start}:{self.pos_end})"

class Tokenizer():
    CHARACTERS = "abcdefghijklmnopqrstuvwABCDEFGHIJKLMNOPQRSTUVW_"
    DIGITS = "1234567890"
    CHARACTERS_AND_DIGITS = "abcdefghijklmnopqrstuvwABCDEFGHIJKLMNOPQRSTUVW_1234567890"
    BOOLS = "TF"
    WHITESPACE = " \n\r\t"
    OPERATOR_SYMBOLS = "*-+=!<>&|/%^~"

    def __init__(self):
        self.position = 0

    def tokenize(self, value: str) -> list[Token]:
        return self._tokenize(value, 0)

    def _tokenize(self, value: str, ptr: int) -> list[Token]:
        result = []
        while len(value) > ptr:
            # skip over all whitespaces
            while len(value) > ptr and value[ptr] in self.WHITESPACE:
                ptr+=1
            if len(value) == ptr:
                break # stream ended with whitespace so it is safe to break

            SINGLE_SYMBOLS = ["(", ")", "{", "}", "?", ";", "$", ":"]
            if value[ptr] in SINGLE_SYMBOLS:
                token_kind = \
                    { "(" : TokenKind.PARENTHESIS_LEFT
                    , ")" : TokenKind.PARENTHESIS_RIGHT
                    , "{" : TokenKind.CURLY_PARENTHESIS_LEFT
                    , "}" : TokenKind.CURLY_PARENTHESIS_RIGHT
                    , "?" : TokenKind.QUESTION_MARK
                    , ";" : TokenKind.SEMICOLON
                    , "$" : TokenKind.DOLLAR
                    , ":" : TokenKind.COLON
                    }.get(value[ptr])
                assert token_kind, f"unexpected single symbol {value[ptr]}"
                result.append(Token(None, token_kind, ptr, ptr))
                ptr+=1
            elif value[ptr] in self.BOOLS:
                # parse bool
                token = Token(value[ptr] == "T", TokenKind.BOOLEAN, ptr, ptr)
                result.append(token)
                ptr+=1
            elif value[ptr] in self.CHARACTERS:
                # parse variable
                token = self._tokenize_identifier(value, ptr)
                result.append(token)
                ptr=token.pos_end+1
            elif value[ptr] in self.DIGITS:
                # parse number
                token = self._tokenize_number(value, ptr)
                result.append(token)
                ptr=token.pos_end+1
            elif value[ptr] in self.OPERATOR_SYMBOLS:
                # parse operator
                token = self._tokenize_operator(value, ptr)
                result.append(token)
                ptr=token.pos_end+1
            else:
                msg = f"Unexpected character '{value[ptr]}' at position '{ptr}'!"
                raise RuleParserException(ptr, msg)
        return result

    def _tokenize_identifier(self, value: str, ptr: int) -> Token:
        name = ""
        pos_start = ptr
        while len(value) > ptr and value[ptr] in self.CHARACTERS_AND_DIGITS:
            name += value[ptr]
            ptr += 1
        return Token(name, TokenKind.IDENTIFIER, pos_start, ptr-1)

    def _tokenize_number(self, value: str, ptr: int) -> Token:
        number_str = ""
        pos_start = ptr
        while len(value) > ptr and value[ptr] in self.DIGITS:
            number_str += value[ptr]
            ptr += 1
        number = int(number_str)
        return Token(number, TokenKind.NUMBER, pos_start, ptr-1)

    def _tokenize_operator(self, value: str, ptr: int) -> Token:
        match value[ptr]:
            case "*":
                if value[ptr+1] == "*":
                    return Token(Operator.POW, TokenKind.OPERATOR, ptr, ptr+1)
                else:
                    return Token(Operator.MUL, TokenKind.OPERATOR, ptr, ptr)
            case "-":
                return Token(Operator.SUB, TokenKind.OPERATOR, ptr, ptr)
            case "+":
                return Token(Operator.ADD, TokenKind.OPERATOR, ptr, ptr)
            case "/":
                return Token(Operator.DIV, TokenKind.OPERATOR, ptr, ptr)
            case "%":
                return Token(Operator.REM, TokenKind.OPERATOR, ptr, ptr)
            case "=":
                if value[ptr+1] == "=":
                    return Token(Operator.EQU, TokenKind.OPERATOR, ptr, ptr+1)
                msg = f"Expects '=' at position {ptr}, but found {value[ptr]}!"
                raise RuleParserException(ptr, msg)
            case "!":
                if value[ptr+1] == "=":
                    return Token(Operator.NEQ, TokenKind.OPERATOR, ptr, ptr+1)
                else:
                    return Token(Operator.NOT, TokenKind.OPERATOR, ptr, ptr)
            case "<":
                if value[ptr+1] == "=":
                   return Token(Operator.LEQ, TokenKind.OPERATOR, ptr, ptr+1)
                else:
                    return Token(Operator.LTH, TokenKind.OPERATOR, ptr, ptr)
            case ">":
                if value[ptr+1] == "=":
                    return Token(Operator.GEQ, TokenKind.OPERATOR, ptr, ptr+1)
                else:
                    return Token(Operator.GTH, TokenKind.OPERATOR, ptr, ptr)
            case "&":
                if value[ptr+1] == "&":
                    return Token(Operator.LAND, TokenKind.OPERATOR, ptr, ptr+1)
                else:
                    return Token(Operator.AND, TokenKind.OPERATOR, ptr, ptr)
            case "|":
                if value[ptr+1] == "|":
                    return Token(Operator.LOR, TokenKind.OPERATOR, ptr, ptr+1)
                else:
                    return Token(Operator.OR, TokenKind.OPERATOR, ptr, ptr)
            case "^":
                if value[ptr+1] == "^":
                    return Token(Operator.LXOR, TokenKind.OPERATOR, ptr, ptr+1)
                else:
                    return Token(Operator.XOR, TokenKind.OPERATOR, ptr, ptr)
            case "~":
                return Token(Operator.COMP, TokenKind.OPERATOR, ptr, ptr)
            case   _:
                msg = f"Expects '*', '-', '+', '=', '!', '<', '>', '~', '&', '|' or '^' at position {ptr}, but found {value[ptr]}!"
                raise RuleParserException(ptr, msg)