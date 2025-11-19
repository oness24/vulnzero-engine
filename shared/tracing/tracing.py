"""
Distributed Tracing with OpenTelemetry
=======================================

Provides distributed tracing capabilities for VulnZero microservices.
"""

import logging
import os
from typing import Optional, Callable, Any, Dict
from functools import wraps
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace import Status, StatusCode, Span

logger = logging.getLogger(__name__)

# Global tracer
_tracer: Optional[trace.Tracer] = None


def setup_tracing(
    service_name: str,
    jaeger_host: str = "jaeger",
    jaeger_port: int = 6831,
    enable_console: bool = False,
) -> trace.Tracer:
    """
    Initialize OpenTelemetry tracing with Jaeger backend.

    Args:
        service_name: Name of the service (e.g., "api-gateway")
        jaeger_host: Jaeger agent hostname
        jaeger_port: Jaeger agent port
        enable_console: Whether to also export to console (debug)

    Returns:
        Tracer instance

    Usage:
        # In your main.py or startup
        tracer = setup_tracing("api-gateway")
    """
    global _tracer

    try:
        # Create resource with service name
        resource = Resource(attributes={
            SERVICE_NAME: service_name,
            "service.version": os.getenv("APP_VERSION", "0.1.0"),
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        })

        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)

        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )

        # Add batch span processor for Jaeger
        tracer_provider.add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )

        # Optionally add console exporter for debugging
        if enable_console:
            console_exporter = ConsoleSpanExporter()
            tracer_provider.add_span_processor(
                BatchSpanProcessor(console_exporter)
            )

        # Set as global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # Get tracer
        _tracer = trace.get_tracer(__name__)

        logger.info(
            f"✓ Distributed tracing initialized for {service_name} "
            f"(Jaeger: {jaeger_host}:{jaeger_port})"
        )

        return _tracer

    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}")
        # Return no-op tracer to avoid breaking the application
        _tracer = trace.get_tracer(__name__)
        return _tracer


def instrument_fastapi(app):
    """
    Instrument FastAPI application with automatic tracing.

    Args:
        app: FastAPI application instance

    Usage:
        from fastapi import FastAPI
        from shared.tracing import setup_tracing, instrument_fastapi

        app = FastAPI()
        setup_tracing("api-gateway")
        instrument_fastapi(app)
    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("✓ FastAPI instrumented for tracing")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")


def instrument_sqlalchemy(engine):
    """
    Instrument SQLAlchemy engine with automatic tracing.

    Args:
        engine: SQLAlchemy engine instance

    Usage:
        from sqlalchemy import create_engine
        from shared.tracing import instrument_sqlalchemy

        engine = create_engine(...)
        instrument_sqlalchemy(engine)
    """
    try:
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,
        )
        logger.info("✓ SQLAlchemy instrumented for tracing")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy: {e}")


def instrument_redis():
    """
    Instrument Redis with automatic tracing.

    Usage:
        from shared.tracing import instrument_redis

        # Call once during startup
        instrument_redis()
    """
    try:
        RedisInstrumentor().instrument()
        logger.info("✓ Redis instrumented for tracing")
    except Exception as e:
        logger.warning(f"Failed to instrument Redis: {e}")


def instrument_http_clients():
    """
    Instrument HTTP clients (requests, httpx) with automatic tracing.

    Usage:
        from shared.tracing import instrument_http_clients

        # Call once during startup
        instrument_http_clients()
    """
    try:
        RequestsInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        logger.info("✓ HTTP clients instrumented for tracing")
    except Exception as e:
        logger.warning(f"Failed to instrument HTTP clients: {e}")


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance.

    Returns:
        Tracer instance

    Usage:
        from shared.tracing import get_tracer

        tracer = get_tracer()
        with tracer.start_as_current_span("my-operation"):
            # Do work
            pass
    """
    global _tracer

    if _tracer is None:
        # Return default tracer if not initialized
        _tracer = trace.get_tracer(__name__)

    return _tracer


