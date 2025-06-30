#!/bin/python3

from pathlib import Path
from datetime import datetime
import argparse
import pathlib
import os
import re
import sys
import logging

if not __package__:
    # Make CLI runnable from source tree with python src/packages
    project_root_directory = Path(os.path.dirname(__file__))
    package_source_path = (project_root_directory / "src").absolute().as_posix()
    sys.path.insert(0, package_source_path)

# check the python version as of 3.7 dictionaries are ordered which is a requirement!
# Furthermore, some systems require 3.11 to use the `Enum` class.
if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] < 11):
    raise Exception("Python >=3.11 or a more recent version is required.")

from circuzz.common.colorlogs import get_color_logger # pyright: ignore

from experiment.core import explore # pyright: ignore
from experiment.core import observe # pyright: ignore
from experiment.core import replay  # pyright: ignore

from experiment.config import load_config_file # pyright: ignore

logger = get_color_logger()

DEFAULT_CONFIG_DIR = Path("res/configs/default")

# ===============================================================
#                    ClI Argument Parser
# ===============================================================

def get_common_settings_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-v', '--verbosity', type=int, default=0,
        help="sets the verbosity of the logger output (error: 0, warning: 1, info: 2, debug: 3)")
    return parser

def get_tool_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--tool', choices=["circom", "corset", "gnark", "noir"], required=True)
    return parser

def get_directory_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--report-dir', type=pathlib.Path, required=True)
    parser.add_argument('--working-dir', type=pathlib.Path, required=True)
    return parser

def get_argument_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action', help='sub-command help', required=True)

    # generate some parent parser
    sub_tool_parser_parent = get_tool_parser()
    sub_dir_parser_parent = get_directory_parser()
    sub_common_parser_parent = get_common_settings_parser()

    # ------------------------------------------------
    #                   explore
    # ------------------------------------------------

    parser_explore = subparsers.add_parser('explore', help='searches for bugs in a given tool',
        parents=[sub_tool_parser_parent, sub_dir_parser_parent, sub_common_parser_parent])

    parser_explore.add_argument('--config', type=pathlib.Path)
    parser_explore.add_argument('--seed', type=float, default=0,
        help="the default seed is the current time (i.e. 'datetime.now().timestamp()')")
    parser_explore.add_argument('--timeout', type=str, required=False, default=None,
        help="timeout in HMS format, e.g. '2h15m10s'. Must evaluate to positive non-zero timeframe.")

    # ------------------------------------------------
    #                   replay
    # ------------------------------------------------

    parser_replay = subparsers.add_parser('replay', help='reproduces a test execution given its seed',
        parents=[sub_tool_parser_parent, sub_common_parser_parent])

    parser_replay.add_argument('--config', type=pathlib.Path)
    parser_replay.add_argument('--seed', type=float, required=True,
        help="seed of single instance to replay")
    parser_replay.add_argument('--report-dir', type=pathlib.Path, required=True)

    # ------------------------------------------------
    #                   observe
    # ------------------------------------------------

    parser_observe = subparsers.add_parser('observe',
        help='Checks the found errors from a running or finished "explore" run and compares \
        it with the current version. It is important to use the same configuration to \
        get proper results!',
        parents=[sub_tool_parser_parent, sub_dir_parser_parent, sub_common_parser_parent])

    parser_observe.add_argument('--config', type=pathlib.Path)
    parser_observe.add_argument('--observe-dir', type=pathlib.Path, required=True)

    return parser


# ===============================================================
#                      Helper Functions
# ===============================================================


def set_log_level(args: argparse.Namespace):
    if args.verbosity <= 0:
        logger.setLevel(logging.ERROR)
    if args.verbosity == 1:
        logger.setLevel(logging.WARNING)
    if args.verbosity == 2:
        logger.setLevel(logging.INFO)
    if args.verbosity >= 3:
        logger.setLevel(logging.DEBUG)

def parse_hms(value: str) -> int:

    hms_pattern = re.compile("^([0-9]+h)?([0-9]+m)?([0-9]+s)?$")
    hms_match = hms_pattern.match(value)
    if hms_match == None:
        raise ValueError(f"expected HMS formatted value, e.g. '2h15m10s', but got '{value}'")

    hours_match = hms_match.group(1)
    hours = 0
    if hours_match != None:
        hours = int(hours_match.rstrip("h"))

    minutes_match = hms_match.group(2)
    minutes = 0
    if minutes_match != None:
        minutes = int(minutes_match.rstrip("m"))

    seconds_match = hms_match.group(3)
    seconds = 0
    if seconds_match != None:
        seconds = int(seconds_match.rstrip("s"))

    seconds_result = (hours * 60 * 60) + (minutes * 60) + seconds

    if seconds_result == 0:
        raise ValueError(f"HMS value for '{value}' was 0")

    return seconds_result


# ===============================================================
#                      Normal CLI Actions
# ===============================================================

def explore_action(args: argparse.Namespace):
    assert args.config != None, "config was not present in arguments" # should be checked before
    config_file = Path(args.config)
    assert config_file.is_file(), f"unable to locate {config_file}" # should be checked before

    # parse config
    config = load_config_file(config_file, args.tool)

    explore(args.seed, args.report_dir, args.working_dir, args.timeout, config)

def replay_action(args: argparse.Namespace):
    assert args.config != None, "config was not present in arguments" # should be checked before
    config_file = Path(args.config)
    assert config_file.is_file(), f"unable to locate {config_file}" # should be checked before

    # parse config
    config = load_config_file(config_file, args.tool)

    replay(args.seed, args.report_dir, config)

def observe_action(args: argparse.Namespace):
    assert args.config != None, "config was not present in arguments" # should be checked before
    config_file = Path(args.config)
    assert config_file.is_file(), f"unable to locate {config_file}" # should be checked before

    # parse config
    config = load_config_file(config_file, args.tool)

    observe(args.observe_dir, args.report_dir, args.working_dir, config)


# ===============================================================
#                        CLI Entry Point
# ===============================================================


if __name__ == "__main__":

    parser = get_argument_parser()
    args = parser.parse_args()

    set_log_level(args)

    if not "action" in args:
        parser.error(f"no action provided, see '--help' for available options")

    if args.action == None:
        parser.error(f"no action provided, see '--help' for available options")

    if "seed" in args: # check if flag is used in current context
        if args.seed == None or args.seed == 0:
            args.seed = datetime.now().timestamp() # use current date and time as seed

    if "config" in args: # check if flag is used in current contexts
        # set config to the default configs if not provided
        if args.config == None:
            args.config = DEFAULT_CONFIG_DIR / f"{args.tool}.json"
        if args.config.is_absolute():
            parser.error("Configuration files have to be inside the project folder and "
                + "referenced using a relative path! This is due to the container management.")
        if not args.config.is_file():
            parser.error(f"unable to locate file '{args.config}' ('--config')")

    if "timeout" in args: # check if flag is properly formatted
        if args.timeout == None:
            pass # no timeout was set, so its good to go
        else:
            # a timeout was set, which needs parsing (HMS format to seconds)
            try:
                timeout_in_sec = parse_hms(args.timeout)
                args.timeout = timeout_in_sec # override the string field with the correct integer field
            except ValueError as e:
                logger.critical(str(e))
                parser.error(f"timeout ('--timeout') format is expected to be in HMS!")

    match args.action:
        case "explore":
            explore_action(args)
        case "replay":
            replay_action(args)
        case "observe":
            observe_action(args)
        case _:
            raise NotImplementedError(f"unimplemented action {args.action}")