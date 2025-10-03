# Enhanced Customer Onboarding Service - OpenTelemetry Demo

A comprehensive, production-ready demonstration of OpenTelemetry instrumentation for ECS Fargate + Lambda containerized applications, designed to showcase best practices for Coralogix integration and customer onboarding workflows.

## 🎯 Overview

This enhanced demo replicates a realistic customer onboarding service architecture, demonstrating:

- **Comprehensive Distributed Tracing**: End-to-end visibility across ECS Fargate → Lambda → AWS Services
- **Business Metrics & KPIs**: Custom metrics for onboarding success rates, processing times, and business insights
- **Structured Logging**: Correlated logs with trace context for debugging and analysis
- **Service Maps**: Visual representation of service dependencies and health
- **Production-Ready Observability**: Realistic error rates, retry logic, and failure scenarios

## 🏗️ Enhanced Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Enhanced Customer Onboarding Service                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   ECS Fargate       │    │   AWS Lambda        │    │   AWS Services      │
│                     │    │                     │    │                     │
│  ┌─────────────────┐│    │  ┌─────────────────┐│    │  ┌─────────────────┐│
│  │ Enhanced API    ││───▶│  │ Enhanced        ││───▶│  │ DynamoDB        ││
│  │ • Validation    ││    │  │ Processing      ││    │  │ • Customers     ││
│  │ • Enrichment    ││    │  │ • Compliance    ││    │  │ • Audit Trail   ││
│  │ • Orchestration ││    │  │ • Audit Trails  ││    │  │                 ││
│  │ • Business Logic││    │  │ • Data Storage  ││    │  │ S3              ││
│  └─────────────────┘│    │  │ • Notifications ││    │  │ • Documents     ││
│                     │    │  │ • Workflows     ││    │  │ • Data Lake     ││
│  ┌─────────────────┐│    │  └─────────────────┘│    │  │                 ││
│  │ OTel Collector  ││    │                     │    │  │ SES / SNS       ││
│  │ (Sidecar)       ││    │  ┌─────────────────┐│    │  │ • Notifications ││
│  │ • Span Metrics  ││    │  │ Coralogix       ││    │  │                 ││
│  │ • Batch Export  ││    │  │ Extension       ││    │  │ SSM             ││
│  └─────────────────┘│    │  └─────────────────┘│    │  │ • Configuration ││
└─────────────────────┘    └─────────────────────┘    │  └─────────────────┘│
         │                           │                │                     │
         └───────────────────────────┼────────────────│  ┌─────────────────┐│
                                     │                │  │ SQS             ││
                        ┌─────────────────────┐       │  │ • Workflows     ││
                        │   Coralogix         │       │  └─────────────────┘│
                        │   (US2)             │       └─────────────────────┘
                        │                     │
                        │  📊 Dashboards      │
                        │  🔍 Service Maps    │
                        │  📈 Metrics         │
                        │  📋 Traces          │
                        │  📝 Logs            │
                        │  🚨 Alerts          │
                        └─────────────────────┘
