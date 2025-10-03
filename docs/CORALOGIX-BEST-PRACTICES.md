# Coralogix Best Practices & Configuration Guide
## Enhanced Customer Onboarding Demo

This guide provides comprehensive Coralogix configuration recommendations and best practices for the enhanced customer onboarding service, demonstrating production-ready observability patterns.

## 🎯 Overview

The enhanced customer onboarding service demonstrates:
- **Distributed Tracing**: ECS Fargate → Lambda → AWS Services
- **Business Metrics**: Custom metrics for onboarding success rates, processing times
- **Structured Logging**: Correlated logs with trace context
- **Service Maps**: Visual representation of service dependencies
- **Alerting**: Business-critical failure detection

## 📊 Service Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   ECS Fargate       │    │   AWS Lambda        │    │   AWS Services      │
│                     │    │                     │    │                     │
│  ┌─────────────────┐│    │  ┌─────────────────┐│    │  ┌─────────────────┐│
│  │ Enhanced API    ││───▶│  │ Enhanced        ││───▶│  │ DynamoDB        ││
│  │ • Validation    ││    │  │ Processing      ││    │  │ S3              ││
│  │ • Enrichment    ││    │  │ • Compliance    ││    │  │ SES             ││
│  │ • Orchestration ││    │  │ • Audit         ││    │  │ SSM             ││
│  └─────────────────┘│    │  │ • Workflows     ││    │  └─────────────────┘│
│                     │    │  └─────────────────┘│    │                     │
│  ┌─────────────────┐│    │                     │    │                     │
│  │ OTel Collector  ││    │  ┌─────────────────┐│    │                     │
│  │ (Sidecar)       ││    │  │ OTel Extension  ││    │                     │
│  └─────────────────┘│    │  └─────────────────┘│    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
                        ┌─────────────────────┐
                        │   Coralogix         │
                        │   (US2)             │
                        │                     │
                        │  • Traces           │
                        │  • Metrics          │
                        │  • Logs             │
                        │  • Service Maps     │
                        │  • Dashboards       │
                        │  • Alerts           │
                        └─────────────────────┘
```

## 🔧 OpenTelemetry Collector Configuration

### Production Collector Configuration (`production-collector.yaml`)

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
    send_batch_max_size: 2048
  
  # Add consistent resource attributes
  resource:
    attributes:
      - key: service.namespace
        action: insert
        value: customer-onboarding
      - key: deployment.environment  
        action: insert
        value: production
      - key: business.domain
        action: insert
        value: customer-management
        
  # Generate span metrics for service maps and APM
  spanmetrics:
    metrics_exporter: coralogix
    latency_histogram_buckets: [2ms, 4ms, 6ms, 8ms, 10ms, 50ms, 100ms, 200ms, 400ms, 800ms, 1s, 1400ms, 2s, 5s, 10s, 15s]
    dimensions:
      - name: http.method
        default: GET
      - name: http.status_code
      - name: service.version
      - name: customer.type
      - name: business.operation
    dimensions_cache_size: 10000

  # Memory limiter to prevent OOM
  memory_limiter:
    limit_mib: 512
    spike_limit_mib: 128
    check_interval: 5s

extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  pprof:
    endpoint: 0.0.0.0:1777

exporters:
  coralogix:
    domain: "us2.coralogix.com"
    private_key: "${CORALOGIX_PRIVATE_KEY}"
    
    # Application mapping for Coralogix
    application_name: "customer-onboarding"
    application_name_attributes: ["service.namespace"]
    subsystem_name_attributes: ["service.name"]
    
    # Production optimizations
    timeout: 30s
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s
    sending_queue:
      enabled: true
      num_consumers: 10
      queue_size: 5000

service:
  extensions: [health_check, pprof]
  
  telemetry:
    logs:
      level: "info"
    metrics:
      address: 0.0.0.0:8888
      
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch, resource, spanmetrics]
      exporters: [coralogix]
      
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch, resource]
      exporters: [coralogix]
      
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch, resource]
      exporters: [coralogix]
```

