#!/bin/bash

# Activate your virtual environment
source /Users/mahi/Projects/prime_numbers/venv/bin/activate

# Set OpenTelemetry environment variables
export OTEL_PYTHON_AUTO_INSTRUMENTATION_ENABLED=true
export OTEL_SERVICE_NAME=django-app
export OTEL_TRACES_EXPORTER=console
export OTEL_METRICS_EXPORTER=none
export OTEL_PYTHON_LOG_LEVEL=debug

# Optional: Django settings module (if needed)
export DJANGO_SETTINGS_MODULE=prime_numbers.settings
# Start Celery worker
opentelemetry-instrument celery -A prime_numbers worker --loglevel=info

