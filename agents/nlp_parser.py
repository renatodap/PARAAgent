from anthropic import Anthropic
from config import settings
from typing import Dict, Any
from datetime import datetime, timedelta
import json
import re

class NaturalLanguageTaskParser:
    """
    Parse natural language input into structured task data
    Examples:
    - "Schedule meeting prep for Thursday 2pm for 1 hour"
    - "Finish project proposal by Friday"
    - "Call mom tomorrow morning"
    - "Review Q4 budget next Monday high priority"
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL

    async def parse(self, user_input: str, user_id: str) -> Dict[str, Any]:
        """
        Parse natural language input into task structure
        """

        # Get user's timezone and preferences
        user_profile = await self._get_user_profile(user_id)

        prompt = f"""Parse this natural language task input into structured data:

Input: "{user_input}"

Current date/time: {datetime.now().isoformat()}
User timezone: {user_profile.get('timezone', 'UTC')}

Extract:
1. Task title (clean, concise)
2. Due date (as ISO datetime)
3. Estimated duration in minutes
4. Priority (urgent/high/medium/low)
5. Any project/area association keywords

Return as JSON:
{{
  "title": "...",
  "description": "..." or null,
  "due_date": "ISO datetime" or null,
  "estimated_duration_minutes": number or null,
  "priority": "urgent|high|medium|low",
  "keywords": ["keyword1", "keyword2"] or [],
  "confidence": 0.0-1.0
}}

Examples:
- "Schedule meeting prep for Thursday 2pm for 1 hour" →
  {{
    "title": "Meeting prep",
    "due_date": "2025-10-23T14:00:00",
    "estimated_duration_minutes": 60,
    "priority": "medium",
    "confidence": 0.95
  }}

- "Finish project proposal by Friday high priority" →
  {{
    "title": "Finish project proposal",
    "due_date": "2025-10-24T17:00:00",
    "priority": "high",
    "keywords": ["project", "proposal"],
    "confidence": 0.9
  }}
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        parsed_task = json.loads(response.content[0].text)

        # Post-process: link to existing projects if keywords match
        if parsed_task.get('keywords'):
            linked_item = await self._find_related_para_item(
                user_id,
                parsed_task['keywords']
            )
            if linked_item:
                parsed_task['para_item_id'] = linked_item['id']
                parsed_task['linked_to'] = linked_item['title']

        return parsed_task

    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile for context"""
        from database import supabase

        result = supabase.table('user_profiles')\
            .select('timezone, para_preferences')\
            .eq('id', user_id)\
            .single()\
            .execute()

        return result.data if result.data else {}

    async def _find_related_para_item(
        self,
        user_id: str,
        keywords: list[str]
    ) -> Dict[str, Any] | None:
        """Find related PARA item based on keywords"""
        from database import supabase

        # Simple keyword matching (could be improved with embeddings)
        for keyword in keywords:
            result = supabase.table('para_items')\
                .select('id, title')\
                .eq('user_id', user_id)\
                .eq('status', 'active')\
                .ilike('title', f'%{keyword}%')\
                .limit(1)\
                .execute()

            if result.data:
                return result.data[0]

        return None

    def extract_time_info(self, text: str) -> Dict[str, Any]:
        """
        Extract time-related information from text using regex
        (backup method if Claude is unavailable)
        """

        # Common time patterns
        patterns = {
            'tomorrow': timedelta(days=1),
            'next week': timedelta(days=7),
            'next month': timedelta(days=30),
        }

        # Priority keywords
        priority_keywords = {
            'urgent': 'urgent',
            'asap': 'urgent',
            'high priority': 'high',
            'important': 'high',
            'low priority': 'low',
        }

        # Duration patterns
        duration_pattern = r'(\d+)\s*(hour|hr|minute|min)s?'

        result = {
            'due_date': None,
            'priority': 'medium',
            'estimated_duration_minutes': None
        }

        text_lower = text.lower()

        # Check for relative dates
        for keyword, delta in patterns.items():
            if keyword in text_lower:
                result['due_date'] = (datetime.now() + delta).isoformat()
                break

        # Check for priority
        for keyword, priority in priority_keywords.items():
            if keyword in text_lower:
                result['priority'] = priority
                break

        # Check for duration
        duration_match = re.search(duration_pattern, text_lower)
        if duration_match:
            amount = int(duration_match.group(1))
            unit = duration_match.group(2)

            if 'hour' in unit or unit == 'hr':
                result['estimated_duration_minutes'] = amount * 60
            else:
                result['estimated_duration_minutes'] = amount

        return result