## 📈 Key Metrics to Monitor

### Business Metrics

1. **Onboarding Success Rate**
   ```
   sum(rate(onboarding_success_total[5m])) / sum(rate(onboarding_requests_total[5m]))
   ```

2. **Processing Duration by Customer Type**
   ```
   histogram_quantile(0.95, rate(onboarding_duration_seconds_bucket[5m]))
   ```

3. **Lambda Processing Success Rate**
   ```
   sum(rate(lambda_processing_success_total[5m])) / sum(rate(lambda_processing_requests_total[5m]))
   ```

### Technical Metrics

1. **HTTP Error Rate**
   ```
   sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
   ```

2. **Service Latency (P95)**
   ```
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
   ```

3. **Lambda Cold Start Rate**
   ```
   sum(rate(aws_lambda_init_duration_total[5m])) / sum(rate(aws_lambda_invocations_total[5m]))
   ```

## 🚨 Recommended Alerts

### Critical Business Alerts

1. **High Onboarding Failure Rate**
   ```yaml
   alert: OnboardingFailureRateHigh
   expr: |
     (
       sum(rate(onboarding_requests_total[5m])) - sum(rate(onboarding_success_total[5m]))
     ) / sum(rate(onboarding_requests_total[5m])) > 0.1
   for: 2m
   severity: critical
   description: "Onboarding failure rate is above 10% for 2 minutes"
   ```

2. **Compliance Check Failures**
   ```yaml
   alert: ComplianceCheckFailures
   expr: |
     sum(rate(compliance_checks_failed_total[5m])) > 0
   for: 1m
   severity: high
   description: "Compliance checks are failing"
   ```

3. **Customer Processing Delays**
   ```yaml
   alert: ProcessingDelayHigh
   expr: |
     histogram_quantile(0.95, rate(onboarding_duration_seconds_bucket[5m])) > 30
   for: 5m
   severity: warning
   description: "95th percentile processing time exceeds 30 seconds"
   ```

### Technical Alerts

1. **Service Unavailability**
   ```yaml
   alert: ServiceDown
   expr: |
     up{service_name="onboarding-api"} == 0
   for: 1m
   severity: critical
   description: "Onboarding API service is down"
   ```

2. **High Error Rate**
   ```yaml
   alert: HighErrorRate
   expr: |
     sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
   for: 3m
   severity: high
   description: "HTTP 5xx error rate is above 5%"
   ```

## 📊 Dashboard Configuration

### Executive Dashboard

**Key Performance Indicators:**
- Customer onboarding success rate (last 24h)
- Average processing time by customer type
- Total customers onboarded (daily/weekly/monthly)
- Service availability percentage

### Operations Dashboard

**Service Health:**
- Request rate and latency percentiles
- Error rate by service and endpoint
- Service dependencies and health status
- Resource utilization (CPU, memory, Lambda duration)

### Business Dashboard

**Customer Insights:**
- Onboarding funnel conversion rates
- Customer type distribution
- Processing time trends by customer type
- Compliance check success rates
- Geographic distribution (if available)

## 🔍 Log Parsing and Enrichment

### Structured Log Parsing Rules

1. **API Request Logs**
   ```json
   {
     "timestamp": "2025-10-02T10:30:00Z",
     "level": "INFO",
     "service": "onboarding-api",
     "request_id": "req-12345",
     "customer_id": "cust-67890",
     "customer_type": "premium",
     "endpoint": "/onboard",
     "processing_time_ms": 1250,
     "success_score": 0.95,
     "trace_id": "abc123...",
     "span_id": "def456..."
   }
   ```

2. **Lambda Processing Logs**
   ```json
   {
     "timestamp": "2025-10-02T10:30:01Z",
     "level": "INFO",
     "service": "onboarding-lambda",
     "lambda_request_id": "lambda-12345",
     "request_id": "req-12345",
     "customer_id": "cust-67890",
     "compliance_passed": true,
     "risk_level": "low",
     "processing_time_ms": 2100,
     "trace_id": "abc123...",
     "span_id": "ghi789..."
   }
   ```

