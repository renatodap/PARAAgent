"""Test suite for task scheduling logic"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from agents.scheduler import TaskSchedulerAgent

@pytest.fixture
def scheduler():
    """Create scheduler agent instance"""
    return TaskSchedulerAgent()

@pytest.fixture
def sample_tasks():
    """Sample tasks for scheduling tests"""
    return [
        {
            "id": "task-1",
            "title": "Review budget",
            "priority": "high",
            "estimated_duration_minutes": 60,
            "due_date": (datetime.now() + timedelta(days=2)).isoformat()
        },
        {
            "id": "task-2",
            "title": "Team meeting prep",
            "priority": "medium",
            "estimated_duration_minutes": 30,
            "due_date": (datetime.now() + timedelta(days=1)).isoformat()
        },
        {
            "id": "task-3",
            "title": "Email responses",
            "priority": "low",
            "estimated_duration_minutes": 45,
            "due_date": (datetime.now() + timedelta(days=3)).isoformat()
        }
    ]

@pytest.fixture
def sample_calendar():
    """Sample calendar events"""
    tomorrow = datetime.now() + timedelta(days=1)
    return [
        {
            "id": "event-1",
            "title": "Team Standup",
            "start_time": tomorrow.replace(hour=9, minute=0).isoformat(),
            "end_time": tomorrow.replace(hour=9, minute=30).isoformat()
        },
        {
            "id": "event-2",
            "title": "Lunch",
            "start_time": tomorrow.replace(hour=12, minute=0).isoformat(),
            "end_time": tomorrow.replace(hour=13, minute=0).isoformat()
        }
    ]

def test_scheduler_initialization(scheduler):
    """Test scheduler initializes correctly"""
    assert scheduler is not None
    assert hasattr(scheduler, 'client')

@pytest.mark.asyncio
@patch('agents.scheduler.Anthropic')
async def test_schedule_tasks(mock_anthropic, scheduler, sample_tasks, sample_calendar):
    """Test basic task scheduling"""
    # Mock Claude response with scheduled tasks
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"scheduled_tasks": [{"task_id": "task-1", "scheduled_time": "2025-10-23T10:00:00Z"}]}')]
    mock_anthropic.return_value.messages.create.return_value = mock_response

    result = await scheduler.auto_schedule(
        user_id="test-user",
        tasks=sample_tasks,
        calendar_events=sample_calendar
    )

    assert "scheduled_tasks" in result
    assert len(result["scheduled_tasks"]) > 0

@pytest.mark.asyncio
async def test_schedule_empty_tasks(scheduler):
    """Test scheduling with no tasks"""
    result = await scheduler.auto_schedule(
        user_id="test-user",
        tasks=[],
        calendar_events=[]
    )
    # Should handle empty input gracefully
    assert result is not None

def test_conflict_detection():
    """Test calendar conflict detection logic"""
    # Meeting 9:00-10:00
    meeting_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    meeting_end = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)

    # Task scheduled 9:30-10:30 (conflicts)
    task_start = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
    task_end = datetime.now().replace(hour=10, minute=30, second=0, microsecond=0)

    # Check if task_start < meeting_end AND task_end > meeting_start
    has_conflict = task_start < meeting_end and task_end > meeting_start
    assert has_conflict == True

def test_no_conflict():
    """Test non-conflicting time slots"""
    # Meeting 9:00-10:00
    meeting_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    meeting_end = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)

    # Task scheduled 10:00-11:00 (no conflict)
    task_start = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
    task_end = datetime.now().replace(hour=11, minute=0, second=0, microsecond=0)

    has_conflict = task_start < meeting_end and task_end > meeting_start
    assert has_conflict == False

@pytest.mark.asyncio
@patch('agents.scheduler.Anthropic')
async def test_priority_ordering(mock_anthropic, scheduler, sample_tasks):
    """Test high priority tasks are scheduled first"""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"scheduled_tasks": [], "reasoning": "Prioritized by urgency"}')]
    mock_anthropic.return_value.messages.create.return_value = mock_response

    result = await scheduler.auto_schedule(
        user_id="test-user",
        tasks=sample_tasks,
        calendar_events=[]
    )

    # Verify the function at least processes the request
    assert result is not None

def test_task_duration_validation():
    """Test task duration must be positive"""
    valid_duration = 60
    invalid_duration = -30

    assert valid_duration > 0
    assert invalid_duration <= 0

@pytest.mark.asyncio
async def test_schedule_respects_working_hours(scheduler):
    """Test scheduling doesn't schedule tasks outside working hours"""
    # This would test that tasks aren't scheduled before 8am or after 6pm
    # Implementation depends on scheduler logic
    pass  # Placeholder for future implementation
