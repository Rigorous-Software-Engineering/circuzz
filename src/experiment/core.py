import time
from pathlib import Path
from random import Random

from backends.circom.core import run_circom_metamorphic_tests
from backends.noir.core import run_noir_metamorphic_tests
from backends.corset.core import run_corset_metamorphic_tests
from backends.gnark.core import run_gnark_metamorphic_tests

from circuzz.common.filesystem import clean_or_create_dir
from circuzz.common.filesystem import remove_dir_if_exists
from circuzz.common.colorlogs import get_color_logger

from experiment.config import Config
from experiment.config import OnlineTuning
from experiment.config import TuningStrategy
from experiment.config import ZKPLanguage

from .data import DataEntry, TestResult

logger = get_color_logger()

def worker \
    ( seed: float
    , working_dir: Path
    , config: Config
    , online_tuning: OnlineTuning
    ) -> tuple[TestResult | None, Exception | None]:

    test_result : TestResult | None = None
    exception : Exception | None = None
    try:
        lang = config.zkp_language
        match lang:
            case ZKPLanguage.CIRCOM:
                test_result = run_circom_metamorphic_tests(seed, working_dir, config, online_tuning)
            case ZKPLanguage.NOIR:
                test_result = run_noir_metamorphic_tests(seed, working_dir, config, online_tuning)
            case ZKPLanguage.CORSET:
                test_result = run_corset_metamorphic_tests(seed, working_dir, config, online_tuning)
            case ZKPLanguage.GNARK:
                test_result = run_gnark_metamorphic_tests(seed, working_dir, config, online_tuning)
            case _:
                raise NotImplementedError(f"unexpected ZKP language {config.zkp_language}")
    except Exception as e: # catch any exception that is not caught so far
        logger.critical(f"internal error with seed '{seed}'")
        logger.critical(str(e))
        exception = e
    return test_result, exception


# ===============================================================
#                       Explore Mode
# ===============================================================


def explore(seed: float, report_dir: Path, working_dir: Path, timeout: int | None, config: Config):

    """
    Explores a ZKP tool using metamorphic testing. Given an initial seed,
    a report directory, a working directory and a configuration, this function
    will run metamorphic tests until either a time limit is reached or the
    process is terminated.

    Every run it reports gathered information, e.g. execution time or error status,
    in a `summary.csv` and an `errors.csv` CSV-file inside of the report directory.

    At the end of the execution, it writes the seed and execution time into a `.done`
    file inside of the report directory.
    """

    print(f" +-----------------------------------------------------------------------")
    print(f" | Exploring {config.zkp_language} with")
    print(f" |     - time-limit: {timeout}s")
    print(f" |     - seed:       {seed}")
    print(f" +-----------------------------------------------------------------------")

    # clean up directories
    logger.info(f"clean or create report directory {report_dir}")
    clean_or_create_dir(report_dir)

    # prepare summary file
    summary_csv = report_dir / "summary.csv"
    with open(summary_csv, "w") as file_handle:
        file_handle.write(TestResult.csv_header() + "\n")
    errors_csv = report_dir / "errors.csv"
    with open(errors_csv, "w") as file_handle:
        file_handle.write(TestResult.csv_header() + "\n")

    # randomness for current explore run
    rng = Random(seed)

    # loop and thread variables
    is_stop = False
    cycle = 0

    online_tuning = OnlineTuning()
    online_tuning.set_prove_and_verify_tuning \
        ( strategy=config.experiment.prove_and_verify_tuning_strategy
        , percentage=config.experiment.prove_and_verify_tuning_percentage
        )

    start_time = time.time()
    try:
        # main explore loop
        while not is_stop:

            # start the test execution
            result, exception = worker(rng.random(), working_dir, config, online_tuning)

            # test has terminated and exploration time can be gathered
            explore_time = time.time() - start_time

            # check if cleanup is required
            if config.experiment.enable_working_dir_cleanup:
                logger.info(f"deleting working dir {working_dir}")
                remove_dir_if_exists(working_dir) # cleanup

            if exception != None:
                is_stop = True # stop on an error
                logger.warning("stopping exploration due to exception ...")
            else:
                assert result, "unexpected empty exception and test result"

                # update every entry with cycle and explore time
                entries = result.entries
                for entry in entries:
                    entry.cycle = cycle
                    entry.explore_time = explore_time

                # bundle lines and write them once
                error_csv_lines: list[str] = []
                summary_csv_lines: list[str] = []

                if result.is_error() and config.experiment.enable_exit_on_failure: # stop if flag is set
                   is_stop = True
                   logger.warning("stopping exploration due to found error / bug ...")

                # add lines to write
                error_csv_lines += result.csv_error_lines()
                summary_csv_lines += result.csv_lines()

                # preserve information
                if len(error_csv_lines) > 0:
                    with open(errors_csv, 'a') as file_handle:
                        file_handle.writelines(s + '\n' for s in error_csv_lines)
                if len(summary_csv_lines) > 0:
                    with open(summary_csv, 'a') as file_handle:
                        file_handle.writelines(s + '\n' for s in summary_csv_lines)

            # get again current explore time
            explore_time = time.time() - start_time

            # check if we have reached our time limit
            if timeout != None:
                if explore_time >= timeout:
                    raise TimeoutError("configuration timeout reached!")

            # update cycles
            cycle += 1

    except (KeyboardInterrupt, TimeoutError) as e:
        logger.warning(f"{e}")
        pass # expected behavior
    finally:
        # finally write a .done file with basic info
        end_time = time.time() - start_time
        logger.info(f"finished in {round(end_time, 2)}s")
        with open(report_dir / ".done", "w") as file_handler:
            file_handler.write(f"time: {end_time}\nseed: {seed}")


