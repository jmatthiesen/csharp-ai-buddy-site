from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, AsyncGenerator, Optional, Callable, TypeVar, Any
import os
import logging
from datetime import datetime
import json
import asyncio
import random
import time
from functools import wraps

from models import ChatRequest, Message, AIFilters
from agents import Agent, Runner, function_tool, WebSearchTool
from agents.mcp import MCPServerStreamableHttp
from openai import OpenAI, RateLimitError
from openai.types.responses import ResponseTextDeltaEvent
from nuget_search import search_nuget_packages, get_nuget_package_details
from pymongo import MongoClient

router = APIRouter()
logger = logging.getLogger(__name__)

def retry_on_rate_limit(max_attempts: int = 5, base_delay: float = 1.0):
    """
    Decorator for retrying OpenAI API calls on rate limit errors.
    
    Args:
        max_attempts (int): Maximum number of retry attempts (default: 5)
        base_delay (float): Base delay in seconds for exponential backoff (default: 1.0)
    
    Returns:
        Decorated function that retries on RateLimitError with exponential backoff
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                        
                except RateLimitError as e:
                    last_exception = e
                    attempt_num = attempt + 1
                    
                    logger.warning(
                        f"Rate limit error on attempt {attempt_num}/{max_attempts} for {func.__name__}: {str(e)}"
                    )
                    
                    if attempt_num >= max_attempts:
                        logger.error(
                            f"Max retry attempts ({max_attempts}) reached for {func.__name__}. "
                            f"Final error: {str(e)}"
                        )
                        break
                    
                    # Calculate exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying {func.__name__} in {delay:.2f} seconds (attempt {attempt_num + 1}/{max_attempts})")
                    
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    # For non-rate-limit exceptions, don't retry
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise
            
            # If we get here, all retries failed due to rate limiting
            raise last_exception
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                        
                except RateLimitError as e:
                    last_exception = e
                    attempt_num = attempt + 1
                    
                    logger.warning(
                        f"Rate limit error on attempt {attempt_num}/{max_attempts} for {func.__name__}: {str(e)}"
                    )
                    
                    if attempt_num >= max_attempts:
                        logger.error(
                            f"Max retry attempts ({max_attempts}) reached for {func.__name__}. "
                            f"Final error: {str(e)}"
                        )
                        break
                    
                    # Calculate exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying {func.__name__} in {delay:.2f} seconds (attempt {attempt_num + 1}/{max_attempts})")
                    
                    time.sleep(delay)
                    
                except Exception as e:
                    # For non-rate-limit exceptions, don't retry
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise
            
            # If we get here, all retries failed due to rate limiting
            raise last_exception
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator

async def validate_magic_key(magic_key: str) -> bool:
    """
    Validate the magic key against the database configuration.
    
    Args:
        magic_key (str): The magic key to validate.
        
    Returns:
        bool: True if the key is valid, False otherwise.
    """
    try:
        # Check environment variables
        mongodb_uri = os.getenv("MONGODB_URI")
        database_name = os.getenv("DATABASE_NAME")
        
        if not mongodb_uri or not database_name:
            logger.error("MongoDB configuration not available for magic key validation")
            return False
            
        # Connect to MongoDB
        mongoClient = MongoClient(mongodb_uri)
        db = mongoClient[database_name]
        config_collection = db["chatFeatures"]
        
        # Look for the magic key configuration
        config_doc = config_collection.find_one({"_id": "magic_key_config"})
        
        if not config_doc:
            logger.warning("Magic key configuration not found in database")
            return False
            
        valid_key = config_doc.get("magic_key")
        is_valid = valid_key is not None and magic_key == valid_key
        
        logger.info(f"Magic key validation result: {is_valid}")
        return is_valid
        
    except Exception as e:
        logger.error(f"Error validating magic key: {str(e)}", exc_info=True)
        return False

@retry_on_rate_limit(max_attempts=5, base_delay=1.0)
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
async def search_knowledge_base(user_query: str, filters: Optional[AIFilters] = None) -> str:
    """
    Retrieve relevant documents for a user query using vector search.

    Args:
        user_query (str): The user's query.
        filters (AIFilters, optional): Filters used to narrow results, with a schema similar to:
            {
            "dotnetVersion": ".NET 9",
            "aiLibrary": "OpenAI",
            "aiProvider": "OpenAI"
            }

    Returns:
        str: The retrieved documents as a string.
    """
    try:
        logger.info(
            f"Searching knowledge base for query: '{user_query[:50]}{'...' if len(user_query) > 50 else ''}'"
        )
        
        # Use filters directly if provided
        if filters:
            logger.info(f"Using filters: {filters}")
        
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
        collection = db["document_chunks"]

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
                    "_id": 0,  # Exclude document ID
                    "source_url": 1,
                    "title": 1,
                    "content": 1,  # Include the document body
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
            [f"{doc.get('title')}\n{doc.get('source_url')}\n{doc.get('content')}" for doc in documents]
        )

        logger.info(
            f"Successfully retrieved {len(documents)} documents, total context length: {len(context)} characters"
        )
        return context

    except Exception as e:
        logger.error(f"Error in search_knowledge_base: {str(e)}", exc_info=True)
        return f"Sorry, I encountered an error while searching the knowledge base: {str(e)}"

async def get_agent(mcp_servers: List[MCPServerStreamableHttp], 
                    filters: Optional[AIFilters] = None) -> Agent:

    # mcp_servers = await build_mcp_servers()
    
    # Build context-aware instructions based on filters
#     base_instructions = """
# You are a C#/.NET development expert with deep knowledge about building AI-based applications using .NET 8 and later. When asked questions about how to build applications using AI, you give up to date guidance about official SDKs and documentation. You prioritize Microsoft documentation and blog posts.

