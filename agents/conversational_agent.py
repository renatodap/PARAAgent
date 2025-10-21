"""Context-aware conversational AI agent with tool use.

This is the "Autopilot" - the brain that executes multi-step tasks.
"""

from anthropic import Anthropic
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import settings
from database import supabase, db
import json
import logging

logger = logging.getLogger(__name__)
client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


AGENT_SYSTEM_PROMPT = """You are PARA Autopilot - an intelligent AI assistant that helps users manage their work and life using the PARA method (Projects, Areas, Resources, Archive).

You have access to the user's complete productivity system:
- **Projects**: Active work with deadlines and goals
- **Areas**: Ongoing responsibilities (Health, Finances, etc.)
- **Resources**: Reference material and knowledge
- **Archive**: Completed or inactive items
- **Tasks**: Actionable items with due dates and priorities
- **Calendar**: Meetings and events
- **Emails**: Gmail integration for communication
- **Google Tasks**: Mobile task sync

## Your Personality
- **Proactive**: Suggest improvements and optimizations
- **Context-aware**: Remember user's projects, preferences, patterns
- **Concise**: Get to the point, don't over-explain
- **Confirmatory**: Always confirm before sending emails or making big changes
- **Helpful**: Offer alternatives when info is missing

## How You Work

### 1. UNDERSTAND INTENT
- Parse what the user wants to accomplish
- Identify required information
- Break down multi-step requests

### 2. GATHER CONTEXT
- Use tools to search PARA items, emails, calendar
- Semantic search for relevant information
- Consider user's work patterns and history

### 3. REASON & PLAN
- Think through the steps needed
- Identify dependencies
- Spot potential issues

### 4. CONFIRM BEFORE ACTING
- **ALWAYS** show email drafts before sending
- **ALWAYS** confirm before creating/deleting items
- Explain your reasoning
- Offer alternatives

### 5. EXECUTE & LOG
- Perform the action using tools
- Log what you did for transparency
- Suggest relevant follow-ups

### 6. HANDLE ERRORS GRACEFULLY
- If info not found, ask clarifying questions
- Suggest alternatives ("Should I search your Drive?")
- **NEVER** guess or make up email addresses
- **NEVER** assume context you don't have

## Important Guidelines

### Email Handling
- Always find recipient email address using search_contacts
- If multiple matches, ask user which one
- If not found, ask user to provide it
- Draft in user's writing style (formal vs. casual based on history)
- Include relevant context from PARA system

### Task Management
- Link tasks to relevant projects when possible
- Suggest realistic due dates based on user's workload
- Consider user's calendar when scheduling
- Auto-sync to Google Tasks if user prefers mobile access

### Context Building
- Reference user's projects when relevant
- Mention past conversations/decisions
- Connect related items (emails → tasks → projects)
- Provide summaries, not raw data dumps

### Proactive Suggestions
- Notice patterns ("You always do X on Tuesday mornings")
- Detect conflicts ("This task is due but your calendar is full")
- Spot stale items ("This project hasn't been updated in 10 days")

## Tools Available

Use tools to interact with user's data. Chain them together for complex tasks.

**Search & Retrieval:**
- `search_para_items` - Semantic search across all PARA items
- `search_emails` - Search Gmail with filters
- `search_contacts` - Find email addresses
- `get_calendar_events` - Check schedule

**Creation & Modification:**
- `create_task` - Add new task
- `create_para_item` - Add project/area/resource
- `update_task` - Modify existing task
- `send_email` - Send email (CONFIRM FIRST!)

**Analysis:**
- `get_project_status` - Get project details & progress
- `analyze_productivity` - Get stats and insights
- `find_similar_items` - Semantic similarity search

Remember: You're not just a search engine - you're an intelligent assistant that takes action and helps users accomplish their goals!
"""


