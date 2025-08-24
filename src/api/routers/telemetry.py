from fastapi import APIRouter, HTTPException
from opentelemetry import trace
import logging
from datetime import datetime

from models import TelemetryEvent

router = APIRouter()
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

@router.post("/api/telemetry")
async def record_telemetry(event: TelemetryEvent):
    """
    Record telemetry events.
    """
    with tracer.start_as_current_span("record_telemetry") as span:
        try:
            # Only process if user has given consent
            if not event.user_consent:
                return {"message": "Telemetry event ignored due to user preference"}
            
            span.set_attribute("event_type", event.event_type)
            
            # Add timestamp if not provided
            if not event.timestamp:
                event.timestamp = datetime.utcnow().isoformat()
            
            # Log the telemetry event for now (could be sent to a proper analytics service)
            logger.info(f"Telemetry event: {event.event_type}", extra={
                "event_type": event.event_type,
                "event_data": event.data,
                "timestamp": event.timestamp
            })
            
            # Record as OpenTelemetry span attributes for observability
            for key, value in event.data.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(f"event_data.{key}", value)
            
            return {"message": "Telemetry recorded successfully"}
            
        except Exception as e:
            span.record_exception(e)
            logger.error(f"Error in record_telemetry: {str(e)}", exc_info=True)
            # Don't fail the request for telemetry errors
            return {"message": "Telemetry recording failed"}
