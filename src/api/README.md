# C# AI Buddy API

A FastAPI-based backend service providing AI-powered assistance for C# and .NET development using the OpenAI Agents SDK. The system delivers real-time streaming responses with integrated MongoDB vector search for documentation retrieval, OpenTelemetry tracing for observability, and Arize for feedback tracking. The API supports conversational AI chat, code samples gallery, .NET AI news aggregation, and user feedback collection.

## Features

- **Streaming AI Chat**: Real-time streaming responses using OpenAI Agents SDK with JSON-L format
- **Vector Search**: MongoDB-powered semantic search through .NET AI documentation
- **Knowledge Base Integration**: Access to curated Microsoft Learn documentation and blog posts
- **MCP Integration**: Microsoft Learn Model Context Protocol server for up-to-date documentation
- **Code Samples Gallery**: Searchable repository of .NET AI code examples with tag filtering
- **News Aggregation**: RSS feed-based .NET AI news with automatic summarization
- **NuGet Search**: Search and retrieve NuGet package information and documentation
- **User Feedback System**: Arize-integrated feedback collection for continuous improvement
- **Telemetry & Analytics**: OpenTelemetry instrumentation with Arize Phoenix observability
- **AI Filters**: Context-aware responses based on .NET version, AI library, and provider
- **Magic Key Authentication**: Beta access control system (disabled in development mode)
- **CORS Support**: Configured for frontend integration with customizable origins

## Environment Setup