# ===============================================================
#                      Replay Mode
# ===============================================================


def replay(seed: float, report_dir: Path, config: Config):

    """
    Replays a single test run given a specific seed.

    At the end of the execution, it writes the seed, execution state and
    execution time into a `.done` file inside of the report directory.
    """

    print(f" +-----------------------------------------------------------------------")
    print(f" | Replay {config.zkp_language} with")
    print(f" |     - seed: {seed}")
    print(f" +-----------------------------------------------------------------------")

    start_time = time.time()

    clean_or_create_dir(report_dir)

    # create a dummy online tuner and disable all
    # tuning, i.e. always execute the whole pipeline.
    online_tuning = OnlineTuning()
    online_tuning.set_prove_and_verify_tuning(TuningStrategy.ALWAYS)

    # since we want to preserve, we write it into the report directory
    result, exception = worker(seed, report_dir, config, online_tuning)

    status = "success"
    if exception != None:
        status = "crash"
    else:
        assert result, "unexpected empty exception and test result"
        error_entries = result.filter_errors()
        if len(error_entries) > 0:
            for error_entry in error_entries:
                logger.error(f"failure: {error_entry.error}")
            status = "failure"

        summary_csv = report_dir / "summary.csv"
        with open(summary_csv, 'w') as file_handler:
            file_handler.write(TestResult.csv_header() + "\n")
            for csv_line in result.csv_lines():
                file_handler.write(csv_line + "\n")

    end_time = time.time() - start_time
    with open(report_dir / ".done", "w") as file_handler:
        file_handler.write(f"time: {end_time}\nseed: {seed}\nstatus: {status}")

    logger.info(f"finished in {round(end_time, 2)}s")


# ===============================================================
#                      Observer Mode
# ===============================================================


