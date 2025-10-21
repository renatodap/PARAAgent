"""API router for semantic search endpoints."""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from auth import get_current_user_id
from agents.embeddings import (
    find_similar_para_items,
    semantic_search_across_all,
    batch_embed_para_items,
    batch_embed_tasks
)

router = APIRouter()


@router.get("/similar")
async def search_similar_items(
    query: str = Query(..., description="Natural language search query"),
    limit: int = Query(5, ge=1, le=20),
    match_threshold: float = Query(0.7, ge=0.0, le=1.0),
    user_id: str = Depends(get_current_user_id)
):
    """Search for similar PARA items using semantic search.

    Uses vector embeddings to find items semantically similar to the query,
    even if they don't share exact keywords.

    Example: "side projects I want to learn from" might match Resources
    about learning and Projects marked as learning-focused.
    """
    results = find_similar_para_items(
        query=query,
        user_id=user_id,
        limit=limit,
        match_threshold=match_threshold
    )

    return {
        "query": query,
        "results": results,
        "count": len(results)
    }


@router.get("/all")
async def search_all(
    query: str = Query(..., description="Natural language search query"),
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id)
):
    """Search across all PARA items and tasks using semantic search."""
    results = semantic_search_across_all(
        query=query,
        user_id=user_id,
        limit=limit
    )

    return results


@router.post("/embed/para-items")
async def embed_all_para_items(
    user_id: str = Depends(get_current_user_id)
):
    """Generate embeddings for all PARA items that don't have them yet.

    This is useful for:
    - Initial setup after importing items
    - Backfilling embeddings for existing items
    - After bulk item creation
    """
    result = batch_embed_para_items(user_id)

    return {
        "message": f"Embedded {result['success']} of {result['total']} items",
        "success": result['success'],
        "failed": result['failed'],
        "total": result['total']
    }


@router.post("/embed/tasks")
async def embed_all_tasks(
    user_id: str = Depends(get_current_user_id)
):
    """Generate embeddings for all tasks that don't have them yet."""
    result = batch_embed_tasks(user_id)

    return {
        "message": f"Embedded {result['success']} of {result['total']} tasks",
        "success": result['success'],
        "failed": result['failed'],
        "total": result['total']
    }