### Prerequisites
- **[Python 3.11+](https://www.python.org/downloads/)** with pip
- **[MongoDB](https://www.mongodb.com/docs/atlas/getting-started/)** instance with vector search capability (MongoDB Atlas recommended)
- **[OpenAI API Key](https://platform.openai.com/api-keys)** with access to GPT-4 and embeddings models
- **[Arize Account](https://arize.com/get-started/)** (optional, for observability and feedback tracking)

### Installation

1. **Navigate to the API directory:**
   ```bash
   cd src/api
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # Required - OpenAI Configuration
   OPENAI_API_KEY=sk-your-openai-api-key-here
   
   # Required - MongoDB Configuration
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net
   DATABASE_NAME=csharpAIBuddy
   
   # Optional - Arize Observability
   ARIZE_SPACE_ID=your-arize-space-id
   ARIZE_API_KEY=your-arize-api-key
   ARIZE_PROJECT_NAME=csharp-ai-buddy
   
   # Optional - Server Configuration
   PORT=8000
   ENVIRONMENT=development  # or 'production'
   ```

5. **Set up MongoDB vector search index:**
   
   Ensure your MongoDB database has a vector search index named `vector_index` on the `document_chunks` collection:
   ```json
   {
     "type": "vectorSearch",
     "fields": [{
       "type": "vector",
       "path": "embeddings",
       "numDimensions": 1536,
       "similarity": "cosine"
     }]
   }
   ```

### Running the Server

**Development mode with auto-reload:**
```bash
python main.py
```

**Or using uvicorn directly:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Production mode:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health & Information

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/` | GET | API information and available endpoints |
| `/docs` | GET | Interactive Swagger UI documentation |
| `/redoc` | GET | ReDoc API documentation |

**Health Check Example:**
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-10-20T12:34:56.789Z",
  "version": "1.0.0"
}
```

### Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Streaming AI chat responses |

**Request Body:**
```json
{
  "message": "How do I use ML.NET for image classification?",
  "history": [
    {
      "role": "user",
      "content": "What is ML.NET?"
    },
    {
      "role": "assistant",
      "content": "ML.NET is Microsoft's machine learning framework..."
    }
  ],
  "filters": {
    "dotnetVersion": ".NET 9",
    "aiLibrary": "ML.NET",
    "aiProvider": "Local"
  },
  "magic_key": "your-magic-key-here"
}
```

**Response:** Streaming JSON-L (JSON Lines) format
```
{"type": "metadata", "span_id": "abc123...", "timestamp": "2024-10-20T12:34:56.789Z"}
{"type": "content", "content": "To use ML.NET for image classification"}
{"type": "content", "content": ", you'll need to follow these steps:\n\n1. Install"}
{"type": "tool_call", "content": "Tool called"}
{"type": "content", "content": " the ML.NET package..."}
{"type": "complete", "span_id": "abc123...", "timestamp": "2024-10-20T12:35:01.234Z"}
```

**Notes:**
- `magic_key` is optional in development mode (`ENVIRONMENT=development`)
- `history` is optional but recommended for context
- `filters` are optional but help provide context-aware responses
- Responses are streamed in real-time using Server-Sent Events pattern

### News

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/news` | GET | Get paginated .NET AI news items |
| `/api/news/rss` | GET | Get news as RSS/XML feed |

**Query Parameters:**
- `page` (int, default: 1): Page number
- `page_size` (int, default: 20, max: 100): Items per page
- `search` (string, optional): Search query

**Example:**
```bash
curl "http://localhost:8000/api/news?page=1&page_size=10&search=semantic+kernel"
```

**Response:**
```json
{
  "news": [
    {
      "id": "doc_20241020_123456",
      "title": "New Semantic Kernel Features in .NET 9",
      "summary": "Microsoft announces new features...",
      "source": "Microsoft DevBlogs",
      "author": "John Doe",
      "published_date": "2024-10-20",
      "url": "https://devblogs.microsoft.com/..."
    }
  ],
  "total": 150,
  "page": 1,
  "pages": 15,
  "page_size": 10
}
```

### Samples

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/samples` | GET | Get paginated code samples |
| `/api/samples/tags` | GET | Get all available tags |
| `/api/samples/{sample_id}` | GET | Get specific sample by ID |

**Query Parameters:**
- `page` (int, default: 1): Page number
- `page_size` (int, default: 20, max: 100): Items per page
- `search` (string, optional): Search query
- `tags` (string, optional): Comma-separated tags (e.g., "Semantic Kernel,ML.NET")

**Example:**
```bash
curl "http://localhost:8000/api/samples?tags=Semantic+Kernel&page=1&page_size=20"
```

**Response:**
```json
{
  "samples": [
    {
      "id": "sample_123",
      "title": "Getting Started with Semantic Kernel",
      "description": "A simple example showing...",
      "preview": "https://example.com/preview.png",
      "authorUrl": "https://github.com/author",
      "author": "Jane Smith",
      "source": "https://github.com/author/repo",
      "tags": ["Semantic Kernel", "OpenAI"]
    }
  ],
  "total": 45,
  "page": 1,
  "pages": 3,
  "page_size": 20
}
```

### Feedback

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/feedback` | POST | Submit user feedback on AI responses |

**Request Body:**
```json
{
  "span_id": "abc123def456",
  "feedback_type": "thumbs_up",
  "comment": "Very helpful explanation!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Feedback submitted successfully"
}
```

**Notes:**
- `span_id`: Obtained from chat response metadata
- `feedback_type`: Either "thumbs_up" or "thumbs_down"
- `comment`: Optional user comment

### Telemetry

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/telemetry` | POST | Record user interaction events |

**Request Body:**
```json
{
  "event_type": "filter_used",
  "data": {
    "dotnetVersion": ".NET 9",
    "aiLibrary": "Semantic Kernel"
  },
  "user_consent": true
}
```

**Event Types:**
- `filter_used`: User applied filters
- `sample_viewed`: User viewed a code sample
- `external_click`: User clicked external link
- `search_no_results`: Search returned no results

## AI Filters

The chat endpoint supports optional filters to provide context-aware responses:

```typescript
{
  "dotnetVersion": ".NET 9" | ".NET 8" | ".NET 7" | null,
  "aiLibrary": "Semantic Kernel" | "ML.NET" | "AutoGen" | "Microsoft.Extensions.AI" | null,
  "aiProvider": "OpenAI" | "Azure OpenAI" | "Anthropic" | "Google" | null
}
```

These filters help the AI agent tailor code examples and recommendations to your specific technology stack.

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_streaming.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### E2E Tests

```bash
cd e2eTests
pytest test_news_e2e.py -v
```

### Evaluation Framework

```bash
cd evals
python run_evaluations.py
```

Test cases are defined in `evals/test_cases/*.json`

## Deployment

### Docker Deployment

**Build the image:**
```bash
docker build -t csharp-ai-buddy-api .
```

**Run the container:**
```bash
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e MONGODB_URI=your-uri \
  -e DATABASE_NAME=your-db \
  csharp-ai-buddy-api
```

### Render Deployment

The API is configured for Render deployment with `render.yaml`:

1. Connect your GitHub repository to Render
2. Render will automatically detect the configuration
3. Set environment variables in Render dashboard
4. Deploy will trigger on git push

### Production Recommendations

1. **Use HTTPS**: Always use TLS in production
2. **Configure CORS**: Set specific origins instead of `"*"`
3. **Set up Monitoring**: Use Arize Phoenix or similar observability tool
4. **Enable Rate Limiting**: Implement per-key rate limits
5. **Use Connection Pooling**: Configure MongoDB connection pool size
6. **Set Workers**: Use multiple uvicorn workers for scale
7. **Configure Logging**: Use structured logging to external service
8. **Rotate Secrets**: Regularly rotate API keys and database credentials

**Example Production Start Command:**
```bash
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

## Authentication

### Magic Key System

The API uses a simple magic key system for beta access control:

**How it works:**
1. User provides `magic_key` in chat requests
2. API validates key against `userRegistrations` collection in MongoDB
3. Key must exist with `is_enabled: true`
4. Invalid keys receive 403 Forbidden response

**Development Mode:**
- Set `ENVIRONMENT=development` to skip validation
- Useful for local development and testing

**Production Mode:**
- Set `ENVIRONMENT=production` to enforce validation
- All chat requests require valid magic key

**Managing Keys:**
```javascript
// Add a new magic key
db.userRegistrations.insertOne({
  _id: "user_magic_key_abc123",
  is_enabled: true,
  created_at: new Date()
})

// Disable a key
db.userRegistrations.updateOne(
  { _id: "user_magic_key_abc123" },
  { $set: { is_enabled: false } }
)
```

## Architecture

For detailed information about the API architecture, component design, and integration patterns, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Supported AI Frameworks

The system has knowledge about these .NET AI frameworks:

- **Microsoft.Extensions.AI** - Unified AI abstractions for .NET
- **Semantic Kernel** - AI orchestration SDK
- **Semantic Kernel Agents** - Multi-agent orchestration
- **Semantic Kernel Process Framework** - Process-driven AI workflows
- **ML.NET** - Machine learning framework
- **AutoGen** - Multi-agent AI framework
- **Microsoft Agent Framework** - Agent development platform
- **OpenAI SDK** - Official OpenAI .NET SDK
- **Azure AI Services** - Azure cognitive services integration

## Contributing

Contributions are welcome! Please see the architecture documentation for information about the codebase structure and design patterns.

## License

[Your License Here]

## Support

For issues and questions:
- **Documentation**: See `/docs` endpoint for interactive API docs
- **Architecture**: Review `docs/ARCHITECTURE.md` for technical details
- **Health Check**: Monitor `/health` endpoint for service status
- **Logs**: Check application logs for detailed error messages

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for LLM and embeddings |
| `MONGODB_URI` | Yes | - | MongoDB connection string |
| `DATABASE_NAME` | Yes | - | MongoDB database name |
| `ARIZE_SPACE_ID` | No | - | Arize space ID for observability |
| `ARIZE_API_KEY` | No | - | Arize API key |
| `ARIZE_PROJECT_NAME` | No | - | Arize project name |
| `PORT` | No | 8000 | Server port |
| `ENVIRONMENT` | No | production | Environment mode (development/production) |