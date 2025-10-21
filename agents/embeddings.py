"""Vector embeddings for semantic search using OpenAI.

Since Anthropic doesn't provide embedding endpoints, we use OpenAI's
text-embedding-3-small model which provides excellent quality at low cost.
"""

from typing import List, Dict, Optional
from config import settings
from database import supabase


# Note: OpenAI is optional - add to requirements.txt if using embeddings
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if hasattr(settings, 'OPENAI_API_KEY') else None
except ImportError:
    OPENAI_AVAILABLE = False
    openai_client = None


def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding vector for text using OpenAI.

    Args:
        text: Text to embed (max ~8000 tokens)

    Returns:
        1536-dimensional embedding vector or None if unavailable
    """
    if not OPENAI_AVAILABLE or not openai_client:
        return None

    try:
        # Use OpenAI's latest embedding model
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",  # $0.02 per 1M tokens
            input=text,
            encoding_format="float"
        )
        return response.data[0].embedding

    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def embed_para_item(item_id: str, title: str, description: str = "") -> bool:
    """Generate and store embedding for a PARA item.

    Args:
        item_id: UUID of the PARA item
        title: Item title
        description: Item description

    Returns:
        True if successful, False otherwise
    """
    # Combine title and description for richer embedding
    text = f"{title}\n\n{description}" if description else title

    embedding = generate_embedding(text)
    if not embedding:
        return False

    try:
        # Update the para_items table with the embedding
        supabase.table("para_items")\
            .update({"embedding": embedding})\
            .eq("id", item_id)\
            .execute()
        return True

    except Exception as e:
        print(f"Error storing embedding: {e}")
        return False


def embed_task(task_id: str, title: str, description: str = "") -> bool:
    """Generate and store embedding for a task.

    Args:
        task_id: UUID of the task
        title: Task title
        description: Task description

    Returns:
        True if successful, False otherwise
    """
    text = f"{title}\n\n{description}" if description else title

    embedding = generate_embedding(text)
    if not embedding:
        return False

    try:
        supabase.table("tasks")\
            .update({"embedding": embedding})\
            .eq("id", task_id)\
            .execute()
        return True

    except Exception as e:
        print(f"Error storing embedding: {e}")
        return False


def find_similar_para_items(
    query: str,
    user_id: str,
    limit: int = 5,
    match_threshold: float = 0.7
) -> List[Dict]:
    """Find similar PARA items using vector search.

    Args:
        query: Natural language query
        user_id: User UUID to filter by
        limit: Maximum number of results
        match_threshold: Minimum similarity score (0.0-1.0)

    Returns:
        List of similar PARA items with similarity scores
    """
    query_embedding = generate_embedding(query)
    if not query_embedding:
        return []

    try:
        # Use the Supabase RPC function for vector similarity search
        result = supabase.rpc(
            'match_para_items',
            {
                'query_embedding': query_embedding,
                'match_threshold': match_threshold,
                'match_count': limit,
                'filter_user_id': user_id
            }
        ).execute()

        return result.data

    except Exception as e:
        print(f"Error searching similar items: {e}")
        return []


def batch_embed_para_items(user_id: str) -> Dict[str, int]:
    """Batch generate embeddings for all PARA items without embeddings.

    Args:
        user_id: User UUID

    Returns:
        Dictionary with success/failure counts
    """
    # Fetch items without embeddings
    result = supabase.table("para_items")\
        .select("id, title, description")\
        .eq("user_id", user_id)\
        .is_("embedding", "null")\
        .execute()

    items = result.data
    success_count = 0
    failure_count = 0

    for item in items:
        if embed_para_item(item["id"], item["title"], item.get("description", "")):
            success_count += 1
        else:
            failure_count += 1

    return {
        "total": len(items),
        "success": success_count,
        "failed": failure_count
    }


def batch_embed_tasks(user_id: str) -> Dict[str, int]:
    """Batch generate embeddings for all tasks without embeddings.

    Args:
        user_id: User UUID

    Returns:
        Dictionary with success/failure counts
    """
    result = supabase.table("tasks")\
        .select("id, title, description")\
        .eq("user_id", user_id)\
        .is_("embedding", "null")\
        .execute()

    tasks = result.data
    success_count = 0
    failure_count = 0

    for task in tasks:
        if embed_task(task["id"], task["title"], task.get("description", "")):
            success_count += 1
        else:
            failure_count += 1

    return {
        "total": len(tasks),
        "success": success_count,
        "failed": failure_count
    }


def semantic_search_across_all(
    query: str,
    user_id: str,
    limit: int = 10
) -> Dict[str, List[Dict]]:
    """Search across both PARA items and tasks using semantic search.

    Args:
        query: Natural language query
        user_id: User UUID
        limit: Total number of results (split between items and tasks)

    Returns:
        Dictionary with 'para_items' and 'tasks' lists
    """
    para_results = find_similar_para_items(query, user_id, limit=limit // 2)

    # Similar function for tasks (would need similar RPC in Supabase)
    # For now, just return PARA items
    task_results = []  # TODO: Implement task similarity search

    return {
        "para_items": para_results,
        "tasks": task_results,
        "query": query
    }
