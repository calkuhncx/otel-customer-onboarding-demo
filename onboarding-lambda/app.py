# app.py - Golden Path Lambda Consumer with Serverless Dashboard Support
import os, logging, atexit, json, time
from typing import Dict, Any, List
from grpc import ssl_channel_credentials
from opentelemetry import trace, propagate
from opentelemetry.trace import get_tracer, SpanKind, Link
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

# Only init OTel if not in build environment
if not os.getenv("SKIP_OTEL_INIT"):
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL","DEBUG"),
        format='%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    log = logging.getLogger("onboarding-lambda")
    log.setLevel(logging.DEBUG)  # Ensure logger itself is enabled

    resource = Resource.create({
      SERVICE_NAME: os.getenv("SERVICE_NAME","onboarding-lambda"),
      "cx.application.name": os.getenv("CX_APPLICATION","onboarding"),
      "cx.subsystem.name": os.getenv("CX_SUBSYSTEM","lambda"),
      # Lambda-specific resource attributes for Coralogix serverless dashboard
      "faas.name": os.getenv("AWS_LAMBDA_FUNCTION_NAME", "cal-onboarding-lambda-arm64"),
      "faas.version": os.getenv("AWS_LAMBDA_FUNCTION_VERSION", "$LATEST"),
      "faas.runtime": "python3.11",
      "faas.architecture": "arm64",
      "cloud.provider": "aws",
      "cloud.platform": "aws_lambda",
      "cloud.region": os.getenv("AWS_REGION", "us-west-2"),
    })

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(__name__)

    # --- OTLP gRPC exporter with lowercase authorization header + TLS ---
    API_KEY = os.environ["CORALOGIX_API_KEY"]  # Send-Your-Data key (cxtp_...)
    ENDPOINT = os.getenv("CORALOGIX_OTLP_ENDPOINT", "ingress.us2.coralogix.com:443")

    otlp = OTLPSpanExporter(
      endpoint=ENDPOINT,                              # gRPC host:port (no https, no /v1/traces)
      headers=(("authorization", f"Bearer {API_KEY}"),),  # <-- LOWERCASE key
      credentials=ssl_channel_credentials(),
      timeout=5,
    )
    provider.add_span_processor(BatchSpanProcessor(otlp))

    # Console exporter to mirror spans to logs
    try:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    except ImportError:
        # Fallback: simple logging
        class _SimpleConsoleExporter:
            def export(self, spans):
                for s in spans:
                    log.info("🔍 SPAN: %s trace=%s", s.name, format(s.context.trace_id, "032x"))
                from opentelemetry.sdk.trace.export import SpanExportResult
                return SpanExportResult.SUCCESS
            def shutdown(self): pass
        provider.add_span_processor(SimpleSpanProcessor(_SimpleConsoleExporter()))

    # canary span to get a trace_id you can search for
    with tracer.start_as_current_span("cold_start_canary") as s:
      tid = format(s.get_span_context().trace_id, "032x")
      log.info("🟡 cold_start_canary trace_id=%s endpoint=%s", tid, ENDPOINT)

    def _shutdown():
      try:
        ok = provider.force_flush(timeout_millis=4000); log.info("✅ flush@exit=%s", ok)
      finally:
        provider.shutdown()
    atexit.register(_shutdown)

def _carrier_from_sqs_attributes(attrs: Dict[str, Any]) -> Dict[str, str]:
    carrier = {}
    for k, v in (attrs or {}).items():
        key = k.lower()
        sv = v.get("stringValue") or v.get("StringValue")
        if isinstance(sv, str): 
            carrier[key] = sv.strip()
    return carrier