# # Available Tools
# * microsoft_docs_search: Use this when searching microsoft documentation 
# * search_knowledge_base: Search the knowledge base for relevant documents

# # System Instructions
# * Always start searches with Microsoft documentation
# * Always search the knowledge base for relevant documents, prioritizing content from microsoft.com urls
# * When asked about AI topics, you prioritize generative AI topics unless asked specifically about machine learning.
# * Answer questions succinctly and clearly, avoiding unnecessary complexity unless asked for advanced details.
# * Default to start discussions using the Microsoft.Extensions.AI library unless another library is mentioned.
# * When providing code examples, focus on the minimal implementation needed. For example, do not include dependency injection examples unless asked for it.
# * Provide answers that do not require cloud providers (Azure, Amazon Bedrock, Google Cloud, or others) unless specifically asked for it.
# * Cite sources as [Document Title](URL)
# * If you're asked to create a complex application, respond saying that you don't yet support that and recommend using a coding assistant, don't attempt to answer the question.
# """
    base_instructions="""You are an AI assistant specialized in helping developers learn and implement AI solutions using C# and .NET. Your expertise includes:

**Core Responsibilities:**
- Guide developers through AI/ML concepts using .NET frameworks (ML.NET, Semantic Kernel, Azure AI services)
- Translate Python AI examples and tutorials into equivalent C#/.NET code
- Provide practical, working code examples with proper error handling and security best practices
- Explain AI concepts in the context of .NET development patterns and conventions
- Create and test .NET sample code in a sandboxed environment to verify code works

**Available Tools:**
- search_knowledge_base: Search Microsoft documentation and knowledge base
- search_nuget_packages: Search for NuGet packages
- get_nuget_package_details: Get detailed information about NuGet packages
- execute_dotnet_command: Execute .NET CLI commands and bash commands in a sandbox
- create_csharp_file: Create C# source files in the sandbox
- read_sandbox_file: Read files from the sandbox environment
- list_sandbox_directory: List directory contents in the sandbox

**When answering questions:**
1. Always start by searching Microsoft documentation, starting with the learn.microsoft.com/*/dotnet/ai content
2. Always search the knowledge base for relevant documents, prioritizing content from microsoft.com urls
3. If providing code examples, use the sandbox tools to create and test the code
4. For project creation requests, use the sandbox to create actual working projects
5. When showing code examples, you can verify they compile using the sandbox
6. If no relevant documents are found, answer using a web search tool to find up-to-date information
7. Only answer questions based on the context provided by the above instructions
8. Answer succinctly and clearly, avoiding unnecessary complexity unless asked for advanced details
9. Provide links to relevant content using a markdown format like [link text](url)
10. Format code using the latest C# syntax and .NET best practices, show console code using top-level statements

Do not make up answers or provide information outside the context of C# and .NET AI development. If you don't know the answer, say "I don't know" or suggest searching the knowledge base or web for more information.
"""

    # Add filter-specific context if filters are provided
    if filters:
        # Serialize filters to JSON for clear context passing
        filter_json = json.dumps(filters.dict(), indent=2)
        filter_context = (
            "\n\n**AIFilters (JSON):**\n"
            f"{filter_json}\n"
            "Please use these filter values to tailor your responses and code examples accordingly.\n"
        )
        
        base_instructions += filter_context
    
    agent = Agent(
        name="C# AI Buddy",
        instructions=base_instructions,
        tools=[
            search_knowledge_base,
            WebSearchTool(search_context_size="medium")
        ],
        mcp_servers=mcp_servers
    )
    return agent

