"""API router for PARA items endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from auth import get_current_user_id
from database import db
from models.para import (
    PARAItem,
    PARAItemCreate,
    PARAItemUpdate,
    PARAClassificationRequest,
    PARAClassificationResponse,
    PARAType,
    PARAStatus
)
from models.para_details import (
    PARAItemDetailed,
    PARATask,
    PARATaskCreate,
    PARATaskUpdate,
    PARANote,
    PARANoteCreate,
    PARANoteUpdate,
    PARAFile,
    PARAFileCreate,
    PARARelationship,
    PARARelationshipCreate
)

router = APIRouter()


@router.get("/", response_model=List[PARAItem])
async def get_para_items(
    para_type: Optional[PARAType] = None,
    status: Optional[PARAStatus] = None,
    user_id: str = Depends(get_current_user_id)
):
    """Get all PARA items for current user with optional filters."""
    filters = {}
    if para_type:
        filters["para_type"] = para_type.value
    if status:
        filters["status"] = status.value

    items = db.get_user_data(user_id, "para_items", filters)
    return items


@router.get("/{item_id}", response_model=PARAItem)
async def get_para_item(
    item_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific PARA item by ID."""
    items = db.get_user_data(user_id, "para_items", {"id": item_id})

    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    return items[0]


@router.post("/", response_model=PARAItem, status_code=status.HTTP_201_CREATED)
async def create_para_item(
    item: PARAItemCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new PARA item."""
    item_data = item.model_dump()
    item_data["user_id"] = user_id

    created_item = db.insert_record("para_items", item_data)
    return created_item


@router.put("/{item_id}", response_model=PARAItem)
async def update_para_item(
    item_id: str,
    item: PARAItemUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Update a PARA item."""
    # Verify ownership
    existing_items = db.get_user_data(user_id, "para_items", {"id": item_id})
    if not existing_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    # Update only provided fields
    update_data = item.model_dump(exclude_unset=True)
    updated_item = db.update_record("para_items", item_id, update_data)

    return updated_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_para_item(
    item_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a PARA item."""
    # Verify ownership
    existing_items = db.get_user_data(user_id, "para_items", {"id": item_id})
    if not existing_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    success = db.delete_record("para_items", item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete item"
        )


@router.post("/classify", response_model=PARAClassificationResponse)
async def classify_item(
    request: PARAClassificationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Classify an item into PARA categories using AI."""
    from agents.classifier import classify_item as ai_classify

    # Call AI classification
    result = ai_classify(
        title=request.title,
        description=request.description or "",
        context=request.context or ""
    )

    # Log the action
    db.log_agent_action(
        user_id=user_id,
        action_type="classify",
        input_data=request.model_dump(),
        output_data=result,
        model_used="claude-haiku-4.5",
        tokens_used=result["usage"]["input_tokens"] + result["usage"]["output_tokens"],
        cost_usd=result["usage"]["cost_usd"]
    )

    # Remove usage from result to create classification
    usage = result.pop("usage")
    classification = result

    return {
        "classification": classification,
        "usage": usage
    }


# ============================================================
# DETAILED PARA ITEM ENDPOINT
# ============================================================

@router.get("/{item_id}/detailed", response_model=PARAItemDetailed)
async def get_para_item_detailed(
    item_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a PARA item with all related data (tasks, notes, files, relationships)."""
    # Get the base PARA item
    items = db.get_user_data(user_id, "para_items", {"id": item_id})
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    item = items[0]

    # Get related tasks
    tasks = db.get_user_data(user_id, "para_tasks", {"para_item_id": item_id})

    # Get related notes
    notes = db.get_user_data(user_id, "para_notes", {"para_item_id": item_id})

    # Get related files
    files = db.get_user_data(user_id, "para_files", {"para_item_id": item_id})

    # Get relationships (both directions)
    relationships_from = db.get_user_data(user_id, "para_relationships", {"from_item_id": item_id})

    # For each relationship, fetch the related item details
    for rel in relationships_from:
        related_items = db.get_user_data(user_id, "para_items", {"id": rel["to_item_id"]})
        if related_items:
            rel["related_item"] = related_items[0]

    # Calculate task statistics
    active_tasks = [t for t in tasks if not t.get("completed", False)]
    completed_tasks = [t for t in tasks if t.get("completed", False)]
    total_tasks = len(tasks)

    completion_percentage = 0
    if total_tasks > 0:
        completion_percentage = int((len(completed_tasks) / total_tasks) * 100)

    # Build detailed response
    return {
        **item,
        "tasks": tasks,
        "notes": notes,
        "files": files,
        "relationships": relationships_from,
        "active_tasks_count": len(active_tasks),
        "completed_tasks_count": len(completed_tasks),
        "completion_percentage": completion_percentage
    }


# ============================================================
# TASK ENDPOINTS
# ============================================================

@router.get("/{item_id}/tasks", response_model=List[PARATask])
async def get_para_item_tasks(
    item_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get all tasks for a PARA item."""
    # Verify item ownership
    items = db.get_user_data(user_id, "para_items", {"id": item_id})
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    tasks = db.get_user_data(user_id, "para_tasks", {"para_item_id": item_id})
    return tasks


@router.post("/{item_id}/tasks", response_model=PARATask, status_code=status.HTTP_201_CREATED)
async def create_para_item_task(
    item_id: str,
    task: PARATaskCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new task for a PARA item."""
    # Verify item ownership
    items = db.get_user_data(user_id, "para_items", {"id": item_id})
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    task_data = task.model_dump()
    task_data["para_item_id"] = item_id
    task_data["user_id"] = user_id

    created_task = db.insert_record("para_tasks", task_data)
    return created_task


@router.patch("/{item_id}/tasks/{task_id}", response_model=PARATask)
async def update_para_item_task(
    item_id: str,
    task_id: str,
    task: PARATaskUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Update a task."""
    # Verify ownership
    tasks = db.get_user_data(user_id, "para_tasks", {"id": task_id, "para_item_id": item_id})
    if not tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    update_data = task.model_dump(exclude_unset=True)

    # If marking as completed, set completed_at timestamp
    if update_data.get("completed") == True:
        from datetime import datetime
        update_data["completed_at"] = datetime.utcnow()
    elif update_data.get("completed") == False:
        update_data["completed_at"] = None

    updated_task = db.update_record("para_tasks", task_id, update_data)
    return updated_task


@router.delete("/{item_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_para_item_task(
    item_id: str,
    task_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a task."""
    # Verify ownership
    tasks = db.get_user_data(user_id, "para_tasks", {"id": task_id, "para_item_id": item_id})
    if not tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    success = db.delete_record("para_tasks", task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )


# ============================================================
# NOTE ENDPOINTS
# ============================================================

@router.get("/{item_id}/notes", response_model=List[PARANote])
async def get_para_item_notes(
    item_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get all notes for a PARA item."""
    # Verify item ownership
    items = db.get_user_data(user_id, "para_items", {"id": item_id})
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    notes = db.get_user_data(user_id, "para_notes", {"para_item_id": item_id})
    return notes


@router.post("/{item_id}/notes", response_model=PARANote, status_code=status.HTTP_201_CREATED)
async def create_para_item_note(
    item_id: str,
    note: PARANoteCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new note for a PARA item."""
    # Verify item ownership
    items = db.get_user_data(user_id, "para_items", {"id": item_id})
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    note_data = note.model_dump()
    note_data["para_item_id"] = item_id
    note_data["user_id"] = user_id

    created_note = db.insert_record("para_notes", note_data)
    return created_note


@router.patch("/{item_id}/notes/{note_id}", response_model=PARANote)
async def update_para_item_note(
    item_id: str,
    note_id: str,
    note: PARANoteUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Update a note."""
    # Verify ownership
    notes = db.get_user_data(user_id, "para_notes", {"id": note_id, "para_item_id": item_id})
    if not notes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    update_data = note.model_dump()
    updated_note = db.update_record("para_notes", note_id, update_data)
    return updated_note


@router.delete("/{item_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_para_item_note(
    item_id: str,
    note_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a note."""
    # Verify ownership
    notes = db.get_user_data(user_id, "para_notes", {"id": note_id, "para_item_id": item_id})
    if not notes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )

    success = db.delete_record("para_notes", note_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete note"
        )


# ============================================================
# FILE ENDPOINTS
# ============================================================

@router.get("/{item_id}/files", response_model=List[PARAFile])
async def get_para_item_files(
    item_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get all files for a PARA item."""
    # Verify item ownership
    items = db.get_user_data(user_id, "para_items", {"id": item_id})
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    files = db.get_user_data(user_id, "para_files", {"para_item_id": item_id})
    return files


@router.post("/{item_id}/files", response_model=PARAFile, status_code=status.HTTP_201_CREATED)
async def create_para_item_file(
    item_id: str,
    file: PARAFileCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Register a new file for a PARA item (file should already be uploaded to storage)."""
    # Verify item ownership
    items = db.get_user_data(user_id, "para_items", {"id": item_id})
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    file_data = file.model_dump()
    file_data["para_item_id"] = item_id
    file_data["user_id"] = user_id

    created_file = db.insert_record("para_files", file_data)
    return created_file


@router.delete("/{item_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_para_item_file(
    item_id: str,
    file_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a file record (does not delete from storage)."""
    # Verify ownership
    files = db.get_user_data(user_id, "para_files", {"id": file_id, "para_item_id": item_id})
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    success = db.delete_record("para_files", file_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )


# ============================================================
# RELATIONSHIP ENDPOINTS
# ============================================================

@router.get("/{item_id}/relationships", response_model=List[PARARelationship])
async def get_para_item_relationships(
    item_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get all relationships for a PARA item."""
    # Verify item ownership
    items = db.get_user_data(user_id, "para_items", {"id": item_id})
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PARA item not found"
        )

    relationships = db.get_user_data(user_id, "para_relationships", {"from_item_id": item_id})

    # Fetch related item details
    for rel in relationships:
        related_items = db.get_user_data(user_id, "para_items", {"id": rel["to_item_id"]})
        if related_items:
            rel["related_item"] = related_items[0]

    return relationships


@router.post("/{item_id}/relationships", response_model=PARARelationship, status_code=status.HTTP_201_CREATED)
async def create_para_item_relationship(
    item_id: str,
    relationship: PARARelationshipCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a relationship between two PARA items."""
    # Verify both items exist and belong to user
    from_items = db.get_user_data(user_id, "para_items", {"id": item_id})
    to_items = db.get_user_data(user_id, "para_items", {"id": relationship.to_item_id})

    if not from_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="From item not found"
        )
    if not to_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="To item not found"
        )

    # Prevent linking item to itself
    if item_id == relationship.to_item_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link item to itself"
        )

    relationship_data = relationship.model_dump()
    relationship_data["from_item_id"] = item_id
    relationship_data["user_id"] = user_id

    try:
        created_relationship = db.insert_record("para_relationships", relationship_data)

        # Fetch the related item details
        related_items = db.get_user_data(user_id, "para_items", {"id": relationship.to_item_id})
        if related_items:
            created_relationship["related_item"] = related_items[0]

        return created_relationship
    except Exception as e:
        # Handle duplicate relationship error
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Relationship already exists"
            )
        raise


@router.delete("/{item_id}/relationships/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_para_item_relationship(
    item_id: str,
    relationship_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a relationship."""
    # Verify ownership
    relationships = db.get_user_data(user_id, "para_relationships", {"id": relationship_id, "from_item_id": item_id})
    if not relationships:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found"
        )

    success = db.delete_record("para_relationships", relationship_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete relationship"
        )
