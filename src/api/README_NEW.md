# C# AI Buddy API

A FastAPI-based backend service that provides AI assistance for C# and .NET development using the OpenAI Agents SDK and vector search capabilities.

## Features

- **Streaming Responses**: Real-time streaming chat responses using OpenAI Agents SDK
- **Knowledge Base Search**: Vector search through Microsoft Learn documentation using MongoDB
- **C# Expertise**: Specialized in C#/.NET AI/ML development guidance
- **Tool Integration**: Leverages function tools for enhanced capabilities

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here
MONGODB_URI=mongodb://your_mongodb_connection_string_here
DATABASE_NAME=your_database_name_here

# Optional
PORT=8000
ENVIRONMENT=development
```

### 3. MongoDB Setup

Your MongoDB database should have:
- A collection named `documents`
- A vector search index named `vector_index` on the `embeddings` field
- Documents with the following structure:
  ```json
  {
    "documentId": "unique_id",
    "title": "Document Title",
    "markdownContent": "Document content...",
    "embeddings": [0.1, 0.2, ...] // Vector embeddings
  }
  ```

### 4. Run the Server

```bash
# Development mode with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Health Check
```
GET /health
```

Returns the API health status.

### Chat
```
POST /api/chat
```

Streaming chat endpoint that accepts:

```json
{
  "message": "How do I use ML.NET for image classification?",
  "history": [
    {
      "role": "user",
      "content": "Previous message"
    },
    {
      "role": "assistant", 
      "content": "Previous response"
    }
  ]
}
```

Returns streaming JSON-L responses:

```json
{"type": "content", "content": "Response text chunk"}
{"type": "tool_call", "content": "Using tool: search_knowledge_base"}
{"type": "complete", "timestamp": "2025-01-26T..."}
```

### Documentation
- Interactive API docs: `/docs`
- ReDoc documentation: `/redoc`

## Testing

Run the test script to verify functionality:

```bash
python test_streaming.py
```

This will test both the health endpoint and streaming chat functionality.

## Agent Architecture

The API uses the OpenAI Agents SDK with:

- **Agent Name**: C# AI Buddy
- **Tools**: `search_knowledge_base` for vector search
- **Instructions**: Specialized for C#/.NET AI/ML development
- **Streaming**: Real-time response streaming using raw response events

## Streaming Implementation

The streaming functionality uses:

1. `Runner.run_streamed()` for agent execution
2. `raw_response_event` handling for token-by-token streaming
3. `run_item_stream_event` for tool call notifications
4. JSON-L format for client consumption

## Error Handling

- Configuration validation on startup
- Graceful error responses in streaming format
- Comprehensive logging to `ai_buddy_api.log`
- Environment variable validation

## Production Deployment

For production deployment:

1. Set `ENVIRONMENT=production`
2. Configure proper CORS origins
3. Use a production WSGI server
4. Set up proper logging and monitoring
5. Secure your MongoDB connection
6. Use environment variables for all secrets

## Dependencies

- **FastAPI**: Web framework
- **OpenAI Agents SDK**: AI agent functionality
- **OpenAI Python SDK**: Embeddings and LLM access
- **PyMongo**: MongoDB connectivity
- **python-dotenv**: Environment variable management
- **uvicorn**: ASGI server
