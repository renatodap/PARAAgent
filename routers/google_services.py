"""Google Services integration endpoints - Gmail, Tasks, Drive."""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
from auth import get_current_user_id
from database import db, supabase
from mcp.sync_service import decrypt_token
from config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class EmailSearchRequest(BaseModel):
    """Request model for email search."""
    query: str
    max_results: int = 50
    after: Optional[datetime] = None


class EmailToTaskRequest(BaseModel):
    """Request model for converting email to task."""
    email_id: str
    create_google_task: bool = True


class TaskSyncRequest(BaseModel):
    """Request model for task sync."""
    task_ids: Optional[List[str]] = None  # If None, sync all
    sync_to_google: bool = True
    sync_from_google: bool = True


# ============================================================================
# GMAIL ENDPOINTS
# ============================================================================

@router.get("/gmail/unread")
async def get_unread_emails(
    max_results: int = 100,
    user_id: str = Depends(get_current_user_id)
):
    """Get unread emails from Gmail.

    Returns emails that can be parsed for tasks/projects.
    """
    try:
        # Get Gmail integration
        integration = await _get_integration(user_id, "google_calendar")  # Uses same OAuth

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Google integration not found. Please connect your Google account first."
            )

        # Initialize Gmail client
        from mcp.gmail_mcp import GmailMCP
        gmail = GmailMCP({
            'access_token': decrypt_token(integration['oauth_token_encrypted']),
            'refresh_token': decrypt_token(integration['refresh_token_encrypted']) if integration.get('refresh_token_encrypted') else None
        })

        # Get unread emails
        emails = gmail.get_unread_emails(max_results=max_results)

        return {
            "count": len(emails),
            "emails": emails
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching unread emails: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch emails: {str(e)}"
        )


