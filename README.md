# Circuzz

A metamorphic testing framework for zero-knowledge-proof (ZKP) pipelines.

This is the repository for our paper "Fuzzing Processing Pipelines for Zero-Knowledge Circuits".

## Prerequisites

Following dependencies are needed:

  * `linux` (e.g. `debian`)
  * `python` version 3.10 or higher
  * `podman` version 4.3.1 or higher, visit the [docs](https://docs.podman.io/en/latest/) for more information.

**TIP**: We recommend to set podman's `graphDriver` to `overlay` as this drastically speeds
up the startup times of the used images. Following [link](https://docs.podman.io/en/latest/markdown/podman-system-reset.1.html#examples) should provide more information on this topic.

## Quick Start Example

A quick guide to get something running.

### Installing Dependencies

Installation of `python` and `podman` using a package manager:

~~~
> sudo apt-get -y install python3 podman
~~~

Optionally, setting `podman`'s graph-driver to `overlay`:

~~~
> mkdir -p ~/.config/images
> echo '[storage] driver = "overlay"' > ~/.config/images/storage.conf
> podman system reset
~~~

**WARNING**: any podman resources that are currently installed might be deleted or become unusable!

### Generate Circuits

To only see the circuit generation and translation in action without having to run or install the tools, simply execute the tests:

~~~
> python3 src/run_tests.py
~~~

This will print a random circuit IR together with the different language translations. See the [test files](./src/tests/) for more information.

### Building A Podman Image

We use `circuzz` together with the containerization software `podman` (similar to `docker`).
We provide a [podman build script](./res/scripts/podman-build.sh) to build all the required images to run the experiments.
For the sake of simplicity we will manually pick only the commands that build the required 
images for our *quick start*-example:

~~~
> podman build -t circuzz/base -f ./images/base.docker --build-arg=RUST_VERSION="1.81.0" --build-arg=GO_VERSION="1.23.2" .
> podman build -t circuzz/circom-base -f ./images/circom-base.docker .
> podman build -t circuzz/circom-f97b7ca -f ./images/circom.docker --build-arg=CIRCOM_COMMIT=f97b7ca .
~~~

These commands will first build a base image containing rust version `1.81.0` and go version `1.23.2`, together with other useful tools. Second, a circom base image is created. Finally, a concrete circom image is created containing the circom tool build from the git commit hash `f97b7ca`.

### Running A Single Metamorphic Test 

To see if everything was successfully build and installed, we are now finally ready to execute a single fuzz run for `circom` using following commands:

~~~
podman run -v ./:/app -ti --rm circuzz/circom-f97b7ca python3 cli.py replay --tool circom --report-dir obj/test --seed 0.12345 -v3
~~~

The resulting test files can now be observed in the `obj/test` directory.

For further information try `python3 cli.py --help` or take a look at the [client](#client) section.

## Client

`Circuzz`'s entry point is the client script (`cli.py`). The client supports 3 modi:

 * explore
 * replay
 * observe

*Explore* starts a fuzzing campaign, generating metamorphic circuit pairs and providing them to a specified zkp pipeline.
*Replay* is used to run a single metamorphic circuit pair instance on a specified pipeline.
*Observe* is a special mode used for re-finding old bugs. It listens on an *explore* working directory and executes failing instances from it.

To see the different options for the modi execute:

~~~
> python3 cli.py <MODE> --help
~~~

After the mode, specific settings are provided. The following list gives a short overview and description of them:

  * `--tool <TOOL>`, specifies the pipeline backend / tool that should be tested.
  * `--report-dir <DIR>`, the target directory for storing test entries (CSV-files)
  * `--working-dir <DIR>`, the target directory used for intermediate pipeline files. To increase the performance and to be easy on the drive it is recommended to use a `ramfs` as target location. (See the [podman run script](./res/scripts/podman-run.sh) for "/tmp" mounting options.)
  * `--verbosity <LEVEL>`, the tool uses the default python logging facility. The provided level specifies what kinds of logs are visible. With the default level, i.e., 0, only **ERROR** and **CRITICAL** logs are visible. Increasing the level to 1 or 2, **INFO** and **DEBUG** logs become visible.
  * `--config <CONFIG>`, this flag is used to provide a configuration file for circuit generation, circuit transformation and backend specific settings. If this flag is not provided the program will take the available tool specific configuration file from inside of the [default](./res/configs/default) directory. More on the configurations can be found in the [configuration section](#configuration)
  * `--seed <SEED>`, main seed used to control the randomness for a single fuzzing run or a whole fuzzing campaign.
  * `--timeout <TIME>`, used to set a timeout in HMS format (hours, minutes, seconds, e.g. 2h15m10s) for a fuzzing campaign. The default is no timeout.

## Configuration

In this section we will describe the different configuration options.
The configurations are provided in form of a `.json` file.
Following example is a quick overview of the different available fields:

~~~json
{
    "experiment" : { /* this section is used to control the experiments */

        "enable_exit_on_failure" : false, /* if this is enabled, the program stops if a bug is detected */
        "enable_working_dir_cleanup" : true, /* if this is enabled, the working directory is cleaned after each run (WARNING: disabling this can lead to A LOT of data) */

        "prove_and_verify_tuning_strategy" : "time", /* strategy for the pipeline execution tuner, see the throughput optimization section below */
        "prove_and_verify_tuning_percentage" : 0.5 /* percentage used by the tuner */
    },

    "circom": { /* circom specific setting */
        "boundary_input_probability" : 0.1, /* probability to pick a boundary value as constant */
        "test_iterations" : 2, /* how many inputs iterations are tested */

        "likelihood_cpp_witness_generation" : 0.2, /* probability to use the CPP witness generator together with the node JS generator */
        "likelihood_snark_witness_check" : 0, /* probability to perform a snarkjs witness check */

        "constraint_assignment_probability" : 0.5 /* probability to constrain an assignment */
    },
  
    "corset": { /* corset specific setting */
        "bundle_size" : 1, /* number of circuits that are tested in parallel against the original */
        "executions" : 3, /* number of corset check executions with different flags */
        "rust_corset_check_timeout" : 5, /* specific timeout for the corset check command */
        "general_memory_limit" : 8000, /* memory limit for corset pipeline executables */
        "general_timeout" : 100, /* timeout for corset pipeline executables */
        "guard_variable_probability" : 0.5 /* probability to use a guard variable ST to gain better control over inputs */
    },

    "gnark": { /* gnark specific setting */
        "bundle_size" : 1, /* number of circuit pairs tested in parallel */
        "boundary_input_probability" : 0.1, /* probability to pick a boundary value as constant */
        "test_iterations" : 2, /* how many inputs iterations are tested */
        "go_test_timeout" : "24h" /* go test timeout, this should be the same amount as the test timeout */
    },

    "noir": { /* noir specific setting */
        "boundary_input_probability" : 0.1, /* probability to pick a boundary value as constant */
        "test_iterations"  : 2 /* how many inputs iterations are tested */
    },

    "ir" : { /* everything IR related */
        "operators" : { /* configurations concerning the supported operations */
            "relations"                   : ["<" , ... ], /* list of relation operations used for circuit generation */
            "boolean_unary_operators"     : ["!" , ... ], /* list of boolean unary operations used for circuit generation */
            "boolean_binary_operators"    : ["&&", ... ], /* list of boolean binary operations used for circuit generation */
            "arithmetic_unary_operators"  : ["-" , ... ], /* list of arithmetic unary operations used for circuit generation */
            "arithmetic_binary_operators" : ["+" , ... ], /* list of arithmetic binary operations used for circuit generation */

            "is_arithmetic_ternary_supported" : true, /* if enabled, ternary ifs are generated for boolean expressions */
            "is_boolean_ternary_supported"    : true /* if enabled, ternary ifs are generated for arithmetic expressions */
        },

        "generation" : { /* configurations concerning the circuit generation */
            "generator" : "arithmetic", /* generator type: "boolean" or "arithmetic", depending on the type the inputs are expected to be filed values or boolean values */

            "constant_probability_weight" : 1, /* probability weight given to select a constant if an expression is requested */
            "variable_probability_weight" : 1, /* probability weight given to select a variable if an expression is requested */
            "unary_probability_weight"    : 1, /* probability weight given to select an unary expression if an expression is requested */
            "binary_probability_weight"   : 1, /* probability weight given to select an binary expression if an expression is requested */
            "relation_probability_weight" : 1, /* probability weight given to select a relation if an expression is requested */
            "ternary_probability_weight"  : 1, /* probability weight given to select a ternary if an expression is requested */

            "max_expression_depth"           : 4, /* controls the maximal expression depth of the original circuit */
            "min_number_of_assertions"       : 0, /* controls the minimal amount of generated assertions */
            "max_number_of_assertions"       : 2, /* controls the maximal amount of generated assertions */
            "min_number_of_input_variables"  : 0, /* controls the minimal amount of generated circuit inputs */
            "max_number_of_input_variables"  : 2, /* controls the maximal amount of generated circuit inputs */
            "min_number_of_output_variables" : 0, /* controls the minimal amount of generated circuit outputs */
            "max_number_of_output_variables" : 2, /* controls the maximal amount of generated circuit outputs */

            "max_exponent_value" : 4, /* maximal amount of an exponent (exponents are for now always constant) */
            "boundary_value_probability" : 0.25 /* probability to select a boundary value for a constant */
        },

        "rewrite" : { /* configurations concerning the circuit rewrites */
            "weakening_probability" : 0, /* probability to pick weakening over equality as metamorphic oracle */
            "min_rewrites" : 1, /* minimal number of rewrites per circuit */
            "max_rewrites" : 64, /* maximal number of rewrites per circuit */
            "rules" : { /* see the rule section below for more information on how rules are specified */
                "equivalence" : [ /* list of rules used for the equality oracle */
                    ...
                ],
                "weakening" : [ /* list of rules used for the weakening oracle */
                    ...
                ]
            }
        }
    }
}
~~~

Other examples can be found inside of the [default](./res/configs/default) directory.

#### throughput optimization

The throughput optimizer is a component inside of `circuzz` that tries to balance the execution of pipeline frontends, e.g. compilation stage, and their backends, e.g. prove stage.
The optimizer currently has following strategies:

  * never
  * always
  * time
  * execution
  * likelihood

When set to *never* or *always*, the optimizer is ignored and the backend parts are executed either never or always (if possible). After every execution of a pipeline binary, the execution time is registered inside of the optimizer. If the optimizer is set to *time*, it takes these times and tries to balance the times based on the provided percentage, e.g. if the percentage is `20%`, the optimizer tries to execute the prover and verifier roughly `20%` of the time and skip it otherwise. The same idea applies if it is set to *execution* but instead of time, the absolute number of possible executions is considered. The *likelihood* setting executes the backends based on probability using the provided percentage.

**NOTE:** We found the *time* setting to be the most useful, which is why it is the default and the only setting used in our experiments.

#### Rules

Rules are used to describe the metamorphic translations. A rule consists of consists of three parts:

  - unique identifier
  - matching pattern
  - transformation pattern

Following example shows a rewrite rule for commutativity:

~~~json
{ "name"    : "commutativity"
, "match"   : "(?a + b?)"
, "rewrite" : "(?b + a?)"
}
~~~

The `?` symbol matches a random node which must be given an identifier symbol.
This symbol can be reused in the match and transform pattern and matches or creates
the exact same pattern.

Each operation (unary or  binary) has to be wrapped inside of parenthesis, e.g `( ... )`.
Supported operations are all operations allowed by the circuit IR.

Sometimes it is important to distinguish between boolean and integer values.
To distinguish between them the `:` operator followed by `int` or `bool` can be used.
This operation does not have to be enclosed by parenthesis.

~~~json
{ "name"    : "zero-element-or"
, "match"   : "?a:bool"
, "rewrite" : "(?a || F)"
}

{ "name"    : "zero-element-add"
, "match"   : "?a:int"
, "rewrite" : "(?a + 0)"
}
~~~

A list of all the rules used for bug-hunting can be found [here](./res/configs/rules/rules.json).


## Project Structure

This section describes the different parts of the project.

#### ./data

Contains the processed experiment data from our 6 runs. Each experiment has its own folder with the corresponding `report.txt` file and the four distinct tool configurations.

#### ./images

The images folder contains the different docker files used for podman. To reuse cached image data we separated the required dependency into a general [base image](./images/base.docker) and separate base images per pipelines depending on it. Finally, there are the specific images taking tool versions as argument.

#### ./res

The resource folder is a collection of different resources that do not belong into any of the other directories. It is further structured into three folders containing:

 * configurations
 * go files
 * quality of life scripts

##### ./res/configs

This directory contains a set of default configurations and a collection of all the rules used during bug hunting.

##### ./res/go

This directory contains go files for two different projects, i.e. `corset` and `gnark`.
During the build process of the podman images, these files are added to the final `corset` or `gnark` image.

##### ./res/script

The directory contains following scripts:

  * `experiments.sh`: runs the experiments for the current default settings
  * `explore.sh`: starts bug-finding 
  * `podman-build.sh`: builds all required images to re-run the experiments
  * `podman-run.sh`: creates and starts a podman container given a specific image id
  * `process-data.py`: takes the experiment result folder as argument and summarizes the data

All of these scripts are expected to be executed from the **project root**.
Most of them have additional configuration options at the beginning of the script.

For more information see also the [experiments section](#experiments).

#### ./src

This directory contains the implementation of `circuzz`. The source code is split into four parts.

  * **backends**: contains the pipeline specific implementation, ranging from the translation and code emission to calling the pipeline components
  * **circuzz**: implementation of the circuit IR, circuit fuzzer and circuit rewriter
  * **experiment**: functions as entry point, experiment and data management
  * **tests**

#### Others

  * `BUGS.md`: information on found bugs together with their github commits, issues or fix-PRs.
  * `cli.py`: entry point to `circuzz`, see the [client section](#client) for more details.


## Experiments

For finding bugs we started different instances with all kinds of different settings.
The [explore.sh](./res/scripts/explore.sh) script show-cases how multiple instances can be run in parallel.

For reproducing our findings we use the [experiments.sh](./res/scripts/experiments.sh) script and updated the default configurations, i.e. files in [this folder](./res/configs/default), for every run.

To run our experiments, first all the buggy tool versions have to be available on the system.
The following command builds all the required podman images:

~~~
> ./res/scripts/podman-build.sh
~~~

Depending on the system this can take from 10 minutes up to 1 hour and uses roughly 30GB of disk space. Make sure that a stable internet connection is established before running the script.

After building the images, make sure that before executing the `experiments.sh`, the expected system resources are met. The script expects at least 150 cores and a sufficient amount of RAM (experiments were executed on 1 TB of RAM). Additionally the `/tmp` folder should be a `ramfs` for the best performance. Furthermore, the configuration files have to be updated if other settings than the default ones are desired. After these preparation, the experiment script can be executed.

~~~
> ./res/scripts/experiments.sh
~~~

Depending on the configuration under test, the script will run 16 to 24 hours before the results are finished. All results are placed inside of a directory in the `obj` folder and follow the naming convention `seed-<SEED>-date-<TIMESTAMP>`. The generated folder structure contains logging files and raw data (in form of CVS files) produced by the different processes.

To generate a summarized report out of the data use the script [process-data.py](./res/scripts/process-data.py) and pass the `seed-<SEED>-date-<TIMESTAMP>` folder as argument.
Note that if the experiments are adapted, e.g. reduced number of repetitions, the `process-data.py` has to be adapted.

The reports and the corresponding configurations from our experiments can be found inside of the [data](./data/) directory.