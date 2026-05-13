"""Request observability middleware — tracks latency, error rates, and throughput.

Inspired by Cast AI / Kimchi: monitor SLO signals so your team stops firefighting.
Metrics are held in-memory and exposed via GET /api/metrics for the frontend badge.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


@dataclass
class EndpointMetrics:
    request_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    latencies: list[float] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        if not self.request_count:
            return 0.0
        return self.total_latency_ms / self.request_count

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_l = sorted(self.latencies)
        idx = int(len(sorted_l) * 0.95)
        return sorted_l[min(idx, len(sorted_l) - 1)]

    @property
    def error_rate(self) -> float:
        if not self.request_count:
            return 0.0
        return self.error_count / self.request_count


class MetricsStore:
    def __init__(self, max_latencies: int = 500):
        self.endpoints: dict[str, EndpointMetrics] = defaultdict(EndpointMetrics)
        self._max = max_latencies
        self.start_time = time.time()

    def record(self, path: str, latency_ms: float, status: int) -> None:
        m = self.endpoints[path]
        m.request_count += 1
        m.total_latency_ms += latency_ms
        if status >= 400:
            m.error_count += 1
        m.latencies.append(latency_ms)
        if len(m.latencies) > self._max:
            m.latencies = m.latencies[-self._max:]

    def summary(self) -> dict:
        uptime = time.time() - self.start_time
        total_reqs = sum(m.request_count for m in self.endpoints.values())
        total_errors = sum(m.error_count for m in self.endpoints.values())
        all_latencies = []
        for m in self.endpoints.values():
            all_latencies.extend(m.latencies)

        avg = sum(all_latencies) / len(all_latencies) if all_latencies else 0.0
        sorted_l = sorted(all_latencies)
        p95 = sorted_l[int(len(sorted_l) * 0.95)] if sorted_l else 0.0

        return {
            "uptime_s": round(uptime, 1),
            "total_requests": total_reqs,
            "total_errors": total_errors,
            "error_rate": round(total_errors / total_reqs, 4) if total_reqs else 0.0,
            "avg_latency_ms": round(avg, 2),
            "p95_latency_ms": round(p95, 2),
            "endpoints": {
                path: {
                    "requests": m.request_count,
                    "errors": m.error_count,
                    "avg_ms": round(m.avg_latency_ms, 2),
                    "p95_ms": round(m.p95_latency_ms, 2),
                    "error_rate": round(m.error_rate, 4),
                }
                for path, m in self.endpoints.items()
            },
        }


metrics_store = MetricsStore()


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/api/metrics", "/health"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000

        metrics_store.record(request.url.path, latency_ms, response.status_code)

        response.headers["X-Response-Time-Ms"] = f"{latency_ms:.1f}"
        return response
