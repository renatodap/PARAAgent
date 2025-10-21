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
