#!/bin/bash 

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Initialize micromamba and activate the base environment
export MAMBA_ROOT_PREFIX=/opt/micromamba
eval "$(micromamba shell hook --shell=bash )"
micromamba activate 

# Change directory to the celeryapp
cd /opt/celeryapp

# Start the worker as a detached process
celery -A app worker -l ERROR -Q ${CELERY_QUEUE_NAME} --pidfile /var/run/batch-celery-worker.pid --detach 

while [ true ]; do
  if [ ! -f "/var/run/batch-celery-worker.pid" ]; then
    sleep 2
  else
    # Get the process ID for the Celery worker
    PID=$(cat /var/run/batch-celery-worker.pid)
    echo "Celery worker parent PID=$PID"
    break
  fi
done

# Enter a wait loop and periodically check the message queue size. 
# If no messages, break
while [ true ]
do 
  sleep 60
  n=$(aws sqs get-queue-attributes --queue-url ${CELERY_QUEUE_URL} --attribute-names ApproximateNumberOfMessages --query "Attributes.ApproximateNumberOfMessages" --output text)
  if [ $n -eq 0 ]; then
    break;
  else
    echo "NUM_MESSAGES=$n";
  fi
done

# No more messages, stop the worker and exit
echo "SIGTERM CELERY PID=$PID"
kill -15 $PID
while [ true ]; do
  if [ -f "/var/run/batch-celery-worker.pid" ]; then
    break
  fi
  sleep 5
done
echo "EXIT(0)"
exit