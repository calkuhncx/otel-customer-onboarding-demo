# Lambda Observability Dashboard

## Overview

This dashboard provides **complete observability** for the `cal-onboarding-lambda-arm64` containerized Lambda function, including:

- **Lambda Performance**: Invocation rates, duration percentiles, concurrent executions
- **Reliability**: Error rates, throttles, alerting thresholds
- **SQS Integration**: Queue depth, message flow, processing lag
- **End-to-End Metrics**: API success rates, request latency distribution
- **Operational**: Extension overhead, resource utilization

## What Makes This Special

Since you're using a **Lambda container image** (not a ZIP deployment), you **cannot** use the Coralogix Lambda Layer, which means the built-in Serverless Dashboard won't populate. This custom dashboard **replaces and exceeds** that functionality using:

1. **CloudWatch Metrics** (via AWS Metric Streams)
2. **Application Metrics** (from your ECS service)
3. **Distributed Traces** (full E2E visibility via OpenTelemetry)

## Data Sources Required

### 1. AWS CloudWatch Metric Streams

You need to subscribe to these **AWS Metric Groups** in your CloudWatch Metric Stream:

#### Required Groups:
- ✅ **AWS/Lambda** - Lambda function metrics (invocations, duration, errors, throttles, concurrent executions)
- ✅ **AWS/SQS** - SQS queue metrics (message counts, age, visibility)

#### Optional (Recommended):
- **AWS/ECS** - ECS task metrics (CPU, memory utilization)
- **AWS/ApplicationELB** - If you add a load balancer
- **AWS/Logs** - CloudWatch Logs metrics

### 2. Application Metrics

Your ECS service already exports these via the OpenTelemetry collector:
- `onboarding_api_requests_total` - Total requests received
- `onboarding_api_success_total` - Successful requests
- `onboarding_api_duration_seconds` - Request latency histogram

### 3. Distributed Traces

Already configured! Your setup sends full E2E traces:
```
ECS Fargate (onboarding-api)
    ↓ W3C TraceContext via SQS MessageAttributes
Lambda (cal-onboarding-lambda-arm64)
    ↓ OTLP gRPC to Coralogix
Coralogix APM
```

## How to Set Up CloudWatch Metric Streams

If you don't already have Metric Streams configured, follow these steps:

### Step 1: Create Kinesis Firehose Delivery Stream

```bash
aws firehose create-delivery-stream \
  --delivery-stream-name coralogix-metrics-stream \
  --delivery-stream-type DirectPut \
  --http-endpoint-destination-configuration '{
    "EndpointConfiguration": {
      "Url": "https://ingress.us2.coralogix.com/aws/firehose",
      "Name": "Coralogix"
    },
    "RequestConfiguration": {
      "ContentEncoding": "GZIP",
      "CommonAttributes": [
        {
          "AttributeName": "private_key",
          "AttributeValue": "YOUR_CORALOGIX_SEND_YOUR_DATA_KEY"
        },
        {
          "AttributeName": "applicationName",
          "AttributeValue": "customer-onboarding"
        },
        {
          "AttributeName": "subsystemName",
          "AttributeValue": "aws-metrics"
        }
      ]
    },
    "BufferingHints": {
      "SizeInMBs": 1,
      "IntervalInSeconds": 60
    },
    "CloudWatchLoggingOptions": {
      "Enabled": true,
      "LogGroupName": "/aws/kinesisfirehose/coralogix-metrics",
      "LogStreamName": "metrics"
    },
    "S3Configuration": {
      "RoleARN": "arn:aws:iam::YOUR_ACCOUNT:role/FirehoseBackupRole",
      "BucketARN": "arn:aws:s3:::YOUR_BACKUP_BUCKET"
    }
  }'
```

### Step 2: Create CloudWatch Metric Stream

```bash
aws cloudwatch put-metric-stream \
  --name coralogix-lambda-sqs-stream \
  --firehose-arn arn:aws:firehose:us-west-2:YOUR_ACCOUNT:deliverystream/coralogix-metrics-stream \
  --role-arn arn:aws:iam::YOUR_ACCOUNT:role/CloudWatchMetricStreamRole \
  --output-format opentelemetry0.7 \
  --include-filters '[
    {"Namespace": "AWS/Lambda"},
    {"Namespace": "AWS/SQS"},
    {"Namespace": "AWS/ECS"}
  ]'
```

