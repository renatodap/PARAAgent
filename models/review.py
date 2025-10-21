"""Pydantic models for weekly reviews."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import date, datetime
from enum import Enum


class ReviewStatus(str, Enum):
    """Weekly review status."""
    DRAFT = "draft"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class RolloverTask(BaseModel):
    """Task that rolled over from previous week."""
    task_id: str
    reason: str
    suggestion: str


class NextWeekProposal(BaseModel):
    """Proposed outcome for next week."""
    outcome: str
    tasks: List[str]
    estimated_hours: int


class WeeklyReviewBase(BaseModel):
    """Base schema for weekly reviews."""
    week_start_date: date
    week_end_date: date
    summary: Optional[str] = None
    insights: Dict[str, Any] = Field(default_factory=dict)
    user_notes: Optional[str] = None
    status: ReviewStatus = ReviewStatus.DRAFT


class WeeklyReviewCreate(BaseModel):
    """Schema for creating a weekly review."""
    week_start_date: date


class WeeklyReviewUpdate(BaseModel):
    """Schema for updating a weekly review."""
    summary: Optional[str] = None
    insights: Optional[Dict[str, Any]] = None
    user_notes: Optional[str] = None
    status: Optional[ReviewStatus] = None


class WeeklyReview(WeeklyReviewBase):
    """Complete weekly review schema with DB fields."""
    id: str
    user_id: str
    completed_tasks_count: int = 0
    rollover_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    next_week_proposals: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WeeklyReviewGenerateRequest(BaseModel):
    """Request to generate AI weekly review."""
    week_start_date: date
    include_calendar_events: bool = True


class WeeklyReviewInsights(BaseModel):
    """Structured insights from weekly review."""
    summary: str
    projects_update: Dict[str, str]
    areas_update: Dict[str, str]
    wins: List[str]
    rollovers: List[RolloverTask]
    next_week_proposals: List[NextWeekProposal]
    insights: List[str]


class WeeklyReviewGenerateResponse(BaseModel):
    """Response from generating weekly review."""
    review_id: str
    review_data: WeeklyReviewInsights
    usage: Dict[str, Any]
