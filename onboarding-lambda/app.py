# app.py - Vendor-agnostic OTEL Lambda Consumer (Final Form)
import os, json, atexit, logging, sys
from typing import Dict, Any, List

# Setup logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
log = logging.getLogger("onboarding.lambda")

print("🔵 Lambda cold start - initializing OTel SDK...")
log.info("🔵 Lambda cold start - initializing OTel SDK...")

try:
    from opentelemetry import trace, propagate
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    
    print("✅ OTel imports successful")
    log.info("✅ OTel imports successful")
    
    # --- Resource: include cx.application.name / cx.subsystem.name ---
    res = Resource.create({
        "service.name": os.getenv("SERVICE_NAME", "onboarding-lambda"),
        "service.namespace": os.getenv("SERVICE_NAMESPACE", "onboarding"),
        "cx.application.name": os.getenv("CX_APPLICATION", "onboarding"),
        "cx.subsystem.name": os.getenv("CX_SUBSYSTEM", "lambda"),
        "cloud.provider": "aws",
        "cloud.platform": "aws_lambda",
        "cloud.region": os.getenv("AWS_REGION", "us-west-2"),
        "aws.account.id": os.getenv("AWS_ACCOUNT_ID", "104013952213"),
        "faas.name": os.getenv("AWS_LAMBDA_FUNCTION_NAME", "cal-onboarding-lambda-arm64"),
        "faas.version": os.getenv("AWS_LAMBDA_FUNCTION_VERSION", "$LATEST"),
    })
    
    provider = TracerProvider(resource=res)
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(__name__)
    
    print("✅ TracerProvider configured")
    log.info("✅ TracerProvider configured")
    
    # --- gRPC OTLP exporter: tuple-of-tuples headers, lowercase keys ---
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "ingress.us2.coralogix.com:443")
    if endpoint.startswith(("http://", "https://")):
        endpoint = endpoint.split("://", 1)[1]
    
    def _parse_headers(env: str):
        pairs = []
        for kv in filter(None, (p.strip() for p in env.split(","))):
            if "=" in kv:
                k, v = kv.split("=", 1)
                pairs.append((k.strip().lower(), v.strip()))
        return tuple(pairs) if pairs else None
    
    headers = _parse_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""))
    
    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    
    print(f"🟢 OTLP exporter active → {endpoint} ; headers={headers}")
    log.info("🟢 OTLP exporter active → %s ; headers=%s", endpoint, headers)
    
    atexit.register(lambda: processor.force_flush())
    
    OTEL_INITIALIZED = True

except Exception as e:
    print(f"❌ OTel initialization failed: {e}")
    log.error("❌ OTel initialization failed: %s", e, exc_info=True)
    OTEL_INITIALIZED = False
    # Create no-op tracer
    tracer = None
    processor = None

# --- SQS helpers ---
def _flatten_attrs(msg_attrs: Dict[str, Any]) -> Dict[str, str]:
    out = {}
    if msg_attrs:
        for k, v in msg_attrs.items():
            sval = v.get("stringValue") or v.get("StringValue")
            if isinstance(sval, str):
                out[k.lower()] = sval
    return out

def _extract_parent(rec: Dict[str, Any]):
    h = _flatten_attrs(rec.get("messageAttributes") or {})
    if "traceparent" in h or "baggage" in h:
        return propagate.extract(h)
    xr = rec.get("attributes", {}).get("AWSTraceHeader")
    if xr:
        return propagate.extract({"x-amzn-trace-id": xr})
    return None

# --- Handler ---
def handler(event, context):
    """AWS Lambda handler with proper FaaS span structure"""
    print(f"🔵 Handler invoked with {len(event.get('Records', []))} records")
    log.info("🔵 Handler invoked with %d records", len(event.get('Records', [])))
    
    records: List[Dict[str, Any]] = (event or {}).get("Records", []) or []
    
    if not OTEL_INITIALIZED:
        print("⚠️ OTel not initialized, processing without tracing")
        log.warning("⚠️ OTel not initialized, processing without tracing")
        return {"status": "ok", "count": len(records), "otel": "disabled"}

    # Create root Lambda invocation span (required for Serverless Catalog)
    with tracer.start_as_current_span(
        "aws.lambda",
        kind=trace.SpanKind.SERVER,
        attributes={
            "faas.execution": context.request_id if context else "local",
            "faas.trigger": "pubsub",
            "faas.invoked_name": os.getenv("AWS_LAMBDA_FUNCTION_NAME", "cal-onboarding-lambda-arm64"),
            "faas.invoked_region": os.getenv("AWS_REGION", "us-west-2"),
            "cloud.resource_id": context.invoked_function_arn if context else "local",
        },
    ) as lambda_span:
        # Process SQS batch
        with tracer.start_as_current_span(
            "sqs.receive",
            kind=trace.SpanKind.CONSUMER,
            attributes={
                "messaging.system": "aws.sqs",
                "messaging.destination.kind": "queue",
                "messaging.destination.name": "cal-onboarding-queue",
                "messaging.operation": "receive",
                "messaging.batch.message_count": len(records),
            },
        ):
            for rec in records:
                parent_ctx = _extract_parent(rec)
                
                print(f"📨 Processing message {rec.get('messageId')}")
                log.info("📨 Processing message %s", rec.get('messageId'))

                # Each record is a CONSUMER child of producer
                with tracer.start_as_current_span(
                    "sqs.process",
                    context=parent_ctx,
                    kind=trace.SpanKind.CONSUMER,
                    attributes={
                        "messaging.system": "aws.sqs",
                        "messaging.destination.kind": "queue",
                        "messaging.destination.name": "cal-onboarding-queue",
                        "messaging.operation": "process",
                        "messaging.message.id": rec.get("messageId"),
                    },
                ):
                    body = rec.get("body") or "{}"
                    payload = json.loads(body)
                    print(f"✅ Processed customer_id={payload.get('customer_id')}")
                    log.info("✅ Processed customer_id=%s", payload.get('customer_id'))

        print("🔄 Flushing spans...")
        log.info("🔄 Flushing spans...")
        processor.force_flush()
        print("✅ Flush complete")
        log.info("✅ Flush complete")
    
    return {"status": "ok", "count": len(records)}