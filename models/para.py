"""Pydantic models for PARA items."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class PARAType(str, Enum):
    """PARA category types."""
    PROJECT = "project"
    AREA = "area"
    RESOURCE = "resource"
    ARCHIVE = "archive"


class PARAStatus(str, Enum):
    """Status options for PARA items."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ON_HOLD = "on_hold"


class PARAItemBase(BaseModel):
    """Base schema for PARA items."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    para_type: PARAType
    status: PARAStatus = PARAStatus.ACTIVE
    due_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PARAItemCreate(PARAItemBase):
    """Schema for creating a PARA item."""
    pass


class PARAItemUpdate(BaseModel):
    """Schema for updating a PARA item."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    para_type: Optional[PARAType] = None
    status: Optional[PARAStatus] = None
    due_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class PARAItem(PARAItemBase):
    """Complete PARA item schema with DB fields."""
    id: str
    user_id: str
    completion_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PARAClassificationRequest(BaseModel):
    """Request schema for AI classification."""
    title: str
    description: Optional[str] = None
    context: Optional[str] = None


class PARAClassificationResult(BaseModel):
    """AI classification result."""
    para_type: PARAType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    suggested_next_actions: List[str] = Field(default_factory=list)
    estimated_duration_weeks: Optional[int] = None


class PARAClassificationResponse(BaseModel):
    """Response for classification endpoint."""
    classification: PARAClassificationResult
    item_id: Optional[str] = None
    usage: Dict[str, Any]
