# Use Coralogix's Python wrapper and exporter
FROM coralogixrepo/coralogix-python-wrapper-and-exporter:27 as coralogix
FROM public.ecr.aws/lambda/python:3.11

# Copy Coralogix components to /opt
WORKDIR /opt
COPY --from=coralogix /opt/ .

# Set up application
WORKDIR ${LAMBDA_TASK_ROOT}
COPY onboarding-lambda/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY onboarding-lambda/app.py ${LAMBDA_TASK_ROOT}/

# No wrapper needed - using pure OTel SDK in code

# Coralogix environment variables (will be set at runtime via Lambda config)
# CX_DOMAIN=us2.coralogix.com
# CX_API_KEY=<from-secrets-manager>
# CX_REPORTING_STRATEGY=REPORT_AFTER_INVOCATION

ENV OTEL_PROPAGATORS=tracecontext,baggage,xray
ENV OTEL_RESOURCE_ATTRIBUTES="service.namespace=onboarding,service.name=onboarding-lambda"

CMD ["app.handler"]