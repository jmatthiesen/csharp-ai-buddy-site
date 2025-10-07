"""
Feedback API router for handling user feedback on AI responses.
Integrates with Arize SDK for human annotations and feedback tracking.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os
import logging
from datetime import datetime
import pandas as pd

from models import FeedbackRequest, FeedbackResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Import Arize SDK for human annotations
try:
    from arize.pandas.logger import Client

    # Initialize Arize client with environment variables
    arize_client = Client(
        space_id=os.getenv("ARIZE_SPACE_ID"), api_key=os.getenv("ARIZE_API_KEY")
    )
    ARIZE_AVAILABLE = True
except ImportError:
    ARIZE_AVAILABLE = False
    logger.warning("Arize SDK not available - feedback will be logged only")
except Exception as e:
    ARIZE_AVAILABLE = False
    logger.warning(
        f"Arize SDK configuration error: {str(e)} - feedback will be logged only"
    )


async def send_feedback_to_arize(
    span_id: str, feedback_type: str, comment: str = None
) -> bool:
    """
    Send feedback to Arize using the Arize SDK for human annotations.

    Args:
        span_id (str): The span ID from Arize telemetry
        feedback_type (str): 'thumbs_up' or 'thumbs_down'
        comment (str, optional): Optional user comment

    Returns:
        bool: True if feedback was successfully sent
    """
    try:
        if not ARIZE_AVAILABLE:
            logger.info(
                f"Arize not available - logging feedback: {span_id}, {feedback_type}, {comment}"
            )
            return True

        # Convert feedback type to score for Arize
        score = 1.0 if feedback_type == "thumbs_up" else 0.0
        label = "👍" if feedback_type == "thumbs_up" else "👎"

        # Create annotation data using Arize SDK format
        annotation_data = {
            "context.span_id": [span_id],
            "annotation.rating.score": [score],
            "annotation.rating.label": [label],
            "annotation.rating.updated_by": ["Website user"],
            "annotation.notes": [comment or ""],
        }
        annotations_df = pd.DataFrame(annotation_data)

        # Send human annotations using Arize SDK
        response = arize_client.log_annotations(
            dataframe=annotations_df,
            project_name=os.getenv("ARIZE_PROJECT_NAME"),
            validate=True,
            verbose=True,
        )

        if response:
            logger.info("\n✅ Successfully logged annotations!")
            logger.info(f"   Annotation Records Updated: {response.records_updated}")
            return True
        else:
            logger.error(
                "\n⚠️ Annotation logging call completed, but no response received (check SDK logs/platform)."
            )
            return False

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
                detail="Invalid feedback type. Must be 'thumbs_up' or 'thumbs_down'",
            )

        # Validate span ID (basic format check)
        if not request.span_id or not isinstance(request.span_id, str):
            raise HTTPException(status_code=400, detail="Invalid span ID format")

        logger.info(
            f"Received feedback: span_id={request.span_id}, "
            f"type={request.feedback_type}, comment={'present' if request.comment else 'none'}"
        )

        # Send feedback to Arize using human annotations
        success = await send_feedback_to_arize(
            request.span_id, request.feedback_type, request.comment
        )

        if success:
            return FeedbackResponse(
                success=True, message="Feedback submitted successfully"
            )
        else:
            return FeedbackResponse(
                success=False,
                message="Feedback logged but may not have reached all systems",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in feedback endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
