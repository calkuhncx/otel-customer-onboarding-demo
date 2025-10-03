import os
import time
import logging
import json
import random
from flask import Flask, jsonify, request
import boto3
from opentelemetry import trace

# Customer onboarding API - demonstrates ECS Fargate + OpenTelemetry collector sidecar
app = Flask(__name__)
log = logging.getLogger("onboarding.api")
log.setLevel(logging.INFO)

# Get tracer for business logic spans
tracer = trace.get_tracer(__name__, version="1.0.0")

# Initialize AWS clients (auto-instrumented by OpenTelemetry)
lambda_client = boto3.client('lambda', region_name='us-west-2')
sqs = boto3.client('sqs', region_name='us-west-2')

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "service": "onboarding-api",
        "version": "1.0.0",
        "timestamp": time.time()
    })

@app.route("/onboard", methods=["POST"])
def onboard():
    """
    Customer onboarding endpoint - demonstrates ECS Fargate with OpenTelemetry
    
    This demonstrates:
    - ECS Fargate deployment with collector sidecar
    - OpenTelemetry auto-instrumentation for HTTP and AWS SDK
    - Structured logging with trace correlation  
    - Business logic spans for APM visibility
    - Service-to-service calls (API → Lambda)
    """
    start_time = time.time()
    
    # Create main business transaction span
    with tracer.start_as_current_span("customer_onboarding_api") as span:
        try:
            # Extract request data
            payload = request.get_json(silent=True) or {}
            customer_id = payload.get("customer_id", f"customer-{random.randint(1000, 9999)}")
            customer_type = payload.get("type", "standard")
            
            # Add business context for APM
            span.set_attribute("customer.id", customer_id)
            span.set_attribute("customer.type", customer_type)
            span.set_attribute("business.operation", "initiate_onboarding")
            span.set_attribute("service.version", "1.0.0")
            span.set_attribute("http.method", "POST")
            span.set_attribute("http.route", "/onboard")
            
            log.info("Customer onboarding request received", extra={
                "customer_id": customer_id,
                "customer_type": customer_type,
                "endpoint": "/onboard",
                "service": "onboarding-api"
            })
            
            # Input validation
            if not customer_id or len(customer_id) < 3:
                span.set_attribute("validation.error", "invalid_customer_id")
                log.error("Invalid customer ID", extra={
                    "customer_id": customer_id,
                    "validation_error": "min_length_3"
                })
                return jsonify({"error": "Invalid customer ID"}), 400
            
            # Simulate initial processing
            with tracer.start_as_current_span("initial_processing") as proc_span:
                proc_span.set_attribute("processing.type", customer_type)
                
                processing_time = 0.2 if customer_type == "premium" else 0.1
                proc_span.set_attribute("processing.duration_ms", processing_time * 1000)
                
                log.info("Processing customer request", extra={
                    "customer_id": customer_id,
                    "processing_type": customer_type,
                    "duration": processing_time
                })
                
                time.sleep(processing_time)
                proc_span.set_attribute("processing.status", "completed")
            
            # Trigger downstream processing (Lambda)
            with tracer.start_as_current_span("downstream_processing") as downstream_span:
                downstream_span.set_attribute("downstream.service", "lambda")
                downstream_span.set_attribute("downstream.function", "cal-onboarding-lambda")
                
                try:
                    # Invoke Lambda for downstream processing
                    lambda_payload = {
                        "customer_id": customer_id,
                        "type": customer_type,
                        "event_type": "api_initiated_onboarding",
                        "source": "onboarding-api"
                    }
                    
                    log.info("Invoking downstream Lambda", extra={
                        "customer_id": customer_id,
                        "lambda_function": "cal-onboarding-lambda",
                        "payload_size": len(json.dumps(lambda_payload))
                    })
                    
                    # Async Lambda invocation (will be auto-instrumented)
                    response = lambda_client.invoke(
                        FunctionName='cal-onboarding-lambda',
                        InvocationType='Event',  # Async
                        Payload=json.dumps(lambda_payload)
                    )
                    
                    downstream_span.set_attribute("lambda.invocation.success", True)
                    downstream_span.set_attribute("lambda.status_code", response.get('StatusCode', 0))
                    
                    log.info("Lambda invocation successful", extra={
                        "customer_id": customer_id,
                        "lambda_status": response.get('StatusCode'),
                        "lambda_request_id": response.get('ResponseMetadata', {}).get('RequestId')
                    })
                    
                except Exception as e:
                    downstream_span.set_attribute("lambda.invocation.error", str(e))
                    downstream_span.set_attribute("error", True)
                    log.warning("Lambda invocation failed", extra={
                        "customer_id": customer_id,
                        "error": str(e)
                    })
            
            # Simulate business workflow steps
            workflow_steps = ["validate", "enrich", "queue"]
            completed_steps = []
            
            for step in workflow_steps:
                with tracer.start_as_current_span(f"workflow_{step}") as step_span:
                    step_span.set_attribute("workflow.step", step)
                    step_span.set_attribute("customer.id", customer_id)
                    
                    step_duration = random.uniform(0.02, 0.08)
                    time.sleep(step_duration)
                    
                    # Simulate occasional step failures
                    if random.random() > 0.95:  # 5% failure rate
                        step_span.set_attribute("step.error", "timeout")
                        log.warning(f"Workflow step {step} failed", extra={
                            "customer_id": customer_id,
                            "step": step,
                            "error": "timeout"
                        })
                        break
                    else:
                        completed_steps.append(step)
                        step_span.set_attribute("step.status", "completed")
                        step_span.set_attribute("step.duration_ms", step_duration * 1000)
            
            # Calculate final results
            total_duration = time.time() - start_time
            success_rate = len(completed_steps) / len(workflow_steps)
            
            # Set final span attributes for APM
            span.set_attribute("processing.total_duration_ms", total_duration * 1000)
            span.set_attribute("business.success_rate", success_rate)
            span.set_attribute("workflow.completed_steps", len(completed_steps))
            span.set_attribute("http.status_code", 200 if success_rate > 0.8 else 206)
            
            result = {
                "status": "accepted" if success_rate > 0.8 else "partial",
                "customer_id": customer_id,
                "customer_type": customer_type,
                "processing_time_ms": round(total_duration * 1000, 2),
                "completed_steps": completed_steps,
                "success_rate": round(success_rate, 2),
                "downstream_triggered": True,
                "timestamp": time.time()
            }
            
            log.info("Customer onboarding API completed", extra={
                "customer_id": customer_id,
                "processing_time_ms": round(total_duration * 1000, 2),
                "success_rate": success_rate,
                "result": result["status"]
            })
            
            return jsonify(result)
            
        except Exception as e:
            # Handle errors with proper span status
            duration = time.time() - start_time
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("processing.duration_ms", duration * 1000)
            
            log.error("Customer onboarding API error", extra={
                "customer_id": payload.get("customer_id", "unknown"),
                "error": str(e),
                "processing_time_ms": round(duration * 1000, 2)
            }, exc_info=True)
            
            return jsonify({"error": "Internal server error"}), 500

@app.route("/customers/<customer_id>", methods=["GET"])
def get_customer(customer_id):
    """Customer lookup endpoint for testing"""
    with tracer.start_as_current_span("customer_lookup") as span:
        span.set_attribute("customer.id", customer_id)
        span.set_attribute("operation", "lookup")
        
        log.info("Customer lookup", extra={
            "customer_id": customer_id,
            "operation": "lookup"
        })
        
        # Simulate lookup
        time.sleep(random.uniform(0.05, 0.15))
        
        return jsonify({
            "customer_id": customer_id,
            "status": "found",
            "type": random.choice(["standard", "premium"]),
            "timestamp": time.time()
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
