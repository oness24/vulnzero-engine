"""
Health Check System
===================

Comprehensive health check system with liveness and readiness probes
for production deployment and Kubernetes readiness.

Concepts:
---------
- **Liveness**: Is the application running and responsive?
  - Failures should trigger container restart
  - Should NOT check external dependencies
  - Quick and lightweight

- **Readiness**: Is the application ready to serve traffic?
  - Failures should remove from load balancer
  - Should check critical dependencies
  - Can take longer to execute

- **Health**: Overall health status with detailed diagnostics
  - Shows status of all components
  - Used for monitoring and dashboards
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status for a single component"""
    name: str
    status: HealthStatus
    message: str = ""
    response_time_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """
    Health check orchestrator.

    Performs various health checks on application components
    and aggregates results.
    """

    def __init__(self):
        self.startup_time = time.time()
        self._readiness_checks: List[str] = []
        self._critical_components = {"database", "redis"}

    def get_uptime(self) -> float:
        """Get application uptime in seconds"""
        return time.time() - self.startup_time

    async def check_liveness(self) -> Dict[str, Any]:
        """
        Liveness check - is the application alive and responsive?

        This is a lightweight check that should always pass unless
        the application is truly dead. Does NOT check dependencies.

        Returns:
            Dict with liveness status
        """
        return {
            "status": HealthStatus.HEALTHY,
            "alive": True,
            "uptime_seconds": self.get_uptime(),
            "timestamp": time.time(),
        }

    async def check_database(self) -> ComponentHealth:
        """
        Check database connectivity and performance.

        Returns:
            ComponentHealth object with database status
        """
        from shared.config.database import engine

        start_time = time.time()

        try:
            # Test basic connectivity
            with engine.connect() as conn:
                result = conn.execute("SELECT 1 AS health_check")
                row = result.fetchone()

                if row and row[0] == 1:
                    response_time = (time.time() - start_time) * 1000

                    # Warn if database is slow
                    if response_time > 1000:  # > 1 second
                        return ComponentHealth(
                            name="database",
                            status=HealthStatus.DEGRADED,
                            message=f"Database responding slowly ({response_time:.0f}ms)",
                            response_time_ms=response_time,
                        )

                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.HEALTHY,
                        message="Connected",
                        response_time_ms=response_time,
                    )
                else:
                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.UNHEALTHY,
                        message="Query returned unexpected result",
                    )

        except Exception as e:
            logger.error(f"Database health check failed: {e}", exc_info=True)
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection failed: {str(e)[:100]}",
            )

    async def check_redis(self) -> ComponentHealth:
        """
        Check Redis connectivity and performance.

        Returns:
            ComponentHealth object with Redis status
        """
        try:
            from shared.cache.redis_client import get_redis_client

            start_time = time.time()
            redis_client = await get_redis_client()

            # Test ping
            pong = await redis_client.ping()
            response_time = (time.time() - start_time) * 1000

            if pong:
                # Get additional info
                try:
                    info = await redis_client.info('server')
                    details = {
                        "version": info.get("redis_version", "unknown"),
                        "uptime_days": info.get("uptime_in_days", 0),
                    }
                except Exception:
                    details = {}

                if response_time > 500:  # > 500ms
                    return ComponentHealth(
                        name="redis",
                        status=HealthStatus.DEGRADED,
                        message=f"Redis responding slowly ({response_time:.0f}ms)",
                        response_time_ms=response_time,
                        details=details,
                    )

                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Connected",
                    response_time_ms=response_time,
                    details=details,
                )
            else:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.UNHEALTHY,
                    message="Ping failed",
                )

        except Exception as e:
            logger.error(f"Redis health check failed: {e}", exc_info=True)
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection failed: {str(e)[:100]}",
            )

    async def check_celery_workers(self) -> ComponentHealth:
        """
        Check Celery worker availability.

        Returns:
            ComponentHealth object with Celery status
        """
        try:
            from shared.celery_app import celery_app

            start_time = time.time()

            # Inspect active workers
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()

            response_time = (time.time() - start_time) * 1000

            if active_workers:
                worker_count = len(active_workers)
                return ComponentHealth(
                    name="celery_workers",
                    status=HealthStatus.HEALTHY,
                    message=f"{worker_count} worker(s) active",
                    response_time_ms=response_time,
                    details={"worker_count": worker_count},
                )
            else:
                return ComponentHealth(
                    name="celery_workers",
                    status=HealthStatus.DEGRADED,
                    message="No active workers found",
                    response_time_ms=response_time,
                )

        except Exception as e:
            logger.warning(f"Celery health check failed: {e}")
            return ComponentHealth(
                name="celery_workers",
                status=HealthStatus.DEGRADED,
                message="Unable to check worker status",
            )

    async def check_disk_space(self) -> ComponentHealth:
        """
        Check available disk space.

        Returns:
            ComponentHealth object with disk status
        """
        try:
            import shutil

            # Check primary data directory
            from shared.config.settings import settings
            data_path = getattr(settings, 'data_path', '/app')

            stat = shutil.disk_usage(data_path)

            # Calculate percentage used
            percent_used = (stat.used / stat.total) * 100
            percent_free = 100 - percent_used

            details = {
                "total_gb": round(stat.total / (1024**3), 2),
                "used_gb": round(stat.used / (1024**3), 2),
                "free_gb": round(stat.free / (1024**3), 2),
                "percent_used": round(percent_used, 2),
                "percent_free": round(percent_free, 2),
            }

            if percent_used > 90:
                return ComponentHealth(
                    name="disk_space",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Disk usage critical: {percent_used:.1f}% used",
                    details=details,
                )
            elif percent_used > 80:
                return ComponentHealth(
                    name="disk_space",
                    status=HealthStatus.DEGRADED,
                    message=f"Disk usage high: {percent_used:.1f}% used",
                    details=details,
                )
            else:
                return ComponentHealth(
                    name="disk_space",
                    status=HealthStatus.HEALTHY,
                    message=f"{percent_free:.1f}% free",
                    details=details,
                )

        except Exception as e:
            logger.warning(f"Disk space check failed: {e}")
            return ComponentHealth(
                name="disk_space",
                status=HealthStatus.DEGRADED,
                message="Unable to check disk space",
            )

    async def check_memory(self) -> ComponentHealth:
        """
        Check available memory.

        Returns:
            ComponentHealth object with memory status
        """
        try:
            import psutil

            memory = psutil.virtual_memory()
            percent_used = memory.percent

            details = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent_used": percent_used,
                "percent_free": 100 - percent_used,
            }

            if percent_used > 90:
                return ComponentHealth(
                    name="memory",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Memory usage critical: {percent_used:.1f}% used",
                    details=details,
                )
            elif percent_used > 80:
                return ComponentHealth(
                    name="memory",
                    status=HealthStatus.DEGRADED,
                    message=f"Memory usage high: {percent_used:.1f}% used",
                    details=details,
                )
            else:
                return ComponentHealth(
                    name="memory",
                    status=HealthStatus.HEALTHY,
                    message=f"{100 - percent_used:.1f}% free",
                    details=details,
                )

        except ImportError:
            # psutil not available
            return ComponentHealth(
                name="memory",
                status=HealthStatus.HEALTHY,
                message="psutil not available, skipping check",
            )
        except Exception as e:
            logger.warning(f"Memory check failed: {e}")
            return ComponentHealth(
                name="memory",
                status=HealthStatus.DEGRADED,
                message="Unable to check memory",
            )

    async def check_readiness(self) -> Dict[str, Any]:
        """
        Readiness check - is the application ready to serve traffic?

        Checks critical dependencies:
        - Database connection
        - Redis connection

        Returns:
            Dict with readiness status and component details
        """
        # Check critical dependencies in parallel
        db_check, redis_check = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
        )

        components = {
            "database": {
                "status": db_check.status,
                "message": db_check.message,
                "response_time_ms": db_check.response_time_ms,
            },
            "redis": {
                "status": redis_check.status,
                "message": redis_check.message,
                "response_time_ms": redis_check.response_time_ms,
            },
        }

        # Determine overall readiness
        # Application is ready only if all critical components are healthy
        critical_components = [db_check, redis_check]
        all_healthy = all(c.status == HealthStatus.HEALTHY for c in critical_components)
        any_unhealthy = any(c.status == HealthStatus.UNHEALTHY for c in critical_components)

        if all_healthy:
            overall_status = HealthStatus.HEALTHY
            ready = True
        elif any_unhealthy:
            overall_status = HealthStatus.UNHEALTHY
            ready = False
        else:
            overall_status = HealthStatus.DEGRADED
            ready = True  # Still ready, but degraded

        return {
            "status": overall_status,
            "ready": ready,
            "components": components,
            "timestamp": time.time(),
        }

    async def check_health(self, include_optional: bool = True) -> Dict[str, Any]:
        """
        Comprehensive health check - detailed status of all components.

        Args:
            include_optional: Whether to include optional component checks

        Returns:
            Dict with complete health status
        """
        from shared.config.settings import settings

        # Check all components in parallel
        checks = [
            self.check_database(),
            self.check_redis(),
        ]

        if include_optional:
            checks.extend([
                self.check_celery_workers(),
                self.check_disk_space(),
                self.check_memory(),
            ])

        results = await asyncio.gather(*checks, return_exceptions=True)

        # Build components dict
        components = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check failed with exception: {result}")
                continue
            if isinstance(result, ComponentHealth):
                components[result.name] = {
                    "status": result.status,
                    "message": result.message,
                    "response_time_ms": result.response_time_ms,
                    "details": result.details,
                }

        # Determine overall health
        statuses = [c["status"] for c in components.values()]

        if not statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            # Check if unhealthy component is critical
            unhealthy_components = [
                name for name, data in components.items()
                if data["status"] == HealthStatus.UNHEALTHY
            ]
            if any(c in self._critical_components for c in unhealthy_components):
                overall_status = HealthStatus.UNHEALTHY
            else:
                overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status,
            "version": "0.1.0",
            "environment": settings.environment,
            "uptime_seconds": self.get_uptime(),
            "components": components,
            "timestamp": time.time(),
        }


# Global health checker instance
health_checker = HealthChecker()
