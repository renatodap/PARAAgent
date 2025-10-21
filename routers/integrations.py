"""API router for MCP integrations endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict
from datetime import datetime
from auth import get_current_user_id
from database import db, supabase
from mcp.sync_service import encrypt_token, decrypt_token

router = APIRouter()


@router.get("/", response_model=List[Dict])
async def get_integrations(
    user_id: str = Depends(get_current_user_id)
):
    """Get all integrations for current user."""
    integrations = db.get_user_data(user_id, "mcp_integrations")

    # Remove sensitive data before returning
    for integration in integrations:
        integration.pop('oauth_token_encrypted', None)
        integration.pop('refresh_token_encrypted', None)

    return integrations


@router.get("/{integration_type}")
async def get_integration(
    integration_type: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific integration by type."""
    result = supabase.table("mcp_integrations")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("integration_type", integration_type)\
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_type}' not found"
        )

    integration = result.data[0]

    # Remove sensitive data
    integration.pop('oauth_token_encrypted', None)
    integration.pop('refresh_token_encrypted', None)

    return integration


@router.post("/{integration_type}/connect")
async def connect_integration(
    integration_type: str,
    access_token: str,
    refresh_token: str = None,
    token_expires_at: datetime = None,
    config: Dict = None,
    user_id: str = Depends(get_current_user_id)
):
    """Connect a new integration.

    Args:
        integration_type: Type of integration (google_calendar, todoist, notion)
        access_token: OAuth access token
        refresh_token: OAuth refresh token (optional)
        token_expires_at: Token expiration datetime (optional)
        config: Integration-specific configuration (optional)
    """
    # Check if integration already exists
    existing = supabase.table("mcp_integrations")\
        .select("id")\
        .eq("user_id", user_id)\
        .eq("integration_type", integration_type)\
        .execute()

    # Encrypt tokens
    encrypted_access = encrypt_token(access_token)
    encrypted_refresh = encrypt_token(refresh_token) if refresh_token else None

    integration_data = {
        "user_id": user_id,
        "integration_type": integration_type,
        "is_enabled": True,
        "oauth_token_encrypted": encrypted_access,
        "refresh_token_encrypted": encrypted_refresh,
        "token_expires_at": token_expires_at.isoformat() if token_expires_at else None,
        "config": config or {}
    }

    if existing.data:
        # Update existing integration
        result = supabase.table("mcp_integrations")\
            .update(integration_data)\
            .eq("id", existing.data[0]['id'])\
            .execute()
    else:
        # Create new integration
        result = supabase.table("mcp_integrations")\
            .insert(integration_data)\
            .execute()

    integration = result.data[0]

    # Remove sensitive data
    integration.pop('oauth_token_encrypted', None)
    integration.pop('refresh_token_encrypted', None)

    return {
        "message": f"Successfully connected {integration_type}",
        "integration": integration
    }


@router.post("/{integration_type}/disconnect")
async def disconnect_integration(
    integration_type: str,
    user_id: str = Depends(get_current_user_id)
):
    """Disconnect an integration."""
    result = supabase.table("mcp_integrations")\
        .delete()\
        .eq("user_id", user_id)\
        .eq("integration_type", integration_type)\
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_type}' not found"
        )

    return {
        "message": f"Successfully disconnected {integration_type}"
    }


@router.post("/{integration_type}/toggle")
async def toggle_integration(
    integration_type: str,
    enabled: bool,
    user_id: str = Depends(get_current_user_id)
):
    """Enable or disable an integration without disconnecting it."""
    result = supabase.table("mcp_integrations")\
        .update({"is_enabled": enabled})\
        .eq("user_id", user_id)\
        .eq("integration_type", integration_type)\
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_type}' not found"
        )

    return {
        "message": f"Integration {integration_type} {'enabled' if enabled else 'disabled'}",
        "is_enabled": enabled
    }


@router.post("/{integration_type}/sync")
async def trigger_sync(
    integration_type: str,
    user_id: str = Depends(get_current_user_id)
):
    """Manually trigger a sync for a specific integration."""
    from mcp.sync_service import sync_service

    # Get integration
    result = supabase.table("mcp_integrations")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("integration_type", integration_type)\
        .eq("is_enabled", True)\
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active integration '{integration_type}' not found"
        )

    integration = result.data[0]

    try:
        # Trigger sync based on type
        if integration_type == 'google_calendar':
            await sync_service.sync_google_calendar(user_id, integration)
        elif integration_type == 'todoist':
            await sync_service.sync_todoist(user_id, integration)
        elif integration_type == 'notion':
            await sync_service.sync_notion(user_id, integration)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sync not supported for integration type '{integration_type}'"
            )

        return {
            "message": f"Sync completed for {integration_type}",
            "synced_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


@router.get("/sync/status")
async def get_sync_status(
    user_id: str = Depends(get_current_user_id)
):
    """Get sync status for all integrations."""
    integrations = db.get_user_data(user_id, "mcp_integrations")

    sync_status = []
    for integration in integrations:
        sync_status.append({
            "integration_type": integration["integration_type"],
            "is_enabled": integration["is_enabled"],
            "last_sync_at": integration.get("last_sync_at"),
            "sync_healthy": (
                datetime.fromisoformat(integration["last_sync_at"]) > datetime.now() - datetime.timedelta(minutes=10)
                if integration.get("last_sync_at") else False
            )
        })

    return {
        "integrations": sync_status,
        "total": len(integrations),
        "enabled": sum(1 for i in integrations if i["is_enabled"])
    }
