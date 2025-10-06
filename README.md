# Customer Onboarding Demo - OpenTelemetry Best Practices

## 🎯 **Overview**

This demo showcases **production-ready OpenTelemetry instrumentation** for a distributed serverless application using:
- **ECS Fargate** (Python Flask API)
- **AWS SQS** (Message Queue)
- **AWS Lambda** (Containerized Python Function)
- **Coralogix APM** (Observability Platform)

### **Key Features**
✅ **End-to-End Distributed Tracing** with W3C TraceContext propagation  
✅ **Span Metrics** for APM RED metrics (Rate, Error, Duration)  
✅ **Zero Code Changes** for ECS (auto-instrumentation)  
✅ **Pure OpenTelemetry SDK** for Lambda (container images)  
✅ **Production-Ready** with proper error handling and flushing  

---

## 📁 **Repository Structure**

```
customer-onboarding-demo/
├── onboarding-api/           # ECS Fargate Flask application
│   ├── app.py                # Main application with OTel auto-instrumentation
│   ├── Dockerfile            # ECS container image
│   └── requirements.txt      # Python dependencies
│
├── onboarding-lambda/        # AWS Lambda function (container image)
│   ├── app.py                # Lambda handler with manual OTel SDK setup
│   ├── Dockerfile            # Lambda container image
│   └── requirements.txt      # Python dependencies (includes OTLP gRPC exporter)
│
├── otel/                     # OpenTelemetry Collector configurations
│   ├── coralogix-collector.yaml   # Collector with spanmetrics connector
│   └── Dockerfile            # Collector container image
│
├── infrastructure/           # AWS infrastructure setup
│   └── taskdef.json          # ECS task definition template
│
├── generate-sustained-traffic.sh  # Traffic generation script
└── README.md                 # This file
```

---

## 🚀 **Quick Start**

### **Prerequisites**
- AWS Account with ECS, Lambda, SQS, and ECR access
- Docker installed locally
- AWS CLI configured with appropriate credentials
- Coralogix account with Send-Your-Data API key

### **1. Deploy ECS Fargate Service**

```bash
# Build and push ECS application
docker build --platform linux/amd64 -t <ECR_REPO>/cal-onboarding-api:latest -f onboarding-api/Dockerfile .
docker push <ECR_REPO>/cal-onboarding-api:latest

# Build and push OpenTelemetry Collector
docker build --platform linux/amd64 -t <ECR_REPO>/cal-otel-collector:latest -f otel/Dockerfile .
docker push <ECR_REPO>/cal-otel-collector:latest

# Register ECS task definition and create service
# See infrastructure/taskdef.json for configuration
aws ecs register-task-definition --cli-input-json file://infrastructure/taskdef.json
aws ecs create-service --cluster <CLUSTER> --service-name onboarding-api --task-definition cal-onboarding-api-demo
```

### **2. Deploy Lambda Function**

```bash
# Build and push Lambda image (single-arch for AWS Lambda)
cd customer-onboarding-demo
DOCKER_BUILDKIT=0 docker build -t <ECR_REPO>/cal-onboarding-lambda:latest -f onboarding-lambda/Dockerfile .
docker push <ECR_REPO>/cal-onboarding-lambda:latest

# Create or update Lambda function
aws lambda create-function \
  --function-name cal-onboarding-lambda \
  --package-type Image \
  --code ImageUri=<ECR_REPO>/cal-onboarding-lambda:latest \
  --role arn:aws:iam::<ACCOUNT_ID>:role/lambda-execution-role \
  --architecture arm64 \
  --timeout 15 \
  --memory-size 512
```

### **3. Configure Environment Variables**

#### **ECS Task Definition**
```json
{
  "environment": [
    {"name": "OTEL_TRACES_EXPORTER", "value": "otlp"},
    {"name": "OTEL_EXPORTER_OTLP_PROTOCOL", "value": "grpc"},
    {"name": "OTEL_EXPORTER_OTLP_ENDPOINT", "value": "http://127.0.0.1:4317"},
    {"name": "OTEL_PROPAGATORS", "value": "tracecontext,baggage"},
    {"name": "OTEL_TRACES_SAMPLER", "value": "parentbased_always_on"},
    {"name": "OTEL_RESOURCE_ATTRIBUTES", "value": "service.name=onboarding-api,service.namespace=onboarding,cx.application.name=onboarding,cx.subsystem.name=api"}
  ]
}
```

