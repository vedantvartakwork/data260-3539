{
  "family": "s3539-hw1-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "runtimePlatform": {
    "cpuArchitecture": "X86_64",
    "operatingSystemFamily": "LINUX"
  },
  "executionRoleArn": "__EXECUTION_ROLE_ARN__",
  "containerDefinitions": [
    {
      "name": "s3539-hw1-web",
      "image": "__IMAGE_URI__",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8839,
          "hostPort": 8839,
          "protocol": "tcp",
          "name": "web-8839-tcp",
          "appProtocol": "http"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/s3539-hw1",
          "awslogs-region": "__AWS_REGION__",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
