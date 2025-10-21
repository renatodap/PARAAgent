"""Authentication middleware and utilities."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional
from config import settings
from database import supabase


security = HTTPBearer()


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token from Supabase Auth.

    Args:
        token: JWT access token

    Returns:
        Decoded token payload or None
    """
    try:
        # Verify with Supabase
        user = supabase.auth.get_user(token)
        return user.user if user else None
    except Exception as e:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current authenticated user.

    Args:
        credentials: HTTP Bearer token from request header

    Returns:
        User data from Supabase Auth

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    user = verify_token(token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_id(
    user: dict = Depends(get_current_user)
) -> str:
    """Get just the user ID from authenticated user.

    Args:
        user: User data from get_current_user

    Returns:
        User UUID as string
    """
    return user.id


class AuthHelper:
    """Helper class for auth-related operations."""

    @staticmethod
    def get_or_create_user_profile(user_id: str, email: str) -> dict:
        """Get or create user profile in our database.

        Args:
            user_id: User UUID from Supabase Auth
            email: User email

        Returns:
            User profile record
        """
        # Try to get existing profile
        result = supabase.table("user_profiles")\
            .select("*")\
            .eq("id", user_id)\
            .execute()

        if result.data:
            return result.data[0]

        # Create new profile
        profile = {
            "id": user_id,
            "email": email,
            "onboarding_completed": False,
            "para_preferences": {}
        }

        result = supabase.table("user_profiles").insert(profile).execute()
        return result.data[0]
