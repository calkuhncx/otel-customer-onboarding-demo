#!/bin/bash
set -e

echo "🚀 Deploying Enhanced Customer Onboarding Service..."

# Build enhanced images (not the clean versions)
echo "📦 Building enhanced API image..."
docker build --platform linux/amd64 \
  -t 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-onboarding-api:enhanced \
  -f onboarding-api/Dockerfile .

echo "📦 Building enhanced Lambda image..."
docker build --platform linux/amd64 \
  -t 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-onboarding-lambda:enhanced \
  -f onboarding-lambda/Dockerfile .

echo "🔑 Login to ECR..."
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 104013952213.dkr.ecr.us-west-2.amazonaws.com

echo "⬆️  Pushing enhanced images..."
docker push 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-onboarding-api:enhanced
docker push 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-onboarding-lambda:enhanced

echo "🔄 Updating Lambda function..."
aws lambda update-function-code \
  --function-name cal-onboarding-lambda \
  --image-uri 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-onboarding-lambda:enhanced \
  --region us-west-2

echo "🔄 Updating ECS service..."
# Update task definition to use enhanced image
sed 's|:production|:enhanced|g' ecs/taskdef.fargate.json > ecs/taskdef-enhanced.json

aws ecs register-task-definition \
  --cli-input-json file://ecs/taskdef-enhanced.json \
  --region us-west-2

aws ecs update-service \
  --cluster cal-onboarding-cluster \
  --service cal-onboarding-api \
  --force-new-deployment \
  --region us-west-2

echo "✅ Enhanced version deployment initiated!"
echo "⏳ Wait 2-3 minutes for services to restart with enhanced features"
echo "🧪 Then test with: curl -X POST http://34.219.67.30:8000/onboard -H 'Content-Type: application/json' -d '{\"customer_id\":\"enhanced-test\",\"email\":\"test@example.com\",\"type\":\"premium\",\"company_name\":\"Test Corp\"}'"