#### **Lambda Function**
```bash
aws lambda update-function-configuration \
  --function-name cal-onboarding-lambda \
  --environment "Variables={
    SERVICE_NAME=onboarding-lambda,
    SERVICE_NAMESPACE=onboarding,
    CX_APPLICATION=onboarding,
    CX_SUBSYSTEM=lambda,
    OTEL_EXPORTER_OTLP_ENDPOINT=ingress.us2.coralogix.com:443,
    OTEL_EXPORTER_OTLP_HEADERS=authorization=Bearer <YOUR_API_KEY>
  }"
```

### **4. Set Up SQS Event Source Mapping**

```bash
aws lambda create-event-source-mapping \
  --function-name cal-onboarding-lambda \
  --event-source-arn arn:aws:sqs:<REGION>:<ACCOUNT_ID>:cal-onboarding-queue \
  --batch-size 5
```

---

## 🔍 **OpenTelemetry Implementation Details**

### **ECS Fargate (Producer)**

**Auto-Instrumentation** via `opentelemetry-instrument` CLI:
- Automatically instruments Flask, boto3, requests
- Exports to sidecar collector via OTLP/gRPC
- **W3C TraceContext injection** into SQS message attributes

**Key Code Pattern** (`onboarding-api/app.py`):
```python
from opentelemetry import propagate, trace
from opentelemetry.trace import SpanKind

# Inside queue_for_processing function
with tracer.start_as_current_span("sqs.send", kind=SpanKind.PRODUCER) as producer_span:
    producer_span.set_attribute("messaging.system", "aws.sqs")
    producer_span.set_attribute("messaging.destination.name", "cal-onboarding-queue")
    
    # Inject W3C context
    carrier = {}
    propagate.inject(carrier)
    
    # Map to SQS MessageAttributes
    msg_attrs = {
        k: {"DataType": "String", "StringValue": v}
        for k, v in carrier.items()
        if k in ("traceparent", "tracestate", "baggage")
    }
    
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(payload),
        MessageAttributes=msg_attrs
    )
```

### **AWS Lambda (Consumer)**

**Manual SDK Setup** (required for container images):
- Pure OpenTelemetry SDK initialization at module load
- **W3C TraceContext extraction** from SQS message attributes
- Per-record CONSUMER spans (continues parent trace)
- Batch span with links for analytics
- Explicit `force_flush()` before function return

**Key Code Pattern** (`onboarding-lambda/app.py`):
```python
from opentelemetry import trace, propagate
from opentelemetry.trace import SpanKind

def _flatten_attrs(msg_attrs):
    """Convert SQS messageAttributes to flat carrier dict"""
    out = {}
    if msg_attrs:
        for k, v in msg_attrs.items():
            sval = v.get("stringValue") or v.get("StringValue")
            if isinstance(sval, str):
                out[k.lower()] = sval
    return out

def _extract_parent(rec):
    """Extract parent context from SQS record"""
    h = _flatten_attrs(rec.get("messageAttributes") or {})
    if "traceparent" in h:
        return propagate.extract(h)
    return None

def handler(event, context):
    records = event.get("Records", [])
    
    # Per-record processing with parent context
    for rec in records:
        parent_ctx = _extract_parent(rec)
        
        with tracer.start_as_current_span(
            "sqs.process",
            context=parent_ctx,  # Continue trace from ECS
            kind=SpanKind.CONSUMER
        ) as span:
            span.set_attribute("messaging.system", "aws.sqs")
            span.set_attribute("messaging.destination.name", "cal-onboarding-queue")
            # Process message...
    
    # Force flush before return (critical for Lambda!)
    provider.force_flush(timeout_millis=5000)
```

### **OpenTelemetry Collector (Sidecar)**

**Span Metrics Connector** for APM dashboard:
- Transforms traces into RED metrics
- Exports both traces and metrics to Coralogix
- Enables APM Services Dashboard without sampling

**Configuration** (`otel/coralogix-collector.yaml`):
```yaml
connectors:
  spanmetrics:
    histogram:
      explicit:
        buckets: [2ms, 4ms, 6ms, 8ms, 10ms, 50ms, 100ms, 200ms, 400ms, 800ms, 1s, 1400ms, 2s, 5s, 10s, 15s]
    dimensions:
      - name: http.method
      - name: http.status_code
    metrics_flush_interval: 15s

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [spanmetrics, otlp/traces]
    
    metrics:
      receivers: [spanmetrics]
      processors: [batch]
      exporters: [otlp/metrics]
```

---

## 📊 **Verify in Coralogix**

