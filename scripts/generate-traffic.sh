#!/bin/bash

# Simple Traffic Generator for Customer Onboarding Demo
# Generates realistic traffic patterns across ECS Fargate API and Lambda services

set -e

API_URL="${1:-http://54.189.143.187:8000}"
LAMBDA_FUNCTION="${2:-cal-onboarding-lambda}"
TOTAL_REQUESTS="${3:-16}"

echo "🚀 COMPREHENSIVE TRAFFIC GENERATION"
echo "   API URL: $API_URL"
echo "   Lambda: $LAMBDA_FUNCTION" 
echo "   Total requests: $TOTAL_REQUESTS"
echo ""

SUCCESS_COUNT=0
ERROR_COUNT=0

# Customer templates
declare -a CUSTOMERS=(
    '{"customer_id":"enterprise-001","name":"Enterprise Corp","email":"contact@enterprise.com","company_size":"enterprise","industry":"technology"}'
    '{"customer_id":"startup-001","name":"Startup Inc","email":"hello@startup.com","company_size":"startup","industry":"fintech"}'
    '{"customer_id":"midmarket-001","name":"MidMarket LLC","email":"info@midmarket.com","company_size":"medium","industry":"healthcare"}'
    '{"customer_id":"agency-001","name":"Creative Agency","email":"team@agency.com","company_size":"small","industry":"marketing"}'
)

for i in $(seq 1 $TOTAL_REQUESTS); do
    # Pick random customer template
    CUSTOMER_INDEX=$((RANDOM % ${#CUSTOMERS[@]}))
    CUSTOMER_DATA="${CUSTOMERS[$CUSTOMER_INDEX]}"
    
    # Update customer ID to be unique
    CUSTOMER_DATA=$(echo "$CUSTOMER_DATA" | sed "s/001/$i/g")
    CUSTOMER_ID=$(echo "$CUSTOMER_DATA" | jq -r '.customer_id')
    
    if [ $((i % 2)) -eq 0 ]; then
        # ECS API call
        echo "📤 ECS API: $CUSTOMER_ID"
        if curl -s -f -X POST "$API_URL/onboard" \
           -H 'Content-Type: application/json' \
           -d "$CUSTOMER_DATA" \
           -o "/tmp/ecs_response_$i.json"; then
            echo "✅ ECS API: $CUSTOMER_ID (SUCCESS)"
            ((SUCCESS_COUNT++))
        else
            echo "❌ ECS API: $CUSTOMER_ID (FAILED)"
            ((ERROR_COUNT++))
        fi
    else
        # Lambda call  
        echo "📤 Lambda: $CUSTOMER_ID"
        
        # Create Lambda event payload
        LAMBDA_EVENT="{\"customer_id\":\"$CUSTOMER_ID\",\"customer_data\":$CUSTOMER_DATA,\"event_type\":\"direct_invocation\"}"
        echo "$LAMBDA_EVENT" > "/tmp/lambda_payload_$i.json"
        
        if aws lambda invoke \
           --function-name "$LAMBDA_FUNCTION" \
           --payload "file:///tmp/lambda_payload_$i.json" \
           "/tmp/lambda_response_$i.json" \
           --region us-west-2 \
           --output text > /dev/null 2>&1; then
            
            STATUS_CODE=$(cat "/tmp/lambda_response_$i.json" | jq -r '.statusCode // 200')
            if [ "$STATUS_CODE" = "200" ] || [ "$STATUS_CODE" = "400" ]; then
                echo "✅ Lambda: $CUSTOMER_ID (SUCCESS - $STATUS_CODE)"
                ((SUCCESS_COUNT++))
            else
                echo "❌ Lambda: $CUSTOMER_ID (FAILED - $STATUS_CODE)"
                ((ERROR_COUNT++))
            fi
        else
            echo "❌ Lambda: $CUSTOMER_ID (INVOKE FAILED)"
            ((ERROR_COUNT++))
        fi
    fi
    
    # Add some jitter
    sleep 0.$(($RANDOM % 5 + 1))
done

echo ""
echo "🎯 TRAFFIC GENERATION COMPLETE"
echo "   Total requests: $TOTAL_REQUESTS"
echo "   Successful: $SUCCESS_COUNT"
echo "   Failed: $ERROR_COUNT"
echo "   Success rate: $(( SUCCESS_COUNT * 100 / TOTAL_REQUESTS ))%"
echo ""
echo "🔍 Check Coralogix APM for traces from both services!"
echo "   - Service: onboarding-api (ECS Fargate)"
echo "   - Service: onboarding-lambda (Lambda Container)"

# Cleanup temp files
rm -f /tmp/ecs_response_*.json /tmp/lambda_payload_*.json /tmp/lambda_response_*.json