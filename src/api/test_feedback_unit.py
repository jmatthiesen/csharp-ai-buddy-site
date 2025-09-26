"""
Unit tests for the feedback router functionality.
"""

import pytest
import uuid
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Create a test app with just the feedback router
app = FastAPI()

# Mock the feedback router to avoid dependencies
from routers.feedback import router as feedback_router
app.include_router(feedback_router)

client = TestClient(app)

def test_feedback_models():
    """Test that feedback models work correctly"""
    from models import FeedbackRequest, FeedbackResponse
    
    # Test FeedbackRequest
    request = FeedbackRequest(
        message_id="123e4567-e89b-12d3-a456-426614174000",
        feedback_type="thumbs_up",
        comment="Great response!"
    )
    assert request.message_id == "123e4567-e89b-12d3-a456-426614174000"
    assert request.feedback_type == "thumbs_up"
    assert request.comment == "Great response!"
    
    # Test FeedbackResponse
    response = FeedbackResponse(success=True, message="Feedback submitted successfully")
    assert response.success is True
    assert response.message == "Feedback submitted successfully"

@patch('routers.feedback.send_feedback_to_arize')
async def test_feedback_endpoint_success(mock_arize):
    """Test successful feedback submission"""
    mock_arize.return_value = True
    
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
    
    # Verify Arize function was called
    mock_arize.assert_called_once_with(
        "123e4567-e89b-12d3-a456-426614174000",
        "thumbs_up",
        "Great response!"
    )

@patch('routers.feedback.send_feedback_to_arize')
async def test_feedback_without_comment(mock_arize):
    """Test feedback submission without comment"""
    mock_arize.return_value = True
    
    feedback_data = {
        "message_id": "123e4567-e89b-12d3-a456-426614174001",
        "feedback_type": "thumbs_down"
    }
    
    response = client.post("/api/feedback", json=feedback_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Verify Arize function was called with None comment
    mock_arize.assert_called_once_with(
        "123e4567-e89b-12d3-a456-426614174001",
        "thumbs_down",
        None
    )

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