"""
Deterministic weekly review generation using Jinja2 templates.
Cost-optimized: $0 vs $0.10/week per user.
"""

from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from typing import Dict, List, Any
import os


# Setup Jinja2 environment
template_dir = os.path.dirname(os.path.abspath(__file__))
jinja_env = Environment(loader=FileSystemLoader(template_dir))


def generate_weekly_review(
    week_start: datetime,
    week_end: datetime,
    completed_tasks: List[Dict[str, Any]],
    active_projects: List[Dict[str, Any]],
    active_areas: List[Dict[str, Any]],
    rollovers: List[Dict[str, Any]],
    completion_by_day: Dict[str, int],
    completion_by_hour: Dict[str, int]
) -> Dict[str, Any]:
    """
    Generate weekly review using Jinja2 template.
    Replaces LLM-generated prose with data-driven templates.
    """

    # Calculate metrics
    completed_count = len(completed_tasks)

    # Top wins (highest priority completed tasks)
    top_wins = sorted(
        completed_tasks,
        key=lambda t: (
            {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}.get(t.get('priority', 'medium'), 2),
            t.get('completed_at', '')
        ),
        reverse=True
    )[:5]

    # Find best productivity day
    best_day = None
    if completion_by_day:
        best_day_name = max(completion_by_day.items(), key=lambda x: x[1])
        best_day = {"name": best_day_name[0], "count": best_day_name[1]}

    # Find best time of day
    best_time = None
    if completion_by_hour:
        best_period = max(completion_by_hour.items(), key=lambda x: x[1])
        if best_period[1] > 2:  # Only if significant
            best_time = {"period": best_period[0], "count": best_period[1]}

    # Calculate consistency (active days)
    active_days = sum(1 for count in completion_by_day.values() if count > 0)

    # Generate simple insights
    insights = []

    if best_day and best_day['count'] >= 3:
        insights.append({
            "title": f"{best_day['name']} is your power day",
            "description": f"You completed {best_day['count']} tasks on {best_day['name']}. Schedule important work for this day."
        })

    if len(rollovers) > 3:
        insights.append({
            "title": "High rollover count",
            "description": f"{len(rollovers)} tasks are rolling over. Consider breaking them into smaller, actionable steps."
        })

    if active_days >= 5:
        insights.append({
            "title": "Consistent momentum",
            "description": f"You completed tasks on {active_days} out of 7 days. Consistency compounds!"
        })

    # Simple next week proposals (from active projects with upcoming deadlines)
    next_week_proposals = []
    for project in active_projects[:3]:  # Top 3 projects
        if project.get('due_date'):
            next_week_proposals.append({
                "outcome": f"Make progress on {project['title']}",
                "estimated_hours": 5,
                "tasks": [
                    "Review current status",
                    "Identify next 3 actions",
                    "Complete highest priority action"
                ]
            })

    # Render template
    template = jinja_env.get_template('weekly_review.jinja2')

    rendered = template.render(
        week_start=week_start.strftime('%B %d, %Y'),
        week_end=week_end.strftime('%B %d, %Y'),
        completed_count=completed_count,
        last_week_count=0,  # TODO: fetch from previous week
        top_project=active_projects[0]['title'] if active_projects else None,
        top_wins=top_wins,
        active_projects=active_projects,
        active_areas=active_areas,
        rollovers=rollovers,
        best_day=best_day,
        best_time=best_time,
        active_days=active_days,
        consistency_score=active_days / 7 if active_days else 0,
        next_week_proposals=next_week_proposals,
        insights=insights,
        generated_at=datetime.now().strftime('%B %d, %Y at %I:%M %p')
    )

    # Return structured data matching original format
    return {
        "summary": f"You completed {completed_count} tasks this week.",
        "projects_update": {p['id']: f"Active - {p.get('status', 'in progress')}" for p in active_projects},
        "areas_update": {a['id']: "Maintained" for a in active_areas},
        "wins": [w['title'] for w in top_wins],
        "rollovers": [
            {
                "task_id": r.get('task_id'),
                "task_title": r.get('task_title', r.get('title', 'Unknown')),
                "reason": "Consistently postponed" if r.get('days_overdue', 0) > 3 else "Recently added",
                "suggestion": "Break into smaller tasks" if r.get('days_overdue', 0) > 7 else "Schedule specific time block"
            }
            for r in rollovers
        ],
        "next_week_proposals": next_week_proposals,
        "insights": [i["description"] for i in insights],
        "rendered_markdown": rendered  # Full rendered template for display
    }
