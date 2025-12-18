import logging
import os
import socket

from celery import Celery
from celery.signals import worker_process_init
from opentelemetry import metrics, trace

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

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

    # --- METRICS (Existing) ---
    metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")
    reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    # --- TRACES (New) ---
    trace_provider = TracerProvider(resource=resource)
    span_processor = BatchSpanProcessor(OTLPSpanExporter())
    trace_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(trace_provider)

    # --- LOGS (New) ---
    logger_provider = LoggerProvider(resource=resource)

    log_exporter = OTLPLogExporter(endpoint="http://otel-collector:4318/v1/logs")
    log_processor = BatchLogRecordProcessor(log_exporter)
    logger_provider.add_log_record_processor(log_processor)
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    # 2. Attach to the ROOT logger specifically
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)  # Ensure root doesn't filter out INFO

    # Instrument the Celery worker
    CeleryInstrumentor().instrument()