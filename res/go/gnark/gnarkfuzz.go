package gnarkfuzz

import (
    "bytes"
    "fmt"
    "log"
    "math/big"
    "math/rand"
    "reflect"
    "regexp"
    "runtime/debug"
    "strings"
    "time"

    "github.com/consensys/gnark/backend/groth16"
    "github.com/consensys/gnark/backend/plonk"
    "github.com/consensys/gnark/backend/witness"
    "github.com/consensys/gnark/constraint"
    "github.com/consensys/gnark/constraint/solver"
    "github.com/consensys/gnark-crypto/ecc"
    "github.com/consensys/gnark/frontend"
    "github.com/consensys/gnark/frontend/cs/r1cs"
    "github.com/consensys/gnark/frontend/cs/scs"
    "github.com/consensys/gnark/std/math/bits"
    "github.com/consensys/gnark/std/math/cmp"
    "github.com/consensys/gnark/test/unsafekzg"
    "github.com/rs/zerolog"
)

func workaroundFuncInLib(api frontend.API) {
    // this is a workaround to allow following imports
    //  - "math/big"
    //     - "github.com/consensys/gnark/std/math/cmp"
    //  - "github.com/consensys/gnark/std/math/bits"
    // even if they are not used.

    zero := big.NewInt(0)
    cmp.IsLess(api, zero, zero)
    bits.ToBinary(api, zero)
}

type cmpStatus uint8

const (
    neq cmpStatus = iota
    eq
    wk
    unk
    fail
    pan
)

type proofSystem uint8

const (
    groth16Id proofSystem = iota
    plonkId
)

type csEngine uint8

const (
    r1csId csEngine = iota
    scsId
)

func errorToStr(err error) (string) {
    if err == nil {
        return "ok"
    } else {
        return "err"
    }
}

func errEq(e1 error, e2 error) bool {
    if e1 == e2 {
        return true
    }
    var es1 string
    if e1 != nil {
        es1 = e1.Error()
    }
    var es2 string
    if e2 != nil {
        es2 = e2.Error()
    }
    if es1 == es2 {
        return true
    }
    fileNameRegex := regexp.MustCompile("\t\\S*.go:\\d+")
    es1 = fileNameRegex.ReplaceAllString(es1, "")
    es2 = fileNameRegex.ReplaceAllString(es2, "")
    circuitDeclRegex := regexp.MustCompile("[(][*]C[1-2]_\\d+_\\d+[)]")
    es1 = circuitDeclRegex.ReplaceAllString(es1, "")
    es2 = circuitDeclRegex.ReplaceAllString(es2, "")
    constraintRegex := regexp.MustCompile("constraint #\\d+")
    es1 = constraintRegex.ReplaceAllString(es1, "")
    es2 = constraintRegex.ReplaceAllString(es2, "")
    assertionRegex := regexp.MustCompile("[.]AssertIs\\S+")
    es1 = assertionRegex.ReplaceAllString(es1, "")
    es2 = assertionRegex.ReplaceAllString(es2, "")
    return es1 == es2
}

func isIgnored(panicMsg, stackTrace string) bool {
    tooBigRegex := regexp.MustCompile("^m [(]\\d+[)] is too big: the required root of unity does not exist.*")
    if tooBigRegex.MatchString(panicMsg) {
        // We currently ignore this type of error (see https://github.com/Consensys/gnark/issues/864).
        return true
    }
    modulusZeroRegex := regexp.MustCompile("^modulus is zero.*")
    if modulusZeroRegex.MatchString(panicMsg) {
        if strings.Contains(stackTrace, "emulated.subPadding(") {
            // We currently ignore this type of error.
            return true
        }
    }
    divByZeroRegex := regexp.MustCompile("^division by zero.*")
    if divByZeroRegex.MatchString(panicMsg) {
        if strings.Contains(stackTrace, "emulated.subPadding(") {
            // We currently ignore this type of error.
            // TODO: Remove this exception once the issue has been fixed (see https://github.com/Consensys/gnark/pull/1104).
            return true
        }
    }
    indexOutOfRangeRegexSRS := regexp.MustCompile("^runtime error: index out of range.*")
    if indexOutOfRangeRegexSRS.MatchString(panicMsg) {
        if strings.Contains(stackTrace, "unsafekzg.NewSRS(") {
            // We currently ignore this type of error.
            // TODO: Remove this exception once the issue has been fixed.
            return true
        }
    }
    // TODO: This is probably due to missing variables or asserts!
    //       Nevertheless, this should be investigated further.
    indexOutOfRangeRegexLROSmallDomain := regexp.MustCompile("^runtime error: index out of range.*")
    if indexOutOfRangeRegexLROSmallDomain.MatchString(panicMsg) {
        if strings.Contains(stackTrace, ".evaluateLROSmallDomain(") {
            // We currently ignore this type of error.
            return true
        }
    }
    return false
}

