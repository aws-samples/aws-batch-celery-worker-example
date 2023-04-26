# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

FROM public.ecr.aws/amazonlinux/amazonlinux:2

# RUN yum group install -y "AWS Tools" "Development Tools"
RUN yum install -y tar bzip2 curl unzip

# Install Micromamba
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -C /usr/local -xvj bin/micromamba

RUN mkdir -p /opt/micromamba && \
    export MAMBA_ROOT_PREFIX="/opt/micromamba" && \
    eval "$(micromamba shell hook -s posix)" && \
    micromamba activate && \ 
    micromamba install -y python=3.10 celery boto3 pycurl -c conda-forge

# Install the AWS CLI
RUN cd /tmp && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && ./aws/install

COPY ./celeryapp /opt/celeryapp

CMD ["/opt/celeryapp/run_celery_worker.sh"]