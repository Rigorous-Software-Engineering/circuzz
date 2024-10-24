/**
 * Simple client to test go-corset's compilation and wizard's proof / verify stages.
 * It is important to use following versions:
 *
 *  - go get github.com/consensys/go-corset@2d0aad43bfbd
 *  - go get github.com/consensys/linea-monorepo/prover@ca278a0ae7d8
 *
 * WARNING: If a newer version has (breaking) changes this file might become outdated or
 *          even obsolete!
 */

package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"time"

	_ "unsafe"

	"github.com/consensys/go-corset/pkg/air"
	"github.com/consensys/go-corset/pkg/binfile"
	"github.com/consensys/go-corset/pkg/schema"
	"github.com/consensys/go-corset/pkg/schema/assignment"
	"github.com/consensys/go-corset/pkg/trace"
	"github.com/consensys/go-corset/pkg/trace/json"

	"github.com/consensys/linea-monorepo/prover/backend/files"

	"github.com/consensys/linea-monorepo/prover/maths/common/smartvectors"
	"github.com/consensys/linea-monorepo/prover/maths/field"

	"github.com/consensys/linea-monorepo/prover/protocol/compiler/dummy"
	"github.com/consensys/linea-monorepo/prover/protocol/ifaces"
	"github.com/consensys/linea-monorepo/prover/protocol/wizard"

	_ "github.com/consensys/linea-monorepo/prover/zkevm/arithmetization"
)

// ===============================================================================
// CLI Argument Parsing
// ===============================================================================

var (
	globalBinFPathCLI string
	globalTraceFPathCLI  string
)

func init() {
	flag.StringVar(&globalBinFPathCLI, "bin", "", "path to the `.bin` file containing the constraints.")
	flag.StringVar(&globalTraceFPathCLI, "trace", "", "path to the `.json` trace file")
	flag.Parse()
}

func getParamsFromCLI() (binFPath string, traceFPath string, err error) {
	flag.Parse()
	if len(globalBinFPathCLI) == 0 {
		return "", "", fmt.Errorf("could not find the bin-file path, got '%++v'", globalBinFPathCLI)
	}
	if len(globalTraceFPathCLI) == 0 {
		return "", "", fmt.Errorf("could not find the trace file path, got '%++v'", globalTraceFPathCLI)
	}
	return globalBinFPathCLI, globalTraceFPathCLI, nil
}

// ===============================================================================
// Patched Arithmezation
// ===============================================================================

// copied from github.com/consensys/linea-monorepo/prover/zkevm/arithmetization
type arith_schemaScanner struct {
	LimitMap           map[string]int
	Comp               *wizard.CompiledIOP
	Schema             *air.Schema
	Modules            []schema.Module
	InterleavedColumns map[string]*assignment.Interleaving
}

// copied from github.com/consensys/linea-monorepo/prover/zkevm/arithmetization
type arith_corsetNamed interface {
	Context() trace.Context
}

//go:linkname arith_scanColumns github.com/consensys/linea-monorepo/prover/zkevm/arithmetization.(*schemaScanner).scanColumns
func arith_scanColumns(*arith_schemaScanner)

//go:linkname arith_scanConstraints github.com/consensys/linea-monorepo/prover/zkevm/arithmetization.(*schemaScanner).scanConstraints
func arith_scanConstraints(*arith_schemaScanner)

//go:linkname arith_wizardName github.com/consensys/linea-monorepo/prover/zkevm/arithmetization.wizardName
func arith_wizardName(string, string) string

//go:linkname arith_getModuleName github.com/consensys/linea-monorepo/prover/zkevm/arithmetization.getModuleName
func arith_getModuleName(*air.Schema, arith_corsetNamed) string

func MakeDefine(airSch *air.Schema) wizard.DefineFunc {
	return func(builder *wizard.Builder) {

		moduleLimits := make(map[string]int)
		for _, schemaModule := range airSch.Modules().Collect() {
			moduleLimits[schemaModule.Name()] = 1024
		}

		scanner := &arith_schemaScanner{
			LimitMap:           moduleLimits,
			Comp:               builder.CompiledIOP,
			Schema:             airSch,
			Modules:            airSch.Modules().Collect(),
			InterleavedColumns: map[string]*assignment.Interleaving{},
		}

		arith_scanColumns(scanner)
		arith_scanConstraints(scanner)
	}
}

func MakeProver(traceFile string, airSch *air.Schema) wizard.ProverStep {
	return func(run *wizard.ProverRuntime) {

		traceF := files.MustRead(traceFile)
		trace, errTrace := ReadJsonTraces(traceF, airSch)
		if errTrace != nil {
			fmt.Printf("error loading the trace fpath=%q err=%v", traceFile, errTrace.Error())
		}

		var (
			modules      = trace.Modules().Collect()
			err77        error
			numCols      = trace.Width()
		)

		for _, module := range modules {

			var (
				name   = module.Name()
				limit  = 1024
				height = module.Height()
				ratio  = float64(height) / float64(limit)
			)

			if uint(limit) < height {
				err77 = errors.Join(err77, fmt.Errorf("limit overflow: module %q overflows its limit height=%v limit=%v ratio=%v", name, height, limit, ratio))
			}
		}

		if err77 != nil {
			fmt.Printf("Error code 77: \n%v", err77)
			os.Exit(77) // TraceOverflowExitCode
		}

		for id := uint(0); id < numCols; id++ {

			var (
				col     = trace.Column(id)
				name    = ifaces.ColID(arith_wizardName(arith_getModuleName(airSch, col), col.Name()))
				wCol    = run.Spec.Columns.GetHandle(name)
				padding = col.Padding()
				data    = col.Data()
				plain   = make([]field.Element, data.Len())
			)

			if !run.Spec.Columns.Exists(name) {
				continue
			}

			for i := range plain {
				plain[i] = data.Get(uint(i))
			}

			run.AssignColumn(ifaces.ColID(name), smartvectors.LeftPadded(plain, padding, wCol.Size()))
		}
	}
}

