"""Database client and helper functions for Supabase."""

from supabase import create_client, Client
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import settings


# Initialize Supabase client
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)


class DatabaseHelper:
    """Helper class for common database operations."""

    @staticmethod
    def get_user_data(user_id: str, table: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Fetch user-specific data from a table.

        Args:
            user_id: The user's UUID
            table: Table name to query
            filters: Optional additional filters as dict

        Returns:
            List of records
        """
        query = supabase.table(table).select("*").eq("user_id", user_id)

        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        result = query.execute()
        return result.data

    @staticmethod
    def insert_record(table: str, data: Dict) -> Dict:
        """Insert a record into a table.

        Args:
            table: Table name
            data: Record data as dict

        Returns:
            Inserted record
        """
        result = supabase.table(table).insert(data).execute()
        return result.data[0] if result.data else {}

    @staticmethod
    def update_record(table: str, record_id: str, data: Dict) -> Dict:
        """Update a record by ID.

        Args:
            table: Table name
            record_id: Record UUID
            data: Updated fields

        Returns:
            Updated record
        """
        data["updated_at"] = datetime.utcnow().isoformat()
        result = supabase.table(table).update(data).eq("id", record_id).execute()
        return result.data[0] if result.data else {}

    @staticmethod
    def delete_record(table: str, record_id: str) -> bool:
        """Delete a record by ID.

        Args:
            table: Table name
            record_id: Record UUID

        Returns:
            True if successful
        """
        result = supabase.table(table).delete().eq("id", record_id).execute()
        return len(result.data) > 0

    @staticmethod
    def log_agent_action(
        user_id: str,
        action_type: str,
        input_data: Dict,
        output_data: Dict,
        model_used: str,
        tokens_used: int,
        cost_usd: float,
        status: str = "success",
        error_message: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> Dict:
        """Log an agent action for transparency and debugging.

        Args:
            user_id: User UUID
            action_type: Type of action (classify, schedule, review, etc.)
            input_data: Input to the agent
            output_data: Agent's output
            model_used: Model name used
            tokens_used: Total tokens consumed
            cost_usd: Cost in USD
            status: success, error, or pending
            error_message: Optional error message
            execution_time_ms: Execution time in milliseconds

        Returns:
            Logged action record
        """
        log_data = {
            "user_id": user_id,
            "action_type": action_type,
            "input_data": input_data,
            "output_data": output_data,
            "model_used": model_used,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "status": status,
            "error_message": error_message,
            "execution_time_ms": execution_time_ms
        }

        return DatabaseHelper.insert_record("agent_actions", log_data)


def get_user_mcp_credentials(user_id: str, integration_type: str) -> Optional[Dict[str, str]]:
    """Get decrypted OAuth credentials for a user's MCP integration.

    Args:
        user_id: User UUID
        integration_type: Type of integration (e.g., 'google_calendar')

    Returns:
        Dict with access_token and refresh_token, or None if not found
    """
    from mcp.sync_service import decrypt_token

    integration = supabase.table("mcp_integrations")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("integration_type", integration_type)\
        .eq("is_enabled", True)\
        .execute().data

    if not integration:
        return None

    integration = integration[0]

    return {
        'access_token': decrypt_token(integration['oauth_token_encrypted']),
        'refresh_token': decrypt_token(integration['refresh_token_encrypted']) if integration.get('refresh_token_encrypted') else None
    }


# Convenience instance
db = DatabaseHelper()
