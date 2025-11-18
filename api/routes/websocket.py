"""
WebSocket handlers for real-time updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Set
import asyncio
import json
import structlog

from shared.database.session import get_db
from shared.models.models import Deployment, DeploymentStatus
from services.monitoring.deployment_monitor import DeploymentMonitor
from services.monitoring.alerts import AlertManager

logger = structlog.get_logger()

router = APIRouter(prefix="/ws", tags=["websocket"])

# Connection manager
class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "deployments": set(),
            "alerts": set(),
            "monitoring": set(),
        }

    async def connect(self, websocket: WebSocket, channel: str):
        """Connect a WebSocket client"""
        await websocket.accept()
        if channel in self.active_connections:
            self.active_connections[channel].add(websocket)
            logger.info("websocket_connected", channel=channel)

    def disconnect(self, websocket: WebSocket, channel: str):
        """Disconnect a WebSocket client"""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            logger.info("websocket_disconnected", channel=channel)

    async def broadcast(self, message: dict, channel: str):
        """Broadcast message to all clients in channel"""
        if channel not in self.active_connections:
            return

        dead_connections = set()

        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("websocket_send_failed", error=str(e))
                dead_connections.add(connection)

        # Remove dead connections
        for connection in dead_connections:
            self.active_connections[channel].discard(connection)

    async def send_personal(self, message: dict, websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("websocket_personal_send_failed", error=str(e))


manager = ConnectionManager()
deployment_monitor = DeploymentMonitor()
alert_manager = AlertManager()


@router.websocket("/deployments")
async def websocket_deployments(websocket: WebSocket):
    """
    WebSocket endpoint for deployment updates
    """
    await manager.connect(websocket, "deployments")

    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "subscribe":
                    deployment_id = message.get("deployment_id")

                    # Send initial status
                    from shared.database.session import AsyncSessionLocal
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(
                            select(Deployment).where(Deployment.id == deployment_id)
                        )
                        deployment = result.scalar_one_or_none()

                        if deployment:
                            await manager.send_personal({
                                "type": "deployment_status",
                                "deployment_id": deployment.id,
                                "status": deployment.status,
                                "results": deployment.results,
                            }, websocket)

                elif action == "unsubscribe":
                    # Client unsubscribing from updates
                    pass

            except json.JSONDecodeError:
                logger.error("invalid_websocket_message", data=data)

    except WebSocketDisconnect:
        manager.disconnect(websocket, "deployments")


@router.websocket("/monitoring/{deployment_id}")
async def websocket_monitoring(websocket: WebSocket, deployment_id: int):
    """
    WebSocket endpoint for real-time deployment monitoring
    """
    await manager.connect(websocket, "monitoring")

    try:
        # Send initial monitoring status
        status = deployment_monitor.get_monitoring_status(deployment_id)
        await manager.send_personal({
            "type": "monitoring_status",
            "deployment_id": deployment_id,
            "status": status,
        }, websocket)

        # Stream monitoring updates
        from shared.database.session import AsyncSessionLocal

        while True:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Deployment).where(Deployment.id == deployment_id)
                )
                deployment = result.scalar_one_or_none()

                if not deployment:
                    await manager.send_personal({
                        "type": "error",
                        "message": "Deployment not found",
                    }, websocket)
                    break

                # Get assets
                assets = deployment.results.get("assets", []) if deployment.results else []

                if assets:
                    # Check health
                    health_result = await deployment_monitor.check_deployment_health(
                        deployment_id=deployment_id,
                        assets=assets,
                    )

                    # Send health update
                    await manager.send_personal({
                        "type": "health_update",
                        "deployment_id": deployment_id,
                        "health": health_result,
                        "timestamp": asyncio.get_event_loop().time(),
                    }, websocket)

                    # Collect metrics
                    metrics = {}
                    for asset in assets[:3]:  # Limit to first 3 for demo
                        metrics_result = await deployment_monitor.collect_metrics(asset)
                        if metrics_result.get("success"):
                            metrics[asset.get("name", str(asset.get("id")))] = metrics_result["metrics"]

                    if metrics:
                        await manager.send_personal({
                            "type": "metrics_update",
                            "deployment_id": deployment_id,
                            "metrics": metrics,
                            "timestamp": asyncio.get_event_loop().time(),
                        }, websocket)

            # Wait before next update
            await asyncio.sleep(10)

    except WebSocketDisconnect:
        manager.disconnect(websocket, "monitoring")
    except Exception as e:
        logger.error("websocket_monitoring_error", error=str(e), exc_info=True)
        manager.disconnect(websocket, "monitoring")


@router.websocket("/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alerts
    """
    await manager.connect(websocket, "alerts")

    try:
        # Send current active alerts
        active_alerts = alert_manager.get_active_alerts()
        await manager.send_personal({
            "type": "active_alerts",
            "alerts": active_alerts,
        }, websocket)

        # Keep connection alive and send updates
        last_alert_count = len(alert_manager.alerts)

        while True:
            # Check for new alerts
            current_count = len(alert_manager.alerts)

            if current_count > last_alert_count:
                # New alerts added
                new_alerts = alert_manager.alerts[last_alert_count:]

                for alert in new_alerts:
                    await manager.send_personal({
                        "type": "new_alert",
                        "alert": alert,
                    }, websocket)

                last_alert_count = current_count

            # Wait before next check
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect(websocket, "alerts")
    except Exception as e:
        logger.error("websocket_alerts_error", error=str(e))
        manager.disconnect(websocket, "alerts")


