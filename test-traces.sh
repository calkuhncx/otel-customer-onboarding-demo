#!/bin/bash
# Quick test script to send traces to ECS → SQS → Lambda

set -e

# Get current ECS IP
echo "🔍 Finding ECS task IP..."
TASK_ARN=$(aws ecs list-tasks --cluster cal-onboarding-cluster --service-name cal-onboarding-api --region us-west-2 --profile FullAdminAccess-104013952213 --query 'taskArns[0]' --output text)
ENI=$(aws ecs describe-tasks --cluster cal-onboarding-cluster --tasks $TASK_ARN --region us-west-2 --profile FullAdminAccess-104013952213 --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
ECS_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI --region us-west-2 --profile FullAdminAccess-104013952213 --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

echo "✅ ECS IP: $ECS_IP"
echo ""

# Send 3 test requests
for i in 1 2 3; do
  echo "📤 Sending test trace $i..."
  RESPONSE=$(curl -s -X POST "http://${ECS_IP}:8000/onboard" \
    -H "Content-Type: application/json" \
    -d "{\"customer_id\":\"TEST-${i}\",\"email\":\"test${i}@example.com\",\"name\":\"Test User ${i}\"}")
  
  REQUEST_ID=$(echo "$RESPONSE" | grep -o '"request_id":"[^"]*"' | cut -d'"' -f4)
  
  if [ -n "$REQUEST_ID" ]; then
    echo "✅ Request $i sent - ID: $REQUEST_ID"
  else
    echo "❌ Request $i failed"
    echo "Response: $RESPONSE"
  fi
  
  sleep 2
done

echo ""
echo "✅ All test traces sent!"
echo "🔍 Search Coralogix for: customer_id = TEST-1, TEST-2, or TEST-3"
echo "📊 Expected: Complete ECS → SQS → Lambda traces"