func genOutValMap(output string, curve ecc.ID) map[string]*big.Int {
    signalLogOutputRegex := regexp.MustCompile("^(out\\d+): (-?\\d+)$")
    lines := strings.Split(output, "\n")
    outputMap := make(map[string]*big.Int)
    fr := curve.ScalarField()
    for _, line := range lines {
        match := signalLogOutputRegex.FindStringSubmatch(line)
        if 2 == len(match) {
            name := match[0]
            value := match[1]
            outputMap[name] = new(big.Int)
            num, succ := outputMap[name].SetString(value, 10)
            // check for parsing errors
            if !succ {
                panic("unexpected error during output parsing!")
            }
            // check if parsed (absolute) value fits the current field
            //    -) |num| < fr, must hold
            if new(big.Int).Abs(num).Cmp(fr) >= 0 {
                panic("output value is outside of field!")
            }
            // correct values to only contain positive numbers
            if num.Sign() > 0 {
                outputMap[name].Add(fr, num)
            }
        }
    }
    return outputMap
}

func outEq(out1 string, out2 string, curve ecc.ID) bool {
    out1Map := genOutValMap(out1, curve)
    out2Map := genOutValMap(out2, curve)
    mapEq := reflect.DeepEqual(out1Map, out2Map)
    if !mapEq {
        // TODO: print mis-match
        return false
    }
    return true
}

func compileCircuit(curve ecc.ID, engine csEngine, circuit frontend.Circuit, logHandle string, circuitId string) (constraint.ConstraintSystem, error) {
    var cs constraint.ConstraintSystem
    var err error
    start := time.Now()
    switch engine {
        case r1csId:
            cs, err = frontend.Compile(curve.ScalarField(), r1cs.NewBuilder, circuit, frontend.IgnoreUnconstrainedInputs())
        case scsId:
            cs, err = frontend.Compile(curve.ScalarField(), scs.NewBuilder, circuit, frontend.IgnoreUnconstrainedInputs())
        default:
            panic("unsupported constraint system engine!")
    }
    end := time.Now()
    elapse := end.Sub(start).Seconds()

    log.Printf("%s: Compile %s => %s\n", logHandle, circuitId, errorToStr(err))
    log.Printf("%s: Compile time %s => %f\n", logHandle, circuitId, elapse)

    return cs, err
}

func generateWitness(curve ecc.ID, assign frontend.Circuit, logHandle string, circuitId string) (witness.Witness, error) {
    start := time.Now()
    wtns, err := frontend.NewWitness(assign, curve.ScalarField())
    end := time.Now()
    elapse := end.Sub(start).Seconds()

    log.Printf("%s: NewWitness %s => %s\n", logHandle, circuitId, errorToStr(err))
    log.Printf("%s: NewWitness time %s => %f\n", logHandle, circuitId, elapse)

    return wtns, err
}

func solveWitness(wtns witness.Witness, cs constraint.ConstraintSystem, logHandle string, circuitId string) (string, error) {
    start := time.Now()
    var buffer bytes.Buffer
    outLog := zerolog.New(&zerolog.ConsoleWriter{Out: &buffer, NoColor: true, PartsExclude: []string{zerolog.LevelFieldName, zerolog.TimestampFieldName, zerolog.CallerFieldName}})
    var options []solver.Option
    options = append(options, solver.WithLogger(outLog))
    err := cs.IsSolved(wtns, options...)
    end := time.Now()
    elapse := end.Sub(start).Seconds()

    log.Printf("%s: IsSolved %s => %s\n", logHandle, circuitId, errorToStr(err))
    log.Printf("%s: IsSolved time %s => %f\n", logHandle, circuitId, elapse)

    return buffer.String(), err
}

