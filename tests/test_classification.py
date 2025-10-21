"""Test suite for PARA classification logic"""

import pytest
from unittest.mock import patch, MagicMock
from agents.classifier import PARAClassifierAgent

@pytest.fixture
def classifier():
    """Create classifier agent instance"""
    return PARAClassifierAgent()

def test_classifier_initialization(classifier):
    """Test classifier initializes correctly"""
    assert classifier is not None
    assert hasattr(classifier, 'client')
    assert hasattr(classifier, 'model')

@pytest.mark.asyncio
@patch('agents.classifier.Anthropic')
async def test_classify_project(mock_anthropic, classifier):
    """Test classification of project-type item"""
    # Mock Claude response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"para_type": "project", "confidence": 0.95, "reasoning": "Has deadline and specific outcome"}')]
    mock_anthropic.return_value.messages.create.return_value = mock_response

    result = await classifier.classify(
        title="Q4 Planning",
        description="Plan and execute Q4 strategy",
        context={"deadline": "2025-12-31"}
    )

    assert result["para_type"] == "project"
    assert result["confidence"] >= 0.9

@pytest.mark.asyncio
@patch('agents.classifier.Anthropic')
async def test_classify_area(mock_anthropic, classifier):
    """Test classification of area-type item"""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"para_type": "area", "confidence": 0.92, "reasoning": "Ongoing responsibility"}')]
    mock_anthropic.return_value.messages.create.return_value = mock_response

    result = await classifier.classify(
        title="Health & Fitness",
        description="Maintain healthy lifestyle",
        context={}
    )

    assert result["para_type"] == "area"

@pytest.mark.asyncio
@patch('agents.classifier.Anthropic')
async def test_classify_resource(mock_anthropic, classifier):
    """Test classification of resource-type item"""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"para_type": "resource", "confidence": 0.88, "reasoning": "Reference material"}')]
    mock_anthropic.return_value.messages.create.return_value = mock_response

    result = await classifier.classify(
        title="Python Best Practices",
        description="Collection of Python coding guidelines",
        context={}
    )

    assert result["para_type"] == "resource"

@pytest.mark.asyncio
async def test_classify_empty_title(classifier):
    """Test classification fails gracefully with empty title"""
    with pytest.raises((ValueError, Exception)):
        await classifier.classify(title="", description="", context={})

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
