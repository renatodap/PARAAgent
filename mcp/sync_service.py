"""Background service to sync data from MCP sources."""

from datetime import datetime, timedelta
import asyncio
from typing import Dict, List
from database import supabase
from .calendar_mcp import GoogleCalendarMCP
from .tasks_mcp import TodoistMCP, NotionMCP
from cryptography.fernet import Fernet
import os


# Encryption key for storing OAuth tokens
# In production, this should be stored securely (e.g., environment variable)
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
cipher = Fernet(ENCRYPTION_KEY)


def encrypt_token(token: str) -> str:
    """Encrypt an OAuth token for storage."""
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored OAuth token."""
    return cipher.decrypt(encrypted_token.encode()).decode()


class MCPSyncService:
    """Background service to sync data from MCP sources."""

    def __init__(self, sync_interval: int = 300):
        """Initialize sync service.

        Args:
            sync_interval: Sync interval in seconds (default: 5 minutes)
        """
        self.sync_interval = sync_interval

    async def sync_user_data(self, user_id: str):
        """Sync all MCP integrations for a user.

        Args:
            user_id: User UUID
        """
        # Get user's enabled integrations
        integrations = supabase.table("mcp_integrations")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("is_enabled", True)\
            .execute()

        for integration in integrations.data:
            try:
                if integration['integration_type'] == 'google_calendar':
                    await self.sync_google_calendar(user_id, integration)
                elif integration['integration_type'] == 'todoist':
                    await self.sync_todoist(user_id, integration)
                elif integration['integration_type'] == 'notion':
                    await self.sync_notion(user_id, integration)

                # Update last sync time
                supabase.table("mcp_integrations")\
                    .update({"last_sync_at": datetime.now().isoformat()})\
                    .eq("id", integration['id'])\
                    .execute()

            except Exception as e:
                print(f"Sync error for {integration['integration_type']}: {e}")

    async def sync_google_calendar(self, user_id: str, integration: Dict):
        """Sync Google Calendar events.

        Args:
            user_id: User UUID
            integration: Integration config from database
        """
        calendar = GoogleCalendarMCP({
            'access_token': decrypt_token(integration['oauth_token_encrypted']),
            'refresh_token': decrypt_token(integration['refresh_token_encrypted']) if integration.get('refresh_token_encrypted') else None
        })

        # Fetch events for next 30 days
        start = datetime.now()
        end = start + timedelta(days=30)
        events = calendar.get_events(start, end)

        # Upsert events into database
        for event in events:
            event_data = {
                "user_id": user_id,
                "external_id": event['id'],
                "external_source": "google_calendar",
                "title": event.get('summary', 'Untitled Event'),
                "description": event.get('description', ''),
                "start_time": event['start'].get('dateTime', event['start'].get('date')),
                "end_time": event['end'].get('dateTime', event['end'].get('date')),
                "location": event.get('location', ''),
                "attendees": [{'email': a['email']} for a in event.get('attendees', [])],
                "is_all_day": 'date' in event['start'],
                "last_synced_at": datetime.now().isoformat()
            }

            # Upsert (insert or update if exists)
            supabase.table("calendar_events")\
                .upsert(event_data, on_conflict="user_id,external_id,external_source")\
                .execute()

    async def sync_todoist(self, user_id: str, integration: Dict):
        """Sync Todoist tasks.

        Args:
            user_id: User UUID
            integration: Integration config from database
        """
        todoist = TodoistMCP(decrypt_token(integration['oauth_token_encrypted']))

        # Fetch active tasks
        tasks = await todoist.get_tasks()

        for task in tasks:
            task_data = {
                "user_id": user_id,
                "title": task['content'],
                "description": task.get('description', ''),
                "status": "completed" if task.get('is_completed') else "pending",
                "priority": self._map_todoist_priority(task.get('priority', 1)),
                "due_date": task.get('due', {}).get('date') if task.get('due') else None,
                "source": "imported",
                "source_metadata": {
                    "external_id": task['id'],
                    "external_source": "todoist",
                    "project_id": task.get('project_id'),
                    "labels": task.get('labels', [])
                }
            }

            # Check if task already exists
            existing = supabase.table("tasks")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("source_metadata->>external_id", task['id'])\
                .eq("source_metadata->>external_source", "todoist")\
                .execute()

            if existing.data:
                # Update existing task
                supabase.table("tasks")\
                    .update(task_data)\
                    .eq("id", existing.data[0]['id'])\
                    .execute()
            else:
                # Insert new task
                supabase.table("tasks").insert(task_data).execute()

    async def sync_notion(self, user_id: str, integration: Dict):
        """Sync Notion database (placeholder for future implementation).

        Args:
            user_id: User UUID
            integration: Integration config from database
        """
        # TODO: Implement Notion sync based on specific database structure
        pass

    def _map_todoist_priority(self, todoist_priority: int) -> str:
        """Map Todoist priority (1-4) to our priority system.

        Args:
            todoist_priority: Todoist priority (1=normal, 4=urgent)

        Returns:
            Priority string (low, medium, high, urgent)
        """
        priority_map = {
            1: "low",
            2: "medium",
            3: "high",
            4: "urgent"
        }
        return priority_map.get(todoist_priority, "medium")

    async def run_continuous_sync(self):
        """Run sync loop for all users."""
        print(f"Starting continuous sync with {self.sync_interval}s interval...")

        while True:
            try:
                # Get all users with active integrations
                users = supabase.table("user_profiles")\
                    .select("id")\
                    .execute()

                print(f"Syncing data for {len(users.data)} users...")

                for user in users.data:
                    await self.sync_user_data(user['id'])

                print(f"Sync complete. Next sync in {self.sync_interval}s")

            except Exception as e:
                print(f"Error in continuous sync: {e}")

            await asyncio.sleep(self.sync_interval)


# Singleton instance
sync_service = MCPSyncService()


async def start_sync_service():
    """Start the MCP sync service in the background."""
    await sync_service.run_continuous_sync()
