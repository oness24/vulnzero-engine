"""
Task Status Endpoints

Endpoints for checking Celery task status and results.
Allows users to track the progress of async operations like deployments and scans.
"""

from fastapi import APIRouter, HTTPException, Depends, Path
from celery.result import AsyncResult
from typing import Optional, Dict, Any
import logging

from services.api_gateway.core.security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/{task_id}",
    summary="Get Task Status",
    description="Get the status and result of a Celery task by its ID.",
    response_description="Task status information including state, result, and metadata"
)
async def get_task_status(
    task_id: str = Path(..., description="Celery task ID returned by async endpoints"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the status of a Celery task.

    This endpoint allows you to check the status of asynchronous operations
    like deployments, vulnerability scans, and patch generation.

    **Task States:**
    - `PENDING`: Task is waiting to be executed
    - `STARTED`: Task has started executing
    - `SUCCESS`: Task completed successfully
    - `FAILURE`: Task failed with an error
    - `RETRY`: Task is being retried
    - `REVOKED`: Task was cancelled

    **Example Usage:**
    ```bash
    # Trigger a deployment
    curl -X POST /api/v1/deployments -d '{"patch_id": 1, "asset_id": 1}'
    # Response: {"id": 123, "status": "pending"}

    # Check deployment task status
    curl /api/v1/tasks/{task_id}
    # Response: {"task_id": "abc-123", "state": "SUCCESS", "result": {...}}
    ```

    Args:
        task_id: The Celery task ID to query
        current_user: Authenticated user (from JWT token)

    Returns:
        Task status information including:
        - task_id: The task identifier
        - state: Current task state (PENDING, SUCCESS, FAILURE, etc.)
        - ready: Whether the task has completed (success or failure)
        - successful: Whether the task completed successfully (null if not ready)
        - result: Task result if successful
        - error: Error information if failed
        - info: Additional task information
        - progress: Task progress information (if available)

    Raises:
        HTTPException: If task ID is invalid
    """
    try:
        # Create AsyncResult object to query task status
        result = AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "state": result.state,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
        }

        # Add result or error information based on state
        if result.ready():
            if result.successful():
                # Task completed successfully
                response["result"] = result.result
                response["completed_at"] = result.date_done.isoformat() if result.date_done else None
            else:
                # Task failed
                response["error"] = str(result.info)
                response["traceback"] = result.traceback if hasattr(result, 'traceback') else None
                response["failed_at"] = result.date_done.isoformat() if result.date_done else None
        else:
            # Task is still running or pending
            response["info"] = result.info if result.info else None

            # Check if task has progress information
            if isinstance(result.info, dict):
                progress = result.info.get('progress')
                if progress:
                    response["progress"] = progress

        logger.info(f"Task status queried: {task_id} - State: {result.state}", extra={
            "task_id": task_id,
            "state": result.state,
            "user_id": current_user.get("id")
        })

        return response

    except Exception as e:
        logger.error(f"Error retrieving task status: {e}", exc_info=True, extra={
            "task_id": task_id,
            "user_id": current_user.get("id")
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve task status: {str(e)}"
        )


@router.delete(
    "/{task_id}",
    summary="Cancel Task",
    description="Cancel/revoke a running Celery task.",
    response_description="Cancellation confirmation"
)
async def cancel_task(
    task_id: str = Path(..., description="Celery task ID to cancel"),
    terminate: bool = False,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Cancel a running Celery task.

    This endpoint allows you to cancel an in-progress task like a deployment
    or scan operation.

    **Warning:** Cancelling a deployment task may leave systems in an
    inconsistent state. Use with caution.

    Args:
        task_id: The Celery task ID to cancel
        terminate: If True, forcefully terminate the task (default: False)
        current_user: Authenticated user (from JWT token)

    Returns:
        Cancellation confirmation with task ID and status

    Raises:
        HTTPException: If task cannot be cancelled
    """
    try:
        result = AsyncResult(task_id)

        # Check if task is already complete
        if result.ready():
            logger.warning(f"Attempted to cancel completed task: {task_id}", extra={
                "task_id": task_id,
                "state": result.state,
                "user_id": current_user.get("id")
            })
            return {
                "task_id": task_id,
                "cancelled": False,
                "message": f"Task already completed with state: {result.state}"
            }

        # Revoke the task
        result.revoke(terminate=terminate)

        logger.warning(f"Task cancelled by user: {task_id}", extra={
            "task_id": task_id,
            "terminated": terminate,
            "user_id": current_user.get("id"),
            "user_email": current_user.get("email")
        })

        return {
            "task_id": task_id,
            "cancelled": True,
            "terminated": terminate,
            "message": "Task cancellation requested"
        }

    except Exception as e:
        logger.error(f"Error cancelling task: {e}", exc_info=True, extra={
            "task_id": task_id,
            "user_id": current_user.get("id")
        })
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.get(
    "",
    summary="List Recent Tasks",
    description="List recent Celery tasks (requires Redis result backend)",
    response_description="List of recent task IDs and their states"
)
async def list_recent_tasks(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    List recent Celery tasks.

    Note: This endpoint requires a result backend that supports task
    inspection (e.g., Redis). It may not work with all backends.

    Args:
        limit: Maximum number of tasks to return (default: 20, max: 100)
        current_user: Authenticated user (from JWT token)

    Returns:
        List of recent tasks with their IDs and states

    Raises:
        HTTPException: If task listing is not supported
    """
    try:
        from celery import current_app as celery_app

        # Get active tasks
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()

        tasks = []

        # Collect active tasks
        if active_tasks:
            for worker, worker_tasks in active_tasks.items():
                for task in worker_tasks[:limit]:
                    tasks.append({
                        "task_id": task.get("id"),
                        "name": task.get("name"),
                        "state": "ACTIVE",
                        "worker": worker,
                        "started_at": task.get("time_start")
                    })

        # Collect scheduled tasks
        if scheduled_tasks:
            for worker, worker_tasks in scheduled_tasks.items():
                for task in worker_tasks[:limit]:
                    tasks.append({
                        "task_id": task.get("id"),
                        "name": task.get("name"),
                        "state": "SCHEDULED",
                        "worker": worker,
                        "eta": task.get("eta")
                    })

        # Collect reserved tasks
        if reserved_tasks:
            for worker, worker_tasks in reserved_tasks.items():
                for task in worker_tasks[:limit]:
                    tasks.append({
                        "task_id": task.get("id"),
                        "name": task.get("name"),
                        "state": "RESERVED",
                        "worker": worker
                    })

        logger.info(f"Listed {len(tasks)} recent tasks", extra={
            "count": len(tasks),
            "user_id": current_user.get("id")
        })

        return {
            "tasks": tasks[:limit],
            "count": len(tasks),
            "limit": limit
        }

    except Exception as e:
        logger.warning(f"Task listing not available: {e}", extra={
            "user_id": current_user.get("id")
        })
        raise HTTPException(
            status_code=503,
            detail="Task listing not available. Ensure Celery workers are running and result backend supports inspection."
        )
