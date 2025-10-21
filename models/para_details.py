"""Pydantic models for PARA item details (tasks, notes, files, relationships)."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from models.para import PARAItem


class TaskPriority(str, Enum):
    """Priority levels for tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================
# TASK MODELS
# ============================================================

class PARATaskBase(BaseModel):
    """Base schema for tasks."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None


class PARATaskCreate(PARATaskBase):
    """Schema for creating a task."""
    pass


class PARATaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None


class PARATask(PARATaskBase):
    """Complete task schema with DB fields."""
    id: str
    para_item_id: str
    user_id: str
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# NOTE MODELS
# ============================================================

class PARANoteBase(BaseModel):
    """Base schema for notes."""
    content: str = Field(..., min_length=1)


class PARANoteCreate(PARANoteBase):
    """Schema for creating a note."""
    pass


class PARANoteUpdate(BaseModel):
    """Schema for updating a note."""
    content: str = Field(..., min_length=1)


class PARANote(PARANoteBase):
    """Complete note schema with DB fields."""
    id: str
    para_item_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# FILE MODELS
# ============================================================

class PARAFileBase(BaseModel):
    """Base schema for files."""
    file_name: str
    file_url: str
    file_type: str
    file_size: Optional[int] = None


class PARAFileCreate(PARAFileBase):
    """Schema for creating a file record."""
    pass


class PARAFile(PARAFileBase):
    """Complete file schema with DB fields."""
    id: str
    para_item_id: str
    user_id: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# RELATIONSHIP MODELS
# ============================================================

class PARARelationshipCreate(BaseModel):
    """Schema for creating a relationship."""
    to_item_id: str
    relationship_type: str = "related"


class PARARelationship(BaseModel):
    """Complete relationship schema."""
    id: str
    from_item_id: str
    to_item_id: str
    user_id: str
    relationship_type: str
    created_at: datetime

    # Include the related item's basic info
    related_item: Optional[PARAItem] = None

    class Config:
        from_attributes = True


# ============================================================
# DETAILED PARA ITEM (WITH ALL RELATED DATA)
# ============================================================

class PARAItemDetailed(PARAItem):
    """
    PARA item with all related data for detail pages.
    Extends the base PARAItem with tasks, notes, files, and relationships.
    """
    tasks: List[PARATask] = Field(default_factory=list)
    notes: List[PARANote] = Field(default_factory=list)
    files: List[PARAFile] = Field(default_factory=list)
    relationships: List[PARARelationship] = Field(default_factory=list)

    # Computed fields
    active_tasks_count: int = 0
    completed_tasks_count: int = 0
    completion_percentage: int = 0

    class Config:
        from_attributes = True
