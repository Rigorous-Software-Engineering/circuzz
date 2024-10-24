#!/bin/bash
#
# This scripts runs the experiments
# It requires that the podman-build.sh script was run beforehand!
# The script must be started from the project's root directory
#

set -x
start=`date +%s`

# =================================================
#                  Configuration
# =================================================

SEED=8319
VERBOSITY=3
USE_TMP=1
REPS=10

TMP_DIR=/tmp/circuzz/seed-$SEED-date-$start
OBJ_DIR=./obj/seed-$SEED-date-$start
LOG_DIR=./$OBJ_DIR/logs
WAIT_BETWEEN=2

# Timeout settings
T_SECONDS=0
T_MINUTES=0
T_HOURS=24

# ----------------------------- DO NOT TOUCH -----------------------------

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

# repeat the experiment
for i in $(seq 1 $REPS);
do
    # get a random seed for experiments
    R=$RANDOM
    IDX=1

    # operator ~ (1/2)
    start circom $IMAGE_CIRCOM_2eaaa6d $IMAGE_CIRCOM_9f3da35 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # operator ~ (2/2)
    start circom $IMAGE_CIRCOM_9a4215b $IMAGE_CIRCOM_b1f795d bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # inconsistent prime
    start circom $IMAGE_CIRCOM_9f3da35 $IMAGE_CIRCOM_570911a bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # wrong ~ with small curve prime
    start circom $IMAGE_CIRCOM_c133004 $IMAGE_CIRCOM_f97b7ca bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # expansion and native flags
    start corset $IMAGE_CORSET_3145e74 $IMAGE_CORSET_dd7a010 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # wrong constraint for expansion
    start corset $IMAGE_CORSET_3e60e39 $IMAGE_CORSET_e50d554 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # reworked ifs
    start corset $IMAGE_CORSET_e50d554 $IMAGE_CORSET_fcd3035 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # wrong evaluation of normalized loobean
    start corset $IMAGE_CORSET_fcd3035 $IMAGE_CORSET_3fe818e bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # api.Or
    start gnark $IMAGE_GNARK_e3f932b $IMAGE_GNARK_111a078 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # api.AssertIsLessOrEqual
    start gnark $IMAGE_GNARK_d6d85d4 $IMAGE_GNARK_70baf16 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # min 1 bit for binary decompose
    start gnark $IMAGE_GNARK_aa6efa4 $IMAGE_GNARK_d8ccab5 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # unchecked casted branch
    start gnark $IMAGE_GNARK_d8ccab5 $IMAGE_GNARK_ea53f37 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # wrong assert
    start noir $IMAGE_NOIR_281ebf2_0_41_0 $IMAGE_NOIR_9db206e_0_41_0 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # bb prover error in MemBn254CrsFactory
    start noir $IMAGE_NOIR_79f8954_44b4be6 $IMAGE_NOIR_79f8954_6e36f45 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN

    # stack overflow for lt-expressions
    start noir $IMAGE_NOIR_1a2ca46_0_56_0 $IMAGE_NOIR_c4273a0_0_56_0 bug-$IDX-rep-$i $R &
    echo "started bug-$IDX-rep-$i with $R ..."
    IDX=$(($IDX + 1))
    sleep $WAIT_BETWEEN
done

# wait for all to finish
wait $(jobs -p)

# clean up temporary
rm -rf $TMP_DIR

end=`date +%s`
runtime=$((end-start))
echo "finished in $runtime s"