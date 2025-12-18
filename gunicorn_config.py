import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prime_numbers.settings')

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor


def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

    resource = Resource.create({"service.name": "django-server"})

    # Point to the COLLECTOR
    exporter = OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")

    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=10000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    # Instrument Django inside the forked worker
    DjangoInstrumentor().instrument()