```

## ✨ Enhanced Features

### 🎯 Realistic Business Workflows

- **Multi-step Customer Validation**: Email validation, data enrichment, risk scoring
- **Compliance & Security Checks**: KYC, AML screening, sanctions checks, PEP screening
- **Audit Trail Creation**: Comprehensive audit logging for compliance
- **Data Storage & Management**: Customer documents, metadata, and data lake integration
- **Notification Systems**: Welcome emails, internal team notifications
- **Follow-up Workflows**: Customer success, compliance monitoring, education campaigns

### 📊 Advanced Observability

- **Custom Business Metrics**:
  - Onboarding success rates by customer type
  - Processing duration percentiles
  - Compliance check success rates
  - Error rates and failure patterns

- **Comprehensive Tracing**:
  - Request validation and enrichment spans
  - Database operations (DynamoDB, S3)
  - External service calls (SES, SNS, SSM)
  - Business logic spans with meaningful attributes

- **Structured Logging**:
  - Trace correlation across all services
  - Business context in every log entry
  - Error tracking with stack traces
  - Performance metrics and timing data

### 🚀 Production-Ready Patterns

- **Error Handling**: Realistic failure rates and retry logic
- **Circuit Breakers**: Service degradation patterns
- **Load Balancing**: Distributed request handling
- **Security**: Input validation, sanitization, compliance checks
- **Monitoring**: Health checks, dependency monitoring

## 🛠️ Components

### 1. Enhanced ECS Fargate API (`onboarding-api/`)

**Key Features**:
- **Flask API** with comprehensive business logic
- **OpenTelemetry Auto-instrumentation** for HTTP, AWS SDK, and custom spans
- **Business Metrics** for success rates, processing times, customer types
- **Structured Logging** with trace correlation
- **Error Simulation** for realistic failure scenarios

**Endpoints**:
- `POST /onboard` - Complete customer onboarding workflow
- `GET /health` - Health check with service status
- `GET /customers/{id}` - Customer lookup for testing

### 2. Enhanced Lambda Processing (`onboarding-lambda/`)

**Key Features**:
- **Container Image** deployment with embedded OpenTelemetry
- **Multi-step Processing**: Compliance, audit, storage, notifications
- **AWS Service Integration**: DynamoDB, S3, SES, SSM
- **Business Logic Spans** for each processing step
- **Comprehensive Error Handling** with proper observability

**Processing Steps**:
1. Customer data validation and enrichment
2. Compliance and security checks (KYC, AML, sanctions)
3. Audit trail creation
4. Document and data storage (S3)
5. Customer status updates (DynamoDB)
6. Internal team notifications (SES)
7. Follow-up workflow triggering

### 3. Production OpenTelemetry Collector

**Configuration**:
- **Span Metrics Generation** for service maps and APM
- **Batch Processing** for optimal performance
- **Resource Attribution** for proper service identification
- **Memory Management** to prevent OOM issues
- **Health Monitoring** and metrics exposure

## 🚀 Quick Start

### Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **Docker** for building container images
3. **Jenkins** for automated deployment (optional)
4. **Coralogix Account** with API key

### 1. Clone and Setup

```bash
git clone <repository-url>
cd otel-integration/customer-onboarding-demo

# Set your Coralogix API key
export CORALOGIX_PRIVATE_KEY="your-coralogix-api-key"
```

### 2. Local Development

```bash
# Start local OpenTelemetry Collector
docker run -p 4317:4317 -p 4318:4318 \
  -v $(pwd)/otel/production-collector.yaml:/etc/otelcol/config.yaml \
  otel/opentelemetry-collector-contrib:latest

# Install API dependencies
cd onboarding-api
pip install -r requirements.txt

# Run with auto-instrumentation
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_LOGS_EXPORTER=otlp
export OTEL_RESOURCE_ATTRIBUTES="service.namespace=customer-onboarding,service.name=onboarding-api,service.version=2.0.0,deployment.environment=dev"

opentelemetry-instrument --traces_exporter otlp --metrics_exporter otlp --logs_exporter otlp python app.py
```

### 3. Test the Enhanced API

```bash
# Test comprehensive onboarding workflow
curl -X POST http://localhost:8000/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "demo-customer-001",
    "email": "demo@example.com",
    "type": "premium",
    "company_name": "Demo Corp"
  }'

# Run comprehensive test suite
python test-enhanced-onboarding.py \
  --api-url http://localhost:8000 \
  --test-type demo

# Generate continuous traffic
python continuous-traffic.py \
  --api-url http://localhost:8000 \
  --pattern business_hours \
  --duration 3600
```

## 🎭 Demo Scenarios

### 1. Business Demo Suite

```bash
python test-enhanced-onboarding.py --api-url http://your-api:8000 --test-type demo
```

**Demonstrates**:
- Different customer types (standard, premium, enterprise)
- Validation error handling
- Success and failure scenarios
- Concurrent request processing

### 2. Load Testing

```bash
python test-enhanced-onboarding.py --api-url http://your-api:8000 --test-type load --requests 100
```

**Shows**:
- System performance under load
- Error rate patterns
- Resource utilization
- Service degradation handling

### 3. Continuous Traffic Generation

```bash
python continuous-traffic.py --api-url http://your-api:8000 --pattern business_hours --duration 7200
```

**Simulates**:
- Realistic business hour patterns
- Customer type distributions
- Seasonal variations
- Sustained load patterns

## 🚀 AWS Deployment

### Automated Jenkins Deployment

```bash
# Configure Jenkins pipeline with parameters:
# - OTEL_AUTOINSTRUMENT: true
# - DEPLOY_PRODUCTION: false (for staging)
# - AWS_REGION: us-west-2
# - ECR repositories and Coralogix secret ID

# Run the enhanced Jenkins pipeline
# The pipeline will:
# 1. Build and scan container images
# 2. Deploy to ECS Fargate and Lambda
# 3. Run post-deployment validation
# 4. Generate telemetry test data
```

### Manual Deployment

```bash
# Build and push images
./build-production.sh