### **1. Trace Explorer**
- Filter: `service.name:("onboarding-api" OR "onboarding-lambda")`
- Verify complete E2E traces: `POST /telemetry/smoke` → `sqs.send` → `sqs.process`

### **2. Service Map**
- Should show: `onboarding-api` → `cal-onboarding-queue` → `onboarding-lambda`

### **3. APM Services Dashboard**
- View RED metrics (Rate, Error, Duration) for both services
- Powered by Span Metrics (no sampling needed!)

### **4. Serverless Catalog**
- **Requires CloudWatch Metric Streams** with `AWS/Lambda` namespace
- Shows invocation count, duration, errors, throttles
- Update metric stream:
  ```bash
  aws cloudwatch put-metric-stream \
    --name <STREAM_NAME> \
    --include-filters Namespace=AWS/Lambda \
    --firehose-arn <FIREHOSE_ARN> \
    --role-arn <ROLE_ARN> \
    --output-format opentelemetry0.7
  ```

---

## 🧪 **Testing**

### **Generate Traffic**
```bash
# Run sustained traffic for dashboard population
./generate-sustained-traffic.sh <ECS_PUBLIC_IP> 600 1
# Arguments: IP, duration (seconds), interval (seconds)
```

### **Manual Test**
```bash
# Test ECS API
curl -X POST http://<ECS_IP>:8000/telemetry/smoke \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"TEST-001"}'

# Check ECS logs for trace ID
aws logs tail /ecs/cal-onboarding-api --since 1m | grep "PRODUCER trace_id"

# Check Lambda logs
aws logs tail /aws/lambda/cal-onboarding-lambda --since 1m
```

---

## 🎓 **Best Practices Demonstrated**

### **1. Context Propagation**
- ✅ W3C TraceContext for vendor-agnostic tracing
- ✅ Inject *inside* producer span (not before)
- ✅ Extract and pass `context=parent_ctx` to consumer span
- ✅ Lowercase keys for SQS message attributes

### **2. Span Kinds**
- ✅ `PRODUCER` for SQS send operations
- ✅ `CONSUMER` for SQS receive/process operations
- ✅ `SERVER` for HTTP endpoints

### **3. Lambda-Specific**
- ✅ Initialize SDK at module load (cold start)
- ✅ Explicit `force_flush()` before return
- ✅ Handle SQS batch events with per-record spans
- ✅ Use container images when layers aren't available

### **4. Resource Attributes**
- ✅ `service.name`, `service.namespace` for service identification
- ✅ `cx.application.name`, `cx.subsystem.name` for Coralogix
- ✅ `cloud.*`, `faas.*` attributes for serverless context
- ✅ `messaging.*` attributes for queue operations

### **5. Span Metrics**
- ✅ Use `spanmetrics` connector for 100% APM coverage
- ✅ No sampling needed (metrics from all spans)
- ✅ Configure histogram buckets for latency percentiles

---

## 🐛 **Troubleshooting**

### **No traces in Coralogix**
1. Check collector logs: `aws logs tail /ecs/cal-otel-collector`
2. Verify API key: `authorization: Bearer <SEND_YOUR_DATA_KEY>`
3. Check Lambda flush: Look for "Flush complete" in logs

### **Traces not linked (separate traces)**
1. Verify `traceparent` in SQS: `aws sqs receive-message --message-attribute-names All`
2. Check Lambda extraction: Look for "extracted traceparent" logs
3. Ensure `OTEL_PROPAGATORS=tracecontext,baggage` on both sides

### **No Serverless Catalog data**
1. Verify CloudWatch Metric Stream includes `AWS/Lambda`
2. Check metric stream is `running` state
3. Wait 5-10 minutes for metrics to propagate

### **Lambda not processing SQS**
1. Check event source mapping: `aws lambda list-event-source-mappings`
2. Verify IAM permissions for Lambda execution role
3. Check SQS queue visibility timeout

---

## 📚 **Resources**

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Coralogix OpenTelemetry Integration](https://coralogix.com/docs/opentelemetry/)
- [AWS Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)

---

## 🤝 **Contributing**

This is a **reference implementation** for customer demonstrations. To adapt for your use case:

1. Update service names and endpoints
2. Modify business logic in `onboarding-api/app.py`
3. Adjust collector configuration in `otel/coralogix-collector.yaml`
4. Configure your own Coralogix API keys and endpoints

---

## 📝 **License**

This demo is provided as-is for educational and demonstration purposes.

---

**Built with ❤️ using OpenTelemetry best practices**
