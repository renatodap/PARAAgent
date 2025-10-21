from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from database import supabase
from agents.reviewer import WeeklyReviewerAgent
from mcp.sync_service import MCPSyncService
from notifications import email_service
from typing import List
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Initialize services
reviewer_agent = WeeklyReviewerAgent()
mcp_sync = MCPSyncService()

async def get_all_active_users() -> List[dict]:
    """Get all users who have completed onboarding"""
    result = supabase.table('user_profiles')\
        .select('id, email, full_name')\
        .eq('onboarding_completed', True)\
        .execute()
    return result.data

@scheduler.scheduled_job('cron', day_of_week='mon', hour=6, timezone='UTC')
async def generate_weekly_reviews():
    """
    Generate weekly reviews for all active users every Monday at 6am
    """
    logger.info("Starting weekly review generation for all users")

    try:
        users = await get_all_active_users()
        logger.info(f"Found {len(users)} active users")

        for user in users:
            try:
                # Calculate week boundaries
                today = datetime.now()
                week_start = (today - timedelta(days=today.weekday() + 7)).replace(hour=0, minute=0, second=0)
                week_end = week_start + timedelta(days=7)

                # Generate review
                logger.info(f"Generating review for user {user['id']}")
                review = await reviewer_agent.generate_review(
                    user_id=user['id'],
                    week_start=week_start.isoformat(),
                    week_end=week_end.isoformat()
                )

                # Send email notification
                try:
                    await email_service.send_weekly_review(
                        to_email=user['email'],
                        user_name=user.get('full_name', 'there'),
                        review_data=review
                    )
                    logger.info(f"Sent weekly review email to {user['email']}")
                except Exception as email_error:
                    logger.error(f"Failed to send email to {user['email']}: {str(email_error)}")

                logger.info(f"Successfully generated review for user {user['id']}")

            except Exception as e:
                logger.error(f"Failed to generate review for user {user['id']}: {str(e)}")
                continue

        logger.info("Completed weekly review generation")

    except Exception as e:
        logger.error(f"Failed to generate weekly reviews: {str(e)}")

@scheduler.scheduled_job('interval', minutes=5)
async def sync_all_integrations():
    """
    Sync MCP integrations (Google Calendar, Todoist, Notion) every 5 minutes
    """
    logger.info("Starting MCP integration sync")

    try:
        users = await get_all_active_users()

        for user in users:
            try:
                # Check if user has any integrations enabled
                integrations = supabase.table('user_integrations')\
                    .select('*')\
                    .eq('user_id', user['id'])\
                    .eq('is_active', True)\
                    .execute()

                if not integrations.data:
                    continue

                # Sync all active integrations
                await mcp_sync.sync_user_integrations(user['id'])

                logger.info(f"Synced integrations for user {user['id']}")

            except Exception as e:
                logger.error(f"Failed to sync integrations for user {user['id']}: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Failed to sync integrations: {str(e)}")

@scheduler.scheduled_job('cron', hour=18, timezone='UTC')
async def suggest_tomorrow_tasks():
    """
    Generate task suggestions for tomorrow every evening at 6pm
    """
    logger.info("Starting tomorrow task suggestions")

    try:
        users = await get_all_active_users()

        for user in users:
            try:
                # Get incomplete tasks
                tasks = supabase.table('tasks')\
                    .select('*')\
                    .eq('user_id', user['id'])\
                    .neq('status', 'completed')\
                    .limit(20)\
                    .execute()

                if not tasks.data:
                    continue

                # Get calendar events for tomorrow
                tomorrow = datetime.now() + timedelta(days=1)
                calendar_events = supabase.table('calendar_events')\
                    .select('*')\
                    .eq('user_id', user['id'])\
                    .gte('start_time', tomorrow.replace(hour=0, minute=0, second=0).isoformat())\
                    .lte('start_time', tomorrow.replace(hour=23, minute=59, second=59).isoformat())\
                    .execute()

                # TODO: Use AI agent to suggest optimal task schedule
                # suggestions = await task_suggester_agent.suggest_tasks(
                #     tasks=tasks.data,
                #     calendar=calendar_events.data,
                #     user_preferences=user_preferences
                # )

                # TODO: Create pending approval
                # await create_pending_approval(
                #     user_id=user['id'],
                #     approval_type='task_suggestions',
                #     data=suggestions
                # )

                logger.info(f"Generated suggestions for user {user['id']}")

            except Exception as e:
                logger.error(f"Failed to generate suggestions for user {user['id']}: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Failed to generate task suggestions: {str(e)}")

@scheduler.scheduled_job('cron', hour=0, minute=0, timezone='UTC')
async def cleanup_old_data():
    """
    Clean up old data every day at midnight
    - Delete completed tasks older than 90 days
    - Archive old calendar events
    - Clean up expired cache entries
    """
    logger.info("Starting data cleanup")

    try:
        # Delete old completed tasks
        ninety_days_ago = (datetime.now() - timedelta(days=90)).isoformat()
        supabase.table('tasks')\
            .delete()\
            .eq('status', 'completed')\
            .lt('completed_at', ninety_days_ago)\
            .execute()

        logger.info("Deleted old completed tasks")

        # Delete old calendar events
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        supabase.table('calendar_events')\
            .delete()\
            .lt('end_time', thirty_days_ago)\
            .eq('is_autopilot_created', False)\
            .execute()

        logger.info("Deleted old calendar events")

    except Exception as e:
        logger.error(f"Failed to cleanup old data: {str(e)}")

def start_scheduler():
    """Start the scheduler"""
    logger.info("Starting APScheduler")
    scheduler.start()

def shutdown_scheduler():
    """Shutdown the scheduler"""
    logger.info("Shutting down APScheduler")
    scheduler.shutdown()
