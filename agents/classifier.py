"""PARA Classification Agent - Cost optimized with Groq Llama 3.3 70B."""

from typing import Dict, List
import json
from llm_provider import llm_provider


PARA_CLASSIFICATION_PROMPT = """You are a PARA method expert. Classify the following item into one of these categories:

- **Project**: Has a clear goal and deadline (e.g., "Launch new website by Q2", "Write research paper by March")
  Projects are finite endeavors with specific end goals. They should have clear success criteria.

- **Area**: Ongoing responsibility without a deadline (e.g., "Health", "Finances", "Team Management", "Personal Development")
  Areas are standards to maintain over time. They don't have end dates but require consistent attention.

- **Resource**: Reference material or topics of interest (e.g., "Python tutorials", "Marketing resources", "Design inspiration")
  Resources are information you might want to reference in the future. They're useful but don't require action.

- **Archive**: Completed or inactive items (e.g., "Old client project from 2022", "Cancelled initiative")
  Archives are things that were once active but are now complete or no longer relevant.

Item to classify:
Title: {title}
Description: {description}
Context: {context}

Analyze the item carefully and determine:
1. Does it have a specific end goal? (likely a Project)
2. Is it an ongoing responsibility? (likely an Area)
3. Is it just information to reference? (likely a Resource)
4. Is it no longer active? (likely an Archive)

Return a JSON object with:
{{
  "para_type": "project|area|resource|archive",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why this classification fits",
  "suggested_next_actions": ["action1", "action2", "action3"],
  "estimated_duration_weeks": null or number (for projects only, estimate realistic completion time)
}}

Be concise but specific in your reasoning. Suggest 2-4 concrete next actions that would move this forward."""


def classify_item(title: str, description: str = "", context: str = "") -> Dict:
    """Classify a single item into PARA using Claude Haiku 4.5.

    Args:
        title: Title of the item to classify
        description: Optional description providing more context
        context: Optional additional context (e.g., related items, user notes)

    Returns:
        Dictionary containing:
        - para_type: The classified PARA type
        - confidence: Confidence score (0.0-1.0)
        - reasoning: Explanation for the classification
        - suggested_next_actions: List of suggested actions
        - estimated_duration_weeks: For projects, estimated duration
        - usage: Token usage and cost information
    """
    prompt = PARA_CLASSIFICATION_PROMPT.format(
        title=title,
        description=description or "No description provided",
        context=context or "No additional context"
    )

    try:
        # Use LLM provider abstraction - routes to Groq for cost savings
        response = llm_provider.get_completion(
            task_type='para_classification',
            prompt=prompt,
            max_tokens=1000,
            temperature=0.3  # Lower temperature for consistent classification
        )

        # Parse JSON response
        result = json.loads(response["text"])

        # Add token usage from provider response
        return {**result, "usage": response["usage"]}

    except json.JSONDecodeError as e:
        # If JSON parsing fails, try to extract what we can
        raw_text = response.get("text", "")
        return {
            "para_type": "resource",  # Default fallback
            "confidence": 0.5,
            "reasoning": f"Classification uncertain. Raw response: {raw_text[:200]}",
            "suggested_next_actions": ["Review and manually classify this item"],
            "estimated_duration_weeks": None,
            "usage": response.get("usage", {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0
            })
        }
    except Exception as e:
        # Handle API errors
        return {
            "para_type": "resource",
            "confidence": 0.0,
            "reasoning": f"Error during classification: {str(e)}",
            "suggested_next_actions": ["Retry classification"],
            "estimated_duration_weeks": None,
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0
            }
        }


def batch_classify_items(items: List[Dict]) -> List[Dict]:
    """Classify multiple items efficiently.

    Args:
        items: List of items to classify, each with 'title', 'description', 'context'

    Returns:
        List of classification results with item IDs
    """
    results = []
    for item in items:
        classification = classify_item(
            title=item.get("title", ""),
            description=item.get("description", ""),
            context=item.get("context", "")
        )
        results.append({
            "item_id": item.get("id"),
            "original_title": item.get("title"),
            "classification": classification
        })
    return results


def reclassify_with_feedback(
    title: str,
    description: str,
    current_type: str,
    user_feedback: str
) -> Dict:
    """Reclassify an item with user feedback incorporated.

    Args:
        title: Item title
        description: Item description
        current_type: Current PARA classification
        user_feedback: User's feedback on why current classification is wrong

    Returns:
        New classification result
    """
    enhanced_context = f"""
Current classification: {current_type}
User feedback: {user_feedback}

The user believes the current classification is incorrect. Please reconsider based on their feedback.
"""

    return classify_item(title, description, enhanced_context)
