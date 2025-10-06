# AWS Lambda Python 3.11 - Pure OpenTelemetry SDK (No Wrapper)
# For container images that can't use Lambda layers
FROM public.ecr.aws/lambda/python:3.11

# Copy application code
WORKDIR ${LAMBDA_TASK_ROOT}
COPY onboarding-lambda/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy Lambda handler
COPY onboarding-lambda/app.py ${LAMBDA_TASK_ROOT}/

# Build-time import check (catches syntax errors early)
RUN python -c "import app; print('✅ Import check passed')"

# Set the CMD to your handler
CMD ["app.handler"]
