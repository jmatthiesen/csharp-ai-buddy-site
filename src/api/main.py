from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, AsyncGenerator, Optional
import json
import asyncio
import time
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
from pymongo import MongoClient
import uuid
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from agents import Agent, Runner, function_tool, WebSearchTool
from agents.mcp import MCPServerStreamableHttp
from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent
from nuget_search import search_nuget_packages, get_nuget_package_details

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
    handlers=[logging.FileHandler("ai_buddy_api.log"), logging.StreamHandler()],
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
FastAPIInstrumentor.instrument_app(app)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Request/Response models
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

# Sample-related models
class Sample(BaseModel):
    id: str
    title: str
    description: str
    preview: Optional[str] = None
    authorUrl: str
    author: str
    source: str
    tags: List[str]

class SamplesResponse(BaseModel):
    samples: List[Sample]
    total: int
    page: int
    pages: int
    page_size: int

class TelemetryEvent(BaseModel):
    event_type: str  # 'filter_used', 'sample_viewed', 'external_click', 'search_no_results'
    data: Dict[str, Any]
    timestamp: Optional[str] = None
    user_consent: bool = True

def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for a piece of text.

    Args:
        text (str): The text to embed.

    Returns:
        List[float]: The embedding of the text.
    """
    try:
        logger.debug(f"Generating embedding for text of length: {len(text)}")
        client = OpenAI()

        response = client.embeddings.create(
            input=text, model="text-embedding-3-small"  # Specify the embedding model
        )

        embedding = response.data[0].embedding
        logger.debug(
            f"Successfully generated embedding with {len(embedding)} dimensions"
        )
        return embedding

    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}", exc_info=True)
        raise


@function_tool
async def search_knowledge_base(user_query: str) -> str:
    """
    Retrieve relevant documents for a user query using vector search.

    Args:
        user_query (str): The user's query.

    Returns:
        str: The retrieved documents as a string.
    """
    try:
        logger.info(
            f"Searching knowledge base for query: '{user_query[:50]}{'...' if len(user_query) > 50 else ''}'"
        )

        # Check environment variables
        mongodb_uri = os.getenv("MONGODB_URI")
        database_name = os.getenv("DATABASE_NAME")

        if not mongodb_uri:
            logger.error("MONGODB_URI environment variable is not set")
            raise ValueError("MongoDB URI is not configured")

        if not database_name:
            logger.error("DATABASE_NAME environment variable is not set")
            raise ValueError("Database name is not configured")

        # Connect to MongoDB
        logger.debug("Connecting to MongoDB")
        mongoClient = MongoClient(mongodb_uri)
        db = mongoClient[database_name]
        collection = db["documents"]

        # Generate embedding for the query
        logger.debug("Generating embedding for user query")
        query_embedding = generate_embedding(user_query)

        # Prepare vector search pipeline
        pipeline = [
            {
                # Use vector search to find similar documents
                "$vectorSearch": {
                    "index": "vector_index",  # Name of the vector index
                    "path": "embeddings",  # Field containing the embeddings
                    "queryVector": query_embedding,  # The query embedding to compare against
                    "numCandidates": 150,  # Consider 150 candidates (wider search)
                    "limit": 5,  # Return only top 5 matches
                }
            },
            {
                # Project only the fields we need
                "$project": {
                    "_id": 0,  # Exclude document ID
                    "documentId": 1,
                    "title": 1,
                    "markdownContent": 1,  # Include the document body
                    "score": {
                        "$meta": "vectorSearchScore"
                    },  # Include the similarity score
                }
            },
        ]

        logger.debug("Executing vector search pipeline")
        results = collection.aggregate(pipeline)

        # Process results
        documents = list(results)
        logger.info(f"Found {len(documents)} relevant documents")

        if not documents:
            logger.warning("No documents found for the query")
            return "No relevant documents found for your query."

        # Log search scores for debugging
        for i, doc in enumerate(documents):
            score = doc.get("score", "N/A")
            title = doc.get("title", "Untitled")
            logger.debug(f"Document {i+1}: '{title}' (score: {score})")

        context = "\n\n".join(
            [f"{doc.get('title')}\n{doc.get('markdownContent')}" for doc in documents]
        )

        logger.info(
            f"Successfully retrieved {len(documents)} documents, total context length: {len(context)} characters"
        )
        return context

    except Exception as e:
        logger.error(f"Error in search_knowledge_base: {str(e)}", exc_info=True)
        return f"Sorry, I encountered an error while searching the knowledge base: {str(e)}"


async def build_mcp_servers() -> List[MCPServerStreamableHttp]:
    servers = [
        MCPServerStreamableHttp(
            name="Microsoft Learn Docs MCP Server",
            params={
                "url": "https://learn.microsoft.com/api/mcp",
            },
        )
    ]
    await asyncio.gather(*(server.connect() for server in servers))
    return servers


async def get_agent() -> Agent:

    mcp_servers = await build_mcp_servers()

    # Create agent with knowledge base search tool
    agent = Agent(
        name="C# AI Buddy",
        instructions="""You are an AI assistant specialized in helping developers learn and implement AI solutions using C# and .NET. Your expertise includes:

