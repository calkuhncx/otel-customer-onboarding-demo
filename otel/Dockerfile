FROM otel/opentelemetry-collector-contrib:0.104.0

# Allow config file to be specified at build time
ARG CONFIG_FILE=ecs-collector.yaml

# Copy the collector config
COPY otel/${CONFIG_FILE} /etc/otelcol/config.yaml

# Set the command to use our config
CMD ["--config=/etc/otelcol/config.yaml"]
