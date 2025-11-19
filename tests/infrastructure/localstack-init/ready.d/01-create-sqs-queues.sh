#!/bin/bash
set -e

echo "Creating SQS queue..."

awslocal sqs create-queue --queue-name test-queue

echo "✓ SQS queue 'test-queue' created successfully!"
