#!/usr/bin/env python3
from aws_cdk import (
                     aws_ec2 as ec2, 
                     aws_batch_alpha as batch,
                     aws_ecr_assets as ecr_assets,
                     aws_sqs as sqs,
                     aws_ecs as ecs,
                     aws_iam as iam,
                     aws_cloudwatch as cw,
                     aws_events as events,
                     aws_events_targets as targets, 
                     App, Stack, CfnOutput, Size,  Tags, Duration
                     )
from constructs import Construct
from os import path

class BatchFargateStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # This resource alone will create a private/public subnet in one AZ as well as nat/internet gateway(s)
        vpc = ec2.Vpc(self, "VPC", max_azs=1)

        # Create the SQS queue for Celery workers to send/recieve messages from 
        batch_celery_batch_sqs_queue = sqs.Queue(
            self, "BatchCeleryBatchQueue",
            queue_name="celery-batch"
        )

        # Creates the Docker image and CDK-controlled ECR repository for Celery worker.
        celery_worker_image = ecr_assets.DockerImageAsset(
            self, 
            "BatchCeleryWorkerImage",
            directory=path.join(
              path.dirname(__file__), "batch_celery_container"
            ), 
            platform=ecr_assets.Platform.LINUX_AMD64
        )

        # Create the AWS Batch resources. This includes a Fargate compute environment, a job queue, and a job definition for the Celery worker with the appropriate task execution IAM role to access the ECR registry and SQS queues.
        # Batch CE will be created in the same AZ as the VPC within the private subnet.
        # Batch CE will have a maximum of 48 vCPUs.
        batch_ce = batch.FargateComputeEnvironment(
          self, 
          "batchCeleryComputeEnvironment",
          vpc=vpc,
          vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
          maxv_cpus=48
        )

        # Batch JQ will have a maximum of 48 vCPUs.
        # Batch JQ will be attached the Batch CE created above.
        batch_queue = batch.JobQueue(
            self, 
            "JobQueue",
            compute_environments=[
              batch.OrderedComputeEnvironment(compute_environment=batch_ce, order=1)
            ],
            job_queue_name="batch-celery-job-queue"
        )

        # IAM roles for:
        # * allowing the ECS agent to allow pulling from private ECR repository
        # * allowing the Batch job to have full access to SQS
        ecs_task_execution_role = iam.Role(
            self, 
            "EcsTaskExecutionRole", 
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
              iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )
        batch_celery_job_role = iam.Role(
            self, 
            "BatchCeleryJobRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
              iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSQSFullAccess")
            ]
        )

        # Create a Batch job definition for the Celery worker. 
        batch_celery_worker_job_def = batch.EcsJobDefinition(
            self, 
            "BatchCeleryWorkerJobDef",
            job_definition_name="runCeleryWorker",
            propagate_tags=True, 
            container=batch.EcsFargateContainerDefinition(
              self, 
              "BatchCeleryWorkerContainerDef",
              image=ecs.ContainerImage.from_registry(
                celery_worker_image.image_uri
              ),
              command=["/opt/celeryapp/run_celery_worker.sh"], 
              memory=Size.mebibytes(2048),
              cpu=1,
              execution_role=ecs_task_execution_role,
              job_role=batch_celery_job_role,
              environment={
                "CELERY_QUEUE_NAME": batch_celery_batch_sqs_queue.queue_name, 
                "CELERY_QUEUE_URL":   batch_celery_batch_sqs_queue.queue_url
              }
            )
        )
        Tags.of(batch_celery_worker_job_def).add("project", "batch-celery")

        # Create a Batch job definition to fill the Batch SQS queue with tasks.
        batch_celery_fill_queue_job_def = batch.EcsJobDefinition(
            self, 
            "BatchCeleryFillQueueJobDef",
            job_definition_name="fillCeleryQueue",
            propagate_tags=True, 
            container=batch.EcsFargateContainerDefinition(
              self, 
              "BatchFillCeleryQueueContainerDef",
              image=ecs.ContainerImage.from_registry(
                celery_worker_image.image_uri
              ),
              command=["/opt/celeryapp/fill_batch_queue.sh", "Ref::numMessages"], 
              memory=Size.mebibytes(2048),
              cpu=1,
              execution_role=ecs_task_execution_role,
              job_role=batch_celery_job_role,
              environment={
                "CELERY_QUEUE_NAME": batch_celery_batch_sqs_queue.queue_name, 
                "CELERY_QUEUE_URL":   batch_celery_batch_sqs_queue.queue_url
              }, 
            ), 
            parameters={"numMessages": 5}
        )
        Tags.of(batch_celery_fill_queue_job_def).add("project", "batch-celery")


        # Create the CloudWatch alarms for monitoring the SQS queue for compute intensive Celery tasks. 
        # The low alarm will enter ALARM state once the queue is >=5 messages.
        cw_alarm_low = cw.Alarm(
              self, 
              "CeleryQueueLowAlarm",
              alarm_description="SQS queue for compute intensive Celery tasks is >=5 messages.",
              metric=batch_celery_batch_sqs_queue.metric_approximate_number_of_messages_visible(
                period=Duration.seconds(60)
              ),
              threshold=5,
              comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
              evaluation_periods=1,
              datapoints_to_alarm=1,
              treat_missing_data=cw.TreatMissingData.MISSING
        )
        # The high alarm will enter ALARM state once the queue is >=50 messages.
        cw_alarm_high = cw.Alarm(
              self, 
              "CeleryQueueHighAlarm",
              alarm_description="SQS queue for compute intensive Celery tasks is >=50 messages.",
              metric=batch_celery_batch_sqs_queue.metric_approximate_number_of_messages_visible(
                period=Duration.seconds(60)
              ),
              threshold=50,
              comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
              evaluation_periods=1,
              datapoints_to_alarm=1,
              treat_missing_data=cw.TreatMissingData.MISSING
        )

        # Create EventBridge rule and target to respond to the low alarm. This rule submits a Batch job to start a single Celery worker to drain the SQS queue.
        eb_rule_low = events.Rule(
          self, 
          "CeleryQueueLowAlarmRule",
          description="SQS queue for compute intensive Celery tasks is >=5 messages.",
          event_pattern=events.EventPattern(
              source=["aws.cloudwatch"],
              detail_type=["CloudWatch Alarm State Change"],
              resources=[cw_alarm_low.alarm_arn],
              detail={
                  "state": {
                    "value": ["ALARM"]
                  }
              }
          )
        )
        eb_rule_low.add_target(
          targets.BatchJob(
              batch_queue.job_queue_arn,
              batch_queue,
              batch_celery_worker_job_def.job_definition_arn,
              batch_celery_worker_job_def,
              job_name="runSingleCeleryWorker"
          )
        )
        # Create EventBridge rule and target to respond to the high alarm. This rule submits a Batch array job to start 5 celery workers to drain the SQS queue.
        eb_rule_high = events.Rule(
          self, 
          "CeleryQueueHighAlarmRule",
          description="SQS queue for compute intensive Celery tasks is >=50 messages.",
          event_pattern=events.EventPattern(
              source=["aws.cloudwatch"],
              detail_type=["CloudWatch Alarm State Change"],
              resources=[cw_alarm_high.alarm_arn],
              detail={
                  "state": {
                    "value": ["ALARM"]
                  }
              }
          )
        )
        eb_rule_high.add_target(
          targets.BatchJob(
            batch_queue.job_queue_arn,
            batch_queue,
            batch_celery_worker_job_def.job_definition_arn,
            batch_celery_worker_job_def,
            job_name="runMultipleCeleryWorkers",
            size=10
          )
        )

        # Output CloudFormation resources for use in the example
        CfnOutput(self, "BatchJobQueueArn",value=batch_queue.job_queue_name)
        CfnOutput(self, "BatchCeleryFillQueueJobDefArn",value=batch_celery_fill_queue_job_def.job_definition_name)

app = App()
BatchFargateStack(app, "BatchFargateStack")
app.synth()