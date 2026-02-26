"""
Ishaa Background Tasks — Async task queue and thread pool execution.
"""

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional
from enum import Enum
from functools import wraps

logger = logging.getLogger("ishaa.tasks")


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskResult:
    """Stores the result of a background task."""

    __slots__ = ("task_id", "status", "result", "error", "created_at", "completed_at")

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = time.time()
        self.completed_at = None

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "result": str(self.result) if self.result else None,
            "error": str(self.error) if self.error else None,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class TaskQueue:
    """
    Background task execution engine.
    
    Supports:
        - Async task execution
        - Thread pool for sync tasks
        - Task status tracking
        - Periodic/scheduled tasks
    
    Example:
        tasks = TaskQueue()
        
        @tasks.task
        async def send_email(to, subject, body):
            # ... send email ...
            pass
        
        # Enqueue the task
        task_id = await tasks.enqueue(send_email, "user@example.com", "Hello", "World")
        
        # Check status
        result = tasks.get_result(task_id)
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._results: Dict[str, TaskResult] = {}
        self._periodic_tasks: list = []
        self._running = False

    def task(self, func: Callable) -> Callable:
        """Decorator to mark a function as a background task."""
        func._is_task = True
        func._task_queue = self

        @wraps(func)
        async def delay(*args, **kwargs):
            return await self.enqueue(func, *args, **kwargs)

        func.delay = delay
        return func

    async def enqueue(self, func: Callable, *args, **kwargs) -> str:
        """Submit a task for background execution."""
        task_id = str(uuid.uuid4())
        task_result = TaskResult(task_id)
        self._results[task_id] = task_result

        if asyncio.iscoroutinefunction(func):
            asyncio.create_task(self._run_async_task(task_id, func, *args, **kwargs))
        else:
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                self._executor,
                self._run_sync_task,
                task_id, func, args, kwargs,
            )

        logger.info(f"Task enqueued: {task_id} ({func.__name__})")
        return task_id

    async def _run_async_task(self, task_id: str, func: Callable, *args, **kwargs):
        """Execute an async task."""
        task_result = self._results[task_id]
        task_result.status = TaskStatus.RUNNING

        try:
            result = await func(*args, **kwargs)
            task_result.result = result
            task_result.status = TaskStatus.COMPLETED
            logger.info(f"Task completed: {task_id}")
        except Exception as e:
            task_result.error = str(e)
            task_result.status = TaskStatus.FAILED
            logger.error(f"Task failed: {task_id} - {e}")
        finally:
            task_result.completed_at = time.time()

    def _run_sync_task(self, task_id: str, func: Callable, args: tuple, kwargs: dict):
        """Execute a sync task in the thread pool."""
        task_result = self._results[task_id]
        task_result.status = TaskStatus.RUNNING

        try:
            result = func(*args, **kwargs)
            task_result.result = result
            task_result.status = TaskStatus.COMPLETED
            logger.info(f"Task completed: {task_id}")
        except Exception as e:
            task_result.error = str(e)
            task_result.status = TaskStatus.FAILED
            logger.error(f"Task failed: {task_id} - {e}")
        finally:
            task_result.completed_at = time.time()

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get the result of a task."""
        return self._results.get(task_id)

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task."""
        result = self._results.get(task_id)
        return result.status if result else None

    def periodic(self, seconds: int):
        """Decorator to register a periodic task."""
        def decorator(func):
            self._periodic_tasks.append((func, seconds))
            return func
        return decorator

    async def start_periodic(self):
        """Start all periodic tasks."""
        self._running = True
        for func, interval in self._periodic_tasks:
            asyncio.create_task(self._run_periodic(func, interval))

    async def _run_periodic(self, func: Callable, interval: int):
        """Run a task periodically."""
        while self._running:
            try:
                if asyncio.iscoroutinefunction(func):
                    await func()
                else:
                    await asyncio.get_event_loop().run_in_executor(self._executor, func)
            except Exception as e:
                logger.error(f"Periodic task error ({func.__name__}): {e}")
            await asyncio.sleep(interval)

    def stop(self):
        """Stop the task queue and periodic tasks."""
        self._running = False
        self._executor.shutdown(wait=False)

    def cleanup(self, max_age: int = 3600):
        """Remove old completed task results."""
        now = time.time()
        expired = [
            tid for tid, result in self._results.items()
            if result.completed_at and (now - result.completed_at) > max_age
        ]
        for tid in expired:
            del self._results[tid]


def task(queue: TaskQueue):
    """Standalone decorator to register a function as a background task.
    
    Usage:
        queue = TaskQueue()
        
        @task(queue)
        async def send_email(to, subject):
            ...
        
        # Dispatch with:
        await send_email.delay("user@example.com", "Hello")
    """
    def decorator(func: Callable) -> Callable:
        return queue.task(func)
    return decorator
