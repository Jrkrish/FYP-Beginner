"""
Task Queue Module

Manages task scheduling and execution for agents.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import asyncio
import heapq
from collections import defaultdict
from loguru import logger

from src.dev_pilot.agents.agent_message import AgentTask, MessagePriority


class TaskQueue(ABC):
    """Abstract base class for task queue implementations."""
    
    @abstractmethod
    async def enqueue(self, task: AgentTask) -> str:
        """Add a task to the queue."""
        pass
    
    @abstractmethod
    async def dequeue(self, agent_type: Optional[str] = None) -> Optional[AgentTask]:
        """Get the next task from the queue."""
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[AgentTask]:
        """Get a task by ID."""
        pass
    
    @abstractmethod
    async def update_task(self, task: AgentTask):
        """Update a task."""
        pass
    
    @abstractmethod
    async def get_pending_tasks(self, agent_type: Optional[str] = None) -> List[AgentTask]:
        """Get all pending tasks."""
        pass


class PriorityQueueItem:
    """Wrapper for priority queue items."""
    
    def __init__(self, priority: int, timestamp: datetime, task: AgentTask):
        self.priority = priority
        self.timestamp = timestamp
        self.task = task
    
    def __lt__(self, other):
        # Lower priority number = higher priority
        # For same priority, earlier timestamp wins
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class InMemoryTaskQueue(TaskQueue):
    """
    In-memory task queue implementation.
    
    Uses priority queues for task scheduling.
    """
    
    def __init__(self):
        # Priority queue for all tasks
        self._queue: List[PriorityQueueItem] = []
        
        # Per-agent-type queues
        self._type_queues: Dict[str, List[PriorityQueueItem]] = defaultdict(list)
        
        # Task storage by ID
        self._tasks: Dict[str, AgentTask] = {}
        
        # Task status tracking
        self._pending_tasks: Dict[str, AgentTask] = {}
        self._running_tasks: Dict[str, AgentTask] = {}
        self._completed_tasks: Dict[str, AgentTask] = {}
        self._failed_tasks: Dict[str, AgentTask] = {}
        
        # Callbacks
        self._task_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Metrics
        self._metrics = {
            "total_enqueued": 0,
            "total_completed": 0,
            "total_failed": 0,
        }
        
        logger.info("InMemoryTaskQueue initialized")
    
    async def enqueue(self, task: AgentTask) -> str:
        """
        Add a task to the queue.
        
        Args:
            task: The task to enqueue
            
        Returns:
            The task ID
        """
        # Store the task
        self._tasks[task.task_id] = task
        self._pending_tasks[task.task_id] = task
        
        # Create priority queue item
        item = PriorityQueueItem(
            priority=task.priority.value,
            timestamp=task.created_at,
            task=task
        )
        
        # Add to main queue
        heapq.heappush(self._queue, item)
        
        # Add to type-specific queue if agent is specified
        if task.assigned_agent:
            agent_type = task.assigned_agent.split("-")[0] if "-" in task.assigned_agent else task.assigned_agent
            heapq.heappush(self._type_queues[agent_type], item)
        
        self._metrics["total_enqueued"] += 1
        
        logger.debug(f"Task enqueued: {task.task_id} (priority: {task.priority.value})")
        
        # Trigger callbacks
        await self._trigger_callbacks("task_enqueued", task)
        
        return task.task_id
    
    async def dequeue(self, agent_type: Optional[str] = None) -> Optional[AgentTask]:
        """
        Get the next task from the queue.
        
        Args:
            agent_type: Optional filter for specific agent type
            
        Returns:
            The next task or None if queue is empty
        """
        if agent_type and agent_type in self._type_queues:
            queue = self._type_queues[agent_type]
        else:
            queue = self._queue
        
        while queue:
            item = heapq.heappop(queue)
            task = item.task
            
            # Check if task is still pending
            if task.task_id in self._pending_tasks:
                # Move to running
                del self._pending_tasks[task.task_id]
                self._running_tasks[task.task_id] = task
                
                logger.debug(f"Task dequeued: {task.task_id}")
                return task
        
        return None
    
    async def get_task(self, task_id: str) -> Optional[AgentTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    async def update_task(self, task: AgentTask):
        """
        Update a task's status.
        
        Moves task between status dictionaries based on status.
        """
        self._tasks[task.task_id] = task
        
        # Remove from current status dict
        for status_dict in [self._pending_tasks, self._running_tasks, 
                           self._completed_tasks, self._failed_tasks]:
            if task.task_id in status_dict:
                del status_dict[task.task_id]
                break
        
        # Add to appropriate status dict
        if task.status == "pending":
            self._pending_tasks[task.task_id] = task
        elif task.status == "running":
            self._running_tasks[task.task_id] = task
        elif task.status == "completed":
            self._completed_tasks[task.task_id] = task
            self._metrics["total_completed"] += 1
            await self._trigger_callbacks("task_completed", task)
        elif task.status == "failed":
            self._failed_tasks[task.task_id] = task
            self._metrics["total_failed"] += 1
            await self._trigger_callbacks("task_failed", task)
        
        logger.debug(f"Task updated: {task.task_id} -> {task.status}")
    
    async def get_pending_tasks(self, agent_type: Optional[str] = None) -> List[AgentTask]:
        """Get all pending tasks."""
        tasks = list(self._pending_tasks.values())
        
        if agent_type:
            tasks = [
                t for t in tasks 
                if t.assigned_agent and t.assigned_agent.startswith(agent_type)
            ]
        
        # Sort by priority and timestamp
        tasks.sort(key=lambda t: (t.priority.value, t.created_at))
        
        return tasks
    
    async def get_running_tasks(self) -> List[AgentTask]:
        """Get all running tasks."""
        return list(self._running_tasks.values())
    
    async def get_completed_tasks(self, limit: int = 100) -> List[AgentTask]:
        """Get completed tasks."""
        tasks = list(self._completed_tasks.values())
        return sorted(tasks, key=lambda t: t.completed_at or datetime.min, reverse=True)[:limit]
    
    async def get_failed_tasks(self, limit: int = 100) -> List[AgentTask]:
        """Get failed tasks."""
        tasks = list(self._failed_tasks.values())
        return sorted(tasks, key=lambda t: t.completed_at or datetime.min, reverse=True)[:limit]
    
    async def retry_task(self, task_id: str) -> bool:
        """
        Retry a failed task.
        
        Args:
            task_id: ID of the task to retry
            
        Returns:
            True if task was re-enqueued
        """
        task = self._failed_tasks.get(task_id)
        if not task:
            return False
        
        # Reset task state
        task.status = "pending"
        task.result = None
        task.started_at = None
        task.completed_at = None
        
        # Move back to pending
        del self._failed_tasks[task_id]
        
        # Re-enqueue
        await self.enqueue(task)
        
        logger.info(f"Task retried: {task_id}")
        return True
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if task was cancelled
        """
        task = self._pending_tasks.get(task_id)
        if not task:
            return False
        
        task.status = "cancelled"
        task.metadata["cancelled_at"] = datetime.utcnow().isoformat()
        
        del self._pending_tasks[task_id]
        
        logger.info(f"Task cancelled: {task_id}")
        await self._trigger_callbacks("task_cancelled", task)
        
        return True
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for task events."""
        self._task_callbacks[event].append(callback)
    
    async def _trigger_callbacks(self, event: str, task: AgentTask):
        """Trigger callbacks for an event."""
        for callback in self._task_callbacks[event]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"Error in task callback: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics."""
        return {
            **self._metrics,
            "pending_count": len(self._pending_tasks),
            "running_count": len(self._running_tasks),
            "completed_count": len(self._completed_tasks),
            "failed_count": len(self._failed_tasks),
            "queue_size": len(self._queue),
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed queue status."""
        return {
            "metrics": self.get_metrics(),
            "pending_by_priority": self._count_by_priority(self._pending_tasks),
            "running_tasks": [t.task_id for t in self._running_tasks.values()],
        }
    
    def _count_by_priority(self, tasks: Dict[str, AgentTask]) -> Dict[str, int]:
        """Count tasks by priority."""
        counts = defaultdict(int)
        for task in tasks.values():
            counts[task.priority.name] += 1
        return dict(counts)
    
    def clear(self):
        """Clear all tasks from the queue."""
        self._queue.clear()
        self._type_queues.clear()
        self._tasks.clear()
        self._pending_tasks.clear()
        self._running_tasks.clear()
        self._completed_tasks.clear()
        self._failed_tasks.clear()
        logger.info("TaskQueue cleared")


class DependencyTracker:
    """
    Tracks task dependencies and determines execution order.
    """
    
    def __init__(self):
        self._dependencies: Dict[str, List[str]] = {}  # task_id -> [dependency_ids]
        self._dependents: Dict[str, List[str]] = defaultdict(list)  # task_id -> [dependent_ids]
        self._completed: set = set()
    
    def add_dependency(self, task_id: str, depends_on: str):
        """Add a dependency relationship."""
        if task_id not in self._dependencies:
            self._dependencies[task_id] = []
        self._dependencies[task_id].append(depends_on)
        self._dependents[depends_on].append(task_id)
    
    def mark_completed(self, task_id: str):
        """Mark a task as completed."""
        self._completed.add(task_id)
    
    def can_execute(self, task_id: str) -> bool:
        """Check if a task can be executed (all dependencies completed)."""
        deps = self._dependencies.get(task_id, [])
        return all(dep in self._completed for dep in deps)
    
    def get_ready_tasks(self, pending_tasks: List[str]) -> List[str]:
        """Get tasks that are ready to execute."""
        return [t for t in pending_tasks if self.can_execute(t)]
    
    def get_dependents(self, task_id: str) -> List[str]:
        """Get tasks that depend on the given task."""
        return self._dependents.get(task_id, [])
    
    def clear(self):
        """Clear all tracking data."""
        self._dependencies.clear()
        self._dependents.clear()
        self._completed.clear()
