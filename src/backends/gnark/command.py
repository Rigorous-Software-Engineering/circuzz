from circuzz.common.command import execute_command
from circuzz.common.command import ExecStatus

from pathlib import Path
import shutil

def go_test(working_dir: Path, go_test_timeout: str | None) -> ExecStatus:
    assert shutil.which("go"), "Unable to find 'go' in PATH!"
    command = [shutil.which("go"), "test"]
    if go_test_timeout != None:
        command += ["-timeout", go_test_timeout]
    return execute_command(command, "go-test", working_dir=working_dir)