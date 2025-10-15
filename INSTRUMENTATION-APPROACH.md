# Lambda Instrumentation Approach

## ❓ Question: Is the Lambda Manually or Automatically Instrumented?

**Answer: It's MANUALLY instrumented using the pure OpenTelemetry SDK.**

This is a **hybrid approach** that combines:
- ✅ Manual SDK initialization
- ✅ Manual span creation
- ✅ Coralogix base image (but NOT using their wrapper)

---

## 🔍 Why Manual Instrumentation?

### The Problem
AWS Lambda **container images cannot use Lambda Layers** (including the OpenTelemetry Lambda Layer). This means:
- ❌ Cannot use `arn:aws:lambda:<region>:901920570463:layer:aws-otel-python-<arch>-<version>`
- ❌ Cannot use Coralogix's automatic Lambda Layer wrapper
- ❌ Auto-instrumentation via layers doesn't work for container deployments

### The Solution
We manually initialize OpenTelemetry in the Lambda code itself, giving us:
- ✅ Full control over instrumentation
- ✅ Works with container images
- ✅ Vendor-agnostic (pure OTel)
- ✅ Custom span creation for SQS batch processing
- ✅ Proper distributed tracing (parent-child relationships)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Lambda Container Image                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Base: Coralogix Python Wrapper (Layer in /opt)       │   │
│  │  - We COPY it but DON'T use AWS_LAMBDA_EXEC_WRAPPER   │   │
│  │  - Provides OTel libs in /opt for consistency          │   │
│  └────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Application Layer (LAMBDA_TASK_ROOT)                  │   │
│  │  - app.py: Manual OTel SDK initialization             │   │
│  │  - requirements.txt: Pure OTel packages                │   │
│  │  - No wrapper ENV vars (no CX_* needed for tracing)   │   │
│  └────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  CMD: ["app.handler"]                                  │   │
│  │  - Direct handler invocation (no wrapper)              │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 How It Works: Step-by-Step

### 1. **Dockerfile: Multi-stage Build**
```dockerfile
FROM coralogixrepo/coralogix-python-wrapper-and-exporter:27 as coralogix
FROM public.ecr.aws/lambda/python:3.11

# Copy Coralogix components to /opt (for compatibility, but we don't use the wrapper)
COPY --from=coralogix /opt/ /opt/

# Install pure OpenTelemetry packages
RUN pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc ...

# Direct handler (no wrapper)
CMD ["app.handler"]
```

**Key Points:**
- Uses Coralogix base image for consistency, but **doesn't set `AWS_LAMBDA_EXEC_WRAPPER`**
- Installs pure OpenTelemetry packages from PyPI
- Direct handler invocation (no auto-instrumentation wrapper)

### 2. **app.py: Manual SDK Initialization** (Lines 12-77)
```python
# Import OpenTelemetry SDK components
from opentelemetry import trace, propagate
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Create resource with Lambda-specific attributes
resource = Resource.create({
    SERVICE_NAME: "onboarding-lambda",
    "cx.application.name": "onboarding",
    "cx.subsystem.name": "lambda",
    "faas.name": os.getenv("AWS_LAMBDA_FUNCTION_NAME"),
    "faas.version": os.getenv("AWS_LAMBDA_FUNCTION_VERSION"),
    "faas.runtime": "python3.11",
    "faas.architecture": "arm64",
    "cloud.provider": "aws",
    "cloud.platform": "aws_lambda",
})

# Initialize TracerProvider
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

# Configure OTLP gRPC exporter (direct to Coralogix)
otlp = OTLPSpanExporter(
    endpoint="ingress.us2.coralogix.com:443",
    headers=(("authorization", f"Bearer {API_KEY}"),),
    credentials=ssl_channel_credentials(),
)
provider.add_span_processor(BatchSpanProcessor(otlp))

# Force flush on exit
atexit.register(lambda: provider.force_flush(timeout_millis=4000))
```

**Key Points:**
- **Explicit SDK initialization** at module load (cold start)
- **Programmatic OTLP exporter config** (not via ENV vars)
- **Resource attributes** include `faas.*` for serverless dashboard
- **Force flush** ensures spans are sent before Lambda container freezes

### 3. **handler(): Manual Span Creation** (Lines 91-194)
```python
def handler(event, context):
    # Extract parent context from SQS message attributes
    parent_ctx = propagate.extract(_carrier_from_sqs_attributes(record["messageAttributes"]))
    
    # Create top-level Lambda SERVER span (for serverless dashboard)
    with tracer.start_as_current_span("lambda.invoke", context=parent_ctx, kind=SpanKind.SERVER) as lambda_span:
        
        # Per-record CONSUMER span (unifies with ECS trace)
        for record in event["Records"]:
            ctx = propagate.extract(_carrier_from_sqs_attributes(record["messageAttributes"]))
            
            with tracer.start_as_current_span("sqs.process", context=ctx, kind=SpanKind.CONSUMER) as span:
                span.set_attribute("messaging.system", "aws.sqs")
                span.set_attribute("customer.id", body["customer_id"])
                # ... business logic ...
        
        # Batch KPI span with links (for batch metrics)
        with tracer.start_as_current_span("sqs.batch", links=links, kind=SpanKind.CONSUMER) as batch_span:
            batch_span.set_attribute("messaging.batch_size", len(records))
    
    # Force flush before return
    trace.get_tracer_provider().force_flush(timeout_millis=4000)
```

