from fastapi import APIRouter, Depends, status
from auth import get_current_user_id
from agents.insights import ProactiveInsightsAgent
from typing import Dict, Any

router = APIRouter(prefix="/api/insights", tags=["insights"])

@router.get("/patterns")
async def get_productivity_patterns(
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Get AI-generated productivity patterns and insights
    """
    agent = ProactiveInsightsAgent()
    insights = await agent.analyze_patterns(user_id)
    return insights

@router.get("/reprioritization")
async def get_reprioritization_suggestions(
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Get AI suggestions for task reprioritization when overloaded
    """
    agent = ProactiveInsightsAgent()
    suggestions = await agent.suggest_reprioritization(user_id)
    return suggestions
