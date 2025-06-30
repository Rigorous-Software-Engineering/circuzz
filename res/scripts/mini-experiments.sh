#!/bin/bash
#
# This script runs a minimal version of the experiments. The following
# changes are done compared to the complete `experiments.sh` script:
#
#   - Only one repetition per bug
#   - A timeout of 10 min per bug
#   - Only executes 3 bugs in parallel (requires roughly 6 - 10 cores required)
#
# The expected runtime is now about 1 - 2 hours.
#
# It requires that the podman-build.sh script was run beforehand!
# The script must be started from the project's root directory.

set -x

# =================================================
#                   SETTINGS
# =================================================

# Timeout for a single bug run
T_SECONDS=0
T_MINUTES=10
T_HOURS=0

# How many repetitions should be executed
REPS=1


# ----------------------------- DO NOT TOUCH -----------------------------

# start timer
start=`date +%s`

# =================================================
#                  Configuration
# =================================================

SEED=8319
VERBOSITY=3
USE_TMP=1

TMP_DIR=/tmp/circuzz/seed-$SEED-date-$start
OBJ_DIR=./obj/seed-$SEED-date-$start
LOG_DIR=./$OBJ_DIR/logs
WAIT_BETWEEN=2

# =================================================
#                 Implementation
# =================================================

# gives the tool extra 5m to shutdown, calculates everything into seconds
PODMAN_TIMEOUT=$((($T_HOURS * 60 * 60) + (($T_MINUTES + 5) * 60) + $T_SECONDS))
# uses the exact values given in hms format style
TOOL_TIMEOUT=$(printf "%sh%sm%ss" $T_HOURS $T_MINUTES $T_SECONDS)

# seed randomness
RANDOM=$SEED

# get available images
source ./res/scripts/podman-images.sh

# create folder structure
mkdir -p $OBJ_DIR
mkdir -p $LOG_DIR

# setup tmp file
if [[ $USE_TMP -eq 1 ]]; then
    mkdir -p $TMP_DIR
fi

# helper function
function start() {

    EXPLORE_REP_DIR=$OBJ_DIR/$4/explore/report
    OBSERVE_REP_DIR=$OBJ_DIR/$4/observe/report

    if [[ $USE_TMP -eq 1 ]]; then
        # tmp folders are cleaned above
        EXPLORE_WORK_DIR=/tmp/$4/explore/working
        OBSERVE_WORK_DIR=/tmp/$4/observe/working
    else
        EXPLORE_WORK_DIR=$OBJ_DIR/$4/explore/working
        OBSERVE_WORK_DIR=$OBJ_DIR/$4/observe/working
    fi

    # start explorer
    if [[ $USE_TMP -eq 1 ]]; then
        podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=1 -v ./:/app -v $TMP_DIR:/tmp --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --timeout $TOOL_TIMEOUT --working-dir $EXPLORE_WORK_DIR --report-dir $EXPLORE_REP_DIR --seed $5 > $LOG_DIR/$4-explore.log 2>&1 &
    else
        podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=1 -v ./:/app --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --timeout $TOOL_TIMEOUT --working-dir $EXPLORE_WORK_DIR --report-dir $EXPLORE_REP_DIR --seed $5 > $LOG_DIR/$4-explore.log 2>&1 &
    fi

    sleep 1 # wait at least 1 second between explorer and observer

    # start observer
    if [[ $USE_TMP -eq 1 ]]; then
        podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=1 -v ./:/app -v $TMP_DIR:/tmp --rm $3 python3 cli.py observe --tool $1 -v$VERBOSITY --working-dir $OBSERVE_WORK_DIR --report-dir $OBSERVE_REP_DIR --observe-dir $EXPLORE_REP_DIR > $LOG_DIR/$4-observe.log 2>&1 &
    else
        podman run --timeout=$PODMAN_TIMEOUT --pids-limit=-1 --cpus=1 -v ./:/app --rm $3 python3 cli.py observe --tool $1 -v$VERBOSITY --working-dir $OBSERVE_WORK_DIR --report-dir $OBSERVE_REP_DIR --observe-dir $EXPLORE_REP_DIR > $LOG_DIR/$4-observe.log 2>&1 &
    fi

    # on first job to finish, kill all others and wait
    wait -n
    kill -2 $(jobs -p)
    wait $(jobs -p)
    echo "finished $4!"
}

#
# START RUNS
#

