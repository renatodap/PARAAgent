"""Pytest configuration and fixtures for PARA Autopilot tests"""

import pytest
import os

# Set test environment variables BEFORE any imports
os.environ["ENVIRONMENT"] = "test"
os.environ["SUPABASE_URL"] = os.getenv("SUPABASE_URL", "https://test.supabase.co")
os.environ["SUPABASE_SERVICE_KEY"] = os.getenv("SUPABASE_SERVICE_KEY", "test-key")
os.environ["SUPABASE_ANON_KEY"] = os.getenv("SUPABASE_ANON_KEY", "test-anon-key")
os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ["JWT_SECRET"] = os.getenv("JWT_SECRET", "test-secret-key-for-testing-only")

# Now we can import after env vars are set
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)

@pytest.fixture
def test_user():
    """Mock test user data"""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "TestPassword123!"
    }

@pytest.fixture
def test_project():
    """Mock test project data"""
    return {
        "title": "Q4 Planning",
        "description": "Plan for Q4 2025",
        "para_type": "project",
        "status": "active",
        "deadline": "2025-12-31T23:59:59Z"
    }

@pytest.fixture
def test_task():
    """Mock test task data"""
    return {
        "title": "Review budget proposal",
        "description": "Review and approve Q4 budget",
        "status": "pending",
        "priority": "high",
        "due_date": "2025-10-25T17:00:00Z",
        "estimated_duration_minutes": 60
    }

@pytest.fixture
def mock_auth_header(test_user):
    """Mock authentication header"""
    # In real tests, you'd generate a valid JWT token
    # For now, this is a placeholder
    return {
        "Authorization": "Bearer test-token"
    }
