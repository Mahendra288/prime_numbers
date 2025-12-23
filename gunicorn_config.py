import logging
import os

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prime_numbers.settings')

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter


def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

    resource = Resource.create({
        "service.name": "django-server",
        "service.instance.id": str(worker.pid),  # Track which worker
    })

    # --- TRACES ---
    trace_provider = TracerProvider(resource=resource)
    span_processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces")
    )
    trace_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(trace_provider)  # Set it globally

    # --- METRICS ---
    metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")
    reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    # --- LOGS ---
    logger_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(endpoint="http://otel-collector:4318/v1/logs")
    log_processor = BatchLogRecordProcessor(log_exporter)
    logger_provider.add_log_record_processor(log_processor)

    # Attach OTEL handler to root logger
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Instrument Django inside the forked worker
    DjangoInstrumentor().instrument(
        tracer_provider=trace_provider,
        is_sql_commentor_enabled=True
    )

    server.log.info("OpenTelemetry initialized for worker %s", worker.pid)