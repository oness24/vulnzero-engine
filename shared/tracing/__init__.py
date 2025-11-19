"""Distributed tracing with OpenTelemetry"""

from shared.tracing.tracing import (
    setup_tracing,
    get_tracer,
    trace_function,
    trace_database_query,
    trace_external_call,
    trace_event_publish,
    trace_event_consume,
)

__all__ = [
    "setup_tracing",
    "get_tracer",
    "trace_function",
    "trace_database_query",
    "trace_external_call",
    "trace_event_publish",
    "trace_event_consume",
]
