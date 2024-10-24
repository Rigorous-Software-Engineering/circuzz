#!/bin/bash

#
# This scripts starts an exploration for all tools
# It requires that the podman-build.sh script was run beforehand!
#

set -x
start=`date +%s`

# =================================================
#                  Configuration
# =================================================

SEED=8319
VERBOSITY=3
USE_TMP=1

CIRCOM_NUM=3
CIRCOM_CPUS=5
CORSET_NUM=3
CORSET_CPUS=1
GNARK_NUM=1
GNARK_CPUS=10
NOIR_NUM=4
NOIR_CPUS=10

TMP_DIR=/tmp/circuzz/seed-$SEED-date-$start
OBJ_DIR=./obj/seed-$SEED-date-$start
LOG_DIR=./$OBJ_DIR/logs
WAIT_BETWEEN=2

# ----------------------------- DO NOT TOUCH -----------------------------

# =================================================
#                 Implementation
# =================================================

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

# helper function (tool, image, unique-name, cpus, random)
function start() {

    echo "Starting $1 with seed $5 ..."

    EXPLORE_REP_DIR=$OBJ_DIR/$3/explore/report
    if [[ $USE_TMP -eq 1 ]]; then
        # tmp folders are cleaned above
        EXPLORE_WORK_DIR=/tmp/$3/explore/working
    else
        EXPLORE_WORK_DIR=$OBJ_DIR/$3/explore/working
    fi

    # start explorer
    if [[ $USE_TMP -eq 1 ]]; then
        podman run --pids-limit=-1 --cpus=$4 -v ./:/app -v $TMP_DIR:/tmp --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --working-dir $EXPLORE_WORK_DIR --report-dir $EXPLORE_REP_DIR --seed $5 > $LOG_DIR/$3-explore.log 2>&1 &
    else
        podman run --pids-limit=-1 --cpus=$4 -v ./:/app --rm $2 python3 cli.py explore --tool $1 -v$VERBOSITY --working-dir $EXPLORE_WORK_DIR --report-dir $EXPLORE_REP_DIR --seed $5 > $LOG_DIR/$3-explore.log 2>&1 &
    fi

    wait $(jobs -p)
}

# circom
if [[ $CIRCOM_NUM -ne 0 ]]; then
    for i in $(seq 1 $CIRCOM_NUM);
    do
        R=$RANDOM
        start circom $IMAGE_CIRCOM_DEFAULT circom-$i $CIRCOM_CPUS $R &
        echo "Started circom $i/$CIRCOM_NUM with seed $R ..."
        sleep $WAIT_BETWEEN
    done
fi

# corset
if [[ $CORSET_NUM -ne 0 ]]; then
    for i in $(seq 1 $CORSET_NUM);
    do
        R=$RANDOM
        start corset $IMAGE_CORSET_DEFAULT corset-$i $CORSET_CPUS $R &
        echo "Started corset $i/$CORSET_NUM with seed $R ..."
        sleep $WAIT_BETWEEN
    done
fi

# gnark
if [[ $GNARK_NUM -ne 0 ]]; then
    for i in $(seq 1 $GNARK_NUM);
    do
        R=$RANDOM
        start gnark $IMAGE_GNARK_DEFAULT gnark-$i $GNARK_CPUS $R &
        echo "Started gnark $i/$GNARK_NUM with seed $R ..."
        sleep $WAIT_BETWEEN
    done
fi

# noir
if [[ $NOIR_NUM -ne 0 ]]; then
    for i in $(seq 1 $NOIR_NUM);
    do
        R=$RANDOM
        start noir $IMAGE_NOIR_DEFAULT noir-$i $NOIR_CPUS $R &
        echo "Started noir $i/$NOIR_NUM with seed $R ..."
        sleep $WAIT_BETWEEN
    done
fi

# wait for all to finish
wait $(jobs -p)

# clean up temporary
rm -rf $TMP_DIR

end=`date +%s`
runtime=$((end-start))
echo "finished in $runtime s"