func checkWitness(curve ecc.ID, assign frontend.Circuit, cs constraint.ConstraintSystem, logHandle string, circuitId string) error {
    wtns, wtnsErr := generateWitness(curve, assign, logHandle, circuitId)
    if wtnsErr != nil {
        return wtnsErr
    }
    _, solveErr := solveWitness(wtns, cs, logHandle, circuitId)
    if solveErr != nil {
        return solveErr
    }
    return nil // success
}

func witnessToByte(witness witness.Witness, logHandle string, circuitId string) (int64, *bytes.Buffer, error) {
    start := time.Now()
    witnessWriter := new(bytes.Buffer)
    binary, err := witness.WriteTo(witnessWriter)
    end := time.Now()
    elapse := end.Sub(start).Seconds()

    log.Printf("%s: WitnessWriteTo %s => %s\n", logHandle, circuitId, errorToStr(err))
    log.Printf("%s: WitnessWriteTo time %s => %f\n", logHandle, circuitId, elapse)

    return binary, witnessWriter, err
}

func proofSetup(cs constraint.ConstraintSystem, system proofSystem, logHandle string, circuitId string) (groth16.ProvingKey, groth16.VerifyingKey, plonk.ProvingKey, plonk.VerifyingKey, error) {
    // TODO: Maybe perform differential testing using different engines.
    var gpk groth16.ProvingKey
    var gvk groth16.VerifyingKey
    var ppk plonk.ProvingKey
    var pvk plonk.VerifyingKey
    var setupErr error

    start := time.Now()
    switch system {
        case groth16Id:
            gpk, gvk, setupErr = groth16.Setup(cs)
        case plonkId:
            srs, lsrs, srsErr := unsafekzg.NewSRS(cs)
            log.Printf("%s: NewSRS %s => %s\n", logHandle, circuitId, errorToStr(srsErr))
            if srsErr != nil {
                return nil, nil, nil, nil, srsErr
            }
            ppk, pvk, setupErr = plonk.Setup(cs, srs, lsrs)
        default:
            panic("unknown proof system!")
    }
    end := time.Now()
    elapse := end.Sub(start).Seconds()

    log.Printf("%s: ProofSetup %s => %s\n", logHandle, circuitId, errorToStr(setupErr))
    log.Printf("%s: ProofSetup time %s => %f\n", logHandle, circuitId, elapse)

    return gpk, gvk, ppk, pvk, setupErr
}

func proveCircuit(gpk groth16.ProvingKey, ppk plonk.ProvingKey, witness witness.Witness, cs constraint.ConstraintSystem, system proofSystem, logHandle string, circuitId string) (groth16.Proof, plonk.Proof, error) {
    var gproof groth16.Proof
    var pproof plonk.Proof
    var err error

    start := time.Now()
    switch system {
        case groth16Id:
            gproof, err = groth16.Prove(cs, gpk, witness)
        case plonkId:
            pproof, err = plonk.Prove(cs, ppk, witness)
        default:
            panic("unknown proof system!")
    }
    end := time.Now()
    elapse := end.Sub(start).Seconds()

    log.Printf("%s: Prove %s => %s\n", logHandle, circuitId, errorToStr(err))
    log.Printf("%s: Prove time %s => %f\n", logHandle, circuitId, elapse)

    return gproof, pproof, err
}

func publicWitness(witness witness.Witness, logHandle string, circuitId string) (witness.Witness, error) {
    start := time.Now()
    pub, err := witness.Public()
    end := time.Now()
    elapse := end.Sub(start).Seconds()

    log.Printf("%s: Public %s => %s\n", logHandle, circuitId, errorToStr(err))
    log.Printf("%s: Public time %s => %f\n", logHandle, circuitId, elapse)

    return pub, err
}

