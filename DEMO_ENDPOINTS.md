# Demo Endpoints - Quick Reference

## 🎯 **Two Endpoints for Different Demos**

---

## 1️⃣ **Simple E2E Trace** - `/telemetry/smoke`

**Use Case:** Fast, minimal trace to demonstrate distributed tracing

**What It Does:**
- Simple POST → SQS → Lambda flow
- 3 spans: `smoke_root` → `sqs.send` → `sqs.process`
- Perfect for showing **W3C context propagation**

**Example Request:**
```bash
curl -X POST http://<ECS_IP>:8000/telemetry/smoke \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"DEMO-1"}'
```

**Response:**
```json
{
  "customer_id": "DEMO-1",
  "request_id": "uuid",
  "status": "queued"
}
```

**Trace Structure:**
```
POST /telemetry/smoke (8ms)
  └─ sqs.send (7ms)
       └─ SQS.SendMessage (7ms)
            └─ [Lambda] sqs.process (0.1ms)
```

**Best For:**
- ✅ Quick distributed tracing demo
- ✅ Showing service map connectivity
- ✅ Validating W3C propagation
- ✅ Testing instrumentation setup

---

## 2️⃣ **Rich Business Workflow** - `/onboard`

**Use Case:** Complex, realistic business logic with multiple service integrations

**What It Does:**
- **8-10 spans** per request with realistic business logic
- Integrates: DynamoDB, Lambda, SQS, SNS
- Demonstrates: Validation, async processing, notifications
- Shows **production-like traces** with timing and dependencies

**Example Request:**
```bash
curl -X POST http://<ECS_IP>:8000/onboard \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": "CUST-001",
    "email": "demo@company.com",
    "company_size": "medium",
    "name": "Demo Corporation"
  }'
```

**Response:**
```json
{
  "status": "success",
  "customer_id": "CUST-001",
  "request_id": "uuid",
  "customer_type": "standard",
  "existing_customer": false,
  "operations": {
    "validation": "completed",
    "record_creation": "completed",
    "async_processing": "triggered",
    "queue_processing": "queued",
    "notification": "sent"
  },
  "success_score": 1.0,
  "processing_time_ms": 990.5,
  "timestamp": "2025-10-06T15:57:39Z"
}
```

**Trace Structure:**
```
POST /onboard (990ms)
  └─ customer_onboarding_workflow (980ms)
       ├─ validate_customer_request (5ms)
       ├─ check_existing_customer (45ms)
       │    └─ DynamoDB.Query (40ms)
       ├─ perform_customer_checks (3ms)
       ├─ create_customer_record (120ms)
       │    └─ DynamoDB.PutItem (115ms)
       ├─ trigger_async_processing (250ms)
       │    └─ Lambda.Invoke (245ms)
       ├─ queue_for_processing (180ms)
       │    └─ sqs.send (PRODUCER) (175ms)
       │         └─ SQS.SendMessage (170ms)
       │              └─ [Lambda] sqs.process (CONSUMER) (0.5ms)
       └─ send_welcome_notification (350ms)
            └─ SNS.Publish (345ms)
```

**Span Details:**

| Span Name | Purpose | Attributes |
|-----------|---------|------------|
| `validate_customer_request` | Input validation | `customer.id`, `validation.result` |
| `check_existing_customer` | DynamoDB lookup | `aws.dynamodb.table`, `existing_customer` |
| `perform_customer_checks` | Business rules | `customer.type`, `risk_level` |
| `create_customer_record` | DynamoDB write | `record_id`, `operation` |
| `trigger_async_processing` | Lambda invoke | `lambda.function`, `invocation_type` |
| `queue_for_processing` | SQS producer | `messaging.system`, `messaging.destination` |
| `send_welcome_notification` | SNS publish | `sns.topic`, `message_id` |

**Best For:**
- ✅ Demonstrating APM capabilities
- ✅ Showing realistic microservices patterns
- ✅ Performance analysis (where time is spent)
- ✅ Error handling and retries
- ✅ Business workflow visualization
- ✅ Customer presentations

---

## 🎬 **Demo Scenarios**

### **Scenario 1: Quick Distributed Tracing Demo** (5 minutes)
```bash
# Generate 10 simple traces
for i in {1..10}; do
  curl -X POST http://<ECS_IP>:8000/telemetry/smoke \
    -H 'Content-Type: application/json' \
    -d "{\"customer_id\":\"DEMO-$i\"}"
  sleep 1
done
```

**Show in Coralogix:**
- Service Map: `onboarding-api` → `SQS` → `onboarding-lambda`
- Trace Explorer: Filter by `service.name:("onboarding-api" OR "onboarding-lambda")`
- APM Dashboard: RED metrics for both services

---

