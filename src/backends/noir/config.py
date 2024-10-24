from dataclasses import dataclass

@dataclass(frozen=True)
class NoirConfig():
    """
    noir tool configuration
    """

    # probability to chose boundary values for inputs
    boundary_input_probability : float

    # this value determines how often tests are executed
    test_iterations  : int

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> 'NoirConfig':
        boundary_input_probability = float(value.get("boundary_input_probability", 0.1))
        test_iterations  = int(value.get("test_iterations", 5))
        return NoirConfig \
          ( boundary_input_probability = boundary_input_probability
          , test_iterations = test_iterations
          )