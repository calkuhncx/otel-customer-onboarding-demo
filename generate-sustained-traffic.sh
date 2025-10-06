#!/usr/bin/env bash
# Generate sustained traffic for APM and Serverless dashboard population
set -euo pipefail

ECS_IP="${1:-35.164.173.63}"
DURATION="${2:-300}"  # 5 minutes default
INTERVAL="${3:-2}"    # 2 seconds between requests

echo "🚀 Generating sustained traffic for $DURATION seconds"
echo "📊 ECS Endpoint: http://$ECS_IP:8000/telemetry/smoke"
echo "⏱️  Interval: ${INTERVAL}s"
echo ""

START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION))
REQUEST_COUNT=0

while [ "$(date +%s)" -lt "$END_TIME" ]; do
    REQUEST_COUNT=$((REQUEST_COUNT + 1))
    CUSTOMER_ID="TRAFFIC-$(printf '%04d' $REQUEST_COUNT)"
    
    # Send request
    RESPONSE=$(curl -s -X POST "http://$ECS_IP:8000/telemetry/smoke" \
        -H 'Content-Type: application/json' \
        -d "{\"customer_id\":\"$CUSTOMER_ID\"}" \
        --max-time 5 2>&1 || echo '{"error":"timeout"}')
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status // "error"' 2>/dev/null || echo "error")
    
    if [ "$STATUS" = "queued" ]; then
        echo "✅ $REQUEST_COUNT: $CUSTOMER_ID → queued"
    else
        echo "❌ $REQUEST_COUNT: $CUSTOMER_ID → $STATUS"
    fi
    
    # Progress indicator every 10 requests
    if [ $((REQUEST_COUNT % 10)) -eq 0 ]; then
        ELAPSED=$(($(date +%s) - START_TIME))
        REMAINING=$((DURATION - ELAPSED))
        echo "📈 Progress: $REQUEST_COUNT requests | ${ELAPSED}s elapsed | ${REMAINING}s remaining"
    fi
    
    sleep "$INTERVAL"
done

echo ""
echo "✅ Traffic generation complete!"
echo "📊 Total requests: $REQUEST_COUNT"
echo "⏱️  Duration: $(($(date +%s) - START_TIME))s"
echo ""
echo "🔍 Check Coralogix APM Services Dashboard for metrics"
echo "🔍 Filter: service.name:(\"onboarding-api\" OR \"onboarding-lambda\")"

