# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from celery import Celery
from sys import stderr
from os import environ

app = Celery("celerybatch", 
             broker="sqs://")

# Update some of the configurations. Specifically: 
# * Set the default queue name to be `celery-default`. 
# * Set the task route for the `calculate_pi` method to be the queue named `celery-batch`. 
app.conf.update(
  task_default_queue = 'celery-default',
  task_routes = {
   'app.calculate_pi': 'celery-batch'
  }
)

# A Celery task that will go into the `celery-batch` SQS queue
# This method does a naive calculation of Pi mutliple times to take up CPU cycles. A 1 vCPU Fargate resource should accomlish this task in about 5 seconds. 
@app.task
def calculate_pi():
  s = 0
  for x in range(10):
    # Initialize denominator
    k = 1
    # Initialize sum
    s = 0
    for i in range(1000000):
        # even index elements are positive
        if i % 2 == 0:
            s += 4/k
        else:
            # odd index elements are negative
            s -= 4/k
        # denominator is odd
        k += 2
  stderr.write("Pi = " + str(s) + "\n")
