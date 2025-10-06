# Coralogix Integration Guide

## 🎯 **What You Need in Coralogix**

### **1. Send-Your-Data API Key**
- Navigate to: **Data Flow → API Keys → Send Your Data**
- Copy your API key (starts with `cxtp_...`)
- Used in both ECS collector and Lambda function

### **2. Coralogix Domain**
- Based on your region:
  - `ingress.us2.coralogix.com:443` (US2)
  - `ingress.coralogix.com:443` (EU1)
  - `ingress.eu2.coralogix.com:443` (EU2)
  - `ingress.app.coralogix.in:443` (IN1)

---

## 📊 **Dashboards & Views**

### **APM Services Dashboard**
**What you'll see:**
- **RED Metrics** for each service:
  - **R**ate: Requests per second
  - **E**rror: Error rate percentage
  - **D**uration: Latency percentiles (p50, p95, p99)

**How to access:**
1. Navigate to: **APM → Services**
2. Select time range (last 15 minutes, 1 hour, etc.)
3. Filter by `service.name` or `cx.application.name`

**What powers it:**
- **Span Metrics Connector** in OpenTelemetry Collector
- Generates metrics from **all traces** (no sampling!)
- Updates every 15 seconds

### **Trace Explorer**
**What you'll see:**
- Complete end-to-end traces across services
- Parent-child span relationships
- Request flow: ECS → SQS → Lambda

**How to access:**
1. Navigate to: **Explore → Traces**
2. Use filters:
   ```
   service.name:("onboarding-api" OR "onboarding-lambda")
   ```
3. Click on any trace to see waterfall view

**Key features:**
- Search by trace ID, service name, duration
- View span attributes and events
- Analyze error spans

### **Service Map**
**What you'll see:**
- Visual representation of service dependencies
- `onboarding-api` → `cal-onboarding-queue` → `onboarding-lambda`
- Request rate and error rate per edge

**How to access:**
1. Navigate to: **APM → Service Map**
2. Select time range
3. Click on services or edges for details

### **Serverless Catalog**
**What you'll see:**
- Lambda function invocations count
- Average duration per invocation
- Error count and throttles
- Memory usage and cold starts

**How to access:**
1. Navigate to: **Serverless → Lambda Functions**
2. Filter by function name: `cal-onboarding-lambda`

**Requirements:**
✅ **CloudWatch Metric Streams** with `AWS/Lambda` namespace (configured!)  
✅ **Firehose delivery** to Coralogix  
⏱️  **Wait 5-10 minutes** for metrics to populate  

**What metrics are streamed:**
- `AWS/Lambda` namespace:
  - `Invocations` - Function invocation count
  - `Duration` - Execution time
  - `Errors` - Error count
  - `Throttles` - Throttle count
  - `ConcurrentExecutions` - Concurrent invocations

---

## 🔧 **Coralogix Resource Attributes**

### **Required Attributes**
These attributes must be present in your traces for proper Coralogix integration:

#### **All Services**
```yaml
service.name: "onboarding-api"           # Service identifier
service.namespace: "onboarding"          # Application namespace
cx.application.name: "onboarding"        # Coralogix application name
cx.subsystem.name: "api"                 # Coralogix subsystem name
```

#### **Lambda Functions (Additional)**
```yaml
cloud.provider: "aws"
cloud.platform: "aws_lambda"
cloud.region: "us-west-2"
faas.name: "cal-onboarding-lambda"       # Lambda function name
faas.version: "$LATEST"                  # Function version
aws.account.id: "104013952213"
```

### **Why These Matter**
- **`service.name`** - Groups traces by service in APM
- **`cx.application.name`** - Maps to Coralogix Application
- **`cx.subsystem.name`** - Maps to Coralogix Subsystem
- **`cloud.platform`** - Identifies Lambda for Serverless Catalog
- **`faas.name`** - Links traces to specific Lambda function

---

## 🚨 **Alerts & Monitoring**

### **Recommended Alerts**

#### **1. High Error Rate**
```
Alert when: error_rate > 5%
For: 5 minutes
On service: onboarding-api OR onboarding-lambda
```

#### **2. High Latency (p95)**
```
Alert when: p95_duration > 1000ms
For: 5 minutes
On service: onboarding-api
```

#### **3. Lambda Throttles**
```
Alert when: AWS/Lambda Throttles > 0
For: 1 minute
On function: cal-onboarding-lambda
```

#### **4. Trace Sampling**
```
Alert when: span_drop_rate > 10%
For: 10 minutes
On collector: otel-collector
```

### **How to Create Alerts**
1. Navigate to: **Alerts → Create Alert**
2. Select alert type: **Metric** or **Tracing**
3. Define conditions and thresholds
4. Configure notification channels (email, Slack, PagerDuty)

