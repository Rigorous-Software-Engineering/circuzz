import re
import math

from backends.noir.command import noir_version
from circuzz.common.colorlogs import get_color_logger

from .ir2noir import IR2NoirVisitor

logger = get_color_logger()

def field_str_to_int(field: str) -> int:
    assert len(field) > 0, "unable to convert an empty string to an integer"

    # first remove all multiplications
    if "×" in field:
        return math.prod([field_str_to_int(v) for v in field.split("×")])

    # second remove all exponents (they should be at the end of string)
    exponents = ["⁰", "¹", "²", "³", "⁴", "⁵", "⁶", "⁷", "⁸", "⁹"]
    for exponent, exponent_str in enumerate(exponents):
        if exponent_str == field[-1]:
            return field_str_to_int(field[:-1]) ** exponent

    # nothing special todo, we can simply parse it as integer
    return int(field)


def parse_signals_from_noir_output(output: str, project_name: str, output_names: list[str]) -> dict[str, int]:

    line_prefix = f"[{project_name}] Circuit output:"
    pattern = r"Field\(([-⁰¹²³⁴⁵⁶⁷⁸⁹×\d]+)\)"

    # iterate over the lines to find the specific debug line
    lines = output.split("\n")
    for line in lines:
        if line.startswith(line_prefix):
            match = re.findall(pattern, line)
            values = [field_str_to_int(v) for v in match]
            assert len(values) == len(output_names), "unexpected miss-match of output signals"
            return dict(zip(output_names, values, strict=True))

    if len(output_names) > 0:
        # this should not be reached if everything is fine!
        raise RuntimeError("Unable to parse output signals from provided output!")
    return {}

def parse_signal_from_debug_output(output: str) -> dict[str, int]:
    prefix = IR2NoirVisitor.SIGNAL_DEBUG_PREFIX
    separator = IR2NoirVisitor.SIGNAL_DEBUG_SEPARATOR

    value_map: dict[str, int] = {}
    lines = [line.removeprefix(prefix) for line in output.split("\n") if line.startswith(prefix)]
    for line in lines:
        name, value = line.split(separator)
        if value.startswith("0x"):
            value_map[name] = int(value, 16)
        else:
            value_map[name] = int(value)

    return value_map

# Nargo Version Singleton
__SYSTEM_NARGO_VERSION : None | tuple[int,int,int] = None
def get_system_nargo_verison() -> tuple[int,int,int] | None:
    global __SYSTEM_NARGO_VERSION
    if __SYSTEM_NARGO_VERSION == None:
        version_exec = noir_version()
        if version_exec.returncode != 0:
            logger.critical("unable to execute nargo version")
            logger.info(version_exec.stdout)
            logger.info(version_exec.stderr)
            return None
        first_line = version_exec.stdout.split("\n")[0]
        version_string = first_line.removeprefix("nargo version = ")
        ver_big_str, ver_mid_str, ver_small_str = version_string.split(".")
        ver_big, ver_mid, ver_small = int(ver_big_str), int(ver_mid_str), int(ver_small_str)
        __SYSTEM_NARGO_VERSION = (ver_big, ver_mid, ver_small)
    return __SYSTEM_NARGO_VERSION