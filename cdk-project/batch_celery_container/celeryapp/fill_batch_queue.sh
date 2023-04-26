#!/bin/bash 

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

if [ "$1" != "" ]; then
    NUM_MESSAGES=$1
else
    NUM_MESSAGES=5
fi
# Initialize micromamba and activate the base environment
export MAMBA_ROOT_PREFIX=/opt/micromamba
eval "$(micromamba shell hook --shell=bash )"
micromamba activate 

# Change directory to the celeryapp
cd /opt/celeryapp

# Run the python script to populate the celery queue
python fill-batch-queue.py -n $NUM_MESSAGES