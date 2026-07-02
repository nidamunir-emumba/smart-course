"""OpenTelemetry + Prometheus wiring. Call `setup_observability(app)` in the app factory.

Traces are exported over OTLP to the collector (which fans out to Jaeger). Metrics are
exposed via the /metrics Prometheus endpoint.

The observability stack is REQUIRED in Docker but OPTIONAL for minimal local runs: if the
libraries aren't installed, setup logs a warning and no-ops so the app still boots.
"""
import logging

from fastapi import FastAPI

from app.core.config import settings

logger = logging.getLogger(__name__)


def setup_observability(app: FastAPI) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from prometheus_fastapi_instrumentator import Instrumentator
    except ImportError as exc:  # minimal local env without the observability extras
        logger.warning("Observability libraries not installed (%s); skipping setup.", exc)
        return

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        )
    )
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    # Exposes GET /metrics for Prometheus to scrape.
    Instrumentator().instrument(app).expose(app)