### **Scenario 2: Rich Business Workflow Demo** (10 minutes)
```bash
# Generate 5 complex traces with realistic data
curl -X POST http://<ECS_IP>:8000/onboard -H 'Content-Type: application/json' -d '{
  "customer_id": "ACME-CORP",
  "email": "contact@acme.com",
  "company_size": "large",
  "name": "Acme Corporation"
}'

curl -X POST http://<ECS_IP>:8000/onboard -H 'Content-Type: application/json' -d '{
  "customer_id": "STARTUP-XYZ",
  "email": "hello@startup.io",
  "company_size": "small",
  "name": "Startup XYZ"
}'

# Try a duplicate (existing customer)
curl -X POST http://<ECS_IP>:8000/onboard -H 'Content-Type: application/json' -d '{
  "customer_id": "ACME-CORP",
  "email": "contact@acme.com",
  "company_size": "large",
  "name": "Acme Corporation"
}'
```

**Show in Coralogix:**
- **Trace Waterfall**: Show parallel operations (DynamoDB + Lambda + SNS)
- **Span Attributes**: Business context (`customer.type`, `company_size`)
- **Performance Analysis**: Which operations take longest?
- **Service Dependencies**: 4 AWS services integrated
- **Error Handling**: Duplicate customer scenario

---

### **Scenario 3: Mixed Traffic (Realistic Production)** (15 minutes)
```bash
# Mix of both endpoints to show versatility
while true; do
  # 70% rich workflow
  if [ $((RANDOM % 10)) -lt 7 ]; then
    curl -s -X POST http://<ECS_IP>:8000/onboard \
      -H 'Content-Type: application/json' \
      -d "{\"customer_id\":\"CUST-$RANDOM\",\"email\":\"user$RANDOM@demo.com\",\"company_size\":\"medium\",\"name\":\"Customer $RANDOM\"}"
  else
    # 30% simple smoke tests
    curl -s -X POST http://<ECS_IP>:8000/telemetry/smoke \
      -H 'Content-Type: application/json' \
      -d "{\"customer_id\":\"SMOKE-$RANDOM\"}"
  fi
  sleep 2
done
```

**Show in Coralogix:**
- **APM Dashboard**: Mix of simple and complex operations
- **Span Metrics**: Accurate percentiles across different patterns
- **Service Map**: Same flow, different complexity
- **Custom Dashboards**: Business metrics (success score, customer types)

---

## 📊 **Coralogix Queries**

### **View All Traces**
```
service.name:("onboarding-api" OR "onboarding-lambda")
```

### **Only Rich Workflows**
```
http.route:"/onboard"
```

### **Only Simple Traces**
```
http.route:"/telemetry/smoke"
```

### **Slow Requests (>500ms)**
```
service.name:"onboarding-api" AND duration.ms > 500
```

### **Failed Operations**
```
status.code:"ERROR" AND service.name:"onboarding-api"
```

### **Specific Customer**
```
customer.id:"ACME-CORP"
```

### **By Request ID**
```
business.request_id:"<UUID>"
```

---

## 🎓 **What Each Endpoint Teaches**

### **`/telemetry/smoke`**
**Technical Concepts:**
- ✅ W3C TraceContext propagation
- ✅ SpanKind.PRODUCER / CONSUMER
- ✅ Message queue instrumentation
- ✅ Context extraction in Lambda
- ✅ Synchronous vs asynchronous tracing

**Use When:**
- Teaching distributed tracing basics
- Debugging instrumentation
- Validating integration
- Performance testing (low overhead)

---

### **`/onboard`**
**Business Concepts:**
- ✅ Multi-step workflows
- ✅ Service orchestration patterns
- ✅ Performance bottleneck analysis
- ✅ Error handling strategies
- ✅ Business metrics vs technical metrics

**Use When:**
- Customer presentations
- Demonstrating APM value
- Showing real-world complexity
- Performance optimization discussions
- Business impact analysis

---

## 🚀 **Current ECS IP**

```bash
ECS_IP="54.202.16.47"
```

**Update this if ECS task restarts!**

Check current IP:
```bash
aws ecs describe-tasks --cluster cal-onboarding-cluster \
  --tasks $(aws ecs list-tasks --cluster cal-onboarding-cluster \
    --service-name cal-onboarding-api --region us-west-2 \
    --profile FullAdminAccess-104013952213 --query 'taskArns[0]' --output text) \
  --region us-west-2 --profile FullAdminAccess-104013952213 \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text \
  | xargs -I {} aws ec2 describe-network-interfaces --network-interface-ids {} \
  --region us-west-2 --profile FullAdminAccess-104013952213 \
  --query 'NetworkInterfaces[0].Association.PublicIp' --output text
```

---

**💡 Pro Tip:** Use the **simple endpoint** to verify everything works, then switch to the **rich endpoint** for impressive demos!

