"""Beta waitlist endpoints for PARA Autopilot"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from database import supabase
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class BetaSignup(BaseModel):
    """Beta waitlist signup model"""
    email: EmailStr
    source: str = "landing_page"


@router.post("/signup")
async def signup_for_beta(signup: BetaSignup):
    """Add user to beta waitlist"""
    try:
        # Check if email already exists
        existing = supabase.table('beta_waitlist')\
            .select('email')\
            .eq('email', signup.email)\
            .execute()

        if existing.data:
            return {
                "success": True,
                "message": "You're already on the waitlist!",
                "position": len(existing.data)
            }

        # Add to waitlist
        result = supabase.table('beta_waitlist')\
            .insert({
                "email": signup.email,
                "source": signup.source,
                "signed_up_at": datetime.utcnow().isoformat(),
                "status": "pending"
            })\
            .execute()

        # Get position in waitlist
        count = supabase.table('beta_waitlist')\
            .select('id', count='exact')\
            .execute()

        position = count.count if hasattr(count, 'count') else 1

        logger.info(f"New beta signup: {signup.email} (position: {position})")

        # TODO: Send welcome email
        # await email_service.send_beta_welcome(signup.email, position)

        return {
            "success": True,
            "message": "Successfully joined the waitlist!",
            "position": position,
            "estimated_access": "Within 48 hours" if position <= 50 else "Within 2 weeks"
        }

    except Exception as e:
        logger.error(f"Failed to add beta signup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process signup")


@router.get("/waitlist/stats")
async def get_waitlist_stats():
    """Get current waitlist statistics (public)"""
    try:
        # Total signups
        total = supabase.table('beta_waitlist')\
            .select('id', count='exact')\
            .execute()

        # Approved users
        approved = supabase.table('beta_waitlist')\
            .select('id', count='exact')\
            .eq('status', 'approved')\
            .execute()

        total_count = total.count if hasattr(total, 'count') else 0
        approved_count = approved.count if hasattr(approved, 'count') else 0

        return {
            "total_signups": total_count,
            "beta_users": approved_count,
            "spots_remaining": max(0, 50 - approved_count)
        }

    except Exception as e:
        logger.error(f"Failed to get waitlist stats: {str(e)}")
        return {
            "total_signups": 0,
            "beta_users": 0,
            "spots_remaining": 50
        }