@router.post("/gmail/search")
async def search_emails(
    request: EmailSearchRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Search Gmail with query.

    Uses Gmail search syntax:
    - from:alice@example.com
    - subject:budget
    - has:attachment
    - is:important
    - after:2025/01/01
    """
    try:
        integration = await _get_integration(user_id, "google_calendar")

        from mcp.gmail_mcp import GmailMCP
        gmail = GmailMCP({
            'access_token': decrypt_token(integration['oauth_token_encrypted']),
            'refresh_token': decrypt_token(integration['refresh_token_encrypted']) if integration.get('refresh_token_encrypted') else None
        })

        emails = gmail.search_emails(
            query=request.query,
            max_results=request.max_results,
            after=request.after
        )

        return {
            "query": request.query,
            "count": len(emails),
            "emails": emails
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching emails: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search emails: {str(e)}"
        )


@router.post("/gmail/email-to-task")
async def convert_email_to_task(
    request: EmailToTaskRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """Convert an email to a PARA task using AI parsing.

    This will:
    1. Fetch the email
    2. Parse with Claude to extract task details
    3. Create PARA task
    4. Optionally create Google Task
    5. Label email as "PARA/Processed"
    """
    try:
        integration = await _get_integration(user_id, "google_calendar")

        from mcp.gmail_mcp import GmailMCP
        gmail = GmailMCP({
            'access_token': decrypt_token(integration['oauth_token_encrypted']),
            'refresh_token': decrypt_token(integration['refresh_token_encrypted']) if integration.get('refresh_token_encrypted') else None
        })

        # Get email
        email = gmail.get_email_by_id(request.email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email {request.email_id} not found"
            )

        # Parse email with NLP
        from agents.nlp_parser import NaturalLanguageTaskParser
        parser = NaturalLanguageTaskParser()

        # Combine subject + body for parsing
        email_text = f"{email['subject']}\n\n{email['body']}"
        parsed = await parser.parse(email_text, user_id)

        # Create PARA task
        task_data = {
            "user_id": user_id,
            "title": parsed['title'],
            "description": parsed.get('description', ''),
            "due_date": parsed.get('due_date'),
            "priority": parsed.get('priority', 'medium'),
            "estimated_duration_minutes": parsed.get('estimated_duration_minutes'),
            "status": "pending",
            "source": "gmail",
            "source_metadata": {
                "email_id": email['id'],
                "email_from": email['from'],
                "email_subject": email['subject'],
                "email_date": email['date']
            }
        }

        task = db.insert_record("tasks", task_data)

        # Create Google Task if requested
        google_task = None
        if request.create_google_task:
            from mcp.google_tasks_mcp import GoogleTasksMCP
            google_tasks = GoogleTasksMCP({
                'access_token': decrypt_token(integration['oauth_token_encrypted']),
                'refresh_token': decrypt_token(integration['refresh_token_encrypted']) if integration.get('refresh_token_encrypted') else None
            })

            google_task = google_tasks.create_task(
                title=parsed['title'],
                notes=f"From email: {email['subject']}\n\nOriginal sender: {email['from']}\n\n[PARA Task ID: {task['id']}]",
                due=datetime.fromisoformat(parsed['due_date']) if parsed.get('due_date') else None
            )

            if google_task:
                # Update task with Google Task ID
                db.update_record("tasks", task['id'], {
                    "source_metadata": {
                        **task_data['source_metadata'],
                        "google_task_id": google_task['id']
                    }
                })

        # Label email as processed (in background)
        background_tasks.add_task(gmail.add_label, email['id'], 'PARA/Processed')
        background_tasks.add_task(gmail.mark_as_read, email['id'])

        return {
            "message": "Email converted to task successfully",
            "task": task,
            "google_task": google_task,
            "email": {
                "id": email['id'],
                "subject": email['subject'],
                "from": email['from']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting email to task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert email: {str(e)}"
        )


# ============================================================================
# GOOGLE TASKS ENDPOINTS
# ============================================================================

@router.get("/tasks/google")
async def get_google_tasks(
    user_id: str = Depends(get_current_user_id)
):
    """Get all tasks from Google Tasks."""
    try:
        integration = await _get_integration(user_id, "google_calendar")

        from mcp.google_tasks_mcp import GoogleTasksMCP
        google_tasks = GoogleTasksMCP({
            'access_token': decrypt_token(integration['oauth_token_encrypted']),
            'refresh_token': decrypt_token(integration['refresh_token_encrypted']) if integration.get('refresh_token_encrypted') else None
        })

        tasks = google_tasks.get_tasks(show_completed=False)

        return {
            "count": len(tasks),
            "tasks": tasks
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Google Tasks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Google Tasks: {str(e)}"
        )


@router.post("/tasks/sync")
async def sync_tasks(
    request: TaskSyncRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Bidirectional sync between PARA tasks and Google Tasks.

    - Sync TO Google: Creates/updates Google Tasks from PARA tasks
    - Sync FROM Google: Creates/updates PARA tasks from Google Tasks
    """
    try:
        integration = await _get_integration(user_id, "google_calendar")

        from mcp.google_tasks_mcp import GoogleTasksMCP
        google_tasks = GoogleTasksMCP({
            'access_token': decrypt_token(integration['oauth_token_encrypted']),
            'refresh_token': decrypt_token(integration['refresh_token_encrypted']) if integration.get('refresh_token_encrypted') else None
        })

        synced_to_google = []
        synced_from_google = []

        # SYNC TO GOOGLE: PARA → Google Tasks
        if request.sync_to_google:
            # Get PARA tasks to sync
            if request.task_ids:
                para_tasks = []
                for task_id in request.task_ids:
                    task = db.get_user_data(user_id, "tasks", {"id": task_id})
                    if task:
                        para_tasks.extend(task)
            else:
                # Get all pending/in-progress tasks
                para_tasks = supabase.table("tasks")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .in_("status", ["pending", "in_progress"])\
                    .execute().data

            for task in para_tasks:
                google_task_id = task.get('source_metadata', {}).get('google_task_id')

                if google_task_id:
                    # Update existing Google Task
                    google_task = google_tasks.update_task(google_task_id, {
                        'title': task['title'],
                        'notes': task.get('description', ''),
                        'due': datetime.fromisoformat(task['due_date']) if task.get('due_date') else None,
                        'status': 'completed' if task['status'] == 'completed' else 'needsAction'
                    })
                else:
                    # Create new Google Task
                    google_task = google_tasks.sync_from_para_task(task)

                    if google_task:
                        # Store Google Task ID in PARA
                        db.update_record("tasks", task['id'], {
                            "source_metadata": {
                                **task.get('source_metadata', {}),
                                "google_task_id": google_task['id'],
                                "last_synced_to_google": datetime.now().isoformat()
                            }
                        })

                if google_task:
                    synced_to_google.append(google_task)

        # SYNC FROM GOOGLE: Google Tasks → PARA
        if request.sync_from_google:
            google_task_list = google_tasks.get_tasks(show_completed=False)

            for gtask in google_task_list:
                # Check if task already exists in PARA (by Google Task ID)
                existing = supabase.table("tasks")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .contains("source_metadata", {"google_task_id": gtask['id']})\
                    .execute()

                if existing.data:
                    # Update existing PARA task
                    para_task = existing.data[0]
                    db.update_record("tasks", para_task['id'], {
                        "title": gtask['title'],
                        "description": gtask.get('notes', ''),
                        "status": "completed" if gtask['is_completed'] else "pending",
                        "source_metadata": {
                            **para_task.get('source_metadata', {}),
                            "last_synced_from_google": datetime.now().isoformat()
                        }
                    })
                    synced_from_google.append(para_task)
                else:
                    # Create new PARA task from Google Task
                    new_task = db.insert_record("tasks", {
                        "user_id": user_id,
                        "title": gtask['title'],
                        "description": gtask.get('notes', ''),
                        "status": "completed" if gtask['is_completed'] else "pending",
                        "due_date": gtask.get('due'),
                        "source": "google_tasks",
                        "source_metadata": {
                            "google_task_id": gtask['id'],
                            "imported_from_google": True,
                            "last_synced_from_google": datetime.now().isoformat()
                        }
                    })
                    synced_from_google.append(new_task)

        return {
            "message": "Sync completed successfully",
            "synced_to_google": len(synced_to_google),
            "synced_from_google": len(synced_from_google),
            "tasks_to_google": synced_to_google[:5],  # First 5 for preview
            "tasks_from_google": synced_from_google[:5]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing tasks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync tasks: {str(e)}"
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _get_integration(user_id: str, integration_type: str) -> Optional[Dict]:
    """Get user's integration or raise 404."""
    result = supabase.table("mcp_integrations")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("integration_type", integration_type)\
        .eq("is_enabled", True)\
        .execute()

    if not result.data:
        return None

    return result.data[0]
