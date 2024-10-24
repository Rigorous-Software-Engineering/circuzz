from pathlib import Path
import subprocess
import time
from dataclasses import dataclass
import resource
from typing import Any, Callable

from .colorlogs import get_color_logger
logger = get_color_logger()

def generate_preexec_fn_memory_limit(limit_memory: int | None) -> Callable[[], Any] | None:
    if limit_memory == None:
        return None
    max_virtual_memory = limit_memory * 1024 * 1024 # limit_memory in MB
    return lambda : resource.setrlimit(resource.RLIMIT_AS, \
        (max_virtual_memory, resource.RLIM_INFINITY))

@dataclass
class ExecStatus():
    command: str
    stdout: str
    stderr: str
    returncode: int
    identifier: str
    delta_time: float
    is_timeout: bool = False

    def is_failure(self):
        return not self.returncode == 0

    def is_failure_strict(self):
        return self.is_failure() or len(self.stderr) > 0

    def __str__(self):
        return \
f"""
identifier: {self.identifier}
command   : {self.command}
returncode: {self.returncode}
stdout:
{self.stdout}
stderr:
{self.stderr}
time: {self.delta_time}s
"""

    def as_markdown(self) -> str:
        return \
f"""
# {self.identifier}

  * command: `{self.command}`
  * time: `{self.delta_time}s`
  * returncode: `{self.returncode}`

### STDOUT
~~~
{self.stdout}
~~~

### STDERR
~~~
{self.stderr}
~~~
"""

def execute_command \
    ( command: list[str]
    , identifier: str
    , working_dir: Path | None = None
    , timeout: float | None = None
    , memory: int | None = None
    ) -> ExecStatus:

    logger.info("execute: " + " ".join(command))
    logger.debug(f"    - timeout: {timeout}")
    logger.debug(f"    - memory-limit: {memory}")
    logger.debug(f"    - working_dir: {working_dir}")

    start_time = time.time()
    is_timeout = False
    try:
        complete_proc = subprocess.run\
            ( command
            , close_fds=False
            , shell=False
            , stdin=subprocess.PIPE
            , stdout=subprocess.PIPE
            , stderr=subprocess.PIPE
            , bufsize=-1
            , cwd=working_dir
            , preexec_fn=generate_preexec_fn_memory_limit(memory)
            , timeout=timeout
            )
        stdout_bytes, stderr_bytes = complete_proc.stdout, complete_proc.stderr
        returncode = complete_proc.returncode
    except subprocess.TimeoutExpired as timeErr:
        stdout_bytes, stderr_bytes = timeErr.stdout, timeErr.stderr
        returncode = 124 # TODO: find a reasonable exit code
        is_timeout = True

    end_time = time.time()
    delta_time = end_time - start_time

    stdout, stderr = [x.decode("utf-8") if x else "" for x in [stdout_bytes, stderr_bytes]]
    command_as_str = " ".join(command)

    status = ExecStatus(command_as_str, stdout, stderr, returncode, identifier, delta_time, is_timeout)
    return status