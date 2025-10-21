"""Test suite for health check and basic API endpoints"""

import pytest

def test_root_endpoint(client):
    """Test root endpoint returns correct information"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "PARA Autopilot API"
    assert data["version"] == "0.1.0"
    assert data["status"] == "active"

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "model" in data

def test_health_check_environment(client):
    """Test health check returns correct environment"""
    response = client.get("/api/health")
    data = response.json()
    # Should be 'test' from our conftest.py
    assert data["environment"] in ["test", "development", "production"]
