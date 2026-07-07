import time
import psutil
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Create standard Prometheus registry
REGISTRY = CollectorRegistry()

# Define Prometheus metrics
API_REQUESTS_TOTAL = Counter(
    "api_requests_total",
    "Total count of HTTP requests",
    ["method", "path", "status"],
    registry=REGISTRY
)

API_REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    registry=REGISTRY
)

CACHE_HITS_TOTAL = Counter(
    "cache_hits_total",
    "Total count of cache hits",
    registry=REGISTRY
)

CACHE_MISSES_TOTAL = Counter(
    "cache_misses_total",
    "Total count of cache misses",
    registry=REGISTRY
)

ETL_DURATION_SECONDS = Gauge(
    "etl_duration_seconds",
    "Duration of the last ETL pipeline execution in seconds",
    registry=REGISTRY
)

FORECAST_DURATION_SECONDS = Gauge(
    "forecast_duration_seconds",
    "Duration of the last forecasting retraining execution in seconds",
    registry=REGISTRY
)

SYSTEM_CPU_USAGE = Gauge(
    "system_cpu_usage_percent",
    "Current CPU usage percent",
    registry=REGISTRY
)

SYSTEM_MEMORY_USAGE = Gauge(
    "system_memory_usage_bytes",
    "Current memory usage in bytes",
    registry=REGISTRY
)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to instrument FastAPI endpoints and collect latency / status metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path == "/metrics" or path == "/health" or path.startswith("/static") or path.startswith("/app"):
            return await call_next(request)

        method = request.method
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            
            # Record metrics
            latency = time.perf_counter() - start_time
            API_REQUEST_LATENCY.labels(method=method, path=path).observe(latency)
            API_REQUESTS_TOTAL.labels(method=method, path=path, status=str(response.status_code)).inc()
            
            return response
        except Exception as e:
            latency = time.perf_counter() - start_time
            API_REQUEST_LATENCY.labels(method=method, path=path).observe(latency)
            API_REQUESTS_TOTAL.labels(method=method, path=path, status="500").inc()
            raise e


def get_metrics_page() -> str:
    """Generate the latest metrics payload for scraper consumption."""
    # Update system stats dynamically before scraping
    try:
        SYSTEM_CPU_USAGE.set(psutil.cpu_percent())
        SYSTEM_MEMORY_USAGE.set(psutil.Process().memory_info().rss)
    except Exception:
        pass
    return generate_latest(REGISTRY).decode("utf-8")