### Step 3: Verify Stream is Active

```bash
aws cloudwatch list-metric-streams
aws cloudwatch get-metric-stream --name coralogix-lambda-sqs-stream
```

**Expected Output:**
```json
{
  "Arn": "arn:aws:cloudwatch:us-west-2:...",
  "Name": "coralogix-lambda-sqs-stream",
  "State": "running",
  "OutputFormat": "opentelemetry0.7"
}
```

## Dashboard Installation

### Option 1: Import via Coralogix UI

1. Log into Coralogix
2. Navigate to **Dashboards** → **Import**
3. Upload `lambda-observability-dashboard.json`
4. Verify data sources are connected
5. Click **Save**

### Option 2: Import via Grafana API

```bash
CORALOGIX_GRAFANA_URL="https://ng-api-grpc.us2.coralogix.com:443/grafana"
CORALOGIX_API_KEY="YOUR_API_KEY"

curl -X POST "$CORALOGIX_GRAFANA_URL/api/dashboards/db" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CORALOGIX_API_KEY" \
  -d @lambda-observability-dashboard.json
```

## Dashboard Panels Explained

### Panel 1: Lambda Invocations Rate
**Query:** `sum(rate(amazonaws_com_AWS_Lambda_Invocations{FunctionName="cal-onboarding-lambda-arm64"}[5m])) * 60`

**What it shows:** How many Lambda invocations per minute

**Why it matters:** 
- Tracks workload volume
- Detects traffic spikes
- Correlates with SQS message rate

### Panel 2: Lambda Duration - Percentiles
**Query:** `amazonaws_com_AWS_Lambda_Duration_sum / amazonaws_com_AWS_Lambda_Duration_count`

**What it shows:** Average, min, max Lambda execution time

**Why it matters:**
- P50/P95/P99 latencies for SLOs
- Detect performance degradation
- Cold start impact analysis

### Panel 3: Lambda Error Rate (%)
**Query:** `(sum(rate(Errors)) / sum(rate(Invocations))) * 100`

**What it shows:** Percentage of Lambda invocations that fail

**Why it matters:**
- **ALERT CONFIGURED:** Fires when error rate > 5%
- Reliability metric for SLAs
- Immediate visibility into failures

### Panel 4: Concurrent Executions
**Query:** `max(amazonaws_com_AWS_Lambda_ConcurrentExecutions)`

**What it shows:** How many Lambda instances are running simultaneously

**Why it matters:**
- Detect scaling issues
- Plan for reserved concurrency
- Understand parallel workload

### Panel 5: Lambda Throttles
**Query:** `sum(rate(amazonaws_com_AWS_Lambda_Throttles[5m])) * 60`

**What it shows:** Lambda invocations rejected due to concurrency limits

**Why it matters:**
- **ALERT CONFIGURED:** Fires when any throttles occur
- Indicates you've hit account/function limits
- Direct impact on availability

### Panel 6: SQS Queue Depth (Age)
**Query:** `max(amazonaws_com_AWS_SQS_ApproximateAgeOfOldestMessage)`

**What it shows:** How long messages are waiting in the queue

**Why it matters:**
- **ALERT CONFIGURED:** Warning at 60s, critical at 300s
- Detects Lambda processing backlog
- Early warning of capacity issues

### Panel 7: SQS Message Flow
**Queries:**
- `sum(rate(NumberOfMessagesSent)) * 60` - Messages sent by ECS
- `sum(rate(NumberOfMessagesDeleted)) * 60` - Messages processed by Lambda

**What it shows:** Message producer vs consumer rates

**Why it matters:**
- If sent > deleted = backlog building
- If deleted > sent = queue draining
- Balance indicates healthy system

### Panel 8: Extension Duration Overhead
**Query:** `avg(PostRuntimeExtensionsDuration_sum / PostRuntimeExtensionsDuration_count)`

**What it shows:** Time spent in Lambda extensions (e.g., OpenTelemetry SDK flush)

**Why it matters:**
- Observability overhead monitoring
- Optimize flush settings if high
- Cost optimization opportunity

### Panel 9: End-to-End Success Rate
**Query:** `(sum(rate(onboarding_api_success_total)) / sum(rate(onboarding_api_requests_total))) * 100`

