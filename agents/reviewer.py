"""Weekly Review Agent using Claude Haiku 4.5."""

from anthropic import Anthropic
from datetime import datetime, timedelta
from typing import List, Dict
import json
from config import settings
from database import supabase


client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


WEEKLY_REVIEW_PROMPT = """You are a personal productivity coach conducting a weekly review using the PARA method.

Review period: {week_start} to {week_end}

## Completed Tasks This Week ({completed_count} total):
{completed_tasks}

## Active Projects:
{active_projects}

## Active Areas (Ongoing Responsibilities):
{active_areas}

## Calendar Events Attended:
{calendar_events}

As a thoughtful productivity coach, generate a comprehensive weekly review that:

1. **Celebrates wins** - Acknowledge accomplishments with specific detail and genuine encouragement
2. **Identifies patterns** - Notice trends in productivity, energy, and focus
3. **Offers insight** - Provide thoughtful observations about progress and challenges
4. **Plans forward** - Suggest specific, achievable outcomes for next week

Generate a structured review in JSON format:

{{
  "summary": "A warm, encouraging 2-3 sentence overview of the week's highlights and overall progress",

  "projects_update": {{
    "project_id_1": "Brief status update and suggested next steps",
    "project_id_2": "Brief status update and suggested next steps"
  }},

  "areas_update": {{
    "area_name_1": "Health check on this area of responsibility",
    "area_name_2": "Health check on this area of responsibility"
  }},

  "wins": [
    "Specific accomplishment 1 (be detailed and celebratory)",
    "Specific accomplishment 2",
    "Specific accomplishment 3"
  ],

  "rollovers": [
    {{
      "task_id": "uuid_if_available_or_null",
      "task_title": "Task that didn't get done",
      "reason": "Compassionate analysis of why (without judgment)",
      "suggestion": "Specific suggestion for moving forward"
    }}
  ],

  "next_week_proposals": [
    {{
      "outcome": "Clear, achievable goal statement",
      "tasks": ["Concrete task 1", "Concrete task 2", "Concrete task 3"],
      "estimated_hours": 5
    }},
    {{
      "outcome": "Another clear goal",
      "tasks": ["Task 1", "Task 2"],
      "estimated_hours": 3
    }}
  ],

  "insights": [
    "Pattern or observation about productivity (e.g., 'Most tasks completed on Tuesday and Wednesday mornings')",
    "Insight about energy and focus (e.g., 'Deep work sessions were most effective in 90-minute blocks')",
    "Suggestion for improvement (e.g., 'Consider batching similar tasks to maintain flow state')"
  ]
}}

Guidelines:
- Be specific and actionable, not generic
- Use an encouraging, supportive tone (imagine a thoughtful coach)
- Identify 3-5 key outcomes for next week (not too many)
- Estimate realistic time commitments
- Notice patterns in when/how work gets done
- Celebrate progress without being saccharine
"""


def generate_weekly_review(user_id: str, week_start: datetime) -> Dict:
    """Generate AI-powered weekly review.

    Args:
        user_id: User UUID
        week_start: Start date of the week to review

    Returns:
        Dictionary containing:
        - review_id: UUID of created review
        - review_data: Structured review insights
        - usage: Token usage and cost
    """
    week_end = week_start + timedelta(days=7)

    # Fetch data from database
    completed_tasks = fetch_completed_tasks(user_id, week_start, week_end)
    active_projects = fetch_active_projects(user_id)
    active_areas = fetch_active_areas(user_id)
    calendar_events = fetch_calendar_events(user_id, week_start, week_end)

    # Format data for prompt
    tasks_summary = format_tasks_summary(completed_tasks)
    projects_summary = format_para_items_summary(active_projects)
    areas_summary = format_para_items_summary(active_areas)
    events_summary = format_calendar_summary(calendar_events)

    prompt = WEEKLY_REVIEW_PROMPT.format(
        week_start=week_start.strftime("%Y-%m-%d"),
        week_end=week_end.strftime("%Y-%m-%d"),
        completed_count=len(completed_tasks),
        completed_tasks=tasks_summary,
        active_projects=projects_summary,
        active_areas=areas_summary,
        calendar_events=events_summary
    )

    try:
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
            temperature=0.7,  # Higher temperature for more natural, varied language
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        review_data = json.loads(response.content[0].text)

        # Save to database
        saved_review = supabase.table("weekly_reviews").insert({
            "user_id": user_id,
            "week_start_date": week_start.date().isoformat(),
            "week_end_date": week_end.date().isoformat(),
            "summary": review_data["summary"],
            "insights": review_data,
            "completed_tasks_count": len(completed_tasks),
            "rollover_tasks": review_data.get("rollovers", []),
            "next_week_proposals": review_data.get("next_week_proposals", []),
            "status": "draft"
        }).execute()

        usage = {
            "tokens": response.usage.input_tokens + response.usage.output_tokens,
            "cost_usd": calculate_cost(response.usage.input_tokens, response.usage.output_tokens)
        }

        return {
            "review_id": saved_review.data[0]["id"],
            "review_data": review_data,
            "usage": usage
        }

    except json.JSONDecodeError as e:
        # Handle JSON parsing errors
        return {
            "review_id": None,
            "review_data": {"error": "Failed to parse review"},
            "usage": {"tokens": 0, "cost_usd": 0.0}
        }
    except Exception as e:
        return {
            "review_id": None,
            "review_data": {"error": str(e)},
            "usage": {"tokens": 0, "cost_usd": 0.0}
        }


