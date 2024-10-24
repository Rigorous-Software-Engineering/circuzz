class RuleParserException(Exception):
    def __init__(self, position: int, message: str):
        super().__init__(message)
        self.position = position
        self.message = message