// ===============================================================================
// Go Corset Trace Reader
// ===============================================================================

func ReadJsonTraces(f io.ReadCloser, sch *air.Schema) (trace.Trace, error) {

	defer f.Close()

	readBytes, err := io.ReadAll(f)
	if err != nil {
		return nil, fmt.Errorf("failed reading the file: %w", err)
	}

	rawTraces, err := json.FromBytes(readBytes)
	if err != nil {
		return nil, fmt.Errorf("failed parsing the bytes of the raw trace '.json' file: %w", err)
	}

	expTraces, errs := schema.NewTraceBuilder(sch).Build(rawTraces)
	if len(errs) > 0 {
		fmt.Printf("corset expansion gave the following errors: %v", errors.Join(errs...).Error())
	}

	return expTraces, nil
}

// ===============================================================================
// Go Corset Compilation
// ===============================================================================

func CompileCorsetBinFile(path string) (*air.Schema, error) {
	buf, readErr := os.ReadFile(path)
	if readErr != nil {
		return nil, readErr
	}

	hirSchema, parseErr := binfile.HirSchemaFromJson(buf)
	if parseErr != nil {
		return nil, parseErr
	}

	return hirSchema.LowerToMir().LowerToAir(), nil
}

// ===============================================================================
// Helper
// ===============================================================================

func errorToStatusStr(err error) (string) {
    if err == nil {
        return "ok"
    } else {
        return "err"
    }
}

func wizardCompileWrapper(airSch *air.Schema) (comp *wizard.CompiledIOP, err error) {
	defer func() {
		rec := recover()
        if rec != nil {
            err = fmt.Errorf("Error in wizard compilation: %v", rec)
        }
		if err == nil && comp == nil {
			err = errors.New("Error in wizard compilation: compilation artifact is 'nil'")
		}
    }()
    comp = wizard.Compile(MakeDefine(airSch), dummy.Compile)
	return comp, nil
}

func wizardProveWrapper(traceFile string, airSch *air.Schema, comp *wizard.CompiledIOP) (proof wizard.Proof, err error) {
	defer func() {
		rec := recover()
        if rec != nil {
            err = fmt.Errorf("Error in wizard proof generation: %v", rec)
        }
    }()
	proof = wizard.Prove(comp, MakeProver(traceFile, airSch))
	return proof, nil
}

// ===============================================================================
// Entry Point
// ===============================================================================

func main() {

	//
	// argument parsing
	//

	binFile, traceFile, parseErr := getParamsFromCLI()
	if parseErr != nil {
		fmt.Printf("FATAL\n")
		fmt.Printf("err = %v\n", parseErr)
		os.Exit(1)
	}

	//
	// go-corset compilation of .bin file
	//

	start := time.Now()
	airSch, airErr := CompileCorsetBinFile(binFile)
	end := time.Now()
    elapse := end.Sub(start).Seconds()

	fmt.Printf("<@> go-corset compile time => %f\n", elapse)
	fmt.Printf("<@> go-corset compile => %v\n", errorToStatusStr(airErr))

	if airErr != nil {
		fmt.Printf("err = %v\n", airErr)
		os.Exit(1)
	}

	//
	// wizard protocol compilation (witness generation?)
	//

	start = time.Now()
	comp, compErr := wizardCompileWrapper(airSch)
	end = time.Now()
    elapse = end.Sub(start).Seconds()

	fmt.Printf("<@> wizard compile time => %f\n", elapse)
	if compErr != nil {
		fmt.Printf("<@> wizard compile => err\n")
		fmt.Printf("err = %v\n", compErr)
		os.Exit(1)
	} else {
		fmt.Printf("<@> wizard compile => ok\n")
	}

	//
	// wizard protocol proof generation
	//

	start = time.Now()
	proof, proofErr := wizardProveWrapper(traceFile, airSch, comp)
	end = time.Now()
    elapse = end.Sub(start).Seconds()

	fmt.Printf("<@> wizard prove time => %f\n", elapse)
	if proofErr != nil {
		fmt.Printf("<@> wizard prove => err\n")
		fmt.Printf("err = %v\n", proofErr)
		os.Exit(1)
	} else {
		fmt.Printf("<@> wizard prove => ok\n")
	}

	//
	// wizard protocol verification
	//

	start = time.Now()
	vErr := wizard.Verify(comp, proof)
	end = time.Now()
    elapse = end.Sub(start).Seconds()

	fmt.Printf("<@> wizard verify time => %f\n", elapse)
	fmt.Printf("<@> wizard verify => %v\n", errorToStatusStr(vErr))

	// check the result of the verification

	if vErr == nil {
		fmt.Printf("PASSED\n")
	}

	if vErr != nil {
		fmt.Printf("FAILED\n")
		fmt.Printf("err = %v\n", vErr.Error())
		os.Exit(1)
	}
}