---

## 📈 **Span Metrics Explained**

### **What Are Span Metrics?**
Span Metrics are **metrics derived from traces** using the OpenTelemetry Span Metrics Connector. This approach provides:

✅ **100% coverage** - Metrics from all traces, not sampled  
✅ **Real-time** - Updates every 15 seconds  
✅ **No additional cost** - Generated from existing trace data  
✅ **APM golden signals** - Rate, Error, Duration automatically  

### **How It Works**
```
Traces → Collector → SpanMetrics Connector → Metrics Pipeline → Coralogix
                      ↓
                   Metrics Generated:
                   - calls_total (counter)
                   - duration (histogram)
```

### **Metrics Generated**
- **`calls_total`** - Total span count, dimensions: service, span.kind, status
- **`duration`** - Span duration histogram with configurable buckets

### **Histogram Buckets**
Our configuration uses these buckets for latency percentiles:
```yaml
buckets: [2ms, 4ms, 6ms, 8ms, 10ms, 50ms, 100ms, 200ms, 400ms, 800ms, 1s, 1400ms, 2s, 5s, 10s, 15s]
```

This enables accurate p50, p90, p95, p99 calculations.

---

## 🔍 **Troubleshooting in Coralogix**

### **No Traces Appearing**

**Check:**
1. **Archive Query** - Look for dropped spans
   ```
   Navigate to: Archive → Query
   Filter: _dataprime_dropped = true
   ```

2. **Data Flow Status**
   ```
   Navigate to: Data Flow → OTLP
   Check: Last received timestamp
   ```

3. **API Key Validity**
   ```
   Navigate to: Data Flow → API Keys
   Verify: Send-Your-Data key is active
   ```

### **Traces Not Linked (Separate Traces)**

**Check:**
1. **Trace Context Propagation**
   - Search for spans with `traceparent` attribute
   - Verify W3C format: `00-<trace-id>-<span-id>-01`

2. **Sampling Configuration**
   - Ensure `OTEL_TRACES_SAMPLER=parentbased_always_on`
   - Check collector sampling (should be disabled)

### **Missing Span Metrics**

**Check:**
1. **Collector Configuration**
   - Verify `spanmetrics` connector is enabled
   - Check metrics pipeline exports to Coralogix

2. **Metric Ingestion**
   ```
   Navigate to: Data Flow → Metrics
   Check: Last received timestamp for span metrics
   ```

### **Serverless Catalog Empty**

**Check:**
1. **CloudWatch Metric Streams**
   ```bash
   # Verify stream includes AWS/Lambda
   aws cloudwatch get-metric-stream --name <STREAM_NAME>
   ```

2. **Firehose Delivery**
   - Check Firehose metrics for delivery success
   - Verify S3 backup (if configured)

3. **Wait Time**
   - CloudWatch metrics have 5-10 minute delay
   - Check again after waiting

---

## 📚 **Additional Resources**

### **Coralogix Documentation**
- [OpenTelemetry Integration](https://coralogix.com/docs/opentelemetry/)
- [Span Metrics](https://coralogix.com/docs/span-metrics/)
- [AWS Lambda Integration](https://coralogix.com/docs/aws-lambda/)
- [CloudWatch Metric Streams](https://coralogix.com/docs/aws-cloudwatch-metrics/)

### **OpenTelemetry**
- [Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)

### **Support**
- **Coralogix Support**: support@coralogix.com
- **Community Slack**: [Join here](https://coralogix.com/community/)

---

## ✅ **Verification Checklist**

Use this checklist to verify your Coralogix integration:

### **Traces**
- [ ] Traces appear in Trace Explorer
- [ ] End-to-end traces span all services (ECS → SQS → Lambda)
- [ ] Parent-child relationships are correct
- [ ] Trace IDs match across services

### **APM Dashboard**
- [ ] Services appear in APM Services view
- [ ] RED metrics (Rate, Error, Duration) are displayed
- [ ] Metrics update in real-time (15s intervals)
- [ ] Latency histograms show p50, p95, p99

### **Service Map**
- [ ] All services are visible on the map
- [ ] Edges show request flow (API → Queue → Lambda)
- [ ] Request rates are displayed per edge
- [ ] Error rates are highlighted (if > 0%)

### **Serverless Catalog**
- [ ] Lambda function appears in catalog
- [ ] Invocation count is accurate
- [ ] Duration metrics are displayed
- [ ] Cold start metrics are available

### **Alerts**
- [ ] Sample alerts are created
- [ ] Alert conditions are tested
- [ ] Notification channels are configured
- [ ] Alert history is visible

---

**🎉 Your Coralogix integration is complete!**

If you have any issues, check the troubleshooting section or contact Coralogix support.

