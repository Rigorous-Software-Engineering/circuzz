
from circuzz.common.command import execute_command
from circuzz.common.command import ExecStatus

from pathlib import Path
import shutil

def corset_check \
    ( source: Path
    , trace: Path
    , expansion: int
    , native: bool
    , auto_constraints: list[str]
    , working_dir: Path | None = None
    , timeout: float | None = None
    , memory: int | None = None
    ) -> ExecStatus:

    assert shutil.which("corset"), "Unable to find 'corset' tool in PATH!"
    command = \
        [ shutil.which("corset")
        , "check", str(source)
        , "--trace", str(trace)
        ]

    if expansion > 0 or native:
        args = "-"
        if expansion > 0:
            args += "e" * expansion
        if native:
           args += "N"
        command.append(args)

    if len(auto_constraints) > 0:
        command.append("--auto-constraints")
        command.append(",".join(auto_constraints))

    return execute_command(command, "corset-check", \
        working_dir=working_dir, timeout=timeout, memory=memory)

def corset_compile \
    ( source: Path
    , output: Path
    , expansion: int
    , native: bool
    , auto_constraints: list[str]
    , working_dir: Path | None = None
    , timeout: float | None = None
    , memory: int | None = None
    ) -> ExecStatus:

    assert shutil.which("corset"), "Unable to find 'corset' tool in PATH!"
    command = \
        [ shutil.which("corset")
        , "compile"
        , "--out", str(output)
        ]

    if expansion > 0 or native:
        args = "-"
        if expansion > 0:
            args += "e" * expansion
        if native:
           args += "N"
        command.append(args)

    if len(auto_constraints) > 0:
        command.append("--auto-constraints")
        command.append(",".join(auto_constraints))

    command.append(str(source))

    return execute_command(command, "corset-compile", \
        working_dir=working_dir, timeout=timeout, memory=memory)

def corset_prove \
    ( bin_file: Path
    , trace_file: Path
    , working_dir: Path | None = None
    , timeout: float | None = None
    , memory: int | None = None
    ) -> ExecStatus:

    assert shutil.which("corset-prover"), "Unable to find 'corset-prover' tool in PATH!"

    command = \
        [ shutil.which("corset-prover")
        , "--bin", str(bin_file)
        , "--trace", str(trace_file)
        ]

    return execute_command(command, "corset-prover", working_dir=working_dir, \
        timeout=timeout, memory=memory)