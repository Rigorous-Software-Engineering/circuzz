#!/bin/bash
#
# This scripts builds all required containers
# The script must be started from the project's root directory
#
# NOTE: This script might run for some hours depending on
#       internet speed and processor power.
#
# NOTE: If a command fails it might be due to a lost connection
#       during a download. It is safe to start this script again. 

set -e -x
start=`date +%s`

# -----------------------------------------
# config and flags for building
# -----------------------------------------

# build flags
BUILD_CIRCOM=1
BUILD_CORSET=1
BUILD_GNARK=1
BUILD_NOIR=1

# get the names of available docker container
source ./res/scripts/podman-images.sh

# -----------------------------------------
# Setup debug-log folder structure
# -----------------------------------------

mkdir -p ./obj
mkdir -p ./obj/logs
mkdir -p ./obj/logs/build
rm -rf ./obj/logs/build/*
LOG_FOLDER="./obj/logs/build"

# -----------------------------------------
# base container
# -----------------------------------------

echo "Building base image ..."

podman build --logfile="$LOG_FOLDER/base.log" -t $IMAGE_BASE -f ./images/base.docker --build-arg=RUST_VERSION=$RUST_VERSION --build-arg=GO_VERSION=$GO_VERSION .

echo "Building base image done!"

# -----------------------------------------
# circom containers
# -----------------------------------------

if [[ $BUILD_CIRCOM -eq 1 ]]; then
    echo "Building circom base image ..."

    podman build --logfile="$LOG_FOLDER/circom-base.log" -t $IMAGE_CIRCOM_BASE -f ./images/circom-base.docker .

    echo "Building circom base image done!"

    echo "Building circom images ..."

    podman build --logfile="$LOG_FOLDER/circom-2eaaa6d.log" -t $IMAGE_CIRCOM_2eaaa6d -f ./images/circom.docker --build-arg=CIRCOM_COMMIT=2eaaa6d . &
    podman build --logfile="$LOG_FOLDER/circom-9f3da35.log" -t $IMAGE_CIRCOM_9f3da35 -f ./images/circom.docker --build-arg=CIRCOM_COMMIT=9f3da35 . &
    podman build --logfile="$LOG_FOLDER/circom-570911a.log" -t $IMAGE_CIRCOM_570911a -f ./images/circom.docker --build-arg=CIRCOM_COMMIT=570911a . &
    podman build --logfile="$LOG_FOLDER/circom-9a4215b.log" -t $IMAGE_CIRCOM_9a4215b -f ./images/circom.docker --build-arg=CIRCOM_COMMIT=9a4215b . &
    podman build --logfile="$LOG_FOLDER/circom-b1f795d.log" -t $IMAGE_CIRCOM_b1f795d -f ./images/circom.docker --build-arg=CIRCOM_COMMIT=b1f795d . &
    podman build --logfile="$LOG_FOLDER/circom-c133004.log" -t $IMAGE_CIRCOM_c133004 -f ./images/circom.docker --build-arg=CIRCOM_COMMIT=c133004 . &
    podman build --logfile="$LOG_FOLDER/circom-f97b7ca.log" -t $IMAGE_CIRCOM_f97b7ca -f ./images/circom.docker --build-arg=CIRCOM_COMMIT=f97b7ca . &

    wait $(jobs -p) # <--- join
    echo "Building circom images done!"
fi

# -----------------------------------------
# corset containers
# -----------------------------------------

if [[ $BUILD_CORSET -eq 1 ]]; then
    echo "Building base corset image ..."

    podman build --logfile="$LOG_FOLDER/corset-base.log" -t $IMAGE_CORSET_BASE -f ./images/corset-base.docker .

    echo "Building base corset image done!"

    echo "Building corset images ..."

    podman build --logfile="$LOG_FOLDER/corset-3145e74.log" -t $IMAGE_CORSET_3145e74 -f ./images/corset.docker --build-arg=CORSET_COMMIT=3145e74 . &
    podman build --logfile="$LOG_FOLDER/corset-dd7a010.log" -t $IMAGE_CORSET_dd7a010 -f ./images/corset.docker --build-arg=CORSET_COMMIT=dd7a010 . &
    podman build --logfile="$LOG_FOLDER/corset-3e60e39.log" -t $IMAGE_CORSET_3e60e39 -f ./images/corset.docker --build-arg=CORSET_COMMIT=3e60e39 . &
    podman build --logfile="$LOG_FOLDER/corset-e50d554.log" -t $IMAGE_CORSET_e50d554 -f ./images/corset.docker --build-arg=CORSET_COMMIT=e50d554 . &
    podman build --logfile="$LOG_FOLDER/corset-fcd3035.log" -t $IMAGE_CORSET_fcd3035 -f ./images/corset.docker --build-arg=CORSET_COMMIT=fcd3035 . &
    podman build --logfile="$LOG_FOLDER/corset-3fe818e.log" -t $IMAGE_CORSET_3fe818e -f ./images/corset.docker --build-arg=CORSET_COMMIT=3fe818e . &
    podman build --logfile="$LOG_FOLDER/corset-0f6fb5d.log" -t $IMAGE_CORSET_0f6fb5d -f ./images/corset.docker --build-arg=CORSET_COMMIT=0f6fb5d . &

    wait $(jobs -p) # <--- join
    echo "Building corset images done!"
fi

# -----------------------------------------
# gnark containers
# -----------------------------------------

if [[ $BUILD_GNARK -eq 1 ]]; then
    echo "Building gnark base image ..."

    podman build --logfile="$LOG_FOLDER/gnark-base.log" -t $IMAGE_GNARK_BASE -f ./images/gnark-base.docker .

    echo "Building gnark base image done!"

    echo "Building gnark images (parallel) ..."

    podman build --logfile="$LOG_FOLDER/gnark-e3f932b.log" -t $IMAGE_GNARK_e3f932b -f ./images/gnark.docker --build-arg=GNARK_COMMIT=e3f932b . &
    podman build --logfile="$LOG_FOLDER/gnark-111a078.log" -t $IMAGE_GNARK_111a078 -f ./images/gnark.docker --build-arg=GNARK_COMMIT=111a078 . &
    podman build --logfile="$LOG_FOLDER/gnark-d6d85d4.log" -t $IMAGE_GNARK_d6d85d4 -f ./images/gnark.docker --build-arg=GNARK_COMMIT=d6d85d4 . &
    podman build --logfile="$LOG_FOLDER/gnark-70baf16.log" -t $IMAGE_GNARK_70baf16 -f ./images/gnark.docker --build-arg=GNARK_COMMIT=70baf16 . &
    podman build --logfile="$LOG_FOLDER/gnark-aa6efa4.log" -t $IMAGE_GNARK_aa6efa4 -f ./images/gnark.docker --build-arg=GNARK_COMMIT=aa6efa4 . &
    podman build --logfile="$LOG_FOLDER/gnark-d8ccab5.log" -t $IMAGE_GNARK_d8ccab5 -f ./images/gnark.docker --build-arg=GNARK_COMMIT=d8ccab5 . &
    podman build --logfile="$LOG_FOLDER/gnark-ea53f37.log" -t $IMAGE_GNARK_ea53f37 -f ./images/gnark.docker --build-arg=GNARK_COMMIT=ea53f37 . &
    podman build --logfile="$LOG_FOLDER/gnark-3a0fa0f.log" -t $IMAGE_GNARK_3a0fa0f -f ./images/gnark.docker --build-arg=GNARK_COMMIT=3a0fa0f . &

    wait $(jobs -p) # <--- join
    echo "Building gnark images done!"
fi

# -----------------------------------------
# noir containers
# -----------------------------------------
#
#
# NOTE: due to noirs download of bb, it is best to not execute it in parallel

if [[ $BUILD_NOIR -eq 1 ]]; then
    echo "Building noir base image ..."

    podman build --logfile="$LOG_FOLDER/noir-base.log" -t $IMAGE_NOIR_BASE -f ./images/noir-base.docker .

    echo "Building noir base image done!"

    echo "Building noir images ..."

    podman build --logfile="$LOG_FOLDER/noir-281ebf2-bb-0.41.0.log" -t $IMAGE_NOIR_281ebf2_0_41_0 -f ./images/noir.docker --build-arg=NOIR_COMMIT=281ebf2 --build-arg=BB_VERSION=0.41.0 .
    podman build --logfile="$LOG_FOLDER/noir-9db206e-bb-0.41.0.log" -t $IMAGE_NOIR_9db206e_0_41_0 -f ./images/noir.docker --build-arg=NOIR_COMMIT=9db206e --build-arg=BB_VERSION=0.41.0 .
    podman build --logfile="$LOG_FOLDER/noir-79f8954-bb-44b4be6.log" -t $IMAGE_NOIR_79f8954_44b4be6 -f ./images/noir.docker --build-arg=NOIR_COMMIT=79f8954 --build-arg=BB_COMMIT=44b4be6 .
    podman build --logfile="$LOG_FOLDER/noir-79f8954-bb-6e36f45.log" -t $IMAGE_NOIR_79f8954_6e36f45 -f ./images/noir.docker --build-arg=NOIR_COMMIT=79f8954 --build-arg=BB_COMMIT=6e36f45 .
    podman build --logfile="$LOG_FOLDER/noir-1a2ca46-bb-0.56.0.log" -t $IMAGE_NOIR_1a2ca46_0_56_0 -f ./images/noir.docker --build-arg=NOIR_COMMIT=1a2ca46 --build-arg=BB_VERSION=0.56.0 .
    podman build --logfile="$LOG_FOLDER/noir-c4273a0-bb-0.56.0.log" -t $IMAGE_NOIR_c4273a0_0_56_0 -f ./images/noir.docker --build-arg=NOIR_COMMIT=c4273a0 --build-arg=BB_VERSION=0.56.0 .

    wait $(jobs -p) # <--- join
    echo "Building noir images done!"
fi

# -----------------------------------------
# Finallize 
# -----------------------------------------

# check for absense of successful tags in log files
error_logs="$(grep -L 'Successfully tagged localhost/circuzz' $LOG_FOLDER/*)"
if [[ ! -z $error_logs ]]; then
    echo "Unable to build some dependencies! See following logs:"
    echo $error_logs
fi

end=`date +%s`
runtime=$((end-start))
echo "finished in $runtime s"