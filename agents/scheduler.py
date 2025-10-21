"""Auto-Scheduler Agent using Claude Haiku 4.5."""

from anthropic import Anthropic
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from config import settings
from database import supabase


client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


SCHEDULING_PROMPT = """You are an expert time management assistant. Given the following tasks and calendar constraints, create an optimal schedule.

Current date/time: {current_time}
User timezone: {timezone}

Tasks to schedule:
{tasks_json}

Existing calendar events (avoid conflicts):
{calendar_json}

User preferences:
- Work hours: {work_hours}
- Break frequency: Every {break_frequency} minutes
- Deep work preference: {deep_work_preference} (morning/afternoon/evening)
- Average energy level: {energy_level} (high/medium/low)

Scheduling principles:
1. **Time-box tasks** based on estimated duration (add 10-20% buffer)
2. **Respect existing calendar events** - never schedule over them
3. **Add breaks** between tasks (5-15 minute buffers)
4. **Group similar tasks** when possible to maintain flow
5. **Prioritize high-priority tasks** earlier in available time slots
6. **Match task difficulty to energy levels** (e.g., deep work in morning if that's when energy is high)
7. **Be realistic** - don't overpack the schedule

Create a schedule for the next 7 days. Return a JSON array of scheduled blocks:

[
  {{
    "task_id": "uuid",
    "start_time": "ISO datetime (YYYY-MM-DDTHH:MM:SS)",
    "end_time": "ISO datetime (YYYY-MM-DDTHH:MM:SS)",
    "reasoning": "Brief explanation of why scheduled at this time (e.g., 'High priority, morning slot when energy is highest')"
  }},
  ...
]

Important:
- Only schedule during work hours
- Leave some unscheduled time for flexibility
- If a task is too long, consider breaking it into multiple sessions
- Don't schedule more than 6 hours of focused work per day
"""


def auto_schedule_tasks(
    tasks: List[Dict],
    calendar_events: List[Dict],
    user_preferences: Dict,
    user_id: str
) -> Dict:
    """Auto-schedule tasks onto calendar with smart time-boxing.

    Args:
        tasks: List of tasks to schedule
        calendar_events: Existing calendar events to avoid
        user_preferences: User scheduling preferences
        user_id: User UUID for creating approvals

    Returns:
        Dictionary containing:
        - scheduled_blocks: List of scheduled time blocks
        - approval_id: ID of pending approval record
        - usage: Token usage and cost
    """
    current_time = datetime.now().isoformat()

    # Extract preferences with defaults
    work_hours = user_preferences.get("work_hours", "9:00-17:00")
    break_frequency = user_preferences.get("break_frequency", 90)
    deep_work_preference = user_preferences.get("deep_work_preference", "morning")
    energy_level = user_preferences.get("energy_level", "medium")
    timezone = user_preferences.get("timezone", "UTC")

    # Prepare tasks JSON (include only relevant fields)
    tasks_simplified = [
        {
            "id": task["id"],
            "title": task["title"],
            "priority": task.get("priority", "medium"),
            "estimated_duration_minutes": task.get("estimated_duration_minutes", 60),
            "due_date": task.get("due_date"),
            "description": task.get("description", "")[:100]  # Truncate long descriptions
        }
        for task in tasks
    ]

    # Prepare calendar events JSON
    events_simplified = [
        {
            "title": event["title"],
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "is_all_day": event.get("is_all_day", False)
        }
        for event in calendar_events
    ]

    prompt = SCHEDULING_PROMPT.format(
        current_time=current_time,
        timezone=timezone,
        tasks_json=json.dumps(tasks_simplified, indent=2),
        calendar_json=json.dumps(events_simplified, indent=2),
        work_hours=work_hours,
        break_frequency=break_frequency,
        deep_work_preference=deep_work_preference,
        energy_level=energy_level
    )

    try:
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
            temperature=0.5,  # Moderate creativity for scheduling
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON response
        scheduled_blocks = json.loads(response.content[0].text)

        # Create pending approval record
        approval = create_pending_approval(
            user_id=user_id,
            approval_type="task_schedule",
            description=f"Schedule {len(scheduled_blocks)} tasks over the next 7 days",
            proposed_changes=scheduled_blocks
        )

        # Calculate usage
        usage = {
            "tokens": response.usage.input_tokens + response.usage.output_tokens,
            "cost_usd": calculate_cost(response.usage.input_tokens, response.usage.output_tokens)
        }

        return {
            "scheduled_blocks": scheduled_blocks,
            "approval_id": approval["id"],
            "usage": usage
        }

    except json.JSONDecodeError:
        # Handle JSON parsing errors
        return {
            "scheduled_blocks": [],
            "approval_id": None,
            "usage": {"tokens": 0, "cost_usd": 0.0},
            "error": "Failed to parse scheduling response"
        }
    except Exception as e:
        return {
            "scheduled_blocks": [],
            "approval_id": None,
            "usage": {"tokens": 0, "cost_usd": 0.0},
            "error": str(e)
        }


def create_pending_approval(
    user_id: str,
    approval_type: str,
    description: str,
    proposed_changes: List[Dict]
) -> Dict:
    """Create a pending approval for user to review.

    Args:
        user_id: User UUID
        approval_type: Type of approval needed
        description: Human-readable description
        proposed_changes: The changes being proposed

    Returns:
        Created approval record
    """
    expires_at = (datetime.now() + timedelta(hours=24)).isoformat()

    result = supabase.table("pending_approvals").insert({
        "user_id": user_id,
        "approval_type": approval_type,
        "description": description,
        "proposed_changes": proposed_changes,
        "expires_at": expires_at
    }).execute()

    return result.data[0] if result.data else {}


def apply_schedule(approval_id: str, user_id: str) -> Dict:
    """Apply an approved schedule to tasks.

    Args:
        approval_id: UUID of the approved schedule
        user_id: User UUID for verification

    Returns:
        Dictionary with success status and updated tasks count
    """
    # Get approval
    result = supabase.table("pending_approvals")\
        .select("*")\
        .eq("id", approval_id)\
        .eq("user_id", user_id)\
        .eq("status", "approved")\
        .execute()

    if not result.data:
        return {"success": False, "error": "Approval not found or not approved"}

    approval = result.data[0]
    scheduled_blocks = approval["proposed_changes"]

    # Update tasks with scheduled times
    updated_count = 0
    for block in scheduled_blocks:
        task_id = block["task_id"]
        update_result = supabase.table("tasks")\
            .update({
                "scheduled_start": block["start_time"],
                "scheduled_end": block["end_time"],
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", task_id)\
            .eq("user_id", user_id)\
            .execute()

        if update_result.data:
            updated_count += 1

    # Mark approval as processed
    supabase.table("pending_approvals")\
        .update({"responded_at": datetime.utcnow().isoformat()})\
        .eq("id", approval_id)\
        .execute()

    return {
        "success": True,
        "updated_tasks": updated_count,
        "total_blocks": len(scheduled_blocks)
    }


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for Claude Haiku 4.5."""
    input_cost = (input_tokens / 1_000_000) * settings.CLAUDE_HAIKU_INPUT_COST
    output_cost = (output_tokens / 1_000_000) * settings.CLAUDE_HAIKU_OUTPUT_COST
    return round(input_cost + output_cost, 6)