def handler(event, context):
    if not os.getenv("SKIP_OTEL_INIT"):
        # Create a Lambda invocation span for serverless dashboard
        with tracer.start_as_current_span("lambda.invoke", kind=SpanKind.SERVER) as lambda_span:
            # Add Lambda-specific attributes for serverless dashboard
            lambda_span.set_attribute("faas.execution", getattr(context, "aws_request_id", "n/a"))
            lambda_span.set_attribute("faas.id", getattr(context, "invoked_function_arn", ""))
            lambda_span.set_attribute("cloud.account.id", getattr(context, "invoked_function_arn", "").split(":")[4] if ":" in getattr(context, "invoked_function_arn", "") else "")
            
            log.info("🚀 Handler called - Request ID: %s", getattr(context, "aws_request_id", "n/a"))
            
            records: List[Dict[str, Any]] = (event.get("Records") or []) if isinstance(event, dict) else []
            if not records:
                with tracer.start_as_current_span("lambda.direct_invoke", kind=SpanKind.SERVER):
                    log.info("🎯 Direct invocation trace_id=%s", 
                            format(trace.get_current_span().get_span_context().trace_id, "032x"))
                    trace.get_tracer_provider().force_flush(timeout_millis=4000)
                    return {"ok": True, "source": "direct"}

            # Collect parent SpanContexts for batch KPI span with links
            links: List[Link] = []
            processed_count = 0

            for rec in records:
                carrier = _carrier_from_sqs_attributes(rec.get("messageAttributes"))
                # Use default propagate.extract without custom getter
                ctx = propagate.extract(carrier)

                log.info("📨 Processing SQS message with attributes: %s", list(carrier.keys()))

                # Link target (for batch KPI span)
                parent_sc = trace.get_current_span(ctx).get_span_context()
                if parent_sc.is_valid:
                    links.append(Link(parent_sc))

                # Per-record CONSUMER span — this is what unifies with the ECS trace
                with tracer.start_as_current_span("sqs.process", context=ctx, kind=SpanKind.CONSUMER) as sp:
                    # Log the extracted trace_id for verification
                    tid = sp.get_span_context().trace_id
                    log.info("[LAMBDA] sqs.process trace_id=%032x msg_id=%s", tid, rec.get("messageId"))

                    # Rich attributes for investigation/alerting
                    sp.set_attribute("messaging.system", "aws.sqs")
                    sp.set_attribute("messaging.operation", "process")
                    sp.set_attribute("messaging.destination", rec.get("eventSourceARN", "unknown"))
                    sp.set_attribute("messaging.message_id", rec.get("messageId", ""))
                    sp.set_attribute("faas.trigger", "pubsub")
                    sp.set_attribute("aws.request_id", getattr(context, "aws_request_id", "n/a"))
                    
                    # Business attributes
                    try:
                        body = json.loads(rec.get("body") or "{}")
                        if isinstance(body, dict):
                            customer_id = body.get("customer_id", "")
                            sp.set_attribute("customer.id", customer_id)
                            sp.set_attribute("business.request_id", body.get("request_id", ""))
                            sp.set_attribute("workflow.stage", "lambda_processing")
                            if customer_id:
                                log.info("🎯 Processing customer %s in trace %032x", customer_id, tid)
                    except Exception as e:
                        sp.set_attribute("processing.decode_error", True)
                        sp.set_attribute("error.message", str(e))
                        log.warning("Failed to parse message body: %s", e)

                    # Do the actual work per message
                    time.sleep(0.01)
                    processed_count += 1

            # Batch KPI span (no single parent, just links for metrics)
            with tracer.start_as_current_span("sqs.batch", links=links, kind=SpanKind.CONSUMER) as batch_span:
                batch_span.set_attribute("messaging.system", "aws.sqs")
                batch_span.set_attribute("messaging.operation", "batch_process")
                batch_span.set_attribute("messaging.batch_size", len(records))
                batch_span.set_attribute("messaging.processed_count", processed_count)
                batch_span.set_attribute("faas.trigger", "pubsub")
                batch_span.set_attribute("aws.request_id", getattr(context, "aws_request_id", "n/a"))
                batch_span.set_attribute("workflow.stage", "batch_processing")
                
                log.info("📦 Processed batch of %d messages with %d links", len(records), len(links))

            trace.get_tracer_provider().force_flush(timeout_millis=4000)
            log.info("✅ flush@end=True")
            return {"ok": True, "source": "sqs", "processed": processed_count, "batch_size": len(records)}
