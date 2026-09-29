"""
Minimal in-memory metrics so the system is observable out of the box.

Production swap: replace increment()/observe() bodies with OpenTelemetry counters/
histograms exported to Prometheus, and wrap request/tool/db timings with tracer spans.
"""
import time
import threading
from collections import defaultdict, Counter

_lock = threading.Lock()
_counters: Counter = Counter()
_latencies: dict[str, list[float]] = defaultdict(list)


def increment(name: str, amount: int = 1):
    with _lock:
        _counters[name] += amount


def observe_latency(name: str, seconds: float):
    with _lock:
        _latencies[name].append(seconds)


class timer:
    """Context manager: with timer('tool.get_order_status'): ..."""
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        observe_latency(self.name, time.perf_counter() - self._start)


def snapshot() -> dict:
    with _lock:
        avg_latencies = {
            k: round(sum(v) / len(v), 4) for k, v in _latencies.items() if v
        }
        return {"counters": dict(_counters), "avg_latency_seconds": avg_latencies}
