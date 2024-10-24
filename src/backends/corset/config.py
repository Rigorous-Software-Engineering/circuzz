from dataclasses import dataclass

@dataclass(frozen=True)
class CorsetConfig():
    """
    corset tool configuration
    """

    # amount of different circuits tested at the same time (should be >= 1)
    bundle_size : int

    # amount of different executions with different flags.
    # min: 1, max: 40, everything less or greater is clamped.
    #
    # NOTE: executing with different flags is another form of metamorphic testing
    executions : int

    # if set, it determines the maximal time given to a corset command
    # before it is forcefully killed. Time is given in seconds. This
    # limit does not apply to the corset check command, for this a separate
    # field is used.
    general_timeout : float | None

    # if set, it determines the maximal memory usage given to a corset command
    # (client and prover implementation) before it is forcefully killed.
    # Unit is in mega byte
    general_memory_limit : int | None

    # if set, it determines the maximal time given to a rust corset check command
    # before it is forcefully killed. Time is given in seconds.
    rust_corset_check_timeout : float | None

    # probability to use a guard variable. The guard variable is currently only
    # used to enables exhaustive testing for the boolean generator, i.e. if this
    # is triggered, exhaustive testing is applied. The guard is needed to deal
    # with the zero padding of corset.
    guard_variable_probability : float

    @classmethod
    def from_dict(cls, value: dict[str, str]) -> 'CorsetConfig':
        bundle_size = int(value.get("bundle_size", 5))
        executions = int(value.get("executions", 2))
        general_timeout = None if value.get("general_timeout", None) == None else float(value["general_timeout"])
        general_memory_limit = None if value.get("general_memory_limit", None) == None else int(value["general_memory_limit"])
        rust_corset_check_timeout = None if not "rust_corset_check_timeout" in value else float(value["rust_corset_check_timeout"])
        guard_variable_probability = float(value.get("guard_variable_probability", 0.5))
        return CorsetConfig \
            ( bundle_size = bundle_size
            , general_timeout = general_timeout
            , general_memory_limit = general_memory_limit
            , rust_corset_check_timeout = rust_corset_check_timeout
            , executions = executions
            , guard_variable_probability = guard_variable_probability
            )