from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, AsyncGenerator, Optional
import os
import logging
from datetime import datetime
import json

from pymongo import MongoClient
from agents import Agent, Runner, function_tool, WebSearchTool
from agents.mcp import MCPServerStreamableHttp
from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent
from arize.otel import register

# Import OpenTelemetry for span tracking
from opentelemetry import trace

from models import ChatRequest, Message, AIFilters
from nuget_search import search_nuget_packages, get_nuget_package_details

router = APIRouter()
logger = logging.getLogger(__name__)

# Setup OTel via our convenience function
tracer_provider = register(
    space_id=os.getenv("ARIZE_SPACE_ID"),
    api_key=os.getenv("ARIZE_API_KEY"),
    project_name=os.getenv("ARIZE_PROJECT_NAME"),
)

from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor

OpenAIAgentsInstrumentor().instrument(tracer_provider=tracer_provider)


async def validate_magic_key(magic_key: str) -> bool:
    """
    Validate the magic key against the userRegistrations collection.

    Each key is stored as a separate document in the userRegistrations collection
    with an is_enabled field to control access.

    Args:
        magic_key (str): The magic key to validate.

    Returns:
        bool: True if the key is valid and enabled, False otherwise.
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
        user_registrations_collection = db["userRegistrations"]

        # Look for the key in userRegistrations collection
        # Each key is stored as a document with the key as _id
        key_doc = user_registrations_collection.find_one({"_id": magic_key})

        if not key_doc:
            logger.info(f"Magic key not found in userRegistrations")
            return False

        # Check if the key is enabled
        is_enabled = key_doc.get(
            "is_enabled", True
        )  # Default to True for backwards compatibility

        if not is_enabled:
            logger.info(f"Magic key found but is disabled")
            return False

        logger.info(f"Magic key validation successful")
        return True

    except Exception as e:
        logger.error(f"Error validating magic key: {str(e)}", exc_info=True)
        return False


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
async def search_knowledge_base(
    user_query: str, filters: Optional[AIFilters] = None
) -> str:
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
            [
                f"{doc.get('title')}\n{doc.get('source_url')}\n{doc.get('content')}"
                for doc in documents
            ]
        )

        logger.info(
            f"Successfully retrieved {len(documents)} documents, total context length: {len(context)} characters"
        )
        return context

    except Exception as e:
        logger.error(f"Error in search_knowledge_base: {str(e)}", exc_info=True)
        return f"Sorry, I encountered an error while searching the knowledge base: {str(e)}"


async def get_agent(
    mcp_servers: List[MCPServerStreamableHttp], filters: Optional[AIFilters] = None
) -> Agent:

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
    base_instructions = """You are an AI assistant specialized in helping developers learn and implement AI solutions using C# and .NET. Your expertise includes:

**Core Responsibilities:**
- Guide developers through AI/ML concepts using .NET frameworks (ML.NET, Semantic Kernel, Azure AI services)
- Translate Python AI examples and tutorials into equivalent C#/.NET code
- Provide practical, working code examples with proper error handling and security best practices
- Explain AI concepts in the context of .NET development patterns and conventions
- Create and test .NET sample code in a sandboxed environment to verify code works

**Available Tools:**
- search_knowledge_base: Search Microsoft documentation and knowledge base

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
11. Do not prioritize Azure related content unless the user asks for it.

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
        tools=[search_knowledge_base, WebSearchTool(search_context_size="medium")],
        mcp_servers=mcp_servers,
    )
    return agent


async def generate_streaming_response(
    message: str, history: List[Message], filters: Optional[AIFilters] = None
) -> AsyncGenerator[str, None]:
    """Generate streaming response using OpenAI agents SDK."""

    try:
        # Generate a tracer to capture span information
        span_id = None

        logger.info(
            f"Generating streaming response for message: {message[:100]}{'...' if len(message) > 100 else ''}"
        )

        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span(
            "agent-call",
            openinference_span_kind="agent",
        ) as span:
            # Try to get the current span context to capture span_id
            current_span = trace.get_current_span()
            print(current_span)
            if current_span and current_span.get_span_context().is_valid:
                span_id = format(current_span.get_span_context().span_id, "016x")
                logger.info(f"Captured initial span_id: {span_id}")
            else:
                # Fallback: generate a temporary span_id for development/testing
                import uuid

                span_id = f"temp-{str(uuid.uuid4())[:8]}"
                logger.info(f"Using fallback span_id: {span_id}")

            # Send the span ID first so frontend can track it
            metadata_response = (
                json.dumps(
                    {
                        "type": "metadata",
                        "span_id": span_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                + "\n"
            )
            yield metadata_response
            async with MCPServerStreamableHttp(
                name="Microsoft Learn Docs MCP Server",
                params={
                    "url": "https://learn.microsoft.com/api/mcp",
                },
            ) as docsserver:
                input = ""
                
                # Get the agent instance with filters
                agent = await get_agent([docsserver], filters)

                # Include history in the input for now, to keep things simple
                if history:
                    input += "<chat-history>:\n"
                    for msg in history:
                        # Validate that the role is only "user" or "assistant", to mitigate injection risks
                        if msg.role not in ["user", "assistant"]:
                            logger.warning(f"Invalid message role detected in history: {msg.role}")
                            raise ValueError("Invalid message role in history")

                        input += f"<message>{msg.role}: {msg.content}</message>\n"
                    input += "</chat-history>\n"
                
                input += f"user: {message}\n"

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
                                    json.dumps(
                                        {"type": "content", "content": event.data.delta}
                                    )
                                    + "\n"
                                )
                                yield json_response

                        elif event.type == "run_item_stream_event":
                            # Handle completed items (messages, tool calls, etc.)
                            if event.item.type == "message_output_item":
                                # Try to capture span_id from the completed message if not already captured
                                if not span_id:
                                    current_span = trace.get_current_span()
                                    if (
                                        current_span
                                        and current_span.get_span_context().is_valid
                                    ):
                                        span_id = format(
                                            current_span.get_span_context().span_id,
                                            "016x",
                                        )
                                        logger.info(
                                            f"Captured span_id from completed message: {span_id}"
                                        )
                            elif event.item.type == "tool_call_item":
                                # Optionally notify about tool usage
                                json_response = (
                                    json.dumps(
                                        {"type": "tool_call", "content": f"Tool called"}
                                    )
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
                        logger.error(
                            f"Error processing stream event: {str(e)}", exc_info=True
                        )
                        # Continue processing other events
                        continue

                # Send completion signal with span ID
                span_id = trace.get_current_span().get_span_context().span_id
                print(f"spanId: {span_id}")
                completion_response = (
                    json.dumps(
                        {
                            "type": "complete",
                            "span_id": span_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
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
                    detail="Magic key required for early access. Please provide a valid magic key.",
                )

            # Check if the magic key is valid
            is_valid_key = await validate_magic_key(request.magic_key)
            if not is_valid_key:
                raise HTTPException(
                    status_code=403,
                    detail="Invalid magic key. Please check your key and try again.",
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
            generate_streaming_response(
                request.message, request.history, request.filters
            ),
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
