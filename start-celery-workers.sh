#!/bin/bash

# Activate your virtual environment
source /Users/mahi/Projects/prime_numbers/venv/bin/activate

# Optional: Django settings module (if needed)
export DJANGO_SETTINGS_MODULE=prime_numbers.settings
# Start Celery worker
opentelemetry-instrument celery -A prime_numbers worker --loglevel=info

