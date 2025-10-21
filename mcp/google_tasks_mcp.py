"""MCP-style wrapper for Google Tasks API.

Enables bidirectional sync between PARA tasks and Google Tasks.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from typing import Dict, List, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class GoogleTasksMCP:
    """MCP-style wrapper for Google Tasks API."""

    def __init__(self, user_credentials: Dict):
        """Initialize Google Tasks client.

        Args:
            user_credentials: Dict with 'access_token' and 'refresh_token'
        """
        self.credentials = Credentials(
            token=user_credentials['access_token'],
            refresh_token=user_credentials.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        self.service = build('tasks', 'v1', credentials=self.credentials)

    def get_task_lists(self) -> List[Dict]:
        """Get all task lists.

        Returns:
            List of task lists
        """
        try:
            results = self.service.tasklists().list().execute()
            return results.get('items', [])

        except Exception as e:
            logger.error(f"Error fetching task lists: {e}")
            return []

    def get_tasks(
        self,
        tasklist_id: str = '@default',
        show_completed: bool = False
    ) -> List[Dict]:
        """Get tasks from a task list.

        Args:
            tasklist_id: Task list ID (default: '@default')
            show_completed: Include completed tasks

        Returns:
            List of tasks
        """
        try:
            results = self.service.tasks().list(
                tasklist=tasklist_id,
                showCompleted=show_completed,
                showHidden=show_completed
            ).execute()

            return [self._parse_task(task) for task in results.get('items', [])]

        except Exception as e:
            logger.error(f"Error fetching tasks: {e}")
            return []

    def create_task(
        self,
        title: str,
        notes: str = '',
        due: Optional[datetime] = None,
        tasklist_id: str = '@default'
    ) -> Optional[Dict]:
        """Create a new task.

        Args:
            title: Task title
            notes: Task notes/description
            due: Due date
            tasklist_id: Task list to add to

        Returns:
            Created task or None
        """
        try:
            task = {
                'title': title,
                'notes': notes
            }

            if due:
                # Google Tasks uses RFC 3339 timestamp
                task['due'] = due.strftime('%Y-%m-%dT%H:%M:%S.000Z')

            created_task = self.service.tasks().insert(
                tasklist=tasklist_id,
                body=task
            ).execute()

            return self._parse_task(created_task)

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    def update_task(
        self,
        task_id: str,
        updates: Dict,
        tasklist_id: str = '@default'
    ) -> Optional[Dict]:
        """Update an existing task.

        Args:
            task_id: Google Task ID
            updates: Dict of fields to update
            tasklist_id: Task list ID

        Returns:
            Updated task or None
        """
        try:
            # Get current task
            task = self.service.tasks().get(
                tasklist=tasklist_id,
                task=task_id
            ).execute()

            # Apply updates
            if 'title' in updates:
                task['title'] = updates['title']
            if 'notes' in updates:
                task['notes'] = updates['notes']
            if 'due' in updates:
                if updates['due']:
                    task['due'] = updates['due'].strftime('%Y-%m-%dT%H:%M:%S.000Z')
                else:
                    task.pop('due', None)
            if 'status' in updates:
                task['status'] = updates['status']  # 'needsAction' or 'completed'

            # Update task
            updated_task = self.service.tasks().update(
                tasklist=tasklist_id,
                task=task_id,
                body=task
            ).execute()

            return self._parse_task(updated_task)

        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return None

    def complete_task(
        self,
        task_id: str,
        tasklist_id: str = '@default'
    ) -> bool:
        """Mark a task as completed.

        Args:
            task_id: Google Task ID
            tasklist_id: Task list ID

        Returns:
            True if successful
        """
        try:
            self.service.tasks().update(
                tasklist=tasklist_id,
                task=task_id,
                body={'status': 'completed'}
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return False

    def delete_task(
        self,
        task_id: str,
        tasklist_id: str = '@default'
    ) -> bool:
        """Delete a task.

        Args:
            task_id: Google Task ID
            tasklist_id: Task list ID

        Returns:
            True if successful
        """
        try:
            self.service.tasks().delete(
                tasklist=tasklist_id,
                task=task_id
            ).execute()

            return True

        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False

    def create_tasklist(self, title: str) -> Optional[Dict]:
        """Create a new task list.

        Args:
            title: Task list name

        Returns:
            Created task list or None
        """
        try:
            tasklist = self.service.tasklists().insert(
                body={'title': title}
            ).execute()

            return tasklist

        except Exception as e:
            logger.error(f"Error creating task list: {e}")
            return None

    def _parse_task(self, task: Dict) -> Dict:
        """Parse Google Task response into clean dict.

        Args:
            task: Raw Google Tasks API response

        Returns:
            Parsed task
        """
        return {
            'id': task['id'],
            'title': task.get('title', ''),
            'notes': task.get('notes', ''),
            'status': task.get('status', 'needsAction'),
            'due': task.get('due'),
            'completed': task.get('completed'),
            'updated': task.get('updated'),
            'is_completed': task.get('status') == 'completed',
            'parent': task.get('parent'),  # For subtasks
            'position': task.get('position'),  # Order in list
            'links': task.get('links', [])  # Related links
        }

    def sync_from_para_task(self, para_task: Dict) -> Optional[Dict]:
        """Convert PARA task to Google Task and create/update.

        Args:
            para_task: PARA task dict

        Returns:
            Google Task dict or None
        """
        # Check if task already synced
        google_task_id = para_task.get('source_metadata', {}).get('google_task_id')

        task_data = {
            'title': para_task['title'],
            'notes': f"{para_task.get('description', '')}\n\n[PARA Task ID: {para_task['id']}]",
            'due': para_task.get('due_date')
        }

        if google_task_id:
            # Update existing
            return self.update_task(google_task_id, task_data)
        else:
            # Create new
            return self.create_task(**task_data)

    def get_para_tasklist_id(self) -> str:
        """Get or create 'PARA Autopilot' task list.

        Returns:
            Task list ID
        """
        # Check if PARA task list exists
        lists = self.get_task_lists()
        for tasklist in lists:
            if tasklist['title'] == 'PARA Autopilot':
                return tasklist['id']

        # Create it
        new_list = self.create_tasklist('PARA Autopilot')
        return new_list['id'] if new_list else '@default'
