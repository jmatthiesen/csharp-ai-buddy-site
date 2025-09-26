"""
Test cases for the feedback API endpoint.
"""

import pytest
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_feedback_success():
    """Test successful feedback submission"""
    feedback_data = {
        "message_id": "123e4567-e89b-12d3-a456-426614174000",
        "feedback_type": "thumbs_up",
        "comment": "Great response!"
    }
    
    response = client.post("/api/feedback", json=feedback_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "successfully" in data["message"].lower()

def test_feedback_without_comment():
    """Test feedback submission without comment"""
    feedback_data = {
        "message_id": "123e4567-e89b-12d3-a456-426614174001",
        "feedback_type": "thumbs_down"
    }
    
    response = client.post("/api/feedback", json=feedback_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

def test_invalid_feedback_type():
    """Test invalid feedback type"""
    feedback_data = {
        "message_id": "123e4567-e89b-12d3-a456-426614174000",
        "feedback_type": "invalid_type"
    }
    
    response = client.post("/api/feedback", json=feedback_data)
    
    assert response.status_code == 400
    assert "Invalid feedback type" in response.json()["detail"]

def test_invalid_message_id():
    """Test invalid message ID format"""
    feedback_data = {
        "message_id": "invalid-id-format",
        "feedback_type": "thumbs_up"
    }
    
    response = client.post("/api/feedback", json=feedback_data)
    
    assert response.status_code == 400
    assert "Invalid message ID format" in response.json()["detail"]

def test_missing_required_fields():
    """Test missing required fields"""
    # Missing message_id
    response = client.post("/api/feedback", json={"feedback_type": "thumbs_up"})
    assert response.status_code == 422  # Validation error
    
    # Missing feedback_type
    response = client.post("/api/feedback", json={"message_id": "123e4567-e89b-12d3-a456-426614174000"})
    assert response.status_code == 422  # Validation error

if __name__ == "__main__":
    pytest.main([__file__, "-v"])