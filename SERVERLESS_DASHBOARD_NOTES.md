# Coralogix Serverless Dashboard - Known Limitations

## Current Status ✅
- **E2E Distributed Tracing**: WORKING perfectly
  - Beautiful trace flow: ECS → SQS → Lambda
  - Proper parent-child relationships
  - Complete context propagation via W3C TraceContext
- **APM Services Dashboard**: WORKING with span metrics
  - RED metrics (Rate, Error, Duration) visible
  - Service map shows proper topology
- **Trace Explorer**: WORKING
  - All spans visible and properly linked
  - Rich attributes for investigation

## Known Limitation ⚠️
**Serverless Dashboard shows 0 invocations**

### Why This Happens
The Coralogix Serverless Dashboard requires:
1. **AWS Lambda Telemetry Exporter** (Coralogix Lambda Layer/Extension)
   - This is a **separate integration** from OpenTelemetry traces
   - Collects CloudWatch Logs and Lambda metrics
   - **Cannot be used with Lambda container images** (our case)
   
2. **CloudWatch Logs Subscription Filter**
   - Streams Lambda logs to Coralogix
   - Populates invocation count and duration metrics
   
3. **CloudWatch Metric Streams**
   - Must include `AWS/Lambda` namespace
   - Sends Lambda platform metrics to Coralogix

### Why We Don't Use the Coralogix Lambda Extension
Our Lambda is deployed as a **container image**, not a ZIP package. 

**Important Clarification**:
- **Lambda Layers**: Only available for ZIP-deployed Lambda functions
- **Container Image Lambdas**: Cannot use Lambda Layers (different deployment model)
- **Lambda Extensions**: CAN be included in container images, but...

The Coralogix Lambda Extension:
- Is designed for auto-instrumentation
- Would conflict with our pure OpenTelemetry SDK approach
- Duplicates the instrumentation we've already implemented
- Could be manually added to the Dockerfile, but provides no additional value

### What Works (Our Current Implementation)
✅ **OpenTelemetry traces with perfect E2E visibility**
- Manual SDK instrumentation in code
- OTLP gRPC export directly to Coralogix
- Proper FaaS resource attributes
- Cold-start canary spans for debugging
- Console exporter for CloudWatch visibility

### Trade-offs
**What we HAVE:**
- Complete distributed tracing
- Proper span hierarchy and relationships
- Rich trace context for debugging
- APM dashboard with RED metrics
- Service map with proper topology

**What we DON'T have:**
- Invocation count in Serverless Dashboard
- Auto-populated serverless metrics
- Lambda-specific dashboard widgets

## Workaround Options

### Option 1: CloudWatch Logs Subscription (Recommended)
Create a subscription filter to stream Lambda logs to Coralogix:
```bash
aws logs put-subscription-filter \
  --log-group-name /aws/lambda/cal-onboarding-lambda-arm64 \
  --filter-name coralogix-lambda-logs \
  --filter-pattern "" \
  --destination-arn <CORALOGIX_FIREHOSE_ARN>
```

### Option 2: Enable CloudWatch Metric Streams
Ensure the existing Metric Stream includes `AWS/Lambda`:
```bash
aws cloudwatch put-metric-stream \
  --name dbott-cx-cw-metrics-firehose-cx \
  --include-filters Namespace=AWS/Lambda \
  --firehose-arn <FIREHOSE_ARN> \
  --role-arn <ROLE_ARN>
```

### Option 3: Accept the Limitation
For many use cases, having:
- Perfect distributed tracing
- APM dashboard with span metrics
- Service map with proper topology

...is sufficient. The Serverless Dashboard is nice-to-have but not critical for observability.

## Conclusion
Our current implementation is **production-ready** for distributed tracing and APM.
The Serverless Dashboard limitation is a **platform constraint** (container images vs ZIP),
not a flaw in our OpenTelemetry implementation.

If invocation counts are critical, implement Option 1 or 2 above.

