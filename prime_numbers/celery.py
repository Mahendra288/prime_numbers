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

from celery.signals import task_prerun, task_postrun, task_failure
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.context import attach, detach


@worker_process_init.connect(weak=False)
def init_celery_otel(*args, **kwargs):
    # Resource identifies this worker + adds unique process info
    resource = Resource.create({
        "service.name": "celery-worker",
        "service.instance.id": f"{socket.gethostname()}-{os.getpid()}"
    })

    # Traces
    trace_provider = TracerProvider(resource=resource)
    span_processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces")
    )
    trace_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(trace_provider)

    # Metrics
    metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")
    reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=10000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    # Logs
    logger_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(endpoint="http://otel-collector:4318/v1/logs")
    log_processor = BatchLogRecordProcessor(log_exporter)
    logger_provider.add_log_record_processor(log_processor)

    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Instrument Celery
    CeleryInstrumentor().instrument(tracer_provider=trace_provider)


tracer = trace.get_tracer(__name__)
propagator = TraceContextTextMapPropagator()


# ============================================
# Step 1: Inject trace context when task is called
# ============================================

class TracedTask(app.Task):
    """Custom Task class that handles trace context propagation"""

    def apply_async(self, args=None, kwargs=None, **options):
        """Called when task.delay() or task.apply_async() is used"""

        # Get current trace context
        from opentelemetry.context import get_current
        current_context = get_current()

        # Create a carrier (dictionary) to hold trace context
        carrier = {}

        # Inject trace context into the carrier
        propagator.inject(carrier, context=current_context)

        # Add carrier to task headers (passed to worker)
        headers = options.get('headers') or {}
        headers['tracing'] = carrier
        options['headers'] = headers

        # Call the original apply_async
        return super().apply_async(args, kwargs, **options)


# ============================================
# Step 2: Extract trace context in the worker
# ============================================

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None,
                        kwargs=None, **extra_kwargs):
    """Called BEFORE task execution in worker"""

    # Extract trace context from headers
    headers = task.request.get('headers', {})
    carrier = headers.get('tracing', {})

    if carrier:
        # Extract context from carrier
        context = propagator.extract(carrier)

        # Attach context to current execution
        token = attach(context)

        # Store token to detach later
        task.request.otel_token = token

        # Start a span for the task execution
        span = tracer.start_span(
            name=f"celery.task.{task.name}",
            context=context
        )
        span.set_attribute("celery.task_id", task_id)
        span.set_attribute("celery.task_name", task.name)

        # Store span to end it later
        task.request.otel_span = span


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, **kwargs):
    """Called AFTER successful task execution"""

    # End the span
    if hasattr(task.request, 'otel_span'):
        span = task.request.otel_span
        span.set_attribute("celery.status", "success")
        span.end()

    # Detach context
    if hasattr(task.request, 'otel_token'):
        detach(task.request.otel_token)


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None,
                         task=None, **kwargs):
    """Called when task fails"""

    if hasattr(task.request, 'otel_span'):
        span = task.request.otel_span
        span.set_attribute("celery.status", "failed")
        span.record_exception(exception)
        span.end()

    if hasattr(task.request, 'otel_token'):
        detach(task.request.otel_token)

