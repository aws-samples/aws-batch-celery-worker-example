# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from app import *
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument(
    '-n', 
    '--num_messages', 
    type=int, 
    default=1, 
    help='number of messages of each task to send'
)
args = parser.parse_args()

if __name__ == '__main__':
  for i in range(args.num_messages):
    calculate_pi.apply_async()