class ConversationalAgent:
    """Context-aware AI agent with tool use capabilities."""

    def __init__(self):
        self.client = client
        self.model = "claude-sonnet-4-20250514"

    async def chat(
        self,
        user_id: str,
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Process user message and return agent response with actions.

        Args:
            user_id: User UUID
            message: User's message/request
            conversation_history: Previous messages in conversation

        Returns:
            Dict with response, tool calls, and suggested actions
        """
        try:
            # Build conversation messages
            messages = conversation_history or []
            messages.append({"role": "user", "content": message})

            # Get user context for better responses
            user_context = await self._get_user_context(user_id)

            # Enhanced system prompt with user context
            system_prompt = f"""{AGENT_SYSTEM_PROMPT}

## Current User Context

**Active Projects ({len(user_context['projects'])}):**
{self._format_projects(user_context['projects'])}

**Pending Tasks ({len(user_context['tasks'])}):**
{self._format_tasks(user_context['tasks'])}

**Today's Calendar:**
{self._format_calendar(user_context['calendar_events'])}

**User Timezone:** {user_context.get('timezone', 'UTC')}
**Current Time:** {datetime.now().isoformat()}

Use this context to provide relevant, personalized responses!
"""

            # Call Claude with tools
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=messages,
                tools=self._get_tool_definitions()
            )

            # Process response
            result = {
                "message": "",
                "tool_calls": [],
                "suggested_actions": [],
                "pending_confirmations": [],
                "thinking": "",
                "metadata": {}
            }

            # Handle tool use
            if response.stop_reason == "tool_use":
                # Claude wants to use tools
                tool_results = []

                for block in response.content:
                    if block.type == "text":
                        result["thinking"] = block.text

                    elif block.type == "tool_use":
                        # Execute tool
                        tool_result = await self._execute_tool(
                            user_id,
                            block.name,
                            block.input
                        )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(tool_result)
                        })

                        result["tool_calls"].append({
                            "tool": block.name,
                            "input": block.input,
                            "result": tool_result
                        })

                        # If this is an email draft, add to pending confirmations
                        if block.name == "send_email_draft":
                            result["pending_confirmations"].append({
                                "action_type": "send_email",
                                "action_data": block.input
                            })

                # Continue conversation with tool results
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

                # Get final response
                final_response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    system=system_prompt,
                    messages=messages
                )

                # Extract final message
                for block in final_response.content:
                    if block.type == "text":
                        result["message"] = block.text

            else:
                # No tool use, just return text
                for block in response.content:
                    if block.type == "text":
                        result["message"] = block.text

            # Add usage metadata
            result["metadata"] = {
                "model": self.model,
                "tokens": {
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens,
                    "total": response.usage.input_tokens + response.usage.output_tokens
                },
                "cost_usd": self._calculate_cost(response.usage.input_tokens, response.usage.output_tokens)
            }

            # Log agent interaction
            db.log_agent_action(
                user_id=user_id,
                action_type="conversational_chat",
                input_data={"message": message},
                output_data=result,
                model_used=self.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                cost_usd=result["metadata"]["cost_usd"]
            )

            return result

        except Exception as e:
            logger.error(f"Agent chat error: {str(e)}", exc_info=True)
            return {
                "message": f"I encountered an error: {str(e)}. Please try rephrasing your request.",
                "error": str(e)
            }

    async def _get_user_context(self, user_id: str) -> Dict:
        """Get user's current context for better agent responses."""
        try:
            # Get active projects
            projects = supabase.table("para_items")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("para_type", "project")\
                .eq("status", "active")\
                .limit(10)\
                .execute().data or []

            # Get pending tasks
            tasks = supabase.table("tasks")\
                .select("*")\
                .eq("user_id", user_id)\
                .in_("status", ["pending", "in_progress"])\
                .order("due_date")\
                .limit(20)\
                .execute().data or []

            # Get today's calendar events
            today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
            today_end = datetime.now().replace(hour=23, minute=59, second=59).isoformat()

            calendar_events = supabase.table("calendar_events")\
                .select("*")\
                .eq("user_id", user_id)\
                .gte("start_time", today_start)\
                .lte("start_time", today_end)\
                .execute().data or []

            # Get user profile
            profile = supabase.table("user_profiles")\
                .select("*")\
                .eq("id", user_id)\
                .single()\
                .execute().data or {}

            return {
                "projects": projects,
                "tasks": tasks,
                "calendar_events": calendar_events,
                "timezone": profile.get("timezone", "UTC"),
                "preferences": profile.get("para_preferences", {})
            }

        except Exception as e:
            logger.error(f"Error getting user context: {str(e)}")
            return {
                "projects": [],
                "tasks": [],
                "calendar_events": [],
                "timezone": "UTC",
                "preferences": {}
            }

    def _format_projects(self, projects: List[Dict]) -> str:
        """Format projects for context."""
        if not projects:
            return "No active projects"

        lines = []
        for p in projects[:5]:  # Top 5
            due = p.get('due_date', 'No deadline')
            lines.append(f"- {p['title']} (due: {due})")
        return "\n".join(lines)

    def _format_tasks(self, tasks: List[Dict]) -> str:
        """Format tasks for context."""
        if not tasks:
            return "No pending tasks"

        lines = []
        for t in tasks[:10]:  # Top 10
            due = t.get('due_date', 'No deadline')
            priority = t.get('priority', 'medium')
            lines.append(f"- {t['title']} (due: {due}, priority: {priority})")
        return "\n".join(lines)

    def _format_calendar(self, events: List[Dict]) -> str:
        """Format calendar events for context."""
        if not events:
            return "No events scheduled today"

        lines = []
        for e in events:
            start = e.get('start_time', '')
            lines.append(f"- {start}: {e['title']}")
        return "\n".join(lines)

    def _get_tool_definitions(self) -> List[Dict]:
        """Define tools available to the agent."""
        return [
            {
                "name": "search_para_items",
                "description": "Search user's PARA items (projects, areas, resources, archives) using semantic search. Use this to find relevant projects, reference materials, or past work.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g., 'Q4 budget', 'website redesign')"
                        },
                        "para_type": {
                            "type": "string",
                            "enum": ["project", "area", "resource", "archive"],
                            "description": "Filter by PARA type (optional)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results (default: 10)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_emails",
                "description": "Search user's Gmail inbox. Use Gmail query syntax for filters.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Gmail search query (e.g., 'from:alice subject:budget', 'is:unread', 'has:attachment')"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Max emails to return (default: 20)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_contacts",
                "description": "Find a person's email address from user's contacts. Returns all matches if multiple people have same name.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Person's name to search for"
                        }
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "get_calendar_events",
                "description": "Get user's calendar events for a date range.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date (ISO format)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (ISO format)"
                        }
                    },
                    "required": ["start_date", "end_date"]
                }
            },
            {
                "name": "create_task",
                "description": "Create a new task for the user. Links to project if relevant.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Task title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Task description (optional)"
                        },
                        "due_date": {
                            "type": "string",
                            "description": "Due date (ISO format, optional)"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "Task priority (default: medium)"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Link to project UUID (optional)"
                        }
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "send_email_draft",
                "description": "IMPORTANT: This only DRAFTS an email - it does NOT send it! Shows the draft to user for confirmation. User must explicitly approve before sending.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject"
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body"
                        }
                    },
                    "required": ["to", "subject", "body"]
                }
            }
        ]

    async def _execute_tool(self, user_id: str, tool_name: str, tool_input: Dict) -> Dict:
        """Execute a tool and return results."""
        try:
            if tool_name == "search_para_items":
                return await self._tool_search_para(user_id, tool_input)

            elif tool_name == "search_emails":
                return await self._tool_search_emails(user_id, tool_input)

            elif tool_name == "search_contacts":
                return await self._tool_search_contacts(user_id, tool_input)

            elif tool_name == "get_calendar_events":
                return await self._tool_get_calendar(user_id, tool_input)

            elif tool_name == "create_task":
                return await self._tool_create_task(user_id, tool_input)

            elif tool_name == "send_email_draft":
                return await self._tool_email_draft(user_id, tool_input)

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {str(e)}")
            return {"error": str(e)}

    async def _tool_search_para(self, user_id: str, input: Dict) -> Dict:
        """Search PARA items."""
        from agents.embeddings import find_similar_para_items

        query = input['query']
        para_type = input.get('para_type')
        limit = input.get('limit', 10)

        results = find_similar_para_items(
            user_id=user_id,
            query_text=query,
            para_type=para_type,
            limit=limit
        )

        return {
            "query": query,
            "count": len(results),
            "results": results
        }

    async def _tool_search_emails(self, user_id: str, input: Dict) -> Dict:
        """Search emails."""
        # Get user's Gmail integration
        integration = supabase.table("mcp_integrations")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("integration_type", "google_calendar")\
            .eq("is_enabled", True)\
            .execute().data

        if not integration:
            return {"error": "Gmail not connected. Please connect Google account first."}

        from mcp.gmail_mcp import GmailMCP
        from mcp.sync_service import decrypt_token

        gmail = GmailMCP({
            'access_token': decrypt_token(integration[0]['oauth_token_encrypted']),
            'refresh_token': decrypt_token(integration[0]['refresh_token_encrypted']) if integration[0].get('refresh_token_encrypted') else None
        })

        query = input['query']
        max_results = input.get('max_results', 20)

        emails = gmail.search_emails(query, max_results=max_results)

        # Return summarized results (not full email bodies)
        return {
            "query": query,
            "count": len(emails),
            "emails": [{
                "id": e['id'],
                "subject": e['subject'],
                "from": e['from'],
                "date": e['date'],
                "snippet": e['snippet']
            } for e in emails]
        }

    async def _tool_search_contacts(self, user_id: str, input: Dict) -> Dict:
        """Search contacts - stub for now."""
        name = input['name']

        # For now, search emails to find addresses
        # TODO: Integrate with Google Contacts API

        integration = supabase.table("mcp_integrations")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("integration_type", "google_calendar")\
            .eq("is_enabled", True)\
            .execute().data

        if not integration:
            return {"error": "Google not connected"}

        from mcp.gmail_mcp import GmailMCP
        from mcp.sync_service import decrypt_token

        gmail = GmailMCP({
            'access_token': decrypt_token(integration[0]['oauth_token_encrypted']),
            'refresh_token': decrypt_token(integration[0]['refresh_token_encrypted']) if integration[0].get('refresh_token_encrypted') else None
        })

        # Search recent emails from this person
        emails = gmail.search_emails(f"from:{name}", max_results=5)

        if emails:
            # Extract unique email addresses
            addresses = list(set([e['from'] for e in emails]))
            return {
                "name": name,
                "found": len(addresses),
                "contacts": [{"email": addr, "last_contact": emails[0]['date']} for addr in addresses]
            }
        else:
            return {
                "name": name,
                "found": 0,
                "contacts": [],
                "message": f"No emails found from '{name}'. Please provide email address manually."
            }

    async def _tool_get_calendar(self, user_id: str, input: Dict) -> Dict:
        """Get calendar events."""
        start = input['start_date']
        end = input['end_date']

        events = supabase.table("calendar_events")\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("start_time", start)\
            .lte("start_time", end)\
            .execute().data or []

        return {
            "start_date": start,
            "end_date": end,
            "count": len(events),
            "events": events
        }

    async def _tool_create_task(self, user_id: str, input: Dict) -> Dict:
        """Create a task."""
        task_data = {
            "user_id": user_id,
            "title": input['title'],
            "description": input.get('description', ''),
            "due_date": input.get('due_date'),
            "priority": input.get('priority', 'medium'),
            "status": "pending",
            "source": "ai_agent"
        }

        if input.get('project_id'):
            task_data['para_item_id'] = input['project_id']

        task = db.insert_record("tasks", task_data)

        return {
            "success": True,
            "task": task,
            "message": f"Task '{task['title']}' created successfully"
        }

    async def _tool_email_draft(self, user_id: str, input: Dict) -> Dict:
        """Draft an email (does NOT send it!)."""
        return {
            "draft": True,
            "to": input['to'],
            "subject": input['subject'],
            "body": input['body'],
            "message": "Email draft created. User must approve before sending."
        }

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for Claude Sonnet 4."""
        # Sonnet 4: $3/M input, $15/M output
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0
        return round(input_cost + output_cost, 6)


# Global instance
conversational_agent = ConversationalAgent()
