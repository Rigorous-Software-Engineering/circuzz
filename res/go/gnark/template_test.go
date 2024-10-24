package gnarkfuzz

import (
    "log"
    "math/big"
    "testing"

    "github.com/consensys/gnark-crypto/ecc"
    "github.com/consensys/gnark/frontend"
    "github.com/consensys/gnark/std/math/bits"
    "github.com/consensys/gnark/std/math/cmp"
)

func workaroundFuncInTest(api frontend.API) {
    // this is a workaround to allow following imports
    //  - "math/big"
    //  - "github.com/consensys/gnark/std/math/cmp"
    //  - "github.com/consensys/gnark/std/math/bits"
    // even if they are not used.

    zero := big.NewInt(0)
    cmp.IsLess(api, zero, zero)
    bits.ToBinary(api, zero)
}

// ================================== TESTs ==================================

