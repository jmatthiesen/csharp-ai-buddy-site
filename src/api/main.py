import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Logging & observability related modules
import logging

# from opentelemetry import trace
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
# from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# App specific modules
from routers import chat, samples, news, telemetry, feedback
from models import HealthResponse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # handlers=[logging.FileHandler("ai_buddy_api.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="C# AI Buddy API",
    description="Backend API for C# AI Buddy chat interface and samples gallery",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Instrument FastAPI with OpenTelemetry
# FastAPIInstrumentor.instrument_app(app)
allow_origins = []
environment = os.getenv("ENVIRONMENT", "production").lower()
if environment not in ("development", "production"):
    logger.warning(f"ENVIRONMENT variable is set to an unexpected value: '{environment}'. Defaulting to production CORS settings.")
    environment = "production"
if environment == "development":
    allow_origins = ["*"]
else:
    allow_origins = ["https://csharpaibuddy.com", "https://www.csharpaibuddy.com"]
logger.info(f"ENVIRONMENT: {environment}")
logger.info(f"CORS allow_origins: {allow_origins}")
# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(samples.router)
app.include_router(news.router)
app.include_router(telemetry.router)
app.include_router(feedback.router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy", timestamp=datetime.utcnow().isoformat(), version="1.0.0"
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
        "telemetry": "/api/telemetry",
        "feedback": "/api/feedback",
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
        log_level="info",
    )