@router.websocket("/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard real-time updates
    """
    await manager.connect(websocket, "dashboard")

    try:
        from shared.database.session import AsyncSessionLocal
        from sqlalchemy import func

        while True:
            async with AsyncSessionLocal() as session:
                # Get real-time stats
                from shared.models.models import Vulnerability, Patch

                # Vulnerability count
                vuln_result = await session.execute(select(func.count(Vulnerability.id)))
                vuln_count = vuln_result.scalar()

                # Patch count by status
                patch_result = await session.execute(
                    select(
                        Patch.status,
                        func.count(Patch.id),
                    ).group_by(Patch.status)
                )
                patch_by_status = {status: count for status, count in patch_result.all()}

                # Deployment count
                deploy_result = await session.execute(select(func.count(Deployment.id)))
                deploy_count = deploy_result.scalar()

                # Active deployments
                active_result = await session.execute(
                    select(func.count(Deployment.id)).where(
                        Deployment.status == DeploymentStatus.IN_PROGRESS
                    )
                )
                active_count = active_result.scalar()

                # Active alerts
                active_alerts = len(alert_manager.get_active_alerts())

                # Send dashboard update
                await manager.send_personal({
                    "type": "dashboard_update",
                    "stats": {
                        "vulnerabilities": vuln_count,
                        "patches": patch_by_status,
                        "total_deployments": deploy_count,
                        "active_deployments": active_count,
                        "active_alerts": active_alerts,
                    },
                    "timestamp": asyncio.get_event_loop().time(),
                }, websocket)

            # Wait before next update
            await asyncio.sleep(15)

    except WebSocketDisconnect:
        manager.disconnect(websocket, "dashboard")
    except Exception as e:
        logger.error("websocket_dashboard_error", error=str(e))
        manager.disconnect(websocket, "dashboard")


# Helper function to broadcast deployment updates
async def broadcast_deployment_update(deployment_id: int, status: str, results: dict):
    """
    Broadcast deployment update to all connected clients
    """
    await manager.broadcast({
        "type": "deployment_update",
        "deployment_id": deployment_id,
        "status": status,
        "results": results,
    }, "deployments")


# Helper function to broadcast new alert
async def broadcast_alert(alert: dict):
    """
    Broadcast new alert to all connected clients
    """
    await manager.broadcast({
        "type": "new_alert",
        "alert": alert,
    }, "alerts")
