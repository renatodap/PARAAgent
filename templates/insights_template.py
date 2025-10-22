"""
Deterministic insights generation using templates instead of LLM.
Cost optimized: $0 vs $0.15/week per user.
"""

from typing import Dict, List, Any


def generate_productivity_insights(
    completion_by_day: Dict[str, int],
    completion_by_hour: Dict[str, int],
    blockers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate productivity insights using deterministic analysis and templates.
    Replaces LLM-generated prose with data-driven templates.
    """

    insights = []

    # Insight 1: Best productivity day
    if completion_by_day:
        best_day = max(completion_by_day.items(), key=lambda x: x[1])
        worst_day = min((k, v) for k, v in completion_by_day.items() if v > 0)

        if best_day[1] > 0:
            # Calculate percentage difference
            avg_tasks = sum(completion_by_day.values()) / len(completion_by_day)
            if avg_tasks > 0:
                pct_above_avg = round(((best_day[1] - avg_tasks) / avg_tasks) * 100)

                insights.append({
                    "type": "productivity_pattern",
                    "title": f"Peak Performance: {best_day[0]}s",
                    "description": f"You complete {pct_above_avg}% more tasks on {best_day[0]}s ({best_day[1]} tasks) compared to your average.",
                    "action": f"Schedule your most important work for {best_day[0]}s.",
                    "impact": "high" if pct_above_avg > 30 else "medium"
                })

    # Insight 2: Best time of day
    if completion_by_hour:
        best_period = max(completion_by_hour.items(), key=lambda x: x[1])

        if best_period[1] > 3:  # Only if significant
            insights.append({
                "type": "productivity_pattern",
                "title": f"Optimal Focus Time: {best_period[0]}",
                "description": f"You've completed {best_period[1]} tasks during {best_period[0]}. This appears to be your peak productivity window.",
                "action": f"Block out {best_period[0]} for deep work and important tasks.",
                "impact": "high"
            })

    # Insight 3: Stale projects (blockers)
    stale_projects = [b for b in blockers if b['type'] == 'stale_project']
    if stale_projects:
        if len(stale_projects) == 1:
            project = stale_projects[0]
            insights.append({
                "type": "blocker",
                "title": f"Stalled Project: {project['title']}",
                "description": f"No progress in {project['days_stale']} days. This project may be blocked or no longer relevant.",
                "action": project['suggestion'],
                "impact": "medium"
            })
        else:
            insights.append({
                "type": "blocker",
                "title": f"{len(stale_projects)} Projects Need Attention",
                "description": f"You have {len(stale_projects)} projects with no progress in 2+ weeks. Time to review and unblock or archive.",
                "action": "Review stale projects this week. Break into smaller tasks or archive if no longer relevant.",
                "impact": "high"
            })

    # Insight 4: Rollover tasks (chronic procrastination)
    rollover_tasks = [b for b in blockers if b['type'] == 'rollover_task']
    if rollover_tasks:
        if len(rollover_tasks) == 1:
            task = rollover_tasks[0]
            insights.append({
                "type": "rollover",
                "title": f"Chronic Rollover: {task['title']}",
                "description": f"This task is {task['days_overdue']} days overdue and keeps rolling over.",
                "action": task['suggestion'],
                "impact": "medium"
            })
        else:
            insights.append({
                "type": "rollover",
                "title": f"{len(rollover_tasks)} Tasks Keep Rolling Over",
                "description": f"These tasks are consistently postponed. They may be too big, unclear, or unimportant.",
                "action": "Break down large tasks or consider deleting tasks that aren't truly important.",
                "impact": "high"
            })

    # Insight 5: Low productivity warning
    total_tasks = sum(completion_by_day.values())
    if total_tasks < 5:  # Very low productivity
        insights.append({
            "type": "productivity_pattern",
            "title": "Low Task Completion This Month",
            "description": f"Only {total_tasks} tasks completed in the last 30 days. You may be working on projects without tracking individual tasks.",
            "action": "Break projects into smaller, trackable tasks to maintain momentum and visibility.",
            "impact": "medium"
        })

    # Insight 6: Consistent productivity (positive reinforcement)
    if len(completion_by_day) >= 7:
        days_with_activity = sum(1 for count in completion_by_day.values() if count > 0)
        if days_with_activity >= 5:
            insights.append({
                "type": "productivity_pattern",
                "title": "Consistent Weekly Habits",
                "description": f"You completed tasks on {days_with_activity} out of 7 days this week. Strong consistency!",
                "action": "Keep up the momentum. Consistency compounds over time.",
                "impact": "low"
            })

    # Return structured insights
    return {"insights": insights}


def generate_reprioritization_suggestions(
    urgent_tasks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate reprioritization suggestions using deterministic logic.
    Replaces LLM reasoning with rule-based triage.
    """

    if len(urgent_tasks) <= 3:
        return {"needs_reprioritization": False}

    # Sort by priority, then by estimated duration (quick wins first)
    def task_score(task):
        priority_scores = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
        priority_val = priority_scores.get(task.get('priority', 'medium'), 2)

        # Quick wins get bonus (tasks under 30 min)
        duration = task.get('estimated_duration_minutes', 60)
        quick_win_bonus = 1 if duration < 30 else 0

        # Earlier due dates get priority
        due_date = task.get('due_date', '')

        return (priority_val, quick_win_bonus, due_date)

    sorted_tasks = sorted(urgent_tasks, key=task_score, reverse=True)

    # Top 3-5 to keep
    keep_count = min(5, max(3, len(urgent_tasks) // 3))
    keep = [t['id'] for t in sorted_tasks[:keep_count]]

    # Rest to defer
    defer = [t['id'] for t in sorted_tasks[keep_count:]]

    # Identify tasks to reconsider (low priority or very long duration)
    reconsider = []
    for task in sorted_tasks[keep_count:]:
        if task.get('priority') == 'low' or task.get('estimated_duration_minutes', 0) > 180:
            reconsider.append(task['id'])
            defer.remove(task['id'])

    return {
        "needs_reprioritization": True,
        "message": f"You have {len(urgent_tasks)} tasks due in 24 hours. Focus on the top {keep_count} high-impact tasks.",
        "suggestions": {
            "keep": keep,
            "defer": defer,
            "reconsider": reconsider
        },
        "reasoning": f"Prioritizing by urgency, quick wins (tasks <30 min), and due dates. Deferring {len(defer)} tasks and reconsidering {len(reconsider)} low-priority or very long tasks."
    }
