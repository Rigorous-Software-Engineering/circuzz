from dataclasses import dataclass
from random import Random
from typing import Any
from enum import StrEnum
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from circuzz.common.probability import bernoulli
from circuzz.ir.config import IRConfig

from backends.circom.config import CircomConfig
from backends.corset.config import CorsetConfig
from backends.gnark.config import GnarkConfig
from backends.noir.config import NoirConfig

#
# Online Tuning
#

class TuningStrategy(StrEnum):
    NEVER = "never"
    ALWAYS = "always"
    TIME = "time"
    EXECUTION = "execution"
    LIKELIHOOD = "likelihood"

    @classmethod
    def from_str(cls, value: str) -> 'TuningStrategy':
        match value:
            case "never":
                return TuningStrategy.NEVER
            case "always":
                return TuningStrategy.ALWAYS
            case "time":
                return TuningStrategy.TIME
            case "execution":
                return TuningStrategy.EXECUTION
            case "likelihood":
                return TuningStrategy.LIKELIHOOD
            case _:
                raise NotImplementedError(f"unimplemented tuning strategy '{value}', try {list(TuningStrategy)}")


@dataclass()
class OnlineTuning():

    #
    # online tuning for balancing time spend
    # in the prover and verifier stages
    #

    # Configuration Values
    prove_and_verify_target_percentage : float = 0
    prove_and_verify_tuning_strategy : TuningStrategy = TuningStrategy.ALWAYS

    # Permanently Updated Values
    overall_execution_time : float = 0 # time of all tool components under test
    prove_and_verify_time  : float = 0 # time of prove and verify components under test
    prove_and_verify_ticks : int = 0   # number of possible prove and verify execution opportunities
    prove_and_verify_exec  : int = 0   # number of actually prove and verify executions

    def is_prove_and_verify(self, rng: Random) -> bool:
        match self.prove_and_verify_tuning_strategy:
            case TuningStrategy.ALWAYS:
                return True
            case TuningStrategy.NEVER:
                return False
            case TuningStrategy.TIME:
                available_time_resource = self.overall_execution_time * self.prove_and_verify_target_percentage
                return self.prove_and_verify_time < available_time_resource
            case TuningStrategy.EXECUTION:
                available_exec_resource = self.prove_and_verify_ticks * self.prove_and_verify_target_percentage
                return self.prove_and_verify_exec < available_exec_resource
            case TuningStrategy.LIKELIHOOD:
                return bernoulli(self.prove_and_verify_target_percentage, rng)
            case _:
                raise NotImplementedError(f"unknown strategy {self.prove_and_verify_tuning_strategy}")

    def set_prove_and_verify_tuning(self, strategy: TuningStrategy, percentage: float | None = None):
        if percentage == None:
            percentage = 0
        assert 0 <= percentage and percentage <= 1, \
            "percentage must be a positive number between [0, 1]"
        self.prove_and_verify_tuning_strategy = strategy
        self.prove_and_verify_target_percentage = percentage

    def add_general_execution_time(self, exec_time: float):
        self.overall_execution_time += exec_time

    def add_prove_or_verify_time(self, exec_time: float):
        self.overall_execution_time += exec_time
        self.prove_and_verify_time += exec_time

    def inc_prove_and_verify_ticks(self):
        self.prove_and_verify_ticks += 1

    def inc_prove_and_verify_exec(self):
        self.prove_and_verify_exec += 1

#
# Configurations
#

