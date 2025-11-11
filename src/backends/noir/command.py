from pathlib import Path
import shutil

from circuzz.common.command import ExecStatus
from circuzz.common.command import execute_command

#
# nargo, noir executer and compiler
#

# --expression-width

def noir_execute(working_dir: Path, witness_name: str, expr_width: int = 4) -> ExecStatus:
    assert shutil.which("nargo"), "Unable to find 'nargo' in PATH!"
    command = \
        [ shutil.which("nargo")
        , "execute"
        , "--silence-warnings"
        , "--force"
        , witness_name
        , "--expression-width", str(expr_width)
        ]
    return execute_command(command, "noir-execute", working_dir)

#
# Get current version
#

def noir_version() -> ExecStatus:
    assert shutil.which("nargo"), "Unable to find 'nargo' in PATH!"
    command = [shutil.which("nargo"), "--version"]
    return execute_command(command, "noir-version")

#
# bb, noir prover and verifier
#

def bb_prove(noir_json: Path, witness_gz: Path, vk_file_path: Path, proof: Path) -> ExecStatus:
    assert shutil.which("bb"), "Unable to find 'bb' in PATH!"
    command = \
        [ shutil.which("bb")
        , "prove"
        , "-b", noir_json.as_posix()
        , "-w", witness_gz.as_posix()
        , "-k", vk_file_path.as_posix()
        , "-o", proof.as_posix()
        ]
    return execute_command(command, "noir-bb-prove")

def bb_write_vk(noir_json: Path, vk: Path) -> ExecStatus:
    assert shutil.which("bb"), "Unable to find 'bb' in PATH!"
    command = \
        [ shutil.which("bb")
        , "write_vk"
        , "-b", noir_json.as_posix()
        , "-o", vk.as_posix()
        ]
    return execute_command(command, "noir-bb-write-vk")

def bb_verify(vk: Path, proof: Path, inputs: Path) -> ExecStatus:
    assert shutil.which("bb"), "Unable to find 'bb' in PATH!"
    command = \
        [ shutil.which("bb")
        , "verify"
        , "-k", vk.as_posix()
        , "-p", proof.as_posix()
        , "-i", inputs.as_posix()
        ]
    return execute_command(command, "noir-bb-verify")