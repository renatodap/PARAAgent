"""MCP-style wrapper for task management integrations.

Supports Todoist, ClickUp, and other task managers.
"""

import httpx
from typing import Dict, List, Optional
from datetime import datetime


class TodoistMCP:
    """MCP-style wrapper for Todoist API."""

    def __init__(self, api_token: str):
        """Initialize Todoist client.

        Args:
            api_token: Todoist API token
        """
        self.api_token = api_token
        self.base_url = "https://api.todoist.com/rest/v2"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    async def get_tasks(self, project_id: Optional[str] = None) -> List[Dict]:
        """Fetch all active tasks.

        Args:
            project_id: Optional project ID to filter by

        Returns:
            List of tasks
        """
        url = f"{self.base_url}/tasks"
        params = {}

        if project_id:
            params['project_id'] = project_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            print(f"Error fetching Todoist tasks: {e}")
            return []

    async def create_task(
        self,
        content: str,
        project_id: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: int = 1,
        labels: List[str] = None
    ) -> Optional[Dict]:
        """Create a new task.

        Args:
            content: Task content/title
            project_id: Project ID to add task to
            due_date: Due date in format "YYYY-MM-DD"
            priority: Priority (1-4, where 4 is urgent)
            labels: List of label names

        Returns:
            Created task or None if failed
        """
        url = f"{self.base_url}/tasks"

        data = {
            "content": content,
            "priority": priority
        }

        if project_id:
            data['project_id'] = project_id
        if due_date:
            data['due_string'] = due_date
        if labels:
            data['labels'] = labels

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers, json=data)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            print(f"Error creating Todoist task: {e}")
            return None

    async def update_task(self, task_id: str, updates: Dict) -> Optional[Dict]:
        """Update an existing task.

        Args:
            task_id: Todoist task ID
            updates: Dictionary of fields to update

        Returns:
            Updated task or None if failed
        """
        url = f"{self.base_url}/tasks/{task_id}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers, json=updates)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            print(f"Error updating Todoist task: {e}")
            return None

    async def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed.

        Args:
            task_id: Todoist task ID

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/tasks/{task_id}/close"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers)
                response.raise_for_status()
                return True

        except Exception as e:
            print(f"Error completing Todoist task: {e}")
            return False

    async def get_projects(self) -> List[Dict]:
        """Fetch all projects.

        Returns:
            List of projects
        """
        url = f"{self.base_url}/projects"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            print(f"Error fetching Todoist projects: {e}")
            return []


class NotionMCP:
    """MCP-style wrapper for Notion API (placeholder for future implementation)."""

    def __init__(self, api_token: str):
        """Initialize Notion client.

        Args:
            api_token: Notion integration token
        """
        self.api_token = api_token
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    async def query_database(self, database_id: str, filter_params: Dict = None) -> List[Dict]:
        """Query a Notion database.

        Args:
            database_id: Notion database ID
            filter_params: Optional filter parameters

        Returns:
            List of database pages
        """
        url = f"{self.base_url}/databases/{database_id}/query"
        data = filter_params or {}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers, json=data)
                response.raise_for_status()
                return response.json().get('results', [])

        except Exception as e:
            print(f"Error querying Notion database: {e}")
            return []

    async def create_page(self, parent_id: str, properties: Dict) -> Optional[Dict]:
        """Create a new page in a database.

        Args:
            parent_id: Parent database ID
            properties: Page properties

        Returns:
            Created page or None if failed
        """
        url = f"{self.base_url}/pages"

        data = {
            "parent": {"database_id": parent_id},
            "properties": properties
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers, json=data)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            print(f"Error creating Notion page: {e}")
            return None
