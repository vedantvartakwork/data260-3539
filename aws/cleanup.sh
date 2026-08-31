#!/usr/bin/env bash
set -euo pipefail

HW1_REGION="${HW1_REGION:-us-east-2}"
HW1_PROFILE="${HW1_PROFILE:-data260-school}"
HW1_EXPECTED_ACCOUNT_ID="${HW1_EXPECTED_ACCOUNT_ID:-243396654546}"
HW1_PREFIX="s3539-hw1"

if [[ "${CONFIRM_CLEANUP:-}" != "yes" ]]; then
  echo "This deletes the HW1 AWS resources. Re-run with CONFIRM_CLEANUP=yes."
  exit 2
fi

AWS=(aws --profile "$HW1_PROFILE" --region "$HW1_REGION")
ACCOUNT_ID="$("${AWS[@]}" sts get-caller-identity --query Account --output text)"
if [[ "$HW1_REGION" != "us-east-2" ]]; then
  echo "Refusing to clean up outside the Fresh Canvas project Region us-east-2."
  exit 1
fi
if [[ "$ACCOUNT_ID" != "$HW1_EXPECTED_ACCOUNT_ID" ]]; then
  echo "Refusing to clean up AWS account $ACCOUNT_ID; expected Fresh Canvas account $HW1_EXPECTED_ACCOUNT_ID."
  exit 1
fi
CLUSTER_NAME="$HW1_PREFIX-cluster"
SERVICE_NAME="$HW1_PREFIX-service"
ROLE_NAME="$HW1_PREFIX-ecs-task-execution-role"

"${AWS[@]}" ecs update-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" --desired-count 0 >/dev/null 2>&1 || true
"${AWS[@]}" ecs delete-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" --force >/dev/null 2>&1 || true
"${AWS[@]}" ecs wait services-inactive --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" 2>/dev/null || true

for task_definition in $("${AWS[@]}" ecs list-task-definitions --family-prefix "$HW1_PREFIX-task" --query 'taskDefinitionArns[]' --output text); do
  "${AWS[@]}" ecs deregister-task-definition --task-definition "$task_definition" >/dev/null
done

VPC_ID="$("${AWS[@]}" ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)"
SECURITY_GROUP_ID="$("${AWS[@]}" ec2 describe-security-groups \
  --filters Name=group-name,Values="$HW1_PREFIX-sg" Name=vpc-id,Values="$VPC_ID" \
  --query 'SecurityGroups[0].GroupId' --output text)"

"${AWS[@]}" ecs delete-cluster --cluster "$CLUSTER_NAME" >/dev/null 2>&1 || true
"${AWS[@]}" ecr delete-repository --repository-name "$HW1_PREFIX" --force >/dev/null 2>&1 || true
"${AWS[@]}" logs delete-log-group --log-group-name "/ecs/$HW1_PREFIX" >/dev/null 2>&1 || true
if [[ "$SECURITY_GROUP_ID" != "None" ]]; then
  "${AWS[@]}" ec2 delete-security-group --group-id "$SECURITY_GROUP_ID" >/dev/null
fi
"${AWS[@]}" iam detach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy >/dev/null 2>&1 || true
"${AWS[@]}" iam delete-role --role-name "$ROLE_NAME" >/dev/null 2>&1 || true

echo "Removed the s3539-hw1 ECS, ECR, log, security-group, and execution-role resources."
