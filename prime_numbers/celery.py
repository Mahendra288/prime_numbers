import os
from celery import Celery
from opentelemetry.instrumentation.celery import CeleryInstrumentor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prime_numbers.settings")

app = Celery("prime_numbers")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Instrument Celery
CeleryInstrumentor().instrument(enable_tracing=True)
