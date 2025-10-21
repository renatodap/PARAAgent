from anthropic import Anthropic
from config import settings
from database import supabase
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

class ProactiveInsightsAgent:
    """
    Agent that proactively analyzes user behavior and provides insights
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL

    async def analyze_patterns(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze user patterns and provide insights
        """

        # Get user's task completion history
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()

        tasks = supabase.table('tasks')\
            .select('*')\
            .eq('user_id', user_id)\
            .gte('created_at', thirty_days_ago)\
            .execute()

        if not tasks.data:
            return {"insights": []}

        # Analyze task completion by day of week
        completion_by_day = self._analyze_completion_by_day(tasks.data)

        # Analyze task completion by time of day
        completion_by_hour = self._analyze_completion_by_hour(tasks.data)

        # Identify blockers
        blockers = self._identify_blockers(user_id)

        # Use Claude to generate insights
        prompt = f"""Analyze this user's productivity patterns and provide actionable insights:

Task Completion by Day:
{json.dumps(completion_by_day, indent=2)}

Task Completion by Hour:
{json.dumps(completion_by_hour, indent=2)}

Potential Blockers:
{json.dumps(blockers, indent=2)}

Provide 3-5 specific, actionable insights about:
1. When they're most productive
2. Common blockers
3. Suggestions for improvement

Return as JSON:
{{
  "insights": [
    {{
      "type": "productivity_pattern",
      "title": "...",
      "description": "...",
      "action": "...",
      "impact": "high|medium|low"
    }}
  ]
}}
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        insights_text = response.content[0].text
        insights = json.loads(insights_text)

        return insights

    def _analyze_completion_by_day(self, tasks: List[Dict]) -> Dict[str, int]:
        """Analyze task completion by day of week"""
        completion_by_day = {
            "Monday": 0,
            "Tuesday": 0,
            "Wednesday": 0,
            "Thursday": 0,
            "Friday": 0,
            "Saturday": 0,
            "Sunday": 0
        }

        for task in tasks:
            if task['status'] == 'completed' and task['completed_at']:
                completed_date = datetime.fromisoformat(task['completed_at'])
                day_name = completed_date.strftime('%A')
                completion_by_day[day_name] += 1

        return completion_by_day

    def _analyze_completion_by_hour(self, tasks: List[Dict]) -> Dict[str, int]:
        """Analyze task completion by hour of day"""
        completion_by_hour = {}

        for task in tasks:
            if task['status'] == 'completed' and task['completed_at']:
                completed_date = datetime.fromisoformat(task['completed_at'])
                hour = completed_date.hour

                # Group into time ranges
                if 6 <= hour < 9:
                    period = "Early Morning (6-9am)"
                elif 9 <= hour < 12:
                    period = "Morning (9am-12pm)"
                elif 12 <= hour < 14:
                    period = "Lunch (12-2pm)"
                elif 14 <= hour < 17:
                    period = "Afternoon (2-5pm)"
                elif 17 <= hour < 20:
                    period = "Evening (5-8pm)"
                else:
                    period = "Night (8pm+)"

                completion_by_hour[period] = completion_by_hour.get(period, 0) + 1

        return completion_by_hour

    def _identify_blockers(self, user_id: str) -> List[Dict]:
        """Identify potential blockers"""
        blockers = []

        # Find projects with no progress in 2 weeks
        two_weeks_ago = (datetime.now() - timedelta(days=14)).isoformat()

        stale_projects = supabase.table('para_items')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('para_type', 'project')\
            .eq('status', 'active')\
            .lt('updated_at', two_weeks_ago)\
            .execute()

        for project in stale_projects.data:
            blockers.append({
                "type": "stale_project",
                "title": project['title'],
                "days_stale": (datetime.now() - datetime.fromisoformat(project['updated_at'])).days,
                "suggestion": "Consider breaking this into smaller tasks or archiving if no longer relevant"
            })

        # Find tasks that keep rolling over
        rollover_tasks = supabase.table('tasks')\
            .select('id, title, due_date')\
            .eq('user_id', user_id)\
            .eq('status', 'pending')\
            .lt('due_date', datetime.now().isoformat())\
            .execute()

        for task in rollover_tasks.data:
            if task['due_date']:
                days_overdue = (datetime.now() - datetime.fromisoformat(task['due_date'])).days
                if days_overdue > 3:
                    blockers.append({
                        "type": "rollover_task",
                        "title": task['title'],
                        "days_overdue": days_overdue,
                        "suggestion": "This task keeps rolling over. Consider breaking it down or re-evaluating priority."
                    })

        return blockers

    async def suggest_reprioritization(self, user_id: str) -> Dict[str, Any]:
        """
        Suggest re-prioritization when workload is too high
        """

        # Get tasks due in next 24 hours
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()

        urgent_tasks = supabase.table('tasks')\
            .select('*')\
            .eq('user_id', user_id)\
            .neq('status', 'completed')\
            .lte('due_date', tomorrow)\
            .execute()

        if len(urgent_tasks.data) <= 3:
            return {"needs_reprioritization": False}

        # Too many urgent tasks - suggest reprioritization
        prompt = f"""This user has {len(urgent_tasks.data)} tasks due in the next 24 hours:

{json.dumps([{
    'title': t['title'],
    'priority': t['priority'],
    'estimated_duration': t.get('estimated_duration_minutes', 0)
} for t in urgent_tasks.data], indent=2)}

Suggest which tasks should be:
1. Kept for tomorrow (top 3-5 most important)
2. Deferred to next week
3. Potentially delegated or cancelled

Return as JSON:
{{
  "needs_reprioritization": true,
  "message": "...",
  "suggestions": {{
    "keep": ["task_id1", "task_id2"],
    "defer": ["task_id3"],
    "reconsider": ["task_id4"]
  }},
  "reasoning": "..."
}}
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        suggestion = json.loads(response.content[0].text)
        return suggestion
