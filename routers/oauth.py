"""OAuth2 endpoints for third-party integrations."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from auth import get_current_user_id
from database import supabase
from mcp.sync_service import encrypt_token
from config import settings
import httpx
import secrets
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# OAuth2 state storage (in production, use Redis or database)
# This prevents CSRF attacks
oauth_states = {}


class OAuthCallbackRequest(BaseModel):
    """OAuth callback data."""
    code: str
    state: str


@router.get("/google/init")
async def initiate_google_oauth(
    user_id: str = Depends(get_current_user_id)
):
    """
    Initiate Google OAuth2 flow.

    Returns an authorization URL that the frontend should redirect to.
    User will see Google's consent screen and authorize scopes.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to environment variables."
        )

    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "user_id": user_id,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(minutes=10)
    }

    # Clean up expired states
    expired_states = [k for k, v in oauth_states.items() if v['expires_at'] < datetime.now()]
    for k in expired_states:
        del oauth_states[k]

    # Build Google OAuth URL
    redirect_uri = f"{settings.FRONTEND_URL}/oauth/callback"
    scopes = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={' '.join(scopes)}&"
        f"state={state}&"
        f"access_type=offline&"  # Request refresh token
        f"prompt=consent"  # Force consent screen to always get refresh token
    )

    logger.info(f"Generated OAuth URL for user {user_id}")

    return {
        "auth_url": auth_url,
        "state": state,
        "expires_in": 600  # 10 minutes
    }


@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="CSRF protection state"),
    error: Optional[str] = Query(None, description="Error from Google")
):
    """
    OAuth2 callback endpoint.

    Google redirects here after user authorizes.
    Exchange authorization code for access + refresh tokens.

    This endpoint is called by Google, not your frontend directly.
    After processing, it redirects to your frontend with success/error.
    """
    # Check for errors from Google
    if error:
        logger.error(f"Google OAuth error: {error}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/integrations?error={error}",
            status_code=status.HTTP_302_FOUND
        )

    # Verify state (CSRF protection)
    if state not in oauth_states:
        logger.error(f"Invalid OAuth state: {state}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/integrations?error=invalid_state",
            status_code=status.HTTP_302_FOUND
        )

    state_data = oauth_states[state]
    if state_data['expires_at'] < datetime.now():
        logger.error(f"Expired OAuth state: {state}")
        del oauth_states[state]
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/integrations?error=expired_state",
            status_code=status.HTTP_302_FOUND
        )

    user_id = state_data['user_id']
    del oauth_states[state]  # Clean up used state

    try:
        # Exchange authorization code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": f"{settings.FRONTEND_URL}/oauth/callback",
                    "grant_type": "authorization_code"
                }
            )

            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.text}")
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/settings/integrations?error=token_exchange_failed",
                    status_code=status.HTTP_302_FOUND
                )

            tokens = token_response.json()
            access_token = tokens['access_token']
            refresh_token = tokens.get('refresh_token')  # May not always be present
            expires_in = tokens.get('expires_in', 3600)

        # Get user info from Google
        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_info = userinfo_response.json()

        # Encrypt tokens
        encrypted_access = encrypt_token(access_token)
        encrypted_refresh = encrypt_token(refresh_token) if refresh_token else None

        # Store in database
        integration_data = {
            "user_id": user_id,
            "integration_type": "google_calendar",
            "is_enabled": True,
            "oauth_token_encrypted": encrypted_access,
            "refresh_token_encrypted": encrypted_refresh,
            "token_expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
            "config": {
                "google_user_email": user_info.get('email'),
                "google_user_name": user_info.get('name'),
                "scopes": tokens.get('scope', '').split(' ')
            }
        }

        # Upsert (update if exists, insert if new)
        existing = supabase.table("mcp_integrations")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("integration_type", "google_calendar")\
            .execute()

        if existing.data:
            supabase.table("mcp_integrations")\
                .update(integration_data)\
                .eq("id", existing.data[0]['id'])\
                .execute()
            logger.info(f"Updated Google Calendar integration for user {user_id}")
        else:
            supabase.table("mcp_integrations")\
                .insert(integration_data)\
                .execute()
            logger.info(f"Created Google Calendar integration for user {user_id}")

        # Redirect to frontend with success
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/integrations?success=google_calendar_connected",
            status_code=status.HTTP_302_FOUND
        )

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings/integrations?error=unknown_error",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/google/refresh")
async def refresh_google_token(
    user_id: str = Depends(get_current_user_id)
):
    """
    Manually refresh Google access token using refresh token.

    This is usually done automatically by the sync service,
    but can be triggered manually if needed.
    """
    # Get integration
    result = supabase.table("mcp_integrations")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("integration_type", "google_calendar")\
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Calendar integration not found"
        )

    integration = result.data[0]

    if not integration.get('refresh_token_encrypted'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token available. Please reconnect Google Calendar."
        )

    try:
        from mcp.sync_service import decrypt_token

        refresh_token = decrypt_token(integration['refresh_token_encrypted'])

        # Request new access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "refresh_token": refresh_token,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "grant_type": "refresh_token"
                }
            )

            if token_response.status_code != 200:
                logger.error(f"Token refresh failed: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to refresh token. Please reconnect Google Calendar."
                )

            tokens = token_response.json()
            new_access_token = tokens['access_token']
            expires_in = tokens.get('expires_in', 3600)

        # Encrypt and store new access token
        encrypted_access = encrypt_token(new_access_token)

        supabase.table("mcp_integrations")\
            .update({
                "oauth_token_encrypted": encrypted_access,
                "token_expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            })\
            .eq("id", integration['id'])\
            .execute()

        logger.info(f"Refreshed Google token for user {user_id}")

        return {
            "message": "Token refreshed successfully",
            "expires_in": expires_in,
            "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {str(e)}"
        )


@router.delete("/google/revoke")
async def revoke_google_access(
    user_id: str = Depends(get_current_user_id)
):
    """
    Revoke Google access and delete integration.

    This:
    1. Revokes the token with Google (so it can't be used anymore)
    2. Deletes the integration from database
    """
    # Get integration
    result = supabase.table("mcp_integrations")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("integration_type", "google_calendar")\
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Calendar integration not found"
        )

    integration = result.data[0]

    try:
        from mcp.sync_service import decrypt_token

        access_token = decrypt_token(integration['oauth_token_encrypted'])

        # Revoke token with Google
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": access_token}
            )

        logger.info(f"Revoked Google token for user {user_id}")

    except Exception as e:
        logger.warning(f"Failed to revoke token with Google: {str(e)}")
        # Continue anyway - delete from our database

    # Delete integration from database
    supabase.table("mcp_integrations")\
        .delete()\
        .eq("id", integration['id'])\
        .execute()

    return {
        "message": "Google Calendar access revoked successfully"
    }