# Deploy ECS service
aws ecs register-task-definition --cli-input-json file://ecs/taskdef.fargate.json
aws ecs update-service --cluster cal-onboarding-cluster --service cal-onboarding-api --task-definition cal-onboarding-api-demo

# Deploy Lambda function
aws lambda update-function-code --function-name cal-onboarding-lambda --image-uri your-ecr-repo/cal-onboarding-lambda:latest
```

## 📊 Coralogix Integration

### Service Maps

The enhanced setup creates comprehensive service maps showing:
- **ECS API** → **Lambda Processing** → **AWS Services**
- **Request flow** with latency and error rates
- **Dependency health** and performance metrics

### Business Dashboards

**Executive View**:
- Customer onboarding success rates
- Processing time trends by customer type
- Revenue impact metrics
- Service availability SLAs

**Operations View**:
- Request rates and latency percentiles
- Error rates by service and endpoint
- Resource utilization and scaling metrics
- Alert status and incident tracking

### Custom Metrics

```promql
# Onboarding Success Rate
sum(rate(onboarding_success_total[5m])) / sum(rate(onboarding_requests_total[5m]))

# Processing Duration by Customer Type
histogram_quantile(0.95, rate(onboarding_duration_seconds_bucket[5m]))

# Lambda Processing Success Rate
sum(rate(lambda_processing_success_total[5m])) / sum(rate(lambda_processing_requests_total[5m]))
```

### Alerting Rules

**Critical Business Alerts**:
- Onboarding failure rate > 10%
- Processing time P95 > 30 seconds
- Compliance check failures
- Service unavailability

**Technical Alerts**:
- HTTP 5xx error rate > 5%
- Lambda cold start rate > 20%
- Database connection failures
- OpenTelemetry data gaps

## 📚 Best Practices Demonstrated

### 1. OpenTelemetry Implementation
- **Semantic Conventions**: Proper attribute naming and values
- **Span Hierarchies**: Logical parent-child relationships
- **Error Handling**: Proper span status and error attributes
- **Resource Attribution**: Service identification and metadata

### 2. Observability Patterns
- **Golden Signals**: Latency, traffic, errors, saturation
- **Business Metrics**: KPIs that matter to stakeholders
- **Trace Correlation**: Logs and traces properly linked
- **Service Health**: Comprehensive health checks and monitoring

### 3. Production Readiness
- **Error Rates**: Realistic failure scenarios and handling
- **Load Patterns**: Business hour simulation and scaling
- **Security**: Input validation and compliance checks
- **Performance**: Optimized batch processing and resource usage

## 🔍 Troubleshooting

### Common Issues

1. **Missing Traces**: Check OTLP endpoint configuration and collector health
2. **High Latency**: Review batch processor settings and resource allocation
3. **Missing Service Maps**: Verify span attributes and service relationships
4. **Data Gaps**: Check collector connectivity and Coralogix ingestion

### Debug Tools

```bash
# Check collector health
curl http://localhost:13133/

# View collector metrics
curl http://localhost:8888/metrics

# Test OTLP endpoint
curl -X POST http://localhost:4318/v1/traces -H "Content-Type: application/json" -d '{}'

# Validate service endpoints
curl http://your-api:8000/health
```

## 📞 Support Resources

- **[Coralogix Best Practices Guide](./CORALOGIX-BEST-PRACTICES.md)** - Comprehensive configuration and monitoring guide
- **[OpenTelemetry Documentation](https://opentelemetry.io/docs/)** - Official OTel documentation
- **[AWS ADOT Documentation](https://aws-otel.github.io/docs/)** - AWS Distro for OpenTelemetry
- **[Coralogix Documentation](https://coralogix.com/docs/)** - Platform-specific guides

## 🎯 Success Metrics

After deploying this enhanced setup, you should observe:

1. **Complete Service Maps**: All services and dependencies visible with proper relationships
2. **Business Dashboards**: KPIs and business metrics trending accurately
3. **Effective Alerting**: Proactive issue detection and notification
4. **Trace Correlation**: Logs and traces properly correlated across services
5. **Performance Insights**: Bottlenecks and optimization opportunities identified

## 🏆 Customer Demo Value

This enhanced setup demonstrates:

- **Production-Ready Patterns**: Real-world observability implementation
- **Business Value**: Metrics that matter to stakeholders and executives
- **Scalability**: Patterns that work from startup to enterprise scale
- **Best Practices**: Industry-standard approaches to observability
- **ROI Demonstration**: Clear value proposition for observability investment

---

*This enhanced customer onboarding service showcases comprehensive observability patterns for modern microservices architectures, providing a realistic foundation for customer demonstrations and proof-of-concept implementations.*