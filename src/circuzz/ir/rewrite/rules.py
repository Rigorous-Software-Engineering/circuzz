from ..nodes import IRNode

from .parser import MatchFunctionType
from .parser import MatchParser
from .parser import RewriteFunctionType
from .parser import RewriteParser
from .parser import RewriteUtil

class RewriteRule():

    # public members
    name            : str
    match_pattern   : str
    rewrite_pattern : str

    # private computed members
    __match_func   : MatchFunctionType
    __rewrite_func : RewriteFunctionType

    def __init__ \
        ( self
        , name: str
        , match_pattern: str
        , rewrite_pattern: str
        ):

        self.name = name
        self.match_pattern = match_pattern
        self.rewrite_pattern = rewrite_pattern

        self.__match_func = MatchParser().parse(match_pattern)
        self.__rewrite_func = RewriteParser().parse(rewrite_pattern)

    def is_applicable(self, node: IRNode) -> bool:
        lookup = dict()
        return self.__match_func(lookup, node)

    def rewrite(self, node: IRNode, rewrite_util: RewriteUtil) -> IRNode | None:
        lookup = dict()
        if self.__match_func(lookup, node):
            rewrite_node = self.__rewrite_func(lookup, rewrite_util)
            rewrite_node.meta_info["rule"] = self.name
            return rewrite_node
        return None

    def __eq__(self, value: object) -> bool:
        if value == None or not isinstance(value, RewriteRule):
            return False
        return value.name == self.name and \
               value.match_pattern == self.match_pattern and \
               value.rewrite_pattern == self.rewrite_pattern

    def __hash__(self) -> int:
        # name should be unique which is why its used for hashing
        return self.name.__hash__()