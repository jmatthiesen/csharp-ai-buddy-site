from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, AsyncGenerator
import json
import asyncio
import time
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
from pymongo import MongoClient

from agents import Agent, Runner, function_tool, WebSearchTool
from agents.mcp import MCPServerStreamableHttp
from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_buddy_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="C# AI Buddy API",
    description="Backend API for C# AI Buddy chat interface",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
            input=text,
            model="text-embedding-3-small"  # Specify the embedding model
        )
        
        embedding = response.data[0].embedding
        logger.debug(f"Successfully generated embedding with {len(embedding)} dimensions")
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
        logger.info(f"Searching knowledge base for query: '{user_query[:50]}{'...' if len(user_query) > 50 else ''}'")
        
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
                    "path": "embeddings",       # Field containing the embeddings
                    "queryVector": query_embedding,  # The query embedding to compare against
                    "numCandidates": 150,      # Consider 150 candidates (wider search)
                    "limit": 5,                # Return only top 5 matches
                }
            },
            {
                # Project only the fields we need
                "$project": {
                    "_id": 0,                  # Exclude document ID
                    "documentId": 1,
                    "title": 1,
                    "markdownContent": 1,                 # Include the document body
                    "score": {"$meta": "vectorSearchScore"},  # Include the similarity score
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
            score = doc.get('score', 'N/A')
            title = doc.get('title', 'Untitled')
            logger.debug(f"Document {i+1}: '{title}' (score: {score})")

        context = "\n\n".join([f"{doc.get('title')}\n{doc.get('markdownContent')}" for doc in documents])
        
        logger.info(f"Successfully retrieved {len(documents)} documents, total context length: {len(context)} characters")
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
            }
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
""",
        tools=[
            search_knowledge_base,
            WebSearchTool(search_context_size="medium")
        ],
        mcp_servers=mcp_servers
    )
                
    return agent

async def generate_streaming_response(message: str, history: List[Message]) -> AsyncGenerator[str, None]:
    """Generate streaming response using OpenAI agents SDK."""
    
    try:
        logger.info(f"Generating streaming response for message: {message[:100]}{'...' if len(message) > 100 else ''}")
        
        # Get the agent instance
        agent = await get_agent()
        
        # Convert history to a format the agent can understand
        # For now, we'll focus on the current message and let the agent handle context
        
        # Run the agent with streaming
        result = Runner.run_streamed(agent, input=message)
        
        # Stream the response events
        async for event in result.stream_events():
            try:
                if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    # Stream text deltas as they come from the LLM
                    if hasattr(event.data, 'delta') and event.data.delta:
                        json_response = json.dumps({
                            "type": "content",
                            "content": event.data.delta
                        }) + "\n"
                        yield json_response
                        
                elif event.type == "run_item_stream_event":
                    # Handle completed items (messages, tool calls, etc.)
                    if event.item.type == "message_output_item":
                        # This is a completed message - we can extract the full text if needed
                        # But we're already streaming deltas above, so this might be redundant
                        pass
                    elif event.item.type == "tool_call_item":
                        # Optionally notify about tool usage
                        json_response = json.dumps({
                            "type": "tool_call",
                            "content": f"Tool called"
                        }) + "\n"
                        yield json_response
                    elif event.item.type == "tool_call_output_item":
                        # Optionally show tool output
                        json_response = json.dumps({
                            "type": "tool output",
                            "content": f"Tool called {event.item.output}"
                        }) + "\n"
                        yield json_response

            except Exception as e:
                logger.error(f"Error processing stream event: {str(e)}", exc_info=True)
                # Continue processing other events
                continue
        
        # Send completion signal
        completion_response = json.dumps({
            "type": "complete",
            "timestamp": datetime.utcnow().isoformat()
        }) + "\n"
        yield completion_response
        
    except Exception as e:
        logger.error(f"Error in generate_streaming_response: {str(e)}", exc_info=True)
        # Send error response
        error_response = json.dumps({
            "type": "error",
            "content": f"Sorry, I encountered an error while processing your request: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }) + "\n"
        yield error_response

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )

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
        logger.info(f"Received chat request: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")
        
        # Validate that required environment variables are set
        if not os.getenv("MONGODB_URI"):
            logger.error("MONGODB_URI environment variable is not set")
            raise HTTPException(status_code=500, detail="Knowledge base is not configured")
            
        if not os.getenv("DATABASE_NAME"):
            logger.error("DATABASE_NAME environment variable is not set")
            raise HTTPException(status_code=500, detail="Knowledge base is not configured")
        
        return StreamingResponse(
            generate_streaming_response(request.message, request.history),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
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
        "chat": "/api/chat"
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
        log_level="info"
    )