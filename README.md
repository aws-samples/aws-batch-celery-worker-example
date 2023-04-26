## Running Celery workers using AWS Batch

This repository provides a deployable example for the blog post ["Running Celery workers using AWS Batch" blog post](LIVE_BLOG_POST_URL), which discusses how to create an architecture for deploying  [Celery](https://docs.celeryq.dev/en/stable/index.html) workers using [AWS Batch](https://aws.amazon.com/batch/). The following figure (Figure 1) contains a high-level architecture of the example:

![Figure 1: The architecture of the solution. The diagram shows the application sending Celery task requests to an SQS queue. Two CloudWatch alarms are configured to monitor the number of messages in a queue, and enter the `ALARM` state when the threshold is exceeded. A corresponding pair of EventBridge events are configured to either submit a single AWS Batch job for one Celery worker (in the case of a low number of messages) or submit an AWS Batch array job to start a set of workers (in the case when there are a lot of messages in the queue)](images/figure-1-batch-celery-architecture.png)

In the diagram:

1.  A Celery application submits tasks to an SQS queue
2.  [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) alarms monitor the depth of the queue, and enter `ALARM` state when the approximate visible message depth is >=5 and >=50.
3.  [Amazon Event Bridge](https://aws.amazon.com/eventbridge/) rules react to those alarms to start the Celery workers with AWS Batch. The worker processes drain the SQS queue and shut themselves down when the queue is empty for more than 60 seconds. 

### Celery components

You will find the example Celery Python code in the [`cdk-project/batch_celery_container`](cdk-project/batch_celery_container) directory. 

* `app.py` - The Celery app that defines the task to send to the SQS queue and for the Celery worker launched by AWS Batch to process.
* `fill-batch-queue.py` - A small program that imports the Celery app and actually submits a number of Celery requests into the queue for processing. 

### AWS architectural components

This example leverages the [AWS CDK for Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html) to define and manage the infrastructure, including: 

* A VPC with a public and private subnet deployed to a single Availability Zone. The private subnet has a NAT gateway attached. 
* A Docker container and private ECR repository for the Celery processes.
* An AWS Batch compute environment that leverages Fargate to deploy resources to the private VPC. 
* An AWS Batch FIFO job queue attached to the compute environment.
* AWS Batch job definitions that reference the Celery container for submitting the Celery tasks for Batch and for running Celery workers in Batch
* An SQS queue for Celery tasks meant for Batch
* Amazon CloudWatch alarms set to enter ALARM state when the SQS approximate queue depth reaches >= 5 and >= 50 messages
* Amazon EventBridge rules that react to the alarms to submit jobs to AWS Batch to run Celery workers.

### Deploying the example 

If you would like to deploy and run this example in your own AWS account, please refer to the [README.md](cdk-project/README.md) file within the [cdk-project](cdk-project/) subdirectory.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

