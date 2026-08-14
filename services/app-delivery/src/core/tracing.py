"""OpenTelemetry tracing setup and Kafka helpers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import extract, inject
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

TRACER = trace.get_tracer(__name__)


def setup_tracing(
    service_name: str,
    app: Any | None = None,
    instrument_httpx: bool = True,
) -> None:
    """Configure the global TracerProvider and instrument FastAPI/httpx."""
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
    if instrument_httpx:
        HTTPXClientInstrumentor().instrument()


def instrument_sqlalchemy_engine(engine: Any) -> None:
    """Instrument a SQLAlchemy async engine (wraps the underlying sync engine)."""
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


def set_span_error(message: str) -> None:
    """Mark the current span as failed with *message* as the status description."""
    span = trace.get_current_span()
    span.set_attribute("error", message)
    span.set_status(Status(StatusCode.ERROR, message))


def kafka_inject_headers() -> list[tuple[str, bytes]]:
    """Inject the current trace context into Kafka message headers."""
    carrier: dict[str, str] = {}
    inject(carrier)
    return [(k, v.encode("utf-8")) for k, v in carrier.items()]


def kafka_extract_context(headers: list[tuple[str, bytes]] | None) -> Any:
    """Extract a trace context from Kafka message headers."""
    carrier: dict[str, str] = {}
    if headers:
        for key, value in headers:
            try:
                carrier[key] = value.decode("utf-8")
            except Exception:
                continue
    return extract(carrier)


@contextmanager
def start_span(
    name: str,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
) -> Generator[trace.Span]:
    """Convenience helper to create a named internal span."""
    with TRACER.start_as_current_span(
        name,
        kind=kind,
        attributes=attributes or {},
    ) as span:
        yield span
