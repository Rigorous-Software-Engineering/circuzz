#!/bin/bash

set -x
USE_TMP=0 # <-- enable (1) to mount docker "/tmp" to host "/tmp"
IMAGE=$1

# --------------- DO NOT TOUCH ---------------

if [[ -z $IMAGE ]]; then
    echo "ERROR: no prodman image provided!";
    echo "./podman-run.sh <IMAGE>"
    exit 0
fi

if [[ $USE_TMP -eq 1 ]]; then
    podman run --pids-limit=-1 -v ./:/app -v /tmp:/tmp -ti --rm $IMAGE bash
else
    podman run --pids-limit=-1 -v ./:/app -ti --rm $IMAGE bash
fi