**Core Responsibilities:**
- Guide developers through AI/ML concepts using .NET frameworks (ML.NET, Semantic Kernel, Azure AI services)
- Translate Python AI examples and tutorials into equivalent C#/.NET code
- Provide practical, working code examples with proper error handling and security best practices
- Explain AI concepts in the context of .NET development patterns and conventions

**When answering questions:**
1. Prioritize answers from the Microsoft Learn documentation, starting with the learn.microsoft.com/*/dotnet/ai content
2. Search the knowledge base for relevant documents, prioritizing content from microsoft.com urls
3. If no relevant documents are found, answer using a web search tool to find up-to-date information
4. Only answer questions based on the context provided by the above instructions
5. Answer succinctly and clearly, avoiding unnecessary complexity unless asked for advanced details
6. Provide links to relevant content using a markdown format like [link text](url)
7. Format code using the latest C# syntax and .NET best practices.
""",
        tools=[search_knowledge_base, search_nuget_packages, get_nuget_package_details],
        mcp_servers=mcp_servers,
    )

    return agent


async def generate_streaming_response(
    message: str, history: List[Message]
) -> AsyncGenerator[str, None]:
    """Generate streaming response using OpenAI agents SDK."""

    try:
        logger.info(
            f"Generating streaming response for message: {message[:100]}{'...' if len(message) > 100 else ''}"
        )

        # Get the agent instance
        agent = await get_agent()
        
        # Include history in the input for now, to keep things simple
        if history:
            input = "".join([f"{msg.role}: {msg.content}\n" for msg in history]) + f"user: {message}\n"
        else:
            input = f"user: {message}\n"

        # Run the agent with streaming
        result = Runner.run_streamed(agent, input)
        
        # Stream the response events
        async for event in result.stream_events():
            try:
                if event.type == "raw_response_event" and isinstance(
                    event.data, ResponseTextDeltaEvent
                ):
                    # Stream text deltas as they come from the LLM
                    if hasattr(event.data, "delta") and event.data.delta:
                        json_response = (
                            json.dumps({"type": "content", "content": event.data.delta})
                            + "\n"
                        )
                        yield json_response

                elif event.type == "run_item_stream_event":
                    # Handle completed items (messages, tool calls, etc.)
                    if event.item.type == "message_output_item":
                        # This is a completed message - we can extract the full text if needed
                        # But we're already streaming deltas above, so this might be redundant
                        pass
                    elif event.item.type == "tool_call_item":
                        # Optionally notify about tool usage
                        json_response = (
                            json.dumps({"type": "tool_call", "content": f"Tool called"})
                            + "\n"
                        )
                        yield json_response
                    elif event.item.type == "tool_call_output_item":
                        # Optionally show tool output
                        json_response = (
                            json.dumps(
                                {
                                    "type": "tool output",
                                    "content": f"Tool called {event.item.output}",
                                }
                            )
                            + "\n"
                        )
                        yield json_response

            except Exception as e:
                logger.error(f"Error processing stream event: {str(e)}", exc_info=True)
                # Continue processing other events
                continue

        # Send completion signal
        completion_response = (
            json.dumps({"type": "complete", "timestamp": datetime.utcnow().isoformat()})
            + "\n"
        )
        yield completion_response

    except Exception as e:
        logger.error(f"Error in generate_streaming_response: {str(e)}", exc_info=True)
        # Send error response
        error_response = (
            json.dumps(
                {
                    "type": "error",
                    "content": f"Sorry, I encountered an error while processing your request: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            + "\n"
        )
        yield error_response


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy", timestamp=datetime.utcnow().isoformat(), version="1.0.0"
    )

@app.get("/api/samples", response_model=SamplesResponse)
async def get_samples(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of samples per page"),
    search: Optional[str] = Query(None, description="Search query"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags to filter by")
):
    """
    Get samples with pagination, search, and filtering.
    """
    with tracer.start_as_current_span("get_samples") as span:
        try:
            span.set_attribute("page", page)
            span.set_attribute("page_size", page_size)
            if search:
                span.set_attribute("search_query", search)
            if tags:
                span.set_attribute("filter_tags", tags)

            # Connect to MongoDB
            mongodb_uri = os.getenv("MONGODB_URI")
            database_name = os.getenv("DATABASE_NAME")
            
            if not mongodb_uri or not database_name:
                raise HTTPException(status_code=500, detail="Database not configured")
            
            mongoClient = MongoClient(mongodb_uri)
            db = mongoClient[database_name]
            samples_collection = db["samples"]
            
            # Build query
            query = {}
            
            # Add tag filtering
            if tags:
                tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                if tag_list:
                    query["tags"] = {"$in": tag_list}
            
            # Add search functionality (simple text search for now)
            if search:
                search_regex = {"$regex": search, "$options": "i"}
                query["$or"] = [
                    {"title": search_regex},
                    {"description": search_regex},
                    {"author": search_regex},
                    {"tags": search_regex}
                ]
            
            # Count total documents
            total = samples_collection.count_documents(query)
            
            # Calculate pagination
            skip = (page - 1) * page_size
            pages = (total + page_size - 1) // page_size
            
            # Get samples
            cursor = samples_collection.find(query).skip(skip).limit(page_size)
            samples_data = list(cursor)
            
            # Convert MongoDB documents to Sample models
            samples = []
            for doc in samples_data:
                sample = Sample(
                    id=doc.get("id", str(doc.get("_id", ""))),
                    title=doc.get("title", ""),
                    description=doc.get("description", ""),
                    preview=doc.get("preview"),
                    authorUrl=doc.get("authorUrl", ""),
                    author=doc.get("author", ""),
                    source=doc.get("source", ""),
                    tags=doc.get("tags", [])
                )
                samples.append(sample)
            
            span.set_attribute("total_results", total)
            span.set_attribute("returned_results", len(samples))
            
            return SamplesResponse(
                samples=samples,
                total=total,
                page=page,
                pages=pages,
                page_size=page_size
            )
            
        except Exception as e:
            span.record_exception(e)
            logger.error(f"Error in get_samples: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/samples/{sample_id}")
async def get_sample(sample_id: str):
    """
    Get a specific sample by ID.
    """
    with tracer.start_as_current_span("get_sample") as span:
        try:
            span.set_attribute("sample_id", sample_id)
            
            # Connect to MongoDB
            mongodb_uri = os.getenv("MONGODB_URI")
            database_name = os.getenv("DATABASE_NAME")
            
            if not mongodb_uri or not database_name:
                raise HTTPException(status_code=500, detail="Database not configured")
            
            mongoClient = MongoClient(mongodb_uri)
            db = mongoClient[database_name]
            samples_collection = db["samples"]
            
            # Find sample by ID
            sample_doc = samples_collection.find_one({"id": sample_id})
            
            if not sample_doc:
                raise HTTPException(status_code=404, detail="Sample not found")
            
            sample = Sample(
                id=sample_doc.get("id", str(sample_doc.get("_id", ""))),
                title=sample_doc.get("title", ""),
                description=sample_doc.get("description", ""),
                preview=sample_doc.get("preview"),
                authorUrl=sample_doc.get("authorUrl", ""),
                author=sample_doc.get("author", ""),
                source=sample_doc.get("source", ""),
                tags=sample_doc.get("tags", [])
            )
            
            return sample
            
        except HTTPException:
            raise
        except Exception as e:
            span.record_exception(e)
            logger.error(f"Error in get_sample: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/telemetry")
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

@app.get("/api/samples/tags")
async def get_available_tags():
    """
    Get all available tags from samples.
    """
    with tracer.start_as_current_span("get_available_tags"):
        try:
            # Connect to MongoDB
            mongodb_uri = os.getenv("MONGODB_URI")
            database_name = os.getenv("DATABASE_NAME")
            
            if not mongodb_uri or not database_name:
                raise HTTPException(status_code=500, detail="Database not configured")
            
            mongoClient = MongoClient(mongodb_uri)
            db = mongoClient[database_name]
            samples_collection = db["samples"]
            
            # Get all unique tags
            tags = samples_collection.distinct("tags")
            
            return {"tags": sorted(tags)}
            
        except Exception as e:
            logger.error(f"Error in get_available_tags: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that handles streaming responses using OpenAI agents SDK.
    Expects JSON with 'message' and optional 'history' fields.
    Returns streaming JSON-L responses.
    """
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        # Log the request
        logger.info(
            f"Received chat request: {request.message[:100]}{'...' if len(request.message) > 100 else ''}"
        )

        # Validate that required environment variables are set
        if not os.getenv("MONGODB_URI"):
            logger.error("MONGODB_URI environment variable is not set")
            raise HTTPException(
                status_code=500, detail="Knowledge base is not configured"
            )

        if not os.getenv("DATABASE_NAME"):
            logger.error("DATABASE_NAME environment variable is not set")
            raise HTTPException(
                status_code=500, detail="Knowledge base is not configured"
            )

        return StreamingResponse(
            generate_streaming_response(request.message, request.history),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
        reload=False,  # Disable in production
        log_level="info",
    )