# repeat the experiment
for i in $(seq 1 $REPS);
do
    # get a random seed for experiments
    R=$RANDOM

    # == FIRST TRIPLE == 

    start_triple=`date +%s`

    # operator ~ (1/2)
    start circom $IMAGE_CIRCOM_2eaaa6d $IMAGE_CIRCOM_9f3da35 bug-1-rep-$i $R &
    echo "started bug-1-rep-$i with $R..."
    sleep $WAIT_BETWEEN

    # operator ~ (2/2)
    start circom $IMAGE_CIRCOM_9a4215b $IMAGE_CIRCOM_b1f795d bug-2-rep-$i $R &
    echo "started bug-2-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # inconsistent prime
    start circom $IMAGE_CIRCOM_9f3da35 $IMAGE_CIRCOM_570911a bug-3-rep-$i $R &
    echo "started bug-3-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # ------------- sync barrier -------------
    echo "Waiting for bug 1, 2 and 3 ..."
    wait $(jobs -p)
    end=`date +%s`
    runtime=$((end-start_triple))
    echo "Bug 1, 2 and 3 finished in $runtime s"
    # ------------- sync barrier -------------

    # == SECOND TRIPLE == 

    start_triple=`date +%s`

    # wrong ~ with small curve prime
    start circom $IMAGE_CIRCOM_c133004 $IMAGE_CIRCOM_f97b7ca bug-4-rep-$i $R &
    echo "started bug-4-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # expansion and native flags
    start corset $IMAGE_CORSET_3145e74 $IMAGE_CORSET_dd7a010 bug-5-rep-$i $R &
    echo "started bug-5-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # wrong constraint for expansion
    start corset $IMAGE_CORSET_3e60e39 $IMAGE_CORSET_e50d554 bug-6-rep-$i $R &
    echo "started bug-6-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # ------------- sync barrier -------------
    echo "Waiting for bug 4, 5 and 6 ..."
    wait $(jobs -p)
    end=`date +%s`
    runtime=$((end-start_triple))
    echo "Bug 4, 5 and 6 finished in $runtime s"
    # ------------- sync barrier -------------

    # == THIRD TRIPLE == 

    start_triple=`date +%s`

    # reworked ifs
    start corset $IMAGE_CORSET_e50d554 $IMAGE_CORSET_fcd3035 bug-7-rep-$i $R &
    echo "started bug-7-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # wrong evaluation of normalized loobean
    start corset $IMAGE_CORSET_fcd3035 $IMAGE_CORSET_3fe818e bug-8-rep-$i $R &
    echo "started bug-8-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # api.Or
    start gnark $IMAGE_GNARK_e3f932b $IMAGE_GNARK_111a078 bug-9-rep-$i $R &
    echo "started bug-9-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # ------------- sync barrier -------------
    echo "Waiting for bug 7, 8 and 9 ..."
    wait $(jobs -p)
    end=`date +%s`
    runtime=$((end-start_triple))
    echo "Bug 7, 8 and 9 finished in $runtime s"
    # ------------- sync barrier -------------

    # == FOURTH TRIPLE == 

    start_triple=`date +%s`

    # api.AssertIsLessOrEqual
    start gnark $IMAGE_GNARK_d6d85d4 $IMAGE_GNARK_70baf16 bug-10-rep-$i $R &
    echo "started bug-10-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # min 1 bit for binary decompose
    start gnark $IMAGE_GNARK_aa6efa4 $IMAGE_GNARK_d8ccab5 bug-11-rep-$i $R &
    echo "started bug-11-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # unchecked casted branch
    start gnark $IMAGE_GNARK_d8ccab5 $IMAGE_GNARK_ea53f37 bug-12-rep-$i $R &
    echo "started bug-12-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # ------------- sync barrier -------------
    echo "Waiting for bug 10, 11, and 12 ..."
    wait $(jobs -p)
    end=`date +%s`
    runtime=$((end-start_triple))
    echo "Bug 10, 11, and 12 finished in $runtime s"
    # ------------- sync barrier -------------

    # == FIFTH TRIPLE == 

    start_triple=`date +%s`

    # wrong assert
    start noir $IMAGE_NOIR_281ebf2_0_41_0 $IMAGE_NOIR_9db206e_0_41_0 bug-13-rep-$i $R &
    echo "started bug-13-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # bb prover error in MemBn254CrsFactory
    start noir $IMAGE_NOIR_79f8954_44b4be6 $IMAGE_NOIR_79f8954_6e36f45 bug-14-rep-$i $R &
    echo "started bug-14-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # stack overflow for lt-expressions
    start noir $IMAGE_NOIR_1a2ca46_0_56_0 $IMAGE_NOIR_c4273a0_0_56_0 bug-15-rep-$i $R &
    echo "started bug-15-rep-$i with $R ..."
    sleep $WAIT_BETWEEN

    # ------------- sync barrier -------------
    echo "Waiting for bug 13, 14, and 15 ..."
    wait $(jobs -p)
    end=`date +%s`
    runtime=$((end-start_triple))
    echo "Bug 13, 14, and 15 finished in $runtime s"
    # ------------- sync barrier -------------
done

# == END ==

# clean up temporary
rm -rf $TMP_DIR

end=`date +%s`
runtime=$((end-start))
echo "finished in $runtime s"