### Log Parsing Configuration

```json
{
  "rules": [
    {
      "name": "onboarding_api_structured",
      "pattern": "service=onboarding-api",
      "fields": {
        "request_id": "string",
        "customer_id": "string", 
        "customer_type": "string",
        "processing_time_ms": "number",
        "success_score": "number",
        "endpoint": "string"
      }
    },
    {
      "name": "lambda_processing_structured", 
      "pattern": "service=onboarding-lambda",
      "fields": {
        "lambda_request_id": "string",
        "request_id": "string",
        "customer_id": "string",
        "compliance_passed": "boolean",
        "risk_level": "string",
        "processing_time_ms": "number"
      }
    }
  ]
}
```

## 🎛️ Service Map Configuration

### Expected Service Dependencies

```
onboarding-api (ECS)
├── onboarding-lambda (Lambda)
│   ├── DynamoDB (customer-onboarding-demo)
│   ├── DynamoDB (customer-onboarding-audit)
│   ├── S3 (customer-onboarding-data-bucket)
│   ├── SES (notifications)
│   └── SSM (configuration)
├── SQS (customer-onboarding-queue)
└── SNS (welcome-notifications)
```

### Service Map Attributes

Ensure these attributes are present for proper service mapping:
- `service.name`: Service identifier
- `service.version`: Service version
- `service.namespace`: Business domain
- `db.system`: Database type (dynamodb, s3, etc.)
- `messaging.system`: Messaging system (sqs, sns)
- `faas.name`: Lambda function name

## 🔐 Security and Compliance

### Data Privacy

1. **PII Masking**: Ensure customer emails and sensitive data are masked in logs
2. **Trace Sampling**: Use appropriate sampling rates to balance observability and privacy
3. **Data Retention**: Configure appropriate retention policies for different data types

### Compliance Monitoring

1. **Audit Trail**: All compliance checks are logged and traceable
2. **Data Lineage**: Customer data flow is fully observable
3. **Access Logging**: All API access is logged with proper attribution

## 🚀 Deployment Best Practices

### Environment-Specific Configuration

1. **Development**: Higher sampling rates, debug logging
2. **Staging**: Production-like configuration with test data
3. **Production**: Optimized for performance and cost

### Resource Allocation

1. **ECS Task**: 512 CPU, 1024 MB memory
2. **Lambda**: 512 MB memory, 30s timeout
3. **Collector**: 256 MB memory limit, appropriate batch sizes

### Monitoring the Monitoring

1. **Collector Health**: Monitor collector metrics and logs
2. **Data Freshness**: Alert on data ingestion delays
3. **Cost Monitoring**: Track ingestion costs and optimize sampling

## 📚 Troubleshooting Guide

### Common Issues

1. **Missing Traces**: Check OTLP endpoint configuration
2. **High Latency**: Review batch processor settings
3. **Missing Service Maps**: Verify span attributes and relationships
4. **Data Gaps**: Check collector health and network connectivity

### Debug Commands

```bash
# Check collector health
curl http://localhost:13133/

# View collector metrics
curl http://localhost:8888/metrics

# Test OTLP endpoint
curl -X POST http://localhost:4318/v1/traces -H "Content-Type: application/json" -d '{}'
```

## 🎯 Success Metrics

After implementing this configuration, you should see:

1. **Complete Service Maps**: All services and dependencies visible
2. **Business Dashboards**: KPIs and business metrics trending
3. **Effective Alerting**: Proactive issue detection
4. **Trace Correlation**: Logs and traces properly correlated
5. **Performance Insights**: Bottlenecks and optimization opportunities identified

## 📞 Support and Resources

- **Coralogix Documentation**: https://coralogix.com/docs/
- **OpenTelemetry Documentation**: https://opentelemetry.io/docs/
- **AWS ADOT Documentation**: https://aws-otel.github.io/docs/
- **Demo Repository**: This enhanced customer onboarding service

---

*This configuration guide demonstrates production-ready observability patterns for modern microservices architectures using Coralogix and OpenTelemetry.*
