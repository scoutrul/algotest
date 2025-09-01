"""
Performance Monitoring API Endpoints

Provides endpoints for monitoring system performance and metrics.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging

from app.middleware.performance import (
    get_performance_summary,
    get_endpoint_performance,
    SystemMonitor
)
from app.services.cache import get_cache_stats, data_cache, api_cache

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/performance/summary")
async def get_performance_summary_endpoint() -> Dict[str, Any]:
    """
    Get comprehensive performance summary.
    
    Returns:
        Performance metrics and system statistics
    """
    try:
        summary = get_performance_summary()
        return {
            "success": True,
            "data": summary,
            "timestamp": summary['system']['timestamp']
        }
    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/endpoint/{endpoint:path}")
async def get_endpoint_performance_endpoint(endpoint: str) -> Dict[str, Any]:
    """
    Get performance data for specific endpoint.
    
    Args:
        endpoint: The endpoint path to get performance data for
        
    Returns:
        Performance statistics for the endpoint
    """
    try:
        # Remove leading slash if present
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        
        stats = get_endpoint_performance(f"/{endpoint}")
        
        if not stats:
            raise HTTPException(status_code=404, detail=f"No performance data found for endpoint: {endpoint}")
        
        return {
            "success": True,
            "data": stats,
            "endpoint": f"/{endpoint}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get endpoint performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/system")
async def get_system_stats_endpoint() -> Dict[str, Any]:
    """
    Get current system statistics.
    
    Returns:
        System resource usage and statistics
    """
    try:
        stats = SystemMonitor.get_system_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/health")
async def get_performance_health() -> Dict[str, Any]:
    """
    Get performance health status.
    
    Returns:
        Health status based on performance metrics
    """
    try:
        summary = get_performance_summary()
        metrics = summary['metrics']
        system = summary['system']
        
        # Health checks
        health_status = "healthy"
        issues = []
        
        # Check response time
        avg_response_time = metrics.get('avg_response_time', 0)
        if avg_response_time > 5.0:
            health_status = "degraded"
            issues.append(f"High average response time: {avg_response_time:.2f}s")
        
        # Check CPU usage
        cpu_percent = system['system']['cpu_percent']
        if cpu_percent > 80:
            health_status = "degraded"
            issues.append(f"High CPU usage: {cpu_percent}%")
        
        # Check memory usage
        memory_percent = system['system']['memory_percent']
        if memory_percent > 85:
            health_status = "degraded"
            issues.append(f"High memory usage: {memory_percent}%")
        
        # Check disk usage
        disk_percent = system['system']['disk_percent']
        if disk_percent > 90:
            health_status = "critical"
            issues.append(f"High disk usage: {disk_percent}%")
        
        return {
            "success": True,
            "data": {
                "status": health_status,
                "issues": issues,
                "metrics": {
                    "avg_response_time": avg_response_time,
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "total_requests": metrics.get('total_requests', 0),
                    "uptime_seconds": metrics.get('uptime_seconds', 0)
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get performance health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/top-endpoints")
async def get_top_endpoints(limit: int = 10) -> Dict[str, Any]:
    """
    Get top endpoints by request count and response time.
    
    Args:
        limit: Maximum number of endpoints to return
        
    Returns:
        Top endpoints sorted by various metrics
    """
    try:
        summary = get_performance_summary()
        endpoints = summary['metrics']['endpoints']
        
        # Sort by request count
        by_count = sorted(
            endpoints.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:limit]
        
        # Sort by average response time
        by_time = sorted(
            endpoints.items(),
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )[:limit]
        
        # Sort by total time
        by_total_time = sorted(
            endpoints.items(),
            key=lambda x: x[1]['total_time'],
            reverse=True
        )[:limit]
        
        return {
            "success": True,
            "data": {
                "by_request_count": [
                    {
                        "endpoint": endpoint,
                        "count": stats['count'],
                        "avg_time": round(stats['avg_time'], 4)
                    }
                    for endpoint, stats in by_count
                ],
                "by_avg_response_time": [
                    {
                        "endpoint": endpoint,
                        "avg_time": round(stats['avg_time'], 4),
                        "count": stats['count']
                    }
                    for endpoint, stats in by_time
                ],
                "by_total_time": [
                    {
                        "endpoint": endpoint,
                        "total_time": round(stats['total_time'], 4),
                        "count": stats['count']
                    }
                    for endpoint, stats in by_total_time
                ]
            }
        }
    except Exception as e:
        logger.error(f"Failed to get top endpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/cache/stats")
async def get_cache_stats_endpoint() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Cache performance statistics
    """
    try:
        stats = await get_cache_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/cache/clear")
async def clear_cache_endpoint(cache_type: str = "all") -> Dict[str, Any]:
    """
    Clear cache.
    
    Args:
        cache_type: Type of cache to clear (all, data, api)
        
    Returns:
        Cache clear results
    """
    try:
        results = {}
        
        if cache_type in ["all", "data"]:
            data_cleared = await data_cache.clear_data_cache()
            results["data_cache_cleared"] = data_cleared
        
        if cache_type in ["all", "api"]:
            api_cleared = await api_cache.clear_api_cache()
            results["api_cache_cleared"] = api_cleared
        
        return {
            "success": True,
            "data": {
                "cache_type": cache_type,
                "results": results,
                "message": f"Cache cleared successfully"
            }
        }
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))