**What it shows:** Overall system health from user perspective

**Why it matters:**
- Business-level SLO
- Includes ECS → SQS → Lambda → processing
- Single metric for "is the system working?"

### Panel 10: Total Requests Processed
**Query:** `sum(amazonaws_com_AWS_Lambda_Invocations_sum)`

**What it shows:** Cumulative Lambda invocations

**Why it matters:**
- Volume trend over time
- Cost forecasting
- Capacity planning

### Panel 11: API Request Latency Distribution
**Query:** `histogram_quantile(0.50/0.95/0.99, sum(rate(onboarding_api_duration_seconds_bucket[5m])) by (le))`

**What it shows:** P50, P95, P99 latencies for the full request (ECS → Lambda)

**Why it matters:**
- User experience metric
- SLO tracking (e.g., "P95 < 2s")
- Includes network + queue + Lambda time

## Alerting Rules

The dashboard includes **3 pre-configured alerts**:

### Alert 1: High Error Rate
- **Trigger:** Error rate > 5% for 5 minutes
- **Severity:** Critical
- **Action:** Page on-call engineer
- **Query:** Panel 3

### Alert 2: Lambda Throttling
- **Trigger:** Any throttles detected
- **Severity:** Warning
- **Action:** Increase concurrency limits
- **Query:** Panel 5

### Alert 3: SQS Messages Aging
- **Trigger:** Messages > 5 minutes old
- **Severity:** Warning (60s), Critical (300s)
- **Action:** Scale Lambda or investigate slow processing
- **Query:** Panel 6

### How to Enable Alerts in Coralogix

1. Navigate to **Alerts** → **Alert Definitions**
2. Import alert rules from dashboard panels
3. Configure notification channels (PagerDuty, Slack, email)
4. Set runbook URLs for each alert

## Trace Integration

While this dashboard shows **metrics**, you can deep-dive into specific issues using **traces**:

### From Dashboard → Traces Workflow

1. **Dashboard shows high error rate** (Panel 3)
2. Note the timestamp of the spike
3. Navigate to **Explore** → **Traces**
4. Filter by:
   ```
   service.name: "onboarding-lambda"
   cx.application.name: "customer-onboarding"
   status.code: ERROR
   time: <timestamp from dashboard>
   ```
5. Click trace to see full E2E flow:
   - HTTP request to ECS
   - SQS.SendMessage with W3C context
   - Lambda handler processing
   - Error details and stack trace

### Example Trace Query

```sql
service.name = "onboarding-lambda" 
AND span.kind = CONSUMER 
AND span.attributes.messaging.destination.name = "cal-onboarding-queue"
```

## What Metrics Groups to Subscribe To

### Minimum Required (for this dashboard):
1. ✅ **AWS/Lambda**
2. ✅ **AWS/SQS**

### Recommended:
3. **AWS/ECS** - Monitor the producer service
4. **AWS/Logs** - Log-derived metrics

### Optional (for expansion):
5. **AWS/DynamoDB** - If you add a database
6. **AWS/RDS** - If you use relational storage
7. **AWS/ApplicationELB** - If you add a load balancer
8. **AWS/ApiGateway** - If you add an API Gateway

### Cost Consideration

Each metric stream costs ~$0.02 per 1000 metric updates. For Lambda + SQS:
- **Lambda metrics:** ~10 metrics × 1 function × 1/min = 14,400/day = $0.29/day
- **SQS metrics:** ~15 metrics × 1 queue × 5/min = 21,600/day = $0.43/day
- **Total:** ~$0.72/day or **$22/month** for complete Lambda observability

## Other Integrations

### 1. AWS X-Ray (Alternative Tracing)

While you're using OpenTelemetry, you could also enable X-Ray as a backup:

```python
# In Lambda app.py
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()  # Auto-instrument boto3, requests, etc.
```

**Pros:**
- Native AWS integration
- No additional latency
- Works with container images

**Cons:**
- Less flexible than OTel
- Vendor lock-in
- Extra cost (~$5/1M traces)

**Recommendation:** Stick with OpenTelemetry for vendor-agnostic observability.

### 2. CloudWatch Logs Insights

You can query Lambda logs directly:

```sql
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
```

**Integration:** Add this as a dashboard panel using CloudWatch Logs datasource.

### 3. Coralogix RUM (Real User Monitoring)

