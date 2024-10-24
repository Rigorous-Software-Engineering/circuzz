from enum import IntEnum
from random import Random

from .probability import bernoulli

class CurvePrime(IntEnum):
    GOLDILOCKS = 18446744069414584321
    GRUMPKIN   = 21888242871839275222246405745257275088696311157297823662689037894645226208583
    PALLAS     = 28948022309329048855892746252171976963363056481941560715954676764349967630337
    VESTA      = 28948022309329048855892746252171976963363056481941647379679742748393362948097
    SECQ256R1  = 115792089210356248762697446949407573530086143415290314195533631308867097853951
    BN128      = 21888242871839275222246405745257275088548364400416034343698204186575808495617
    BN254      = 21888242871839275222246405745257275088548364400416034343698204186575808495617
    STARK      = 3618502788666131213697322783095070105526743751716087489154079457884512865583
    SECP256K1  = 115792089237316195423570985008687907852837564279074904382605163141518161494337
    BLS24_317  = 30869589236456844204538189757527902584594726589286811523515204428962673459201
    BLS24_315  = 11502027791375260645628074404575422495959608200132055716665986169834464870401
    BLS12_381  = 52435875175126190479447740508185965837690552500527637822603658699938581184513
    BLS12_378  = 14883435066912132899950318861128167269793560281114003360875131245101026639873
    BLS12_377  = 8444461749428370424248824938781546531375899335154063827935233455917409239041
    BW6_761    = 258664426012969094010652733694893533536393512754914660539884262666720468348340822774968888139573360124440321458177
    BW6_756    = 605248206075306171733248481581800960739847691770924913753520744034740935903401304776283802348837311170974282940417
    BW6_633    = 39705142709513438335025689890408969744933502416914749335064285505637884093126342347073617133569

def get_curve_name(curve: CurvePrime) -> str:
    match curve:
        case CurvePrime.GOLDILOCKS:
            return "goldilocks"
        case CurvePrime.GRUMPKIN:
            return "grumpkin"
        case CurvePrime.PALLAS:
            return "pallas"
        case CurvePrime.VESTA:
            return "vesta"
        case CurvePrime.SECQ256R1:
            return "secq256r1"
        case CurvePrime.BN128:
            return "bn128"
        case CurvePrime.BN254:
            return "bn254"
        case CurvePrime.STARK:
            return "stark"
        case CurvePrime.SECP256K1:
            return "secp256k1"
        case CurvePrime.BLS24_317:
            return "bls24_317"
        case CurvePrime.BLS24_315:
            return "bls24_315"
        case CurvePrime.BLS12_381:
            return "bls12_381"
        case CurvePrime.BLS12_378:
            return "bls12_378"
        case CurvePrime.BLS12_377:
            return "bls12_377"
        case CurvePrime.BW6_761:
            return "bw6_761"
        case CurvePrime.BW6_756:
            return "bw6_756"
        case CurvePrime.BW6_633:
            return "bw6_633"
        case _:
            raise NotImplementedError(f"unexpected curve prime {curve}")

# This value is used as upper bound if smaller integers are preferred.
#
# NOTE: if this value is adapted, the function descriptions have to be
#       adapted too.
#
# TODO: think about moving this to the configuration file
DEFAULT_SMALL_INTEGER_UPPER_BOUND = 10

def random_non_zero_field_element \
    ( curve_prime: CurvePrime
    , rng: Random
    , boundary_prob: float = 0
    , small_upper_bound_prob: float = 0
    , small_upper_bound=DEFAULT_SMALL_INTEGER_UPPER_BOUND
    ) -> int:

    """
    Returns a random non zero integer from the provided field curve.
    The `boundary_prob` value indicates the probability of choosing
    a boundary value, i.e. `PRIME-1` or `1`. The `small_upper_bound_prob` value
    indicates the probability of choosing a small integer, i.e. from
    the domain `[1, 10]`.
    """

    prime = curve_prime.value

    # check if we use boundary values
    if bernoulli(boundary_prob, rng):
        return rng.choice([1, prime-1])
    else:
        # check if we prefer a small integer upper bound
        if bernoulli(small_upper_bound_prob, rng):
            return rng.randint(1, small_upper_bound)
        else:
            return rng.randint(1, prime-1)


def random_field_element \
    ( curve_prime: CurvePrime
    , rng: Random
    , exclude_prime=False
    , boundary_prob: float = 0
    , small_upper_bound_prob: float = 0
    , small_upper_bound=DEFAULT_SMALL_INTEGER_UPPER_BOUND
    ) -> int:

    """
    Returns a random integer from the provided field curve.
    The `boundary_prob` value indicates the probability of choosing
    a boundary value, i.e. `[0, 1, PRIME-1, PRIME]` or `[0, 1, PRIME-1]` if
    `exclude_prime` is `True`. The `small_upper_bound_prob` value indicates the
    probability of choosing a small integer, i.e. from the domain `[0 - 10]`.
    """

    prime = curve_prime.value

    # check if we use boundary values
    if bernoulli(boundary_prob, rng):
        # check if the prime value is excluded
        if exclude_prime:
            return rng.choice([0, 1, prime-1])
        else:
            return rng.choice([0, 1, prime-1, prime])
    else:
        # check if we prefer a small integer upper bound
        if bernoulli(small_upper_bound_prob, rng):
            return rng.randint(0, small_upper_bound)
        else:
            # check if the prime value is excluded
            if exclude_prime:
                return rng.randint(0, prime-1)
            else:
                return rng.randint(0, prime)
    # unreachable