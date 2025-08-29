"""Execution state tracking service for Steel actions."""

import asyncio
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status enum."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionState:
    """Represents the state of a single execution."""
    
    def __init__(self, run_id: str, input_text: str):
        self.run_id = run_id
        self.input_text = input_text
        self.status = ExecutionStatus.QUEUED
        self.progress = 0
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.results: Optional[Dict[str, Any]] = None
        self.created_at = datetime.now()
    
    def start(self):
        """Mark execution as started."""
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.now()
        self.progress = 25
        logger.info(f"Execution {self.run_id} started")
    
    def update_progress(self, progress: int):
        """Update execution progress."""
        self.progress = min(max(progress, 0), 100)
        logger.debug(f"Execution {self.run_id} progress: {self.progress}%")
    
    def complete(self, results: Dict[str, Any]):
        """Mark execution as completed with results."""
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.now()
        self.progress = 100
        self.results = results
        logger.info(f"Execution {self.run_id} completed successfully")
    
    def fail(self, error_message: str):
        """Mark execution as failed."""
        self.status = ExecutionStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message
        logger.error(f"Execution {self.run_id} failed: {error_message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "progress": self.progress,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() + "Z" if self.started_at else None,
            "completed_at": self.completed_at.isoformat() + "Z" if self.completed_at else None,
            "created_at": self.created_at.isoformat() + "Z",
        }
    
    def get_results(self) -> Dict[str, Any]:
        """Get execution results."""
        if self.status != ExecutionStatus.COMPLETED or not self.results:
            return {
                "run_id": self.run_id,
                "status": self.status.value,
                "message": "Execution not completed or no results available"
            }
        
        # Return results with metadata
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() + "Z" if self.started_at else None,
            "completed_at": self.completed_at.isoformat() + "Z" if self.completed_at else None,
            "execution_time": (
                int((self.completed_at - self.started_at).total_seconds() * 1000)
                if self.started_at and self.completed_at else None
            ),
            **self.results
        }


class ExecutionTracker:
    """Tracks execution states in memory."""
    
    def __init__(self):
        self._executions: Dict[str, ExecutionState] = {}
        self._cleanup_interval = 3600  # 1 hour
        self._max_age = 7200  # 2 hours
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def start_cleanup_task(self):
        """Start the periodic cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodically clean up old executions."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                current_time = time.time()
                to_remove = []
                
                for run_id, execution in self._executions.items():
                    age = current_time - execution.created_at.timestamp()
                    if age > self._max_age:
                        to_remove.append(run_id)
                
                for run_id in to_remove:
                    del self._executions[run_id]
                    logger.debug(f"Cleaned up old execution: {run_id}")
                    
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def create_execution(self, run_id: str, input_text: str) -> ExecutionState:
        """Create a new execution state."""
        execution = ExecutionState(run_id, input_text)
        self._executions[run_id] = execution
        
        # Start cleanup task if not running
        self.start_cleanup_task()
        
        logger.info(f"Created execution tracking for: {run_id}")
        return execution
    
    def get_execution(self, run_id: str) -> Optional[ExecutionState]:
        """Get execution state by run_id."""
        return self._executions.get(run_id)
    
    def start_execution(self, run_id: str):
        """Mark execution as started."""
        if execution := self._executions.get(run_id):
            execution.start()
    
    def update_progress(self, run_id: str, progress: int):
        """Update execution progress."""
        if execution := self._executions.get(run_id):
            execution.update_progress(progress)
    
    def complete_execution(self, run_id: str, results: Dict[str, Any]):
        """Mark execution as completed with results."""
        if execution := self._executions.get(run_id):
            execution.complete(results)
    
    def fail_execution(self, run_id: str, error_message: str):
        """Mark execution as failed."""
        if execution := self._executions.get(run_id):
            execution.fail(error_message)
    
    def get_status(self, run_id: str) -> Dict[str, Any]:
        """Get execution status."""
        execution = self._executions.get(run_id)
        if not execution:
            return {
                "run_id": run_id,
                "status": "not_found",
                "error_message": "Execution not found"
            }
        return execution.to_dict()
    
    def get_results(self, run_id: str) -> Dict[str, Any]:
        """Get execution results."""
        execution = self._executions.get(run_id)
        if not execution:
            return {
                "run_id": run_id,
                "status": "not_found",
                "error_message": "Execution not found"
            }
        return execution.get_results()


# Global tracker instance
execution_tracker = ExecutionTracker()