If you add a frontend, integrate Coralogix RUM to trace:
```
Browser → API Gateway → ECS → SQS → Lambda
```

### 4. Synthetic Monitoring

Add Coralogix synthetic checks to continuously test your API:

```yaml
# synthetic-check.yaml
name: Onboarding API Health
interval: 5m
steps:
  - http:
      url: http://<ECS_IP>:8000/onboard
      method: POST
      headers:
        Content-Type: application/json
      body: |
        {
          "customer_id": "SYNTHETIC-TEST",
          "email": "synthetic@test.com",
          "company_size": "small",
          "name": "Synthetic Check"
        }
      assertions:
        - status_code: 200
        - response_time_ms: < 2000
        - json_path: "$.status": "success"
```

### 5. Incident Management

Integrate with:
- **PagerDuty** - For alert routing and escalation
- **Slack** - For team notifications
- **Jira** - For automatic ticket creation on critical alerts

## Simplifying the Repository

To make this demo cleaner for your customer:

### Keep:
- ✅ `dashboards/` - Dashboard JSONs and docs
- ✅ `ecs/` - ECS task definitions
- ✅ `onboarding-api/` - Instrumented Python app
- ✅ `onboarding-lambda/` - Instrumented Lambda image
- ✅ `otel-collector/` - Collector config
- ✅ `README.md` - High-level overview
- ✅ `scripts/deploy-*.sh` - Deployment automation

### Remove:
- ❌ Old/test Dockerfiles (keep only `Dockerfile`)
- ❌ Temporary test scripts
- ❌ `.git/` history (squash if needed)

### Add:
- ✅ Architecture diagram (Mermaid or PNG)
- ✅ Quick start guide
- ✅ Troubleshooting section

## Quick Start for Customer

```bash
# 1. Deploy ECS service
cd customer-onboarding-demo
./scripts/deploy-ecs.sh

# 2. Deploy Lambda
./scripts/deploy-lambda.sh

# 3. Configure Metric Streams (see above)

# 4. Import dashboard
# Upload dashboards/lambda-observability-dashboard.json to Coralogix

# 5. Generate traffic
./scripts/generate-traffic.sh 60  # Run for 60 minutes

# 6. View results
# Dashboard: Coralogix → Dashboards → "Lambda Onboarding Service"
# Traces: Coralogix → Explore → filter service.name = onboarding-lambda
```

## Troubleshooting

### Dashboard shows no data

**Check:**
1. Is Metric Stream active? `aws cloudwatch list-metric-streams`
2. Are metrics flowing to Firehose? Check CloudWatch Logs for the stream
3. Is Firehose delivering to Coralogix? Check Firehose metrics
4. Time range correct? Metrics have ~1-2 minute delay

**Fix:**
```bash
# Verify Metric Stream
aws cloudwatch describe-metric-streams \
  --names coralogix-lambda-sqs-stream

# Check Firehose delivery
aws firehose describe-delivery-stream \
  --delivery-stream-name coralogix-metrics-stream
```

### Lambda metrics missing but SQS/ECS present

**Likely cause:** Lambda not in included namespaces

**Fix:**
```bash
aws cloudwatch put-metric-stream \
  --name coralogix-lambda-sqs-stream \
  --include-filters '[{"Namespace": "AWS/Lambda"}, {"Namespace": "AWS/SQS"}]'
```

### Traces not linking to dashboard

Traces and metrics are separate data sources. Use them together:

1. **Metrics** tell you WHEN something went wrong
2. **Traces** tell you WHY it went wrong

**Workflow:**
- Dashboard → Identify time of high errors
- Traces → Filter by that time range + error status
- Logs → Deep dive into specific invocation

## Summary

**What you have:**
- ✅ Complete Lambda observability without the Coralogix Layer
- ✅ Production-ready dashboard with alerts
- ✅ E2E distributed tracing (ECS → SQS → Lambda)
- ✅ CloudWatch metrics integration
- ✅ Vendor-agnostic OpenTelemetry

**What your customer gets:**
- Clean, well-documented demo
- Reusable patterns for their Lambda functions
- Full observability for containerized Lambda
- No vendor lock-in

**Next steps:**
1. Let traffic run for 30 minutes
2. Verify all dashboard panels populate
3. Clean up repository structure
4. Add architecture diagram
5. Push to GitHub

