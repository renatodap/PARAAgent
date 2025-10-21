"""MCP-style wrapper for Google Calendar API.

Note: MCP (Model Context Protocol) is still evolving. This is a wrapper
that provides a clean interface for calendar operations.
"""

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config import settings


class GoogleCalendarMCP:
    """MCP-style wrapper for Google Calendar API."""

    def __init__(self, user_credentials: Dict):
        """Initialize Google Calendar client.

        Args:
            user_credentials: Dict with 'access_token' and 'refresh_token'
        """
        self.credentials = Credentials(
            token=user_credentials['access_token'],
            refresh_token=user_credentials.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def get_events(
        self,
        start_date: datetime,
        end_date: datetime,
        calendar_id: str = 'primary'
    ) -> List[Dict]:
        """Fetch calendar events in date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            calendar_id: Calendar ID (default: 'primary')

        Returns:
            List of calendar events
        """
        try:
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            return events_result.get('items', [])

        except Exception as e:
            print(f"Error fetching calendar events: {e}")
            return []

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        description: str = "",
        location: str = "",
        attendees: List[str] = None,
        calendar_id: str = 'primary'
    ) -> Optional[Dict]:
        """Create a new calendar event.

        Args:
            title: Event title
            start: Start datetime
            end: End datetime
            description: Event description
            location: Event location
            attendees: List of attendee emails
            calendar_id: Calendar ID (default: 'primary')

        Returns:
            Created event or None if failed
        """
        event = {
            'summary': title,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end.isoformat(),
                'timeZone': 'UTC',
            },
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        try:
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()

            return created_event

        except Exception as e:
            print(f"Error creating calendar event: {e}")
            return None

    def update_event(
        self,
        event_id: str,
        updates: Dict,
        calendar_id: str = 'primary'
    ) -> Optional[Dict]:
        """Update an existing calendar event.

        Args:
            event_id: Google Calendar event ID
            updates: Dictionary of fields to update
            calendar_id: Calendar ID (default: 'primary')

        Returns:
            Updated event or None if failed
        """
        try:
            # Get current event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            # Apply updates
            event.update(updates)

            # Update event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            return updated_event

        except Exception as e:
            print(f"Error updating calendar event: {e}")
            return None

    def delete_event(
        self,
        event_id: str,
        calendar_id: str = 'primary'
    ) -> bool:
        """Delete a calendar event.

        Args:
            event_id: Google Calendar event ID
            calendar_id: Calendar ID (default: 'primary')

        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            return True

        except Exception as e:
            print(f"Error deleting calendar event: {e}")
            return False

    def find_free_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int,
        calendar_id: str = 'primary'
    ) -> List[Dict]:
        """Find free time slots in calendar.

        Args:
            start_date: Start of search range
            end_date: End of search range
            duration_minutes: Required slot duration
            calendar_id: Calendar ID (default: 'primary')

        Returns:
            List of free slots with 'start' and 'end' datetimes
        """
        events = self.get_events(start_date, end_date, calendar_id)

        # Extract busy times
        busy_times = []
        for event in events:
            start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
            end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))
            busy_times.append((start, end))

        # Sort busy times
        busy_times.sort(key=lambda x: x[0])

        # Find free slots
        free_slots = []
        current_time = start_date

        for busy_start, busy_end in busy_times:
            # If there's a gap before this busy time
            if current_time + timedelta(minutes=duration_minutes) <= busy_start:
                free_slots.append({
                    'start': current_time,
                    'end': busy_start
                })
            current_time = max(current_time, busy_end)

        # Check if there's time after the last event
        if current_time + timedelta(minutes=duration_minutes) <= end_date:
            free_slots.append({
                'start': current_time,
                'end': end_date
            })

        return free_slots
