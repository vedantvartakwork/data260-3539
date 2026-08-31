#!/usr/bin/env bash
set -euo pipefail

HW1_REGION="${HW1_REGION:-us-east-2}"
HW1_PROFILE="${HW1_PROFILE:-data260-school}"
HW1_EXPECTED_ACCOUNT_ID="${HW1_EXPECTED_ACCOUNT_ID:-243396654546}"
HW1_PREFIX="s3539-hw1"
HW1_PORT="8839"

if [[ "${CONFIRM_DEPLOY:-}" != "yes" ]]; then
  echo "This creates billable AWS resources. Re-run with CONFIRM_DEPLOY=yes after reviewing the script."
  exit 2
fi

AWS=(aws --profile "$HW1_PROFILE" --region "$HW1_REGION")
ACCOUNT_ID="$("${AWS[@]}" sts get-caller-identity --query Account --output text)"
if [[ "$HW1_REGION" != "us-east-2" ]]; then
  echo "Refusing to deploy outside the Fresh Canvas project Region us-east-2."
  exit 1
fi
if [[ "$ACCOUNT_ID" != "$HW1_EXPECTED_ACCOUNT_ID" ]]; then
  echo "Refusing to deploy to AWS account $ACCOUNT_ID; expected Fresh Canvas account $HW1_EXPECTED_ACCOUNT_ID."
  exit 1
fi
ECR_REPOSITORY="$HW1_PREFIX"
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$HW1_REGION.amazonaws.com/$ECR_REPOSITORY:latest"
CLUSTER_NAME="$HW1_PREFIX-cluster"
SERVICE_NAME="$HW1_PREFIX-service"
TASK_FAMILY="$HW1_PREFIX-task"
SECURITY_GROUP_NAME="$HW1_PREFIX-sg"
ROLE_NAME="$HW1_PREFIX-ecs-task-execution-role"

"${AWS[@]}" ecr describe-repositories --repository-names "$ECR_REPOSITORY" >/dev/null 2>&1 || \
  "${AWS[@]}" ecr create-repository --repository-name "$ECR_REPOSITORY" --image-scanning-configuration scanOnPush=true >/dev/null

"${AWS[@]}" ecr get-login-password | \
  docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$HW1_REGION.amazonaws.com"
docker build --platform linux/amd64 -t "$ECR_REPOSITORY:latest" .
docker tag "$ECR_REPOSITORY:latest" "$IMAGE_URI"
docker push "$IMAGE_URI"

"${AWS[@]}" ecs describe-clusters --clusters "$CLUSTER_NAME" --query 'clusters[0].status' --output text 2>/dev/null | grep -q ACTIVE || \
  "${AWS[@]}" ecs create-cluster --cluster-name "$CLUSTER_NAME" >/dev/null
"${AWS[@]}" logs create-log-group --log-group-name "/ecs/$HW1_PREFIX" 2>/dev/null || true

if ! "${AWS[@]}" iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  "${AWS[@]}" iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document file://aws/ecs-task-trust-policy.json >/dev/null
  "${AWS[@]}" iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
fi
EXECUTION_ROLE_ARN="$("${AWS[@]}" iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)"

VPC_ID="$("${AWS[@]}" ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text)"
if [[ -z "$VPC_ID" || "$VPC_ID" == "None" ]]; then
  echo "No default VPC was found in $HW1_REGION. Create/select networking before deploying."
  exit 1
fi
SUBNETS="$("${AWS[@]}" ec2 describe-subnets --filters Name=vpc-id,Values="$VPC_ID" --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')"

SECURITY_GROUP_ID="$("${AWS[@]}" ec2 describe-security-groups \
  --filters Name=group-name,Values="$SECURITY_GROUP_NAME" Name=vpc-id,Values="$VPC_ID" \
  --query 'SecurityGroups[0].GroupId' --output text)"
if [[ "$SECURITY_GROUP_ID" == "None" ]]; then
  SECURITY_GROUP_ID="$("${AWS[@]}" ec2 create-security-group \
    --group-name "$SECURITY_GROUP_NAME" \
    --description "DATA 260 HW1 web access for SID4 3539" \
    --vpc-id "$VPC_ID" --query GroupId --output text)"
  "${AWS[@]}" ec2 authorize-security-group-ingress \
    --group-id "$SECURITY_GROUP_ID" --protocol tcp --port "$HW1_PORT" --cidr 0.0.0.0/0 >/dev/null
fi

TASK_FILE="$(mktemp -t data260-hw1-task.XXXXXX.json)"
trap 'rm -f "$TASK_FILE"' EXIT
sed \
  -e "s|__EXECUTION_ROLE_ARN__|$EXECUTION_ROLE_ARN|g" \
  -e "s|__IMAGE_URI__|$IMAGE_URI|g" \
  -e "s|__AWS_REGION__|$HW1_REGION|g" \
  aws/task-definition.json.tpl >"$TASK_FILE"
TASK_DEFINITION_ARN="$("${AWS[@]}" ecs register-task-definition \
  --cli-input-json "file://$TASK_FILE" --query 'taskDefinition.taskDefinitionArn' --output text)"

NETWORK_CONFIGURATION="awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}"
SERVICE_STATUS="$("${AWS[@]}" ecs describe-services --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" --query 'services[0].status' --output text)"
if [[ "$SERVICE_STATUS" == "ACTIVE" ]]; then
  "${AWS[@]}" ecs update-service \
    --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" \
    --task-definition "$TASK_DEFINITION_ARN" --desired-count 1 \
    --network-configuration "$NETWORK_CONFIGURATION" >/dev/null
else
  "${AWS[@]}" ecs create-service \
    --cluster "$CLUSTER_NAME" --service-name "$SERVICE_NAME" \
    --task-definition "$TASK_DEFINITION_ARN" --desired-count 1 \
    --launch-type FARGATE --platform-version LATEST \
    --network-configuration "$NETWORK_CONFIGURATION" >/dev/null
fi

"${AWS[@]}" ecs wait services-stable --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME"
TASK_ARN="$("${AWS[@]}" ecs list-tasks --cluster "$CLUSTER_NAME" --service-name "$SERVICE_NAME" --query 'taskArns[0]' --output text)"
ENI_ID="$("${AWS[@]}" ecs describe-tasks --cluster "$CLUSTER_NAME" --tasks "$TASK_ARN" \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)"
PUBLIC_IP="$("${AWS[@]}" ec2 describe-network-interfaces --network-interface-ids "$ENI_ID" \
  --query 'NetworkInterfaces[0].Association.PublicIp' --output text)"

echo "ECS service is stable with desired count 1."
echo "Public URL: http://$PUBLIC_IP:$HW1_PORT"
curl --fail --retry 8 --retry-delay 5 "http://$PUBLIC_IP:$HW1_PORT/" >/dev/null
echo "Public URL responded successfully."