async def _generate_streaming_response_with_retry(
    message: str,
    history: List[Message],
    filters: Optional[AIFilters] = None,
    max_attempts: int = 5,
    base_delay: float = 1.0
) -> AsyncGenerator[str, None]:
    """Internal function to generate streaming response with retry logic for rate limiting."""
    
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            logger.info(
                f"Generating streaming response for message (attempt {attempt + 1}/{max_attempts}): "
                f"{message[:100]}{'...' if len(message) > 100 else ''}"
            )

            async with MCPServerStreamableHttp(
                name="Microsoft Learn Docs MCP Server",
                params={
                    "url": "https://learn.microsoft.com/api/mcp",
                },
            ) as docsserver:
                # Get the agent instance with filters
                agent = await get_agent([docsserver], filters)

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
                
                # If we reach here, the streaming completed successfully
                return
                
        except RateLimitError as e:
            last_exception = e
            attempt_num = attempt + 1
            
            logger.warning(
                f"Rate limit error on attempt {attempt_num}/{max_attempts} for streaming response: {str(e)}"
            )
            
            if attempt_num >= max_attempts:
                logger.error(
                    f"Max retry attempts ({max_attempts}) reached for streaming response. "
                    f"Final error: {str(e)}"
                )
                break
            
            # Calculate exponential backoff with jitter
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.info(f"Retrying streaming response in {delay:.2f} seconds (attempt {attempt_num + 1}/{max_attempts})")
            
            await asyncio.sleep(delay)
            
        except Exception as e:
            # For non-rate-limit exceptions, don't retry
            logger.error(f"Non-retryable error in streaming response: {str(e)}", exc_info=True)
            error_response = json.dumps({
                "type": "error",
                "message": f"Sorry, I encountered an error while processing your request: {str(e)}",
                "content": f"Sorry, I encountered an error while processing your request: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }) + "\n"
            yield error_response
            return
    
    # If we get here, all retries failed due to rate limiting
    if last_exception:
        logger.error(f"All retry attempts failed for streaming response due to rate limiting: {str(last_exception)}")
        error_response = json.dumps({
            "type": "error",
            "message": f"Sorry, I'm currently experiencing high demand and couldn't process your request after multiple attempts. Please try again in a few minutes. Error: {str(last_exception)}",
            "content": f"Sorry, I'm currently experiencing high demand and couldn't process your request after multiple attempts. Please try again in a few minutes. Error: {str(last_exception)}",
            "timestamp": datetime.utcnow().isoformat()
        }) + "\n"
        yield error_response

async def generate_streaming_response(
    message: str,
    history: List[Message],
    filters: Optional[AIFilters] = None
) -> AsyncGenerator[str, None]:
    """Generate streaming response using OpenAI agents SDK with retry logic for rate limiting."""
    
    async for response_chunk in _generate_streaming_response_with_retry(message, history, filters):
        yield response_chunk

@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that handles streaming responses using OpenAI agents SDK.
    Expects JSON with 'message' and optional 'history' fields.
    Returns streaming JSON-L responses.
    """
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        # Skip magic key validation in development environment
        environment = os.getenv("ENVIRONMENT", "production").lower()
        if environment != "development":
            # Validate magic key only in non-development environments
            if not request.magic_key:
                raise HTTPException(
                    status_code=401, 
                    detail="Magic key required for early access. Please provide a valid magic key."
                )
                
            # Check if the magic key is valid
            is_valid_key = await validate_magic_key(request.magic_key)
            if not is_valid_key:
                raise HTTPException(
                    status_code=403, 
                    detail="Invalid magic key. Please check your key and try again."
                )

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
            generate_streaming_response(request.message, request.history, request.filters),
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
