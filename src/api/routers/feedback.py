"""
Feedback API router for handling user feedback on AI responses.
Integrates with Arize Phoenix for feedback tracking and annotation.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import logging
from datetime import datetime

from models import FeedbackRequest, FeedbackResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Import Arize Phoenix Client API
try:
    from phoenix.client import Client
    
    # Initialize Phoenix client
    phoenix_client = Client()
    ARIZE_AVAILABLE = True
except ImportError:
    ARIZE_AVAILABLE = False
    logger.warning("Arize Phoenix not available - feedback will be logged only")


async def send_feedback_to_arize(span_id: str, feedback_type: str, comment: str = None) -> bool:
    """
    Send feedback to Arize Phoenix for tracking and annotation.
    
    Args:
        span_id (str): The span ID from Arize Phoenix telemetry
        feedback_type (str): 'thumbs_up' or 'thumbs_down'
        comment (str, optional): Optional user comment
        
    Returns:
        bool: True if feedback was successfully sent
    """
    try:
        if not ARIZE_AVAILABLE:
            logger.info(f"Arize not available - logging feedback: {span_id}, {feedback_type}, {comment}")
            return True
            
        # Convert feedback type to score for Arize
        score = 1 if feedback_type == "thumbs_up" else 0
        
        # Use Phoenix Client to add span annotation
        annotation = phoenix_client.annotations.add_span_annotation(
            annotation_name="user feedback",
            annotator_kind="HUMAN",
            span_id=span_id,
            score=score,
            notes=comment or ""
        )
        
        # Log successful feedback submission
        logger.info(f"Feedback submitted to Arize: span_id={span_id}, type={feedback_type}, score={score}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send feedback to Arize: {str(e)}", exc_info=True)
        return False


@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit user feedback for an AI response.
    
    Args:
        request (FeedbackRequest): Contains span_id, feedback_type, and optional comment
        
    Returns:
        FeedbackResponse: Success status and message
    """
    try:
        # Validate feedback type
        if request.feedback_type not in ["thumbs_up", "thumbs_down"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid feedback type. Must be 'thumbs_up' or 'thumbs_down'"
            )
            
        # Validate span ID (basic format check)
        if not request.span_id or not isinstance(request.span_id, str):
            raise HTTPException(
                status_code=400,
                detail="Invalid span ID format"
            )
            
        logger.info(
            f"Received feedback: span_id={request.span_id}, "
            f"type={request.feedback_type}, comment={'present' if request.comment else 'none'}"
        )
        
        # Send feedback to Arize Phoenix
        success = await send_feedback_to_arize(
            request.span_id, 
            request.feedback_type, 
            request.comment
        )
        
        if success:
            return FeedbackResponse(
                success=True,
                message="Feedback submitted successfully"
            )
        else:
            return FeedbackResponse(
                success=False,
                message="Feedback logged but may not have reached all systems"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in feedback endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")