def trace_function(
    span_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Decorator to trace a function with automatic span creation.

    Args:
        span_name: Name for the span (defaults to function name)
        attributes: Additional attributes to add to span

    Usage:
        @trace_function(span_name="process_vulnerability")
        async def process_vulnerability(vuln_id: int):
            # Function is automatically traced
            pass

        @trace_function(attributes={"operation": "analysis"})
        def analyze_code(code: str):
            # Span will include operation=analysis attribute
            pass
    """

    def decorator(func: Callable) -> Callable:
        func_span_name = span_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()

            with tracer.start_as_current_span(func_span_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))

                # Add function arguments as attributes
                try:
                    # Add positional args
                    for i, arg in enumerate(args):
                        if i == 0 and hasattr(arg, "__class__"):
                            # Skip 'self' or 'cls' arguments
                            continue
                        span.set_attribute(f"arg.{i}", str(arg)[:100])

                    # Add keyword args
                    for key, value in kwargs.items():
                        span.set_attribute(f"arg.{key}", str(value)[:100])
                except Exception:
                    pass  # Don't fail if we can't serialize arguments

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()

            with tracer.start_as_current_span(func_span_name) as span:
                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))

                # Add function arguments
                try:
                    for i, arg in enumerate(args):
                        if i == 0 and hasattr(arg, "__class__"):
                            continue
                        span.set_attribute(f"arg.{i}", str(arg)[:100])

                    for key, value in kwargs.items():
                        span.set_attribute(f"arg.{key}", str(value)[:100])
                except Exception:
                    pass

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR))
                    span.record_exception(e)
                    raise

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@contextmanager
def trace_database_query(query_type: str, table: str):
    """
    Context manager to trace database queries.

    Args:
        query_type: Type of query (SELECT, INSERT, UPDATE, DELETE)
        table: Table name

    Usage:
        with trace_database_query("SELECT", "vulnerabilities"):
            results = db.query(Vulnerability).all()
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(f"db.{query_type}") as span:
        span.set_attribute("db.operation", query_type)
        span.set_attribute("db.table", table)
        span.set_attribute("db.system", "postgresql")

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            raise


@contextmanager
def trace_external_call(service: str, operation: str):
    """
    Context manager to trace external API calls.

    Args:
        service: Name of external service (e.g., "nvd-api")
        operation: Operation being performed

    Usage:
        with trace_external_call("nvd-api", "get_cve"):
            response = requests.get(f"https://nvd.nist.gov/...")
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(f"external.{service}.{operation}") as span:
        span.set_attribute("service.name", service)
        span.set_attribute("service.operation", operation)

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            raise


@contextmanager
def trace_event_publish(event_type: str):
    """
    Context manager to trace event publishing.

    Args:
        event_type: Type of event being published

    Usage:
        with trace_event_publish("vulnerability.detected"):
            await event_bus.publish(event)
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(f"event.publish.{event_type}") as span:
        span.set_attribute("event.type", event_type)
        span.set_attribute("event.operation", "publish")

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            raise


@contextmanager
def trace_event_consume(event_type: str, handler_name: str):
    """
    Context manager to trace event consumption.

    Args:
        event_type: Type of event being consumed
        handler_name: Name of the handler function

    Usage:
        with trace_event_consume("vulnerability.detected", "handle_vulnerability"):
            await handle_vulnerability(event)
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(f"event.consume.{event_type}") as span:
        span.set_attribute("event.type", event_type)
        span.set_attribute("event.operation", "consume")
        span.set_attribute("event.handler", handler_name)

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR))
            span.record_exception(e)
            raise


def add_span_attributes(**attributes):
    """
    Add attributes to the current span.

    Args:
        **attributes: Attributes to add

    Usage:
        from shared.tracing import add_span_attributes

        # Inside a traced function or context
        add_span_attributes(
            user_id=123,
            vulnerability_count=5,
            operation="analysis"
        )
    """
    span = trace.get_current_span()

    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, str(value))


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event to the current span.

    Args:
        name: Event name
        attributes: Optional attributes

    Usage:
        add_span_event("cache_hit", {"key": "vuln:123"})
        add_span_event("processing_started")
    """
    span = trace.get_current_span()

    if span and span.is_recording():
        span.add_event(name, attributes=attributes or {})
