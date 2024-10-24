from dataclasses import dataclass

@dataclass(frozen=True)
class GnarkConfig():
    """
    gnark tool configuration
    """

    # amount of different circuits tested at the same time (should be >= 1)
    bundle_size : int

    # probability to chose boundary values as input values
    boundary_input_probability : float

    # how many inputs are executed on the circuits
    test_iterations : int

    # string which is provided for go test -timeout
    go_test_timeout : str | None

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> 'GnarkConfig':
        bundle_size = int(value.get("bundle_size", 5))
        boundary_input_probability = float(value.get("boundary_input_probability", 0.1))
        test_iterations = int(value.get("test_iterations", 1))
        go_test_timeout = value.get("go_test_timeout", None)
        return GnarkConfig \
            ( bundle_size = bundle_size
            , boundary_input_probability = boundary_input_probability
            , test_iterations = test_iterations
            , go_test_timeout = go_test_timeout
            )