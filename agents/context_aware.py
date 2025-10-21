from anthropic import Anthropic
from config import settings
from database import supabase
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

class ContextAwareSuggestionsAgent:
    """
    Provides context-aware suggestions based on user's current situation
    - Before meetings: "Review notes from last sync"
    - End of day: "3 quick tasks you could finish in 15 minutes"
    - Friday: "Ready to start weekly review?"
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL

    async def get_suggestions(self, user_id: str, context: str = "auto") -> List[Dict[str, Any]]:
        """
        Get context-aware suggestions
        context: "auto", "before_meeting", "end_of_day", "friday", "morning"
        """

        if context == "auto":
            context = self._detect_context()

        suggestions = []

        if context == "before_meeting":
            suggestions = await self._before_meeting_suggestions(user_id)
        elif context == "end_of_day":
            suggestions = await self._end_of_day_suggestions(user_id)
        elif context == "friday":
            suggestions = await self._friday_suggestions(user_id)
        elif context == "morning":
            suggestions = await self._morning_suggestions(user_id)

        return suggestions

    def _detect_context(self) -> str:
        """Auto-detect context based on current time"""
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()  # 0 = Monday, 4 = Friday

        # Friday afternoon
        if day_of_week == 4 and hour >= 15:
            return "friday"

        # Morning (6am - 10am)
        if 6 <= hour < 10:
            return "morning"

        # End of day (5pm - 8pm)
        if 17 <= hour < 20:
            return "end_of_day"

        # Check if there's a meeting in next 30 minutes
        # (would need calendar integration)
        return "general"

    async def _before_meeting_suggestions(self, user_id: str) -> List[Dict[str, Any]]:
        """Suggestions before meetings"""

        # Get upcoming calendar events
        next_hour = (datetime.now() + timedelta(hours=1)).isoformat()

        upcoming_events = supabase.table('calendar_events')\
            .select('*')\
            .eq('user_id', user_id)\
            .gte('start_time', datetime.now().isoformat())\
            .lte('start_time', next_hour)\
            .execute()

        if not upcoming_events.data:
            return []

        suggestions = []

        for event in upcoming_events.data:
            # Check if there's a linked task or project
            if event.get('linked_task_id'):
                task = supabase.table('tasks')\
                    .select('title, para_item_id')\
                    .eq('id', event['linked_task_id'])\
                    .single()\
                    .execute()

                if task.data:
                    suggestions.append({
                        "type": "meeting_prep",
                        "title": f"Prepare for: {event['title']}",
                        "description": f"Review task: {task.data['title']}",
                        "action": "review_task",
                        "action_id": event['linked_task_id'],
                        "urgency": "high"
                    })

            # Generic meeting prep
            suggestions.append({
                "type": "meeting_prep",
                "title": f"Meeting in {self._time_until(event['start_time'])}",
                "description": event['title'],
                "action": "open_calendar",
                "urgency": "medium"
            })

        return suggestions

    async def _end_of_day_suggestions(self, user_id: str) -> List[Dict[str, Any]]:
        """End of day suggestions"""

        # Find quick tasks (< 15 minutes)
        quick_tasks = supabase.table('tasks')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('status', 'pending')\
            .lte('estimated_duration_minutes', 15)\
            .order('priority', desc=True)\
            .limit(5)\
            .execute()

        if not quick_tasks.data:
            return []

        return [{
            "type": "quick_win",
            "title": "3 quick tasks to finish your day strong",
            "description": "These tasks take 15 minutes or less",
            "tasks": [
                {
                    "id": t['id'],
                    "title": t['title'],
                    "duration": t['estimated_duration_minutes']
                }
                for t in quick_tasks.data[:3]
            ],
            "action": "show_quick_tasks",
            "urgency": "low"
        }]

    async def _friday_suggestions(self, user_id: str) -> List[Dict[str, Any]]:
        """Friday afternoon suggestions"""

        # Check if weekly review exists for this week
        week_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = week_start - timedelta(days=week_start.weekday())

        existing_review = supabase.table('weekly_reviews')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('week_start_date', week_start.isoformat())\
            .execute()

        if not existing_review.data:
            return [{
                "type": "weekly_review",
                "title": "Ready to start your weekly review?",
                "description": "Reflect on the week and plan for the next one",
                "action": "start_review",
                "urgency": "medium"
            }]

        return []

    async def _morning_suggestions(self, user_id: str) -> List[Dict[str, Any]]:
        """Morning suggestions"""

        # Get today's tasks
        today = datetime.now().replace(hour=0, minute=0, second=0)
        today_end = today.replace(hour=23, minute=59, second=59)

        today_tasks = supabase.table('tasks')\
            .select('*')\
            .eq('user_id', user_id)\
            .neq('status', 'completed')\
            .gte('due_date', today.isoformat())\
            .lte('due_date', today_end.isoformat())\
            .execute()

        if not today_tasks.data:
            return [{
                "type": "no_tasks",
                "title": "No tasks scheduled for today",
                "description": "Want to run auto-schedule to fill your day?",
                "action": "auto_schedule",
                "urgency": "low"
            }]

        # Prioritize top 3
        top_tasks = sorted(
            today_tasks.data,
            key=lambda t: {"urgent": 0, "high": 1, "medium": 2, "low": 3}[t['priority']]
        )[:3]

        return [{
            "type": "daily_plan",
            "title": f"Good morning! You have {len(today_tasks.data)} tasks today",
            "description": "Here are your top priorities:",
            "tasks": [
                {
                    "id": t['id'],
                    "title": t['title'],
                    "priority": t['priority']
                }
                for t in top_tasks
            ],
            "action": "show_today",
            "urgency": "high"
        }]

    def _time_until(self, future_time: str) -> str:
        """Calculate human-readable time until future event"""
        future = datetime.fromisoformat(future_time)
        delta = future - datetime.now()

        minutes = int(delta.total_seconds() / 60)

        if minutes < 1:
            return "now"
        elif minutes < 60:
            return f"{minutes} minutes"
        else:
            hours = minutes // 60
            return f"{hours} hour{'s' if hours > 1 else ''}"