def observe \
    ( observe_dir: Path
    , report_dir: Path
    , working_dir: Path
    , config: Config
    , recheck_interval : int = 5
    ):

    """
    Observes a running or finished `explore` report directory and its `error.csv`.
    It runs checks in a given time intervals (defaults is 5 sec), to see if the given
    report directory contains an error seed that produces no error when executed in
    the current context. If such a seed was found, this function returns, otherwise it
    keeps running as long as
        1. the reporting directory exists or
        2. the reporting directory does not contain a `.done` file.

    Finally, it creates an `error.csv` and `.done` file, containing information on the
    test seeds and required time.

    This function should be used to check if a found bug using the `explore` action and
    a specific version / commit, was fixed / introduced in the current version / commit
    context.
    """

    print(f" +-----------------------------------------------------------------------")
    print(f" | Observe {config.zkp_language} with")
    print(f" |     - observe-dir: {observe_dir}")
    print(f" +-----------------------------------------------------------------------")

    start_time = time.time()
    is_stop = False

    # define explore .done file, if this is present, we can stop after 1 iteration
    explore_done = observe_dir / ".done"

    # prepare directory
    logger.info(f"clean and create report directory {report_dir}")
    clean_or_create_dir(report_dir)

    # prepare summary file
    summary_csv = report_dir / "summary.csv"
    with open(summary_csv, "w") as file_handle:
        file_handle.write(TestResult.csv_header() + "\n")

    # find error file of the explorer dir
    retry_counts = 1
    retry_timer = 10
    errors_csv = observe_dir / "errors.csv"
    while not errors_csv.is_file():
        logger.warning(f"unable to locate {errors_csv}... tries: {retry_counts}")
        time.sleep(retry_timer)
        retry_counts += 1

    # create a dummy online tuner and disable all
    # tuning, i.e. always execute the whole pipeline.
    online_tuning = OnlineTuning()
    online_tuning.set_prove_and_verify_tuning(TuningStrategy.ALWAYS)

    # usually the tools need at least 10 seconds to find something
    # if they find stuff quicker it is best to terminate manually after
    # the first bugs and check afterwards.
    try:
        working_dict : dict[float, DataEntry] = {}
        current_line_ptr = 1 # start at 1 to skip header
        while not is_stop:

            # the explore process has stop so we can also stop once
            # we are done iterating over the found errors
            is_stop = explore_done.is_file()

            # gather errors
            file_lines = []
            with open(errors_csv, mode="r") as file_handler:
                file_lines = file_handler.readlines()

            current_lines = len(file_lines)
            if current_lines > current_line_ptr: # is there a new unchecked line?
                # parse raw data lines
                entries = [DataEntry.from_csv_line(l.rstrip()) for l in file_lines[current_line_ptr:]]
                current_line_ptr = current_lines

                # for every entry
                for entry in entries:
                    # only check each test seed once and gather all unique ids
                    if not entry.seed in working_dict:
                        working_dict[entry.seed] = entry

            # iterate over lookup map
            summary_lines = []
            while len(working_dict) > 0:
                working_seed, failing_entry = working_dict.popitem()
                failing_unique_id = failing_entry.unique_id()
                result, _ = worker(working_seed, working_dir, config, online_tuning)

                # check if cleanup is required
                if config.experiment.enable_working_dir_cleanup:
                    remove_dir_if_exists(working_dir) # cleanup

                if result != None:
                    # update entries for 'is_fixed'
                    for entry in result.entries:
                        unique_id = entry.unique_id()
                        # check if this particular iteration was a failing one
                        if unique_id == failing_unique_id:
                            if entry.error == None: # no obvious error occurred
                                entry.is_fixed = True
                                logger.info(f"BUG: id: {unique_id}, seed {entry.seed} ==> FIXED")
                                is_stop = True # stop on first found fix
                            else:
                                # this might be a potential new bug
                                entry.is_fixed = False
                                logger.warning(f"BUG: id: {unique_id}, seed {entry.seed} ==> FAILING")
                        else:
                            # if the unique id was not a failing one we cannot say much
                            # about the fix status, but we can check for possible new errors.
                            entry.is_fixed = None
                            if entry.error != None:
                                logger.info(f"BUG: id: {unique_id}, seed {entry.seed} ==> SKIPPED")
                            else:
                                # this might be a potential new bug
                                logger.warning(f"BUG: id: {unique_id}, seed {entry.seed} ==> FAILING")

                    # update the data
                    for csv_line in result.csv_lines():
                        summary_lines.append(csv_line)

            if len(summary_lines) > 0:
                with open(summary_csv, 'a') as file_handler:
                    file_handler.writelines(s + '\n' for s in summary_lines)

            # sleep before rechecking
            time.sleep(recheck_interval)

    except (KeyboardInterrupt, TimeoutError) as e:
        logger.warning(f"{e}")
        pass # expected behavior
    finally:
        # after execution of if stopped, write to .done file
        end_time = time.time() - start_time
        logger.info(f"finished in {round(end_time, 2)}s")
        with open(report_dir / ".done", "w") as file_handler:
            file_handler.write(f"time: {end_time}\nobserve-dir: {observe_dir}")