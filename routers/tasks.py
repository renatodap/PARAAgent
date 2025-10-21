"""API router for tasks endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
from auth import get_current_user_id
from database import db, supabase
from models.task import (
    Task,
    TaskCreate,
    TaskUpdate,
    TaskStatus,
    TaskPriority,
    AutoScheduleRequest,
    AutoScheduleResponse
)

router = APIRouter()


@router.get("/", response_model=List[Task])
async def get_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    priority: Optional[TaskPriority] = None,
    para_item_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """Get all tasks for current user with optional filters."""
    filters = {}
    if status_filter:
        filters["status"] = status_filter.value
    if priority:
        filters["priority"] = priority.value
    if para_item_id:
        filters["para_item_id"] = para_item_id

    tasks = db.get_user_data(user_id, "tasks", filters)
    return tasks


@router.get("/unscheduled", response_model=List[Task])
async def get_unscheduled_tasks(
    user_id: str = Depends(get_current_user_id)
):
    """Get all tasks that haven't been scheduled yet."""
    result = supabase.table("tasks")\
        .select("*")\
        .eq("user_id", user_id)\
        .is_("scheduled_start", "null")\
        .in_("status", ["pending", "in_progress"])\
        .execute()

    return result.data


@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific task by ID."""
    tasks = db.get_user_data(user_id, "tasks", {"id": task_id})

    if not tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return tasks[0]


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new task."""
    task_data = task.model_dump()
    task_data["user_id"] = user_id

    created_task = db.insert_record("tasks", task_data)
    return created_task


@router.put("/{task_id}", response_model=Task)
async def update_task(
    task_id: str,
    task: TaskUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Update a task."""
    # Verify ownership
    existing_tasks = db.get_user_data(user_id, "tasks", {"id": task_id})
    if not existing_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Auto-set completed_at if status changes to completed
    update_data = task.model_dump(exclude_unset=True)
    if task.status == TaskStatus.COMPLETED and not task.completed_at:
        update_data["completed_at"] = datetime.utcnow().isoformat()

    updated_task = db.update_record("tasks", task_id, update_data)
    return updated_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a task."""
    # Verify ownership
    existing_tasks = db.get_user_data(user_id, "tasks", {"id": task_id})
    if not existing_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    success = db.delete_record("tasks", task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )


@router.post("/schedule", response_model=AutoScheduleResponse)
async def auto_schedule_tasks(
    request: AutoScheduleRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Auto-schedule tasks using AI."""
    from agents.scheduler import auto_schedule_tasks as ai_schedule

    # Get tasks to schedule
    if request.task_ids:
        tasks = []
        for task_id in request.task_ids:
            task_data = db.get_user_data(user_id, "tasks", {"id": task_id})
            if task_data:
                tasks.extend(task_data)
    else:
        # Get all unscheduled tasks
        result = supabase.table("tasks")\
            .select("*")\
            .eq("user_id", user_id)\
            .is_("scheduled_start", "null")\
            .in_("status", ["pending", "in_progress"])\
            .execute()
        tasks = result.data

    if not tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tasks to schedule"
        )

    # Get calendar events to avoid conflicts
    result = supabase.table("calendar_events")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("start_time", datetime.utcnow().isoformat())\
        .execute()
    calendar_events = result.data

    # Get user preferences
    profile = supabase.table("user_profiles")\
        .select("para_preferences")\
        .eq("id", user_id)\
        .execute()
    preferences = profile.data[0]["para_preferences"] if profile.data else {}

    # Merge with request preferences
    final_preferences = {**preferences, **request.preferences}

    # Call AI scheduler
    result = ai_schedule(
        tasks=tasks,
        calendar_events=calendar_events,
        user_preferences=final_preferences,
        user_id=user_id
    )

    # Log the action
    db.log_agent_action(
        user_id=user_id,
        action_type="schedule",
        input_data={"task_count": len(tasks), "preferences": final_preferences},
        output_data=result,
        model_used="claude-haiku-4.5",
        tokens_used=result["usage"]["tokens"],
        cost_usd=result["usage"]["cost_usd"]
    )

    return result
