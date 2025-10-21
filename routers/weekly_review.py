"""API router for weekly review endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime, timedelta
from auth import get_current_user_id
from database import db, supabase
from models.review import (
    WeeklyReview,
    WeeklyReviewCreate,
    WeeklyReviewUpdate,
    WeeklyReviewGenerateRequest,
    WeeklyReviewGenerateResponse,
    ReviewStatus
)

router = APIRouter()


@router.get("/", response_model=List[WeeklyReview])
async def get_weekly_reviews(
    user_id: str = Depends(get_current_user_id)
):
    """Get all weekly reviews for current user."""
    reviews = db.get_user_data(user_id, "weekly_reviews")

    # Sort by week_start_date descending
    reviews.sort(key=lambda x: x["week_start_date"], reverse=True)

    return reviews


@router.get("/{review_id}", response_model=WeeklyReview)
async def get_weekly_review(
    review_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific weekly review by ID."""
    reviews = db.get_user_data(user_id, "weekly_reviews", {"id": review_id})

    if not reviews:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weekly review not found"
        )

    return reviews[0]


@router.get("/week/{week_start_date}", response_model=WeeklyReview)
async def get_review_by_week(
    week_start_date: str,  # Format: YYYY-MM-DD
    user_id: str = Depends(get_current_user_id)
):
    """Get weekly review for a specific week."""
    result = supabase.table("weekly_reviews")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("week_start_date", week_start_date)\
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No review found for this week"
        )

    return result.data[0]


@router.post("/generate", response_model=WeeklyReviewGenerateResponse)
async def generate_weekly_review(
    request: WeeklyReviewGenerateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Generate AI-powered weekly review."""
    from agents.reviewer import generate_weekly_review as ai_review

    # Check if review already exists for this week
    existing = supabase.table("weekly_reviews")\
        .select("id")\
        .eq("user_id", user_id)\
        .eq("week_start_date", request.week_start_date.isoformat())\
        .execute()

    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review already exists for this week. Use PUT to update."
        )

    # Generate review using AI
    week_start = datetime.combine(request.week_start_date, datetime.min.time())
    result = ai_review(user_id, week_start)

    # Log the action
    db.log_agent_action(
        user_id=user_id,
        action_type="review",
        input_data={"week_start": request.week_start_date.isoformat()},
        output_data=result,
        model_used="claude-haiku-4.5",
        tokens_used=result["usage"]["tokens"],
        cost_usd=result["usage"]["cost_usd"]
    )

    return result


@router.put("/{review_id}", response_model=WeeklyReview)
async def update_weekly_review(
    review_id: str,
    review: WeeklyReviewUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Update a weekly review (e.g., add user notes, mark as completed)."""
    # Verify ownership
    existing_reviews = db.get_user_data(user_id, "weekly_reviews", {"id": review_id})
    if not existing_reviews:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weekly review not found"
        )

    # Update
    update_data = review.model_dump(exclude_unset=True)
    updated_review = db.update_record("weekly_reviews", review_id, update_data)

    return updated_review


@router.post("/", response_model=WeeklyReview, status_code=status.HTTP_201_CREATED)
async def create_manual_review(
    review: WeeklyReviewCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a manual weekly review (without AI generation)."""
    week_end = review.week_start_date + timedelta(days=7)

    review_data = {
        "user_id": user_id,
        "week_start_date": review.week_start_date.isoformat(),
        "week_end_date": week_end.isoformat(),
        "status": "draft"
    }

    created_review = db.insert_record("weekly_reviews", review_data)
    return created_review
