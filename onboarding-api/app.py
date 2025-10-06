import os
import time
import logging
import json
import random
import uuid
from datetime import datetime, timezone
from flask import Flask, jsonify, request
import boto3
from botocore.exceptions import ClientError
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("onboarding.api")

# Initialize OpenTelemetry tracer and meter
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Define custom business metrics for APM insights
onboarding_requests_counter = meter.create_counter(
    "onboarding_api_requests_total",
    description="Total number of onboarding API requests"
)

onboarding_duration_histogram = meter.create_histogram(
    "onboarding_api_duration_seconds",
    description="Duration of onboarding API operations"
)

onboarding_success_counter = meter.create_counter(
    "onboarding_api_success_total",
    description="Total number of successful onboarding operations"
)

# Enhanced Customer onboarding API - demonstrates ECS Fargate + OpenTelemetry collector sidecar
app = Flask(__name__)

# Initialize AWS clients (auto-instrumented by OpenTelemetry)
lambda_client = boto3.client('lambda', region_name='us-west-2')
sqs = boto3.client('sqs', region_name='us-west-2')
dynamodb = boto3.client('dynamodb', region_name='us-west-2')
sns = boto3.client('sns', region_name='us-west-2')

# Configuration from environment variables
LAMBDA_FUNCTION_NAME = os.environ.get("LAMBDA_FUNCTION_NAME", "cal-onboarding-lambda")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "https://sqs.us-west-2.amazonaws.com/104013952213/cal-onboarding-queue")
CUSTOMER_TABLE_NAME = os.environ.get("CUSTOMER_TABLE_NAME", "customer-onboarding")

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_customer_request(payload, span):
    """Validate and enrich customer request data"""
    with tracer.start_as_current_span("validate_customer_request") as validation_span:
        validation_span.set_attribute("business.operation", "validate_customer_request")
        
        if not payload.get("customer_id"):
            raise ValidationError("Customer ID is required")
        
        # Enrich with defaults and processing metadata
        customer_data = {
            "customer_id": payload["customer_id"],
            "email": payload.get("email", f"{payload['customer_id']}@example.com"),
            "type": payload.get("type", "standard"),
            "company_name": payload.get("company_name", f"{payload['customer_id']} Corp"),
            "industry": payload.get("industry", "technology"),
            "region": payload.get("region", "us-west-2"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "api_request"
        }
        
        validation_span.set_attribute("customer.type", customer_data["type"])
        validation_span.set_attribute("customer.industry", customer_data["industry"])
        validation_span.set_attribute("customer.region", customer_data["region"])
        
        log.info("Customer request validated", extra={
            "customer_id": customer_data["customer_id"],
            "customer_type": customer_data["type"],
            "customer_email": customer_data["email"]
        })
        
        return customer_data

def perform_customer_validation(customer_data, request_id, span):
    """Perform comprehensive customer validation and enrichment"""
    with tracer.start_as_current_span("perform_customer_validation") as validation_span:
        validation_span.set_attribute("business.operation", "perform_customer_validation")
        validation_span.set_attribute("business.request_id", request_id)
        
        # Simulate validation processing time
        time.sleep(random.uniform(0.1, 0.3))
        
        # Add validation results
        enriched_data = customer_data.copy()
        enriched_data.update({
            "validation_score": random.uniform(0.7, 1.0),
            "risk_level": random.choice(["low", "medium", "low", "low"]),  # 75% low risk
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "validation_id": str(uuid.uuid4())
        })
        
        validation_span.set_attribute("customer.validation_score", enriched_data["validation_score"])
        validation_span.set_attribute("customer.risk_level", enriched_data["risk_level"])
        
        log.info("Customer validation completed", extra={
            "request_id": request_id,
            "customer_id": customer_data["customer_id"],
            "validation_score": enriched_data["validation_score"],
            "risk_level": enriched_data["risk_level"]
        })
        
        return enriched_data

def check_existing_customer(customer_id, request_id, span):
    """Check if customer already exists in the system"""
    with tracer.start_as_current_span("check_existing_customer") as check_span:
        check_span.set_attribute("business.operation", "check_existing_customer")
        check_span.set_attribute("business.request_id", request_id)
        check_span.set_attribute("customer.id", customer_id)
        
        try:
            # Simulate database check
            time.sleep(random.uniform(0.05, 0.15))
            
            # 20% chance customer already exists
            existing_customer = None
            if random.random() < 0.2:
                existing_customer = {
                    "customer_id": customer_id,
                    "status": "active",
                    "created_at": "2025-09-15T10:30:00Z",
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            
            check_span.set_attribute("customer.exists", existing_customer is not None)
            
            log.info("Customer existence check completed", extra={
                "request_id": request_id,
                "customer_id": customer_id,
                "customer_exists": existing_customer is not None
            })
            
            return existing_customer
            
        except Exception as e:
            check_span.set_status(Status(StatusCode.ERROR, str(e)))
            check_span.set_attribute("error", True)
            log.error("Customer existence check failed", extra={
                "request_id": request_id,
                "customer_id": customer_id,
                "error": str(e)
            })
            return None

def create_customer_record(customer_data, existing_customer, request_id, span):
    """Create or update customer record in DynamoDB"""
    with tracer.start_as_current_span("create_customer_record") as record_span:
        record_span.set_attribute("business.operation", "create_customer_record")
        record_span.set_attribute("business.request_id", request_id)
        record_span.set_attribute("customer.id", customer_data["customer_id"])
        
        try:
            # Simulate database operation
            time.sleep(random.uniform(0.1, 0.4))
            
            operation = "updated" if existing_customer else "created"
            customer_record = customer_data.copy()
            customer_record.update({
                "record_id": str(uuid.uuid4()),
                "operation": operation,
                "processing_timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            record_span.set_attribute("database.operation", operation)
            record_span.set_attribute("database.table", CUSTOMER_TABLE_NAME)
            record_span.set_attribute("customer.record_id", customer_record["record_id"])
            
            log.info("Customer record processed", extra={
                "request_id": request_id,
                "customer_id": customer_data["customer_id"],
                "operation": operation,
                "record_id": customer_record["record_id"]
            })
            
            return customer_record
            
        except Exception as e:
            record_span.set_status(Status(StatusCode.ERROR, str(e)))
            record_span.set_attribute("error", True)
            log.error("Customer record creation failed", extra={
                "request_id": request_id,
                "customer_id": customer_data["customer_id"],
                "error": str(e)
            })
            raise

def trigger_async_processing(customer_record, request_id, span):
    """Trigger asynchronous processing via Lambda"""
    with tracer.start_as_current_span("trigger_async_processing") as lambda_span:
        lambda_span.set_attribute("business.operation", "trigger_async_processing")
        lambda_span.set_attribute("business.request_id", request_id)
        lambda_span.set_attribute("aws.lambda.function_name", LAMBDA_FUNCTION_NAME)
        
        try:
            # Simulate Lambda invocation
            time.sleep(random.uniform(0.1, 0.2))
            
            # 85% success rate for Lambda invocations
            success = random.random() < 0.85
            
            if success:
                lambda_span.set_attribute("aws.lambda.invocation_result", "success")
                log.info("Lambda processing triggered", extra={
                    "request_id": request_id,
                    "customer_id": customer_record["customer_id"],
                    "lambda_function": LAMBDA_FUNCTION_NAME
                })
            else:
                lambda_span.set_status(Status(StatusCode.ERROR, "Lambda invocation failed"))
                lambda_span.set_attribute("aws.lambda.invocation_result", "failed")
                log.warning("Lambda processing failed", extra={
                    "request_id": request_id,
                    "customer_id": customer_record["customer_id"],
                    "lambda_function": LAMBDA_FUNCTION_NAME
                })
            
            return success
            
        except Exception as e:
            lambda_span.set_status(Status(StatusCode.ERROR, str(e)))
            lambda_span.set_attribute("error", True)
            log.error("Lambda invocation error", extra={
                "request_id": request_id,
                "customer_id": customer_record["customer_id"],
                "error": str(e)
            })
            return False

def queue_for_processing(customer_record, request_id, span):
    """Queue customer for additional processing with golden path W3C trace propagation"""
    with tracer.start_as_current_span("queue_for_processing") as queue_span:
        queue_span.set_attribute("business.operation", "queue_for_processing")
        queue_span.set_attribute("business.request_id", request_id)
        queue_span.set_attribute("aws.sqs.queue_url", SQS_QUEUE_URL)
        
        try:
            from opentelemetry import propagate
            from opentelemetry.trace import SpanKind
            
            # Create message body
            message_body = {
                "customer_id": customer_record["customer_id"],
                "request_id": request_id,
                "event_type": "customer_processing",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "customer_data": customer_record
            }
            
            # PRODUCER span - inject INSIDE this span so traceparent references it
            with tracer.start_as_current_span("sqs.send", kind=SpanKind.PRODUCER) as producer_span:
                producer_span.set_attribute("messaging.system", "aws.sqs")
                producer_span.set_attribute("messaging.destination.kind", "queue")
                producer_span.set_attribute("messaging.destination.name", "cal-onboarding-queue")
                producer_span.set_attribute("messaging.operation", "send")
                producer_span.set_attribute("customer.id", customer_record.get("customer_id", ""))
                producer_span.set_attribute("business.request_id", request_id)
                
                # Inject W3C context INSIDE the PRODUCER span
                carrier = {}
                propagate.inject(carrier)  # carrier now holds traceparent for THIS PRODUCER span
                
                # Log the outgoing trace context for verification
                tid = trace.get_current_span().get_span_context().trace_id
                log.info("[ECS] PRODUCER trace_id=%032x traceparent=%s", tid, carrier.get("traceparent"))
                
                # Map to SQS MessageAttributes (lowercase keys)
                msg_attrs = {
                    k: {"DataType": "String", "StringValue": v}
                    for k, v in carrier.items()
                    if k in ("traceparent", "tracestate", "baggage") and isinstance(v, str)
                }
                # Rich business attributes
                if "customer_id" in customer_record:
                    msg_attrs["customer.id"] = {"DataType": "String", "StringValue": customer_record["customer_id"]}
                
                # Send with the W3C attributes
                response = sqs.send_message(
                    QueueUrl=SQS_QUEUE_URL,
                    MessageBody=json.dumps(message_body),
                    MessageAttributes=msg_attrs
                )
                
                message_id = response.get('MessageId')
                producer_span.set_attribute("messaging.message_id", message_id)
                queue_span.set_attribute("aws.sqs.message_id", message_id)
                queue_span.set_attribute("aws.sqs.message_sent", True)
                queue_span.set_attribute("trace.propagated", True)
                
                log.info("Customer queued for processing with golden path W3C context", extra={
                    "request_id": request_id,
                    "customer_id": customer_record["customer_id"],
                    "sqs_message_id": message_id,
                    "trace_context_injected": bool(carrier),
                    "traceparent": carrier.get("traceparent")
                })
            
            return True
            
        except Exception as e:
            queue_span.set_status(Status(StatusCode.ERROR, str(e)))
            queue_span.set_attribute("aws.sqs.message_sent", False)
            queue_span.record_exception(e)
            
            log.error("Failed to queue customer for processing", extra={
                "request_id": request_id,
                "customer_id": customer_record["customer_id"],
                "error": str(e),
                "error_type": type(e).__name__
            }, exc_info=True)
            return False

def send_welcome_notification(customer_record, request_id, span):
    """Send welcome notification via SNS"""
    with tracer.start_as_current_span("send_welcome_notification") as notification_span:
        notification_span.set_attribute("business.operation", "send_welcome_notification")
        notification_span.set_attribute("business.request_id", request_id)
        
        try:
            # Simulate SNS publish
            time.sleep(random.uniform(0.1, 0.25))
            
            # 80% success rate for notifications
            success = random.random() < 0.8
            
            if success:
                notification_span.set_attribute("aws.sns.message_sent", True)
                log.info("Welcome notification sent", extra={
                    "request_id": request_id,
                    "customer_id": customer_record["customer_id"],
                    "customer_email": customer_record.get("email")
                })
            else:
                notification_span.set_status(Status(StatusCode.ERROR, "SNS publish failed"))
                notification_span.set_attribute("aws.sns.message_sent", False)
                log.warning("Welcome notification failed", extra={
                    "request_id": request_id,
                    "customer_id": customer_record["customer_id"]
                })
            
            return success
            
        except Exception as e:
            notification_span.set_status(Status(StatusCode.ERROR, str(e)))
            notification_span.set_attribute("error", True)
            log.error("Notification sending error", extra={
                "request_id": request_id,
                "customer_id": customer_record["customer_id"],
                "error": str(e)
            })
            return False

def calculate_success_score(lambda_success, queue_success, notification_sent):
    """Calculate overall success score for business metrics"""
    weights = {
        "lambda": 0.4,
        "queue": 0.4,
        "notification": 0.2
    }
    
    score = 0.0
    if lambda_success:
        score += weights["lambda"]
    if queue_success:
        score += weights["queue"]
    if notification_sent:
        score += weights["notification"]
    
    return score

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "onboarding-api",
        "version": "2.0.0",
        "timestamp": time.time()
    })

@app.route("/onboard", methods=["POST"])
def onboard():
    """
    Enhanced customer onboarding endpoint with comprehensive business logic
    
    This demonstrates:
    - Multi-step business workflow
    - Custom OpenTelemetry instrumentation
    - Realistic AWS service integrations
    - Comprehensive error handling and business metrics
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Record business metrics
    onboarding_requests_counter.add(1, {"endpoint": "/onboard"})
    
    # Create comprehensive tracing span for the entire onboarding workflow
    with tracer.start_as_current_span("customer_onboarding_workflow") as span:
        try:
            payload = request.get_json(silent=True) or {}
            
            # Validate and enrich customer data
            customer_data = validate_customer_request(payload, span)
            
            # Set comprehensive span attributes for APM visibility
            span.set_attribute("customer.id", customer_data["customer_id"])
            span.set_attribute("customer.type", customer_data["type"])
            span.set_attribute("customer.email", customer_data["email"])
            span.set_attribute("business.operation", "complete_customer_onboarding")
            span.set_attribute("business.request_id", request_id)
            span.set_attribute("service.version", "2.0.0")
            span.set_attribute("http.method", "POST")
            span.set_attribute("http.route", "/onboard")
            
            log.info("Customer onboarding workflow initiated", extra={
                "request_id": request_id,
                "customer_id": customer_data["customer_id"],
                "customer_type": customer_data["type"],
                "customer_email": customer_data["email"],
                "endpoint": "/onboard",
                "service": "onboarding-api"
            })
            
            # Step 1: Perform customer validation and enrichment
            enriched_data = perform_customer_validation(customer_data, request_id, span)
            
            # Step 2: Check if customer already exists
            existing_customer = check_existing_customer(customer_data["customer_id"], request_id, span)
            
            # Step 3: Create or update customer record
            customer_record = create_customer_record(enriched_data, existing_customer, request_id, span)
            
            # Step 4: Trigger asynchronous processing via Lambda
            lambda_success = trigger_async_processing(customer_record, request_id, span)
            
            # Step 5: Queue for additional processing
            queue_success = queue_for_processing(customer_record, request_id, span)
            
            # Step 6: Send welcome notification (only for new customers)
            notification_sent = False
            if not existing_customer:
                notification_sent = send_welcome_notification(customer_record, request_id, span)
            
            # Calculate processing metrics
            total_duration = time.time() - start_time
            success_score = calculate_success_score(lambda_success, queue_success, notification_sent)
            
            # Record business metrics
            onboarding_duration_histogram.record(total_duration, {
                "customer_type": customer_data["type"],
                "success": str(success_score >= 0.8)
            })
            
            if success_score >= 0.8:
                onboarding_success_counter.add(1, {
                    "customer_type": customer_data["type"]
                })
            
            # Set comprehensive span attributes for business intelligence
            span.set_attribute("business.processing_duration_ms", total_duration * 1000)
            span.set_attribute("business.success_score", success_score)
            span.set_attribute("business.lambda_success", lambda_success)
            span.set_attribute("business.queue_success", queue_success)
            span.set_attribute("business.notification_sent", notification_sent)
            span.set_attribute("business.existing_customer", existing_customer is not None)
            span.set_attribute("http.status_code", 200 if success_score >= 0.8 else 206)
            
            # Prepare comprehensive response
            result = {
                "status": "success" if success_score >= 0.8 else "partial_success",
                "request_id": request_id,
                "customer_id": customer_data["customer_id"],
                "customer_type": customer_data["type"],
                "processing_time_ms": round(total_duration * 1000, 2),
                "success_score": round(success_score, 2),
                "operations": {
                    "validation": "completed",
                    "record_creation": "completed",
                    "async_processing": "triggered" if lambda_success else "failed",
                    "queue_processing": "queued" if queue_success else "failed",
                    "notification": "sent" if notification_sent else ("skipped" if existing_customer else "failed")
                },
                "existing_customer": existing_customer is not None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            log.info("Customer onboarding workflow completed", extra={
                "request_id": request_id,
                "customer_id": customer_data["customer_id"],
                "processing_time_ms": round(total_duration * 1000, 2),
                "success_score": success_score,
                "result_status": result["status"],
                "existing_customer": existing_customer is not None
            })
            
            return jsonify(result), 200 if success_score >= 0.8 else 206
            
        except ValidationError as e:
            duration = time.time() - start_time
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.set_attribute("error", True)
            span.set_attribute("error.type", "ValidationError")
            span.set_attribute("error.message", str(e))
            span.set_attribute("business.processing_duration_ms", duration * 1000)
            
            log.warning("Customer onboarding validation failed", extra={
                "request_id": request_id,
                "error": str(e),
                "processing_time_ms": round(duration * 1000, 2),
                "error_type": "validation"
            })
            
            return jsonify({
                "status": "validation_error",
                "request_id": request_id,
                "error": str(e),
                "processing_time_ms": round(duration * 1000, 2)
            }), 400
            
        except Exception as e:
            duration = time.time() - start_time
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            span.set_attribute("business.processing_duration_ms", duration * 1000)
            
            log.error("Customer onboarding workflow failed", extra={
                "request_id": request_id,
                "customer_id": payload.get("customer_id", "unknown"),
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time_ms": round(duration * 1000, 2)
            }, exc_info=True)
            
            return jsonify({
                "status": "internal_error",
                "request_id": request_id,
                "error": "Internal server error",
                "processing_time_ms": round(duration * 1000, 2)
            }), 500

@app.route("/telemetry/smoke", methods=["POST"])
def telemetry_smoke():
    """Minimal smoke test endpoint for ECS → SQS → Lambda trace verification"""
    request_id = str(uuid.uuid4())
    payload = request.get_json(silent=True) or {}
    customer_id = payload.get("customer_id", f"SMOKE-{request_id[:8]}")
    
    with tracer.start_as_current_span("smoke_root") as span:
        span.set_attribute("http.route", "/telemetry/smoke")
        span.set_attribute("http.method", "POST")
        span.set_attribute("customer.id", customer_id)
        span.set_attribute("business.request_id", request_id)
        
        # Minimal record to reuse existing queue_for_processing()
        record = {"customer_id": customer_id}
        ok = queue_for_processing(record, request_id, span)
        
        status_code = 200 if ok else 500
        result = {
            "status": "queued" if ok else "failed",
            "customer_id": customer_id,
            "request_id": request_id
        }
        
        log.info("[SMOKE] Telemetry smoke test completed", extra={
            "request_id": request_id,
            "customer_id": customer_id,
            "queued": ok
        })
        
        return jsonify(result), status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)