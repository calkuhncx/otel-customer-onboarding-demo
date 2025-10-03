FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY onboarding-api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Default resource attributes (overridable at runtime)
ENV OTEL_RESOURCE_ATTRIBUTES="service.namespace=onboarding,service.name=onboarding-api,deployment.environment=dev"
# App listens on 8000
EXPOSE 8000

COPY onboarding-api/ /app/

# Run under OTel auto-instrumentation; export all 3 signals to a collector
# Set OTEL_EXPORTER_OTLP_ENDPOINT at runtime to point to the sidecar (e.g. http://otel-collector:4317)
CMD ["opentelemetry-instrument", "--traces_exporter", "otlp", "--metrics_exporter", "otlp", "--logs_exporter", "otlp", "gunicorn", "-b", "0.0.0.0:8000", "app:app"]