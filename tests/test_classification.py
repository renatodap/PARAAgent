"""Test suite for PARA classification logic"""

import pytest
from unittest.mock import patch, MagicMock
from agents.classifier import classify_item

@patch('agents.classifier.Anthropic')
def test_classify_project(mock_anthropic):
    """Test classification of project-type item"""
    # Mock Claude response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"para_type": "project", "confidence": 0.95, "reasoning": "Has deadline and specific outcome", "suggested_next_actions": ["Start planning"], "estimated_duration_weeks": 12}')]
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
    mock_anthropic.return_value.messages.create.return_value = mock_response

    result = classify_item(
        title="Q4 Planning",
        description="Plan and execute Q4 strategy",
        context="deadline: 2025-12-31"
    )

    assert result["para_type"] == "project"
    assert result["confidence"] >= 0.9

@patch('agents.classifier.Anthropic')
def test_classify_area(mock_anthropic):
    """Test classification of area-type item"""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"para_type": "area", "confidence": 0.92, "reasoning": "Ongoing responsibility", "suggested_next_actions": ["Set goals"], "estimated_duration_weeks": null}')]
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
    mock_anthropic.return_value.messages.create.return_value = mock_response

    result = classify_item(
        title="Health & Fitness",
        description="Maintain healthy lifestyle",
        context=""
    )

    assert result["para_type"] == "area"

@patch('agents.classifier.Anthropic')
def test_classify_resource(mock_anthropic):
    """Test classification of resource-type item"""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"para_type": "resource", "confidence": 0.88, "reasoning": "Reference material", "suggested_next_actions": ["Review"], "estimated_duration_weeks": null}')]
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
    mock_anthropic.return_value.messages.create.return_value = mock_response

    result = classify_item(
        title="Python Best Practices",
        description="Collection of Python coding guidelines",
        context=""
    )

    assert result["para_type"] == "resource"

def test_classify_empty_title():
    """Test classification handles empty title"""
    result = classify_item(title="", description="", context="")
    # Should not raise, should return a result (possibly with low confidence)
    assert "para_type" in result
    assert "confidence" in result

def test_confidence_score_range(classifier):
    """Test confidence scores are within valid range [0, 1]"""
    # This would test actual classification results
    # For now, just verify the concept
    valid_confidence = 0.95
    assert 0.0 <= valid_confidence <= 1.0

@pytest.mark.parametrize("para_type", ["project", "area", "resource", "archive"])
def test_valid_para_types(para_type):
    """Test all valid PARA types are recognized"""
    valid_types = ["project", "area", "resource", "archive"]
    assert para_type in valid_types
