"""Instrumented FastAPI service for the Observability Platform demo."""

from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any
import logging
import random

import psutil
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("observability-platform")

REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the application.",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
APP_INFO = Gauge(
    "application_info",
    "Static application metadata; value is always 1.",
    ["service", "version", "environment"],
)
PROCESS_CPU = Gauge("process_cpu_percent", "Process CPU utilization percentage.")
PROCESS_MEMORY = Gauge("process_memory_bytes", "Resident memory used by the application process.")
SYSTEM_MEMORY = Gauge("system_memory_percent", "System memory utilization percentage.")
SYSTEM_CPU = Gauge("system_cpu_percent", "System CPU utilization percentage.")
BUSINESS_OPERATIONS = Counter(
    "business_operations_total",
    "Count of simulated business operations.",
    ["operation", "result"],
)

APP_VERSION = "1.0.0"
APP_ENVIRONMENT = "development"


@asynccontextmanager
async def lifespan(_: FastAPI):
    APP_INFO.labels(service="observability-demo-api", version=APP_VERSION, environment=APP_ENVIRONMENT).set(1)
    logger.info("Observability demo API starting (version=%s, environment=%s)", APP_VERSION, APP_ENVIRONMENT)
    yield
    logger.info("Observability demo API stopping")


app = FastAPI(
    title="Observability Platform API",
    description="A production-minded example API instrumented for Prometheus and Grafana.",
    version=APP_VERSION,
    lifespan=lifespan,
)


@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    # Route templates avoid high-cardinality labels such as raw IDs and query strings.
    started = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    finally:
        duration = perf_counter() - started
        route = request.scope.get("route")
        endpoint = getattr(route, "path", None) or "unmatched"
        REQUESTS_TOTAL.labels(request.method, endpoint, str(status_code)).inc()
        REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)


@app.get("/", tags=["service"])
async def root() -> dict[str, str]:
    return {"service": "observability-demo-api", "version": APP_VERSION, "status": "running"}


@app.get("/health", tags=["service"])
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ready", tags=["service"])
async def readiness() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/api/v1/orders", tags=["demo"])
async def list_orders() -> dict[str, Any]:
    """Return deterministic demo data and increment a business-operation metric."""
    BUSINESS_OPERATIONS.labels(operation="list_orders", result="success").inc()
    return {
        "items": [
            {"order_id": "ORD-1001", "status": "shipped", "total": 89.90},
            {"order_id": "ORD-1002", "status": "processing", "total": 42.50},
            {"order_id": "ORD-1003", "status": "delivered", "total": 125.00},
        ],
        "count": 3,
    }


@app.post("/api/v1/checkout", tags=["demo"])
async def checkout(payload: dict[str, Any]) -> dict[str, Any]:
    """Simulate a checkout operation; send simulate_failure=true to test error metrics."""
    if payload.get("simulate_failure") is True:
        BUSINESS_OPERATIONS.labels(operation="checkout", result="failure").inc()
        return JSONResponse(status_code=503, content={"detail": "Simulated checkout service unavailable"})
    BUSINESS_OPERATIONS.labels(operation="checkout", result="success").inc()
    return {"status": "accepted", "order_id": f"ORD-{random.randint(10000, 99999)}"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Expose Prometheus metrics, including lightweight host/process measurements."""
    PROCESS_CPU.set(psutil.Process().cpu_percent(interval=None))
    PROCESS_MEMORY.set(psutil.Process().memory_info().rss)
    SYSTEM_MEMORY.set(psutil.virtual_memory().percent)
    SYSTEM_CPU.set(psutil.cpu_percent(interval=None))
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