func verifyCircuit(gproof groth16.Proof, gvk groth16.VerifyingKey, pproof plonk.Proof, pvk plonk.VerifyingKey, pubWitness witness.Witness, system proofSystem, logHandle string, circuitId string) (error) {
    var err error
    start := time.Now()
    switch system {
        case groth16Id:
            err = groth16.Verify(gproof, gvk, pubWitness)
        case plonkId:
            err = plonk.Verify(pproof, pvk, pubWitness)
        default:
            panic("unknown constraint system!")
    }
    end := time.Now()
    elapse := end.Sub(start).Seconds()

    log.Printf("%s: Verify %s => %s\n", logHandle, circuitId, errorToStr(err))
    log.Printf("%s: Verify time %s => %f\n", logHandle, circuitId, elapse)

    return err
}

func cmpCircuits(curve ecc.ID, c1, c2 frontend.Circuit, a1, a2 frontend.Circuit, skipProverPercentage float64, engine csEngine, system proofSystem, logHandle string) (ret cmpStatus) {
    defer func() {
        if r := recover(); r != nil {
            panicMsg := fmt.Sprintf("%v", r)
            log.Printf("%s: panic: %v\n", logHandle, r)
            stackTrace := string(debug.Stack())
            if isIgnored(panicMsg, stackTrace) {
                ret = unk
                return
            }
            ret = pan
        }
    }()

    log.Printf("%s: start\n", logHandle)

    //
    // Compilation
    //

    cs1, compErr1 := compileCircuit(curve, engine, c1, logHandle, "c1")
    cs2, compErr2 := compileCircuit(curve, engine, c2, logHandle, "c2")

    //
    // Check for violation
    //

    if (compErr1 == nil && compErr2 != nil) {
        checkErr := checkWitness(curve, a1, cs1, logHandle, "c1") // check witness for c1
        if checkErr != nil {
            return unk // maybe not equal ...
        }
        return neq // not equal
    } else if (compErr1 != nil && compErr2 == nil) {
        checkErr := checkWitness(curve, a2, cs2, logHandle, "c2") // check witness for c2
        if checkErr != nil {
            return unk // maybe not equal ...
        }
        return wk // weaker
    } else if (compErr1 != nil && compErr2 != nil) {
        divByConstPrefix := "parse circuit: div by constant(0)"
        if (compErr1 != nil && strings.HasPrefix(compErr1.Error(), divByConstPrefix)) || (compErr2 != nil && strings.HasPrefix(compErr2.Error(), divByConstPrefix)) {
            // We ignore all division related errors as they might get triggered before an assertion
            return unk
        }
        divByZeroPrefix := "parse circuit: div by 0"
        if (compErr1 != nil && strings.HasPrefix(compErr1.Error(), divByZeroPrefix)) || (compErr2 != nil && strings.HasPrefix(compErr2.Error(), divByZeroPrefix)) {
            // We ignore all division related errors as they might get triggered before an assertion
            return unk
        }
        invByConstPrefix := "parse circuit: inverse by constant(0)"
        if (compErr1 != nil && strings.HasPrefix(compErr1.Error(), invByConstPrefix)) || (compErr2 != nil && strings.HasPrefix(compErr2.Error(), invByConstPrefix)) {
            // We ignore all division related errors as they might get triggered before an assertion
            return unk
        }
        // We only check if both compilation errors fail with an assertion
        // TODO: check which assertion was triggered
        anyAssertionRegex := regexp.MustCompile("(r1cs|scs)\\.\\(\\*builder\\)\\.AssertIs.*")
        if (anyAssertionRegex.MatchString(compErr1.Error()) && anyAssertionRegex.MatchString(compErr2.Error())) {
            return eq
        }
        return neq
    }
    // else (compErr1 == nil && compErr2 == nil), both compilations successful 

    //
    // Witness Generation
    //

    witness1, witnessErr1 := generateWitness(curve, a1, logHandle, "c1")
    witness2, witnessErr2 := generateWitness(curve, a2, logHandle, "c2")

    if !errEq(witnessErr1, witnessErr2) {
        return neq
    }

    if witnessErr1 != nil {
        return eq
    }

    wn1, witnessWriter1, writeWitErr1 := witnessToByte(witness1, logHandle, "c1")
    wn2, witnessWriter2, writeWitErr2 := witnessToByte(witness2, logHandle, "c2")

    if !errEq(writeWitErr1, writeWitErr2) {
        return neq
    }

    if writeWitErr1 != nil {
        return eq
    }

    if wn1 != wn2 || !bytes.Equal(witnessWriter1.Bytes(), witnessWriter2.Bytes()) {
        return neq
    }

    outLog1, solveErr1 := solveWitness(witness1, cs1, logHandle, "c1")
    outLog2, solveErr2 := solveWitness(witness2, cs2, logHandle, "c2")

    if !outEq(outLog1, outLog2, curve) {
        log.Printf("%s: error: witness mis-matching outputs\n", logHandle)
        return neq
    }

    if !errEq(solveErr1, solveErr2) {
        constraintUnsatRegex := regexp.MustCompile("^constraint #\\d+ is not satisfied.*")
        if (solveErr1 != nil && constraintUnsatRegex.MatchString(solveErr1.Error())) && (solveErr2 != nil && constraintUnsatRegex.MatchString(solveErr2.Error())) {
            // We currently ignore this type of difference.
            return unk
        }
        if solveErr1 != nil && solveErr2 == nil {
            return wk
        }
        if solveErr1 != nil && solveErr2 != nil {
            // We currently ignore this type of difference.
            // There are two known reasons for such differences:
            //   (1) nondeterminism due to parallelism (see https://github.com/Consensys/gnark/issues/1048), and
            //   (2) subtle changes to the dependency tree.
            // It is possible to eliminate nondeterminism (see https://github.com/Consensys/gnark/pull/1052), but the
            // changes in the dependency tree are intended.
            return unk
        }
        return neq
    }

    log.Printf("%s: prove & verify opportunity\n", logHandle)

    if rand.Float64() >= skipProverPercentage {
        // We skip the prover components to focus on the witness-generation and solver components.
        log.Printf("%s: prove & verify => skip\n", logHandle)
        return eq
    }

    log.Printf("%s: prove & verify => start\n", logHandle)

    //
    // Proving
    //

    // TODO: Maybe perform differential testing using different engines.
    gpk1, gvk1, ppk1, pvk1, setupErr1 := proofSetup(cs1, system, logHandle, "c1")
    gpk2, gvk2, ppk2, pvk2, setupErr2 := proofSetup(cs2, system, logHandle, "c2")

    if !errEq(setupErr1, setupErr2) {
        return neq
    }

    if setupErr1 != nil {
        return eq
    }

    gproof1, pproof1, proveErr1 := proveCircuit(gpk1, ppk1, witness1, cs1, system, logHandle, "c1")
    gproof2, pproof2, proveErr2 := proveCircuit(gpk2, ppk2, witness2, cs2, system, logHandle, "c2")

    if !errEq(proveErr1, proveErr2) {
        constraintUnsatRegex := regexp.MustCompile("^constraint #\\d+ is not satisfied.*")
        if (proveErr1 != nil && constraintUnsatRegex.MatchString(proveErr1.Error())) && (proveErr2 != nil && constraintUnsatRegex.MatchString(proveErr2.Error())) {
            // We currently ignore this type of difference.
            return unk
        }
        if proveErr1 != nil && proveErr2 == nil {
            return wk
        }
        if proveErr1 != nil && proveErr2 != nil {
            // We currently ignore this type of difference.
            // There are two known reasons for such differences:
            //   (1) nondeterminism due to parallelism (see https://github.com/Consensys/gnark/issues/1048), and
            //   (2) subtle changes to the dependency tree.
            // It is possible to eliminate nondeterminism (see https://github.com/Consensys/gnark/pull/1052), but the
            // changes in the dependency tree are intended.
            return unk
        }
        return neq
    }

    if proveErr1 != nil {
        return eq
    }

    pubWitness1, pubWitnessErr1 := publicWitness(witness1, logHandle, "c1")
    pubWitness2, pubWitnessErr2 := publicWitness(witness2, logHandle, "c2")

    if !errEq(pubWitnessErr1, pubWitnessErr2) {
        return neq
    }

    if pubWitnessErr1 != nil {
        return eq
    }

    //
    // Verifying
    //

    verifyErr1 := verifyCircuit(gproof1, gvk1, pproof1, pvk1, pubWitness1, system, logHandle, "c1")
    verifyErr2 := verifyCircuit(gproof2, gvk2, pproof2, pvk2, pubWitness2, system, logHandle, "c2")

    if verifyErr1 != nil || verifyErr2 != nil {
        // A valid proof should never fail to verify.
        return fail
    }

    return eq
}