def fetch_completed_tasks(user_id: str, start: datetime, end: datetime) -> List[Dict]:
    """Fetch tasks completed during the review period."""
    result = supabase.table("tasks")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("status", "completed")\
        .gte("completed_at", start.isoformat())\
        .lte("completed_at", end.isoformat())\
        .order("completed_at", desc=False)\
        .execute()
    return result.data


def fetch_active_projects(user_id: str) -> List[Dict]:
    """Fetch currently active projects."""
    result = supabase.table("para_items")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("para_type", "project")\
        .eq("status", "active")\
        .execute()
    return result.data


def fetch_active_areas(user_id: str) -> List[Dict]:
    """Fetch active areas of responsibility."""
    result = supabase.table("para_items")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("para_type", "area")\
        .eq("status", "active")\
        .execute()
    return result.data


def fetch_calendar_events(user_id: str, start: datetime, end: datetime) -> List[Dict]:
    """Fetch calendar events during review period."""
    result = supabase.table("calendar_events")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("start_time", start.isoformat())\
        .lte("start_time", end.isoformat())\
        .order("start_time", desc=False)\
        .execute()
    return result.data


def format_tasks_summary(tasks: List[Dict]) -> str:
    """Format tasks for prompt."""
    if not tasks:
        return "No tasks completed this week."

    summary = []
    for task in tasks[:20]:  # Limit to most recent 20
        priority = task.get("priority", "medium").upper()
        title = task["title"]
        completed_at = task.get("completed_at", "")[:10]  # Just the date
        summary.append(f"- [{priority}] {title} (completed: {completed_at})")

    if len(tasks) > 20:
        summary.append(f"... and {len(tasks) - 20} more tasks")

    return "\n".join(summary)


def format_para_items_summary(items: List[Dict]) -> str:
    """Format PARA items for prompt."""
    if not items:
        return "None"

    summary = []
    for item in items:
        title = item["title"]
        description = item.get("description", "")[:100]  # Truncate
        due_date = item.get("due_date", "")[:10] if item.get("due_date") else "No deadline"
        summary.append(f"- {title} (due: {due_date})")
        if description:
            summary.append(f"  {description}")

    return "\n".join(summary)


def format_calendar_summary(events: List[Dict]) -> str:
    """Format calendar events for prompt."""
    if not events:
        return "No calendar events recorded."

    summary = []
    for event in events[:15]:  # Limit to 15 most recent
        title = event["title"]
        start = event["start_time"][:10]  # Just the date
        duration_hours = calculate_duration_hours(event["start_time"], event["end_time"])
        summary.append(f"- {title} ({start}, {duration_hours}h)")

    if len(events) > 15:
        summary.append(f"... and {len(events) - 15} more events")

    return "\n".join(summary)


def calculate_duration_hours(start: str, end: str) -> float:
    """Calculate duration in hours between two ISO timestamps."""
    try:
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        duration = end_dt - start_dt
        return round(duration.total_seconds() / 3600, 1)
    except:
        return 0.0


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for Claude Haiku 4.5."""
    input_cost = (input_tokens / 1_000_000) * settings.CLAUDE_HAIKU_INPUT_COST
    output_cost = (output_tokens / 1_000_000) * settings.CLAUDE_HAIKU_OUTPUT_COST
    return round(input_cost + output_cost, 6)