@dataclass(frozen=True)
class ExperimentConfig():
    """
    experiment configuration
    """

    # if an error is detected, the search is stopped
    enable_exit_on_failure : bool

    # after execution, the working dir is deleted
    enable_working_dir_cleanup : bool

    prove_and_verify_tuning_strategy   : TuningStrategy
    prove_and_verify_tuning_percentage : float

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> 'ExperimentConfig':
        enable_exit_on_failure = value.get("enable_exit_on_failure", True) == True
        enable_working_dir_cleanup = value.get("enable_working_dir_cleanup", True) == True

        tuning_strategy_str = value.get("prove_and_verify_tuning_strategy", "always")
        prove_and_verify_tuning_strategy = TuningStrategy.from_str(tuning_strategy_str)
        if prove_and_verify_tuning_strategy in [TuningStrategy.LIKELIHOOD, TuningStrategy.TIME]:
            if not "prove_and_verify_tuning_percentage" in value:
                raise ValueError("unable to find 'prove_and_verify_tuning_percentage' field, "
                    + f"required by tuning strategy '{tuning_strategy_str}'")
        prove_and_verify_tuning_percentage = value.get("prove_and_verify_tuning_percentage", 0)

        return ExperimentConfig \
        ( enable_exit_on_failure = enable_exit_on_failure
        , enable_working_dir_cleanup = enable_working_dir_cleanup
        , prove_and_verify_tuning_strategy = prove_and_verify_tuning_strategy
        , prove_and_verify_tuning_percentage = prove_and_verify_tuning_percentage
        )

class ZKPLanguage(StrEnum):
    CIRCOM = "circom"
    NOIR   = "noir"
    CORSET = "corset"
    GNARK  = "gnark"

    @classmethod
    def from_str(cls, value: str) -> 'ZKPLanguage':
        match value:
            case "circom":
                return ZKPLanguage.CIRCOM
            case "noir":
                return ZKPLanguage.NOIR
            case "corset":
                return ZKPLanguage.CORSET
            case "gnark":
                return ZKPLanguage.GNARK
            case _:
                raise NotImplementedError(f"unimplemented zkp language '{value}', try {list(ZKPLanguage)}")

@dataclass()
class Config():

    # zkp languages
    zkp_language : ZKPLanguage
    zkp_config   : CircomConfig | CorsetConfig | GnarkConfig | NoirConfig

    # ir configurations
    ir : IRConfig

    # experiment configuration
    experiment : ExperimentConfig

    @property
    def circom(self) -> CircomConfig:
        assert self.zkp_language == ZKPLanguage.CIRCOM, \
            f"requested language is not available, available {self.zkp_language}"
        return self.zkp_config # pyright: ignore

    @property
    def corset(self) -> CorsetConfig:
        assert self.zkp_language == ZKPLanguage.CORSET, \
            f"requested language is not available, available {self.zkp_language}"
        return self.zkp_config # pyright: ignore

    @property
    def gnark(self) -> GnarkConfig:
        assert self.zkp_language == ZKPLanguage.GNARK, \
            f"requested language is not available, available {self.zkp_language}"
        return self.zkp_config # pyright: ignore

    @property
    def noir(self) -> NoirConfig:
        assert self.zkp_language == ZKPLanguage.NOIR, \
            f"requested language is not available, available {self.zkp_language}"
        return self.zkp_config # pyright: ignore


def load_config_file(path_to_config: Path, language: str) -> Config:
    assert path_to_config.is_file(), f"Unable to load config file at location {path_to_config}"

    json_obj: dict[str, Any] = {}
    with open(path_to_config, 'r') as file_handler:
        json_obj = json.load(file_handler)

    config_zkp_language = ZKPLanguage.from_str(language)

    if config_zkp_language == ZKPLanguage.CIRCOM and "circom" in json_obj:
        zkp_config = CircomConfig.from_dict(json_obj["circom"])
    elif config_zkp_language == ZKPLanguage.CORSET and "corset" in json_obj:
        zkp_config = CorsetConfig.from_dict(json_obj["corset"])
    elif config_zkp_language == ZKPLanguage.GNARK and "gnark" in json_obj:
        zkp_config = GnarkConfig.from_dict(json_obj["gnark"])
    elif config_zkp_language == ZKPLanguage.NOIR and "noir" in json_obj:
        zkp_config = NoirConfig.from_dict(json_obj["noir"])
    else:
        raise ValueError(f"unable to find configuration for '{config_zkp_language}' in {path_to_config}")

    # parse input
    config_ir = IRConfig.from_dict(json_obj["ir"])
    config_experiment = ExperimentConfig.from_dict(json_obj["experiment"])

    return Config \
              ( zkp_language = config_zkp_language
              , zkp_config = zkp_config
              , ir = config_ir
              , experiment = config_experiment
              )