"""Pydantic models for PARA Autopilot API."""

from .para import (
    PARAType,
    PARAStatus,
    PARAItem,
    PARAItemCreate,
    PARAItemUpdate,
    PARAClassificationRequest,
    PARAClassificationResult,
    PARAClassificationResponse
)

from .task import (
    TaskStatus,
    TaskPriority,
    TaskSource,
    Task,
    TaskCreate,
    TaskUpdate,
    ScheduledBlock,
    AutoScheduleRequest,
    AutoScheduleResponse
)

from .review import (
    ReviewStatus,
    WeeklyReview,
    WeeklyReviewCreate,
    WeeklyReviewUpdate,
    WeeklyReviewGenerateRequest,
    WeeklyReviewInsights,
    WeeklyReviewGenerateResponse
)

__all__ = [
    # PARA
    "PARAType",
    "PARAStatus",
    "PARAItem",
    "PARAItemCreate",
    "PARAItemUpdate",
    "PARAClassificationRequest",
    "PARAClassificationResult",
    "PARAClassificationResponse",
    # Tasks
    "TaskStatus",
    "TaskPriority",
    "TaskSource",
    "Task",
    "TaskCreate",
    "TaskUpdate",
    "ScheduledBlock",
    "AutoScheduleRequest",
    "AutoScheduleResponse",
    # Reviews
    "ReviewStatus",
    "WeeklyReview",
    "WeeklyReviewCreate",
    "WeeklyReviewUpdate",
    "WeeklyReviewGenerateRequest",
    "WeeklyReviewInsights",
    "WeeklyReviewGenerateResponse"
]
