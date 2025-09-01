"""
Performance Monitoring Middleware

This middleware provides comprehensive performance monitoring and profiling
for FastAPI endpoints.
"""

import time
import psutil
import logging
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Performance metrics collector."""
    
    def __init__(self):
        self.metrics = {}
        self.request_count = 0
        self.total_response_time = 0.0
        self.start_time = time.time()
    
    def record_request(self, endpoint: str, method: str, duration: float, status_code: int, memory_delta: float):
        """Record request metrics."""
        self.request_count += 1
        self.total_response_time += duration
        
        if endpoint not in self.metrics:
            self.metrics[endpoint] = {
                'count': 0,
                'total_time': 0.0,
                'avg_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0,
                'status_codes': {},
                'memory_usage': [],
                'last_request': None
            }
        
        metric = self.metrics[endpoint]
        metric['count'] += 1
        metric['total_time'] += duration
        metric['avg_time'] = metric['total_time'] / metric['count']
        metric['min_time'] = min(metric['min_time'], duration)
        metric['max_time'] = max(metric['max_time'], duration)
        
        # Status code tracking
        if status_code not in metric['status_codes']:
            metric['status_codes'][status_code] = 0
        metric['status_codes'][status_code] += 1
        
        # Memory usage tracking
        metric['memory_usage'].append(memory_delta)
        if len(metric['memory_usage']) > 100:  # Keep only last 100 requests
            metric['memory_usage'] = metric['memory_usage'][-100:]
        
        metric['last_request'] = datetime.now().isoformat()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        uptime = time.time() - self.start_time
        
        return {
            'uptime_seconds': round(uptime, 2),
            'total_requests': self.request_count,
            'avg_response_time': round(self.total_response_time / max(self.request_count, 1), 4),
            'requests_per_second': round(self.request_count / max(uptime, 1), 2),
            'endpoints': self.metrics
        }
    
    def get_endpoint_stats(self, endpoint: str) -> Dict[str, Any]:
        """Get statistics for specific endpoint."""
        if endpoint not in self.metrics:
            return {}
        
        metric = self.metrics[endpoint]
        memory_usage = metric['memory_usage']
        
        return {
            'endpoint': endpoint,
            'request_count': metric['count'],
            'avg_response_time': round(metric['avg_time'], 4),
            'min_response_time': round(metric['min_time'], 4),
            'max_response_time': round(metric['max_time'], 4),
            'status_codes': metric['status_codes'],
            'avg_memory_usage': round(sum(memory_usage) / len(memory_usage), 2) if memory_usage else 0,
            'max_memory_usage': round(max(memory_usage), 2) if memory_usage else 0,
            'last_request': metric['last_request']
        }


# Global metrics instance
performance_metrics = PerformanceMetrics()


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for performance monitoring and profiling."""
    
    def __init__(self, app, enable_profiling: bool = True):
        super().__init__(app)
        self.enable_profiling = enable_profiling
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance monitoring."""
        
        # Skip profiling for certain endpoints
        if not self.enable_profiling or request.url.path in ['/docs', '/redoc', '/openapi.json']:
            return await call_next(request)
        
        # Record start metrics
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.error(f"Request failed: {e}")
            status_code = 500
            response = StarletteResponse(
                content=json.dumps({"error": "Internal server error"}),
                status_code=500,
                media_type="application/json"
            )
        
        # Record end metrics
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        duration = end_time - start_time
        memory_delta = end_memory - start_memory
        
        # Record metrics
        endpoint = request.url.path
        method = request.method
        
        performance_metrics.record_request(
            endpoint=endpoint,
            method=method,
            duration=duration,
            status_code=status_code,
            memory_delta=memory_delta
        )
        
        # Log slow requests
        if duration > 2.0:  # Log requests taking more than 2 seconds
            logger.warning(
                f"Slow request: {method} {endpoint} - {duration:.4f}s, "
                f"memory: {memory_delta:+.2f}MB, status: {status_code}"
            )
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.4f}s"
        response.headers["X-Memory-Delta"] = f"{memory_delta:+.2f}MB"
        
        return response


class SystemMonitor:
    """System resource monitoring."""
    
    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """Get current system statistics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process-specific stats
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': round(cpu_percent, 2),
                'memory_total_gb': round(memory.total / 1024 / 1024 / 1024, 2),
                'memory_available_gb': round(memory.available / 1024 / 1024 / 1024, 2),
                'memory_percent': round(memory.percent, 2),
                'disk_total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
                'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
                'disk_percent': round((disk.used / disk.total) * 100, 2)
            },
            'process': {
                'cpu_percent': round(process_cpu, 2),
                'memory_rss_mb': round(process_memory.rss / 1024 / 1024, 2),
                'memory_vms_mb': round(process_memory.vms / 1024 / 1024, 2),
                'num_threads': process.num_threads(),
                'num_fds': process.num_fds() if hasattr(process, 'num_fds') else 0
            }
        }


def get_performance_summary() -> Dict[str, Any]:
    """Get comprehensive performance summary."""
    return {
        'metrics': performance_metrics.get_summary(),
        'system': SystemMonitor.get_system_stats()
    }


def get_endpoint_performance(endpoint: str) -> Dict[str, Any]:
    """Get performance data for specific endpoint."""
    return performance_metrics.get_endpoint_stats(endpoint)
