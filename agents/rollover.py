from anthropic import Anthropic
from config import settings
from database import supabase
from datetime import datetime, timedelta
from typing import Dict, Any
import json

class SmartRolloverAgent:
    """
    Agent that handles smart rollover logic for tasks that keep getting deferred
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL

    async def analyze_rollover_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """
        Analyze a task that has been rolled over multiple times
        """

        # Get task history
        task = supabase.table('tasks')\
            .select('*')\
            .eq('id', task_id)\
            .single()\
            .execute()

        if not task.data:
            return {"error": "Task not found"}

        # Count how many times this task has been rescheduled
        # (This would require a task_history table in production)

        # Get user's recent completed tasks for context
        recent_completed = supabase.table('tasks')\
            .select('title, estimated_duration_minutes')\
            .eq('user_id', user_id)\
            .eq('status', 'completed')\
            .order('completed_at', desc=True)\
            .limit(10)\
            .execute()

        prompt = f"""This task keeps getting rolled over:

Task: {task.data['title']}
Description: {task.data.get('description', 'N/A')}
Priority: {task.data['priority']}
Estimated Duration: {task.data.get('estimated_duration_minutes', 'Unknown')} minutes
Times Rolled Over: 3+ times

Recent Completed Tasks (for context):
{json.dumps([t['title'] for t in recent_completed.data], indent=2)}

This task keeps being deferred. Provide suggestions:

1. Should it be broken into smaller subtasks?
2. Should it be archived/cancelled because it's not actually important?
3. Should it be rescheduled to a specific time next month?
4. Is the estimated duration unrealistic?

Return as JSON:
{{
  "recommendation": "break_down|archive|reschedule|adjust_duration",
  "reasoning": "...",
  "suggested_subtasks": ["task 1", "task 2"] or null,
  "suggested_new_date": "ISO date" or null,
  "new_estimated_duration": number or null,
  "message_to_user": "Friendly message explaining the situation"
}}
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        analysis = json.loads(response.content[0].text)

        # Store the suggestion as a pending approval
        await self._create_rollover_approval(
            user_id=user_id,
            task_id=task_id,
            recommendation=analysis
        )

        return analysis

    async def _create_rollover_approval(
        self,
        user_id: str,
        task_id: str,
        recommendation: Dict[str, Any]
    ):
        """
        Create a pending approval for the rollover recommendation
        """

        supabase.table('pending_approvals').insert({
            "user_id": user_id,
            "approval_type": "rollover_suggestion",
            "data": {
                "task_id": task_id,
                "recommendation": recommendation
            },
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }).execute()

    async def auto_detect_rollovers(self, user_id: str) -> list[str]:
        """
        Automatically detect tasks that keep rolling over
        """

        # Find tasks that are overdue by 3+ days and still pending
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()

        rollover_tasks = supabase.table('tasks')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('status', 'pending')\
            .lt('due_date', three_days_ago)\
            .execute()

        task_ids = [t['id'] for t in rollover_tasks.data]

        # Analyze each one
        for task_id in task_ids:
            try:
                await self.analyze_rollover_task(task_id, user_id)
            except Exception as e:
                print(f"Failed to analyze rollover task {task_id}: {str(e)}")
                continue

        return task_ids
