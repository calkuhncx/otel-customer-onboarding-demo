#!/bin/bash
set -e

echo "🚀 Deploying production demo to AWS..."

# Update task definition to use production images
echo "📝 Updating ECS task definition..."
sed -i.bak 's/:tracing/:production/g' ecs/taskdef.fargate.json
sed -i.bak 's/:apm/:production/g' ecs/taskdef.fargate.json

# Register new task definition
aws ecs register-task-definition \
  --cli-input-json file://ecs/taskdef.fargate.json \
  --region us-west-2 \
  --profile FullAdminAccess-104013952213

# Update ECS service
aws ecs update-service \
  --cluster cal-onboarding-cluster \
  --service cal-onboarding-api \
  --task-definition cal-onboarding-api-demo \
  --region us-west-2 \
  --profile FullAdminAccess-104013952213

# Update Lambda function with production image
echo "📝 Updating Lambda function..."
aws lambda update-function-code \
  --function-name cal-onboarding-lambda \
  --image-uri 104013952213.dkr.ecr.us-west-2.amazonaws.com/cal-onboarding-lambda:production \
  --region us-west-2 \
  --profile FullAdminAccess-104013952213

# Update Lambda environment variables for direct OTLP export
echo "📝 Configuring Lambda environment..."
aws lambda update-function-configuration \
  --function-name cal-onboarding-lambda \
  --environment "Variables={OTEL_EXPORTER_OTLP_HEADERS=x-coralogix-api-key=cxtp_xZDmYSbcnchlkMlolh1RPYkSwwFurk}" \
  --region us-west-2 \
  --profile FullAdminAccess-104013952213

echo "✅ Deployment completed!"
echo ""
echo "🎯 Production Demo Ready:"
echo "  - ECS Fargate API: http://34.219.67.30:8000"
echo "  - Lambda Function: cal-onboarding-lambda"
echo "  - Coralogix Domain: us2.coralogix.com"
echo ""
echo "🧪 Test the demo:"
echo "  curl -X POST http://34.219.67.30:8000/onboard -H 'Content-Type: application/json' -d '{\"customer_id\":\"demo-123\",\"type\":\"premium\"}'"
