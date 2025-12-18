import os
import socket
from celery import Celery
from celery.signals import worker_process_init
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor

# 1. Standard Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prime_numbers.settings')
app = Celery('prime_numbers')

# 2. Configure from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# 3. Discovery happens here - Celery handles the timing internally
app.autodiscover_tasks()


@worker_process_init.connect(weak=False)
def init_celery_otel(*args, **kwargs):
    # Resource identifies this worker + adds unique process info
    resource = Resource.create({
        "service.name": "celery-worker",
        "service.instance.id": f"{socket.gethostname()}-{os.getpid()}"
    })

    # OTLP HTTP Exporter pointing to your collector
    exporter = OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")

    # Set up the Provider with a 10s export interval
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=10000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])

    # Set the global meter provider for this process
    metrics.set_meter_provider(provider)

    # Instrument the Celery worker
    CeleryInstrumentor().instrument()