**Key Points:**
- **Manual context extraction** from SQS message attributes
- **Three span types:**
  1. `lambda.invoke` (SERVER) - Root span for serverless dashboard
  2. `sqs.process` (CONSUMER) - Per-message span, links to ECS trace
  3. `sqs.batch` (CONSUMER) - Batch KPI span with links
- **Explicit flush** before returning (critical for Lambda)

---

## 🆚 Comparison: Manual vs Automatic

| Feature | Manual (This Repo) | Automatic (Lambda Layer) |
|---------|-------------------|-------------------------|
| **Works with Container Images** | ✅ Yes | ❌ No (layers don't work) |
| **Control over Spans** | ✅ Full control | ⚠️ Limited |
| **Custom Batch Processing** | ✅ Yes (3 span types) | ❌ No |
| **Distributed Tracing** | ✅ Explicit W3C propagation | ⚠️ Auto X-Ray only |
| **Vendor Lock-in** | ✅ None (pure OTel) | ⚠️ AWS X-Ray preferred |
| **Setup Complexity** | ⚠️ More code | ✅ Just add layer ARN |
| **Debugging** | ✅ Full visibility | ⚠️ Black box |
| **Force Flush** | ✅ Explicit control | ⚠️ Auto (may lose spans) |

---

## 🎯 Key Decisions & Why

### Decision 1: Use Coralogix Base Image but Not the Wrapper
**Why?**
- Provides OTel libraries in `/opt` for consistency
- No need to install from scratch
- BUT we don't use `AWS_LAMBDA_EXEC_WRAPPER` (no auto-instrumentation)
- Gives us full control over SDK initialization

### Decision 2: Manual Span Creation (Not Auto-instrumentation)
**Why?**
- **SQS batch processing** requires custom logic:
  - Extract parent context from each message
  - Create per-message spans (unified trace)
  - Create batch span with links (for KPIs)
- **Auto-instrumentation** can't handle this complex scenario
- Allows **rich business attributes** (`customer.id`, etc.)

### Decision 3: OTLP gRPC (Not Coralogix Wrapper Export)
**Why?**
- **Vendor-agnostic**: Can switch to any OTLP backend
- **Direct to Coralogix**: No intermediate collector in Lambda
- **Explicit auth**: Programmatic `authorization` header
- **Production-ready**: TLS, timeout, retry built-in

### Decision 4: Force Flush Before Return
**Why?**
- Lambda container **freezes after handler returns**
- **Async export** may not complete before freeze
- **Explicit flush** ensures spans are sent
- 4-second timeout prevents hanging

---

## 📦 What Gets Instrumented?

### Automatic (via SDK initialization):
- ❌ **Nothing** - No auto-instrumentation in this approach
- (We don't use boto3 instrumentor, requests instrumentor, etc.)

### Manual (explicit span creation):
1. **Lambda invocation** (`lambda.invoke` span)
   - Captures function name, version, request ID
   - Root span for serverless dashboard
2. **SQS message processing** (`sqs.process` spans)
   - Per-message spans with parent context
   - Links to upstream ECS trace
3. **Batch processing** (`sqs.batch` span)
   - Batch-level KPIs
   - Span links for analytics
4. **Cold start** (`cold_start_canary` span)
   - Emitted once per container init
   - Easy trace ID for debugging

### Not Instrumented (but could be):
- ❌ Boto3 calls (DynamoDB, S3, etc.)
- ❌ HTTP requests
- ❌ Database queries
- ❌ Third-party libraries

**To add auto-instrumentation:**
```python
# In app.py, after SDK init:
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

BotocoreInstrumentor().instrument()
RequestsInstrumentor().instrument()
```

---

## 🔧 Configuration

### Environment Variables (Lambda Function Config):
```bash
# OpenTelemetry
OTEL_PROPAGATORS=tracecontext,baggage,xray
OTEL_TRACES_SAMPLER=parentbased_always_on

# Coralogix
CORALOGIX_API_KEY=cxtp_...           # Send-Your-Data key
CORALOGIX_OTLP_ENDPOINT=ingress.us2.coralogix.com:443
SERVICE_NAME=onboarding-lambda
CX_APPLICATION=onboarding
CX_SUBSYSTEM=lambda

# Logging
LOG_LEVEL=INFO
```

**Key Points:**
- **No `AWS_LAMBDA_EXEC_WRAPPER`** - We're not using a wrapper
- **No `CX_DOMAIN` or `CX_REPORTING_STRATEGY`** - Not using Coralogix wrapper
- **OTLP endpoint** is host:port (gRPC, not HTTP)
- **Authorization** header set programmatically in code

### Dockerfile ENV (defaults):
```dockerfile
ENV OTEL_PROPAGATORS=tracecontext,baggage,xray
ENV OTEL_RESOURCE_ATTRIBUTES="service.namespace=onboarding,service.name=onboarding-lambda"
```

---

## 🚀 Deployment Flow

```
1. Build Image
   └─> docker build --platform linux/arm64 -t $REPO:$TAG .

2. Push to ECR
   └─> docker push $REPO:$TAG

3. Update Lambda Function
   └─> aws lambda update-function-code --image-uri $REPO@$DIGEST

4. Wait for Update
   └─> aws lambda wait function-updated

5. Invoke Lambda
   └─> ECS sends message to SQS → Lambda processes
   
6. Verify Traces
   └─> Coralogix APM → Filter by service.name:onboarding-lambda
```

---

## ✅ Benefits of This Approach

1. **Works with Lambda Container Images**
   - No dependency on Lambda Layers
   - Full container flexibility

2. **Vendor-Agnostic**
   - Pure OpenTelemetry SDK
   - Can switch from Coralogix to any OTLP backend

3. **Full Control**
   - Custom span creation for complex scenarios
   - Rich business attributes
   - Explicit flush timing

4. **Production-Ready**
   - Proper error handling
   - Force flush ensures data export
   - TLS and authentication built-in

5. **Distributed Tracing**
   - W3C TraceContext propagation
   - Unified traces across ECS → SQS → Lambda
   - Parent-child relationships work correctly

6. **Observable**
   - Console exporter mirrors spans to CloudWatch
   - Cold start canary for debugging
   - DEBUG logs show extraction/export

---

## ⚠️ Trade-offs

### Pros:
- ✅ Full control over instrumentation
- ✅ Works with container images
- ✅ Vendor-agnostic
- ✅ Custom span logic

### Cons:
- ❌ More code to write/maintain
- ❌ No auto-instrumentation of libraries (boto3, requests, etc.)
- ❌ Must manually add spans for each operation
- ❌ Requires OTel knowledge

---

## 🎓 When to Use Manual vs Automatic

### Use Manual Instrumentation When:
- ✅ Using Lambda **container images**
- ✅ Need **custom span logic** (batch processing, etc.)
- ✅ Want **vendor-agnostic** OpenTelemetry
- ✅ Require **rich business attributes**
- ✅ Need **full control** over flush timing

### Use Automatic Instrumentation When:
- ✅ Using Lambda **ZIP deployments** (can use layers)
- ✅ Simple use case (single request in, single response out)
- ✅ Just need basic tracing (no custom spans)
- ✅ Okay with AWS X-Ray integration
- ✅ Want minimal code changes

---

## 📚 Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `onboarding-lambda/app.py` | Manual OTel SDK init + handler | 195 |
| `onboarding-lambda/Dockerfile` | Container image build | 26 |
| `onboarding-lambda/requirements.txt` | Pure OTel packages | 6 |

---

## 🔍 Verification

### Check Manual Instrumentation:
```bash
# 1. Look for manual SDK init in code
grep -A 5 "TracerProvider" onboarding-lambda/app.py

# 2. Verify no wrapper in CMD
docker inspect $IMAGE | jq '.[0].Config.Cmd'
# Should show: ["app.handler"] (not otel wrapper)

# 3. Check Lambda config has no wrapper
aws lambda get-function-configuration --function-name cal-onboarding-lambda-arm64 \
  | jq -r '.Environment.Variables.AWS_LAMBDA_EXEC_WRAPPER // "NONE"'
# Should show: NONE

# 4. Verify traces in Coralogix
# → Filter by service.name:onboarding-lambda
# → Should see lambda.invoke, sqs.process, sqs.batch spans
```

---

## 🎯 Summary

**This Lambda is MANUALLY instrumented** using the pure OpenTelemetry SDK because:

1. **Container images can't use Lambda Layers**
2. **Custom span logic needed** for SQS batch processing
3. **Vendor-agnostic approach** (pure OTel, not Coralogix wrapper)
4. **Full control** over span creation and flush timing

The result is a **production-ready, vendor-agnostic** implementation that:
- ✅ Works with Lambda container images
- ✅ Creates unified distributed traces (ECS → SQS → Lambda)
- ✅ Populates Coralogix APM with rich data
- ✅ Can be easily adapted for any OTLP backend

