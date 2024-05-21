import logging

from opentelemetry import metrics
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes


def start(otlp_exporter_endpoint: str = "localhost:4317", service_name: str = __name__):
    otlp_exporter = OTLPSpanExporter(
        otlp_exporter_endpoint,
        insecure=True,
    )
    resource = Resource(
        attributes={
            ResourceAttributes.SERVICE_NAME: service_name,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)

    exporter = OTLPMetricExporter(endpoint=otlp_exporter_endpoint, insecure=True)
    metric_reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)

    provider = MeterProvider(metric_readers=[metric_reader], resource=resource)

    metrics.set_meter_provider(provider)

    from .instrumentation import EnovaFastAPIInstrumentor, EnovaVllmInstrumentor

    EnovaFastAPIInstrumentor().instrument()
    EnovaVllmInstrumentor().instrument()

    from .metrics_adapter import VLLMLogMetricsAdapter

    metrics_log_handler = VLLMLogMetricsAdapter()
    vllm_logger = logging.getLogger("vllm.engine.metrics")
    vllm_logger.addHandler(metrics_log_handler)
