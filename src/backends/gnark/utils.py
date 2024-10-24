from dataclasses import dataclass
from enum import StrEnum
import io
from random import Random

from circuzz.common.metamorphism import MetamorphicKind
from circuzz.common.field import CurvePrime

from .nodes import CircuitDefinitionCollection
from .emitter import EmitVisitor

from pathlib import Path

# specified inside of docker container
PATH_TO_BASE_PROJECT = Path("/circuzz/gnark/gnarkfuzz")

class GnarkProofSystem(StrEnum):
    GROTH16 = "groth16"
    PLONK = "plonk"

class GnarkCSEngine(StrEnum):
    R1CS = "r1cs"
    SCS = "scs"

class GnarkCurve(StrEnum):
    BN254     = "BN254"
    BLS12_377 = "BLS12_377"
#   BLS12_378 = "BLS12_378"   <-- not supported in builder
    BLS12_381 = "BLS12_381"
    BLS24_315 = "BLS24_315"
    BLS24_317 = "BLS24_317"
    BW6_633   = "BW6_633"
    BW6_761   = "BW6_761"
#   BW6_756   = "BW6_756"
#   STARK     = "STARK_CURVE" <-- not supported in builder
#   SECP256K1 = "SECP256K1"   <-- not supported in builder

def random_engine_system_pair(rng: Random) -> tuple[GnarkCSEngine, GnarkProofSystem]:
    engine = rng.choice(list(GnarkCSEngine))
    match engine:
        case GnarkCSEngine.R1CS:
            return engine, GnarkProofSystem.GROTH16
        case GnarkCSEngine.SCS:
            return engine, GnarkProofSystem.PLONK
        case _:
            raise NotImplementedError(f"unknown engine {engine}")

@dataclass(frozen=True)
class IterationSetting():
    inputs               : dict[str, int]
    engine               : GnarkCSEngine
    skipProverPercentage : float
    system               : GnarkProofSystem

def curve_to_prime(curve: GnarkCurve) -> CurvePrime:
    match curve:
        case GnarkCurve.BN254:
            return CurvePrime.BN254
        case GnarkCurve.BLS12_377:
            return CurvePrime.BLS12_377
        # case GnarkCurve.BLS12_378:
        #     return CurvePrime.BLS12_378
        case GnarkCurve.BLS12_381:
            return CurvePrime.BLS12_381
        case GnarkCurve.BLS24_315:
            return CurvePrime.BLS24_315
        case GnarkCurve.BLS24_317:
            return CurvePrime.BLS24_317
        case GnarkCurve.BW6_633:
            return CurvePrime.BW6_633
        case GnarkCurve.BW6_761:
            return CurvePrime.BW6_761
        # case GnarkCurve.BW6_756:
        #     return CurvePrime.BW6_756
        # case GnarkCurve.STARK:
        #     return CurvePrime.STARK
        # case GnarkCurve.SECP256K1:
        #     return CurvePrime.SECP256K1
        case _:
            raise NotImplementedError(f"unexpected curve {curve}")

def write_test_func_to_buffer \
    ( buffer   : io.StringIO
    , c1       : CircuitDefinitionCollection
    , c2       : CircuitDefinitionCollection
    , rel      : MetamorphicKind
    , curve    : GnarkCurve
    , settings : list[IterationSetting]
    ):

    """
    This function generates a test case for a given circuit-pair
    and input options. The generated test case is written to the provided
    `StringIO` buffer.
    """

    # ------------------------------------------------------
    # circuit definitions and structs
    # ------------------------------------------------------

    # use default emitter for circuits
    emitter = EmitVisitor()
    emitter.emit_to_buffer(buffer, c1)
    buffer.write("\n\n")
    emitter.emit_to_buffer(buffer, c2)
    buffer.write("\n")

    # ------------------------------------------------------
    # func main()
    # ------------------------------------------------------

    c1_name = c1.name
    c2_name = c2.name
    variables = [s.name for s in c1.circuit_struct.fields]

    goRel = { MetamorphicKind.EQUAL: "eq"
            , MetamorphicKind.WEAKER: "wk"
            }.get(rel)
    goCurve = f"ecc.{curve}"

    #
    # write configurations and define circuits
    #

    buffer.write(f"""
func Test_{c1_name} (t *testing.T) {{
    t.Parallel()

    expected := "{goRel}"
    curve := {goCurve}

    var c1 {c1_name}
    var c2 {c2_name}
    var co frontend.Circuit = &c2

    a1 := {c1_name}{{}}
    a2 := {c2_name}{{}}
""")

    #
    # build up settings
    #

    buffer.write(f"""
    type setting struct {{
        engine csEngine
        skipProverPercentage float64
        system proofSystem""")

    for variable in variables:
        buffer.write(f"""
        {variable} *big.Int""")
    buffer.write(f"""
    }}

    var iterSettings [{len(settings)}]setting""")

    for idx, setting in enumerate(settings):
        goCSEngine = f"{setting.engine}Id"
        goSkipProverPercentage = setting.skipProverPercentage
        goSystem = f"{setting.system}Id"

        values = "".join([f", new(big.Int)" for _ in setting.inputs])
        buffer.write(f"""
    iterSettings[{idx}] = setting{{{goCSEngine}, {goSkipProverPercentage}, {goSystem}{values}}}""")

        for key in setting.inputs:
            buffer.write(f"""
    iterSettings[{idx}].FVar_{key}.SetString(\"{setting.inputs[key]}\", 10)""") # "FVar_" is a prefixed added by transformer

    #
    # execute test iterations
    #

    buffer.write(f"""

    for _, s := range iterSettings {{
""")

    #
    # setting variables
    #

    for variable in variables:
        buffer.write(f"""
        a1.{variable} = s.{variable}
        a2.{variable} = s.{variable}""")

    #
    # write compare and error check
    #

    buffer.write(f"""
        var ao frontend.Circuit = &a2
        st := cmpCircuits(curve, &c1, co, &a1, ao, s.skipProverPercentage, s.engine, s.system, "Test_{c1_name}")
        log.Printf("Test_{c1_name}: test status: %v\\n", st)
""")

    buffer.write("""
        if st != unk {
            if expected != "fail" && st == fail {
                t.Errorf("Expected '%v', got '%v'.", expected, "fail")
                return
            }
            if expected != "pan" && st == pan {
                t.Errorf("Expected '%v', got '%v'.", expected, "pan")
                return
            }
            if expected == "eq" && (st == neq || st == wk) {
                stStr := "neq"
                if st == wk {
                    stStr = "wk"
                }
                t.Errorf("Expected '%v', got '%v'.", expected, stStr)
                return
            }
            if expected == "weq" && st == neq {
                t.Errorf("Expected '%v', got '%v'.", expected, "neq")
                return
            }
        }
    }
}

""")