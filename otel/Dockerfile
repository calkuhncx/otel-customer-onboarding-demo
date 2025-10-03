FROM otel/opentelemetry-collector-contrib:0.104.0

# Copy the collector config
COPY otel/ecs-collector.yaml /etc/otelcol/config.yaml

# Set the command to use our config
CMD ["--config=/etc/otelcol/config.yaml"]
