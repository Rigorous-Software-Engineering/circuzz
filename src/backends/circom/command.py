from pathlib import Path
import shutil

from circuzz.common.command import execute_command
from circuzz.common.command import ExecStatus

from .utils import CircomCurve
from .utils import CircomOptimization
from .utils import ProofSystem

def circom_compile \
    ( source: Path
    , output_dir: Path
    , link_libraries: Path | None
    , optimization: CircomOptimization
    , curve: CircomCurve
    ) -> ExecStatus:

    assert shutil.which("circom"), "Unable to find 'circom' compiler in PATH!"
    command = \
        [ shutil.which("circom")
        , "--output", str(output_dir)
        , "--r1cs"
        , "--sym"
        , "--wasm"
        , "--c"
        , "--json"
        , "--prime", curve.value
        , f"--{optimization.value}"
        ]

    if not link_libraries == None and link_libraries.is_dir():
        command.append("-l")
        command.append(str(link_libraries))

    command.append(str(source))

    return execute_command(command, "circom-compile")

def circom_generate_witness_using_js(generate_wtns_js: Path, wasm: Path, input_json: Path, wtns: Path) -> ExecStatus:
    assert shutil.which("node"), "Unable to find 'node' executable in PATH!"
    command = \
        [ shutil.which("node")
        , str(generate_wtns_js)
        , str(wasm)
        , str(input_json)
        , str(wtns)
        ]
    return execute_command(command, "circom-witness-nodejs")

def circom_build_witness_preparation_using_cpp(build_dir: Path) -> ExecStatus:
    assert shutil.which("make"), "Unable to find 'make' executable in PATH!"
    command = \
        [ shutil.which("make")
        , "-C"
        , str(build_dir)
        ]
    # no strict failure as GNU compiler prints some warnings
    return execute_command(command, "circom-witness-preparation-cpp")

def circom_generate_witness_using_cpp(generate_wtns_cpp: Path, input_json: Path, wtns: Path) -> ExecStatus:
    command = \
        [ str(generate_wtns_cpp)
        , str(input_json)
        , str(wtns)
        ]
    return execute_command(command, "circom-witness-cpp")

def snarkjs_check_witness(r1cs: Path, wtns: Path) -> ExecStatus:
    assert shutil.which("snarkjs"), "Unable to find 'snarkjs' executable in PATH!"
    command = \
        [ shutil.which("snarkjs")
        , "wtns", "check"
        , str(r1cs)
        , str(wtns)
        ]
    return execute_command(command, "snarkjs-check-witness")

def snarkjs_generate_zkey(system: ProofSystem, r1cs: Path, ptau: Path, zkey: Path) -> ExecStatus:
    assert shutil.which("snarkjs"), "Unable to find 'snarkjs' executable in PATH!"
    command = \
        [ shutil.which("snarkjs")
        , system.value, "setup"
        , str(r1cs)
        , str(ptau)
        , str(zkey)
        ]
    return execute_command(command, "snarkjs-zkey")

def snarkjs_generate_vkey(zkey: Path, vkey: Path) -> ExecStatus:
    assert shutil.which("snarkjs"), "Unable to find 'snarkjs' executable in PATH!"
    command = \
        [ shutil.which("snarkjs")
        , "zkey", "export", "verificationkey"
        , str(zkey)
        , str(vkey)
        ]
    return execute_command(command, "snarkjs-vkey")

def snarkjs_prove(system: ProofSystem, zkey: Path, wtns: Path, proof: Path, public: Path) -> ExecStatus:
    assert shutil.which("snarkjs"), "Unable to find 'snarkjs' executable in PATH!"
    command = \
        [ shutil.which("snarkjs")
        , system, "prove"
        , str(zkey)
        , str(wtns)
        , str(proof)
        , str(public)
        ]
    return execute_command(command, "snarkjs-prove")

def snarkjs_verify(system: ProofSystem, vkey: Path, public: Path, proof: Path) -> ExecStatus:
    assert shutil.which("snarkjs"), "Unable to find 'snarkjs' executable in PATH!"
    command = \
        [ shutil.which("snarkjs")
        , system, "verify"
        , str(vkey)
        , str(public)
        , str(proof)
        ]
    return execute_command(command, "snarkjs-verify")

def snarkjs_export_witness(wtns: Path, wtns_json: Path) -> ExecStatus:
    assert shutil.which("snarkjs"), "Unable to find 'snarkjs' executable in PATH!"
    command = \
        [ shutil.which("snarkjs")
        , "wtns", "export", "json"
        , str(wtns)
        , str(wtns_json)
        ]
    return execute_command(command, "snarkjs-export-witness")

def snarkjs_export_r1cs(r1cs: Path, r1cs_json: Path) -> ExecStatus:
    assert shutil.which("snarkjs"), "Unable to find 'snarkjs' executable in PATH!"
    command = \
        [ shutil.which("snarkjs")
        , "r1cs", "export", "json"
        , str(r1cs)
        , str(r1cs_json)
        ]
    return execute_command(command, "snarkjs-export-r1cs")
