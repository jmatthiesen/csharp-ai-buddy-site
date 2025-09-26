"""
Feedback API router for handling user feedback on AI responses.
Integrates with Arize Phoenix for feedback tracking and annotation.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import logging
import uuid
from datetime import datetime

from models import FeedbackRequest, FeedbackResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Import Arize Phoenix feedback API
try:
    from arize.otel import register
    from opentelemetry import trace
    from openinference.semconv.trace import SpanKind, TraceAttributes
    
    # Setup tracer for feedback
    tracer = trace.get_tracer(__name__)
    ARIZE_AVAILABLE = True
except ImportError:
    ARIZE_AVAILABLE = False
    logger.warning("Arize Phoenix not available - feedback will be logged only")


async def send_feedback_to_arize(message_id: str, feedback_type: str, comment: str = None) -> bool:
    """
    Send feedback to Arize Phoenix for tracking and annotation.
    
    Args:
        message_id (str): The ID of the message being rated
        feedback_type (str): 'thumbs_up' or 'thumbs_down'
        comment (str, optional): Optional user comment
        
    Returns:
        bool: True if feedback was successfully sent
    """
    try:
        if not ARIZE_AVAILABLE:
            logger.info(f"Arize not available - logging feedback: {message_id}, {feedback_type}, {comment}")
            return True
            
        # Convert feedback type to score for Arize
        score = 1 if feedback_type == "thumbs_up" else 0
        
        with tracer.start_as_current_span(
            "feedback_annotation",
            kind=SpanKind.INTERNAL
        ) as span:
            # Set span attributes for feedback tracking
            span.set_attribute("feedback.message_id", message_id)
            span.set_attribute("feedback.type", feedback_type)
            span.set_attribute("feedback.score", score)
            span.set_attribute("feedback.timestamp", datetime.utcnow().isoformat())
            
            if comment:
                span.set_attribute("feedback.comment", comment)
                
            # Add feedback as annotation
            span.set_attribute(TraceAttributes.FEEDBACK_SCORE, score)
            
            # Log successful feedback submission
            logger.info(f"Feedback submitted to Arize: message_id={message_id}, type={feedback_type}, score={score}")
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to send feedback to Arize: {str(e)}", exc_info=True)
        return False


@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit user feedback for an AI response.
    
    Args:
        request (FeedbackRequest): Contains message_id, feedback_type, and optional comment
        
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
            
        # Validate message ID format (basic UUID check)
        try:
            uuid.UUID(request.message_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid message ID format"
            )
            
        logger.info(
            f"Received feedback: message_id={request.message_id}, "
            f"type={request.feedback_type}, comment={'present' if request.comment else 'none'}"
        )
        
        # Send feedback to Arize Phoenix
        success = await send_feedback_to_arize(
            request.message_id, 
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