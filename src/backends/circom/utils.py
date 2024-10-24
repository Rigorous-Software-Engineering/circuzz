from enum import StrEnum
from random import Random
from pathlib import Path

from circuzz.common.field import CurvePrime

# provided inside of the docker container
PTAU_FILEPATH_2POW17 = Path("/circuzz/ptaus/powersOfTau28_hez_final_17.ptau")
CIRCOMLIB_DIR = Path("/circuzz/circomlib/circuits")

class ProofSystem(StrEnum):
    GROTH16 = "groth16"
    FFLONK = "fflonk"
    PLONK = "plonk"

class CircomOptimization(StrEnum):
    O0 = "O0"
    O1 = "O1"
    O2 = "O2"

class CircomCurve(StrEnum):
    BN128      = "bn128"
    BLS12_381  = "bls12381"
    GOLDILOCKS = "goldilocks"
    GRUMPKIN   = "grumpkin"
    PALLAS     = "pallas"
    VESTA      = "vesta"
    SECQ256R1  = "secq256r1"

def curve_to_prime(curve: CircomCurve) -> CurvePrime:
    match curve:
        case CircomCurve.BN128:
            return CurvePrime.BN128
        case CircomCurve.BLS12_381:
            return CurvePrime.BLS12_381
        case CircomCurve.GOLDILOCKS:
            return CurvePrime.GOLDILOCKS
        case CircomCurve.GRUMPKIN:
            return CurvePrime.GRUMPKIN
        case CircomCurve.PALLAS:
            return CurvePrime.PALLAS
        case CircomCurve.VESTA:
            return CurvePrime.VESTA
        case CircomCurve.SECQ256R1:
            return CurvePrime.SECQ256R1
        case _:
            raise NotImplementedError(f"unknown curve {curve}")

def random_circom_curve(rng: Random) -> CircomCurve:
    return rng.choice(list(CircomCurve))

def random_circom_optimization(rng: Random) -> CircomOptimization:
    return rng.choice(list(CircomOptimization))