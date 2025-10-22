from database import supabase
from datetime import datetime, timedelta
from typing import List, Dict, Any
from templates.insights_template import generate_productivity_insights, generate_reprioritization_suggestions

class ProactiveInsightsAgent:
    """
    Agent that proactively analyzes user behavior and provides insights.
    Cost-optimized: Uses deterministic analysis instead of LLM ($0 vs $0.15/week).
    """

    def __init__(self):
        pass  # No LLM needed - using deterministic templates

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

        # Generate insights using deterministic templates (cost optimized)
        insights = generate_productivity_insights(
            completion_by_day=completion_by_day,
            completion_by_hour=completion_by_hour,
            blockers=blockers
        )

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
        Suggest re-prioritization when workload is too high.
        Cost-optimized: Uses deterministic logic instead of LLM.
        """

        # Get tasks due in next 24 hours
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()

        urgent_tasks = supabase.table('tasks')\
            .select('*')\
            .eq('user_id', user_id)\
            .neq('status', 'completed')\
            .lte('due_date', tomorrow)\
            .execute()

        # Use deterministic reprioritization logic
        suggestion = generate_reprioritization_suggestions(urgent_tasks.data)
        return suggestion
