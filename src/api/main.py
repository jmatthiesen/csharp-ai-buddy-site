from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from routers import chat, samples, news, telemetry
from models import HealthResponse
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter if endpoint is provided
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
if otlp_endpoint:
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    #handlers=[logging.FileHandler("ai_buddy_api.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="C# AI Buddy API",
    description="Backend API for C# AI Buddy chat interface and samples gallery",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(samples.router)
app.include_router(news.router)
app.include_router(telemetry.router)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "C# AI Buddy API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "chat": "/api/chat",
        "samples": "/api/samples",
        "news": "/api/news",
        "news_rss": "/api/news/rss",
        "telemetry": "/api/telemetry"
    }

if __name__ == "__main__":
    import uvicorn

    # Get port from environment variable (Render requirement)
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Disable in production
        log_level="info"
    )