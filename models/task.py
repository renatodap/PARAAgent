"""Pydantic models for tasks."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task status options."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskSource(str, Enum):
    """Source of the task."""
    USER = "user"
    AI_SUGGESTED = "ai_suggested"
    IMPORTED = "imported"


class TaskBase(BaseModel):
    """Base schema for tasks."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    para_item_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    due_date: Optional[datetime] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    source: TaskSource = TaskSource.USER
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskCreate(TaskBase):
    """Schema for creating a task."""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    para_item_id: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    due_date: Optional[datetime] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Task(TaskBase):
    """Complete task schema with DB fields."""
    id: str
    user_id: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduledBlock(BaseModel):
    """A scheduled time block for a task."""
    task_id: str
    start_time: datetime
    end_time: datetime
    reasoning: str


class AutoScheduleRequest(BaseModel):
    """Request for auto-scheduling tasks."""
    task_ids: Optional[List[str]] = None  # If None, schedule all unscheduled tasks
    preferences: Dict[str, Any] = Field(default_factory=dict)


class AutoScheduleResponse(BaseModel):
    """Response from auto-scheduling."""
    scheduled_blocks: List[ScheduledBlock]
    approval_id: str
    usage: Dict[str, Any]
