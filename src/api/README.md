# C# AI Buddy API

FastAPI backend for the C# AI Buddy chat interface.

## Features

- **Streaming Chat API**: Real-time responses using JSON-L format
- **CORS Support**: Frontend integration ready
- **Health Monitoring**: `/health` endpoint for uptime checks
- **Render Ready**: Configured for easy deployment

## API Endpoints

### `POST /api/chat`
Chat endpoint that accepts messages and returns streaming responses.

**Request:**
```json
{
  "message": "How do I create a class in C#?",
  "history": [
    {"role": "user", "content": "Previous message"},
    {"role": "assistant", "content": "Previous response"}
  ]
}
```

**Response:** Streaming JSON-L format
```
{"type": "content", "content": "# Creating Classes in C#\n\nA class in C# is"}
{"type": "content", "content": " a blueprint for creating objects..."}
{"type": "complete", "timestamp": "2024-01-01T12:00:00Z"}
```

### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0"
}
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Deployment to Render

1. Connect your GitHub repository to Render
2. Use the `render.yaml` configuration file
3. Set the root directory to `src/api`
4. The service will automatically deploy and scale

## Environment Variables

- `PORT`: Server port (set automatically by Render)
- `PYTHON_VERSION`: Python runtime version

## C# Knowledge Base

The API includes responses for common C# topics:
- Classes and objects
- Variable types (`var` vs explicit)
- Exception handling
- Async/await patterns
- LINQ queries
- Interfaces
- And more general C# programming concepts