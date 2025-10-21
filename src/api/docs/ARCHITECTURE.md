# C# AI Buddy API - Architecture

## Overview

The C# AI Buddy API is a FastAPI-based backend service that provides AI-powered assistance for C# and .NET development. The system uses the OpenAI Agents SDK to deliver intelligent, context-aware responses with real-time streaming, integrated with MongoDB for vector search capabilities and Arize for observability and feedback tracking.

## Core Architecture

### Technology Stack

- **Web Framework**: FastAPI (async Python framework)
- **AI Engine**: OpenAI Agents SDK with custom tools
- **LLM Provider**: OpenAI GPT-4 models
- **Vector Database**: MongoDB with vector search
- **Observability**: OpenTelemetry + Arize Phoenix
- **HTTP Client**: aiohttp for async requests
- **Data Validation**: Pydantic models

### High-Level Architecture

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │ HTTP/HTTPS
       │ JSON-L Streaming
       │
┌──────▼──────────────────────────────────────────────┐
│              FastAPI Application                     │
│  ┌────────────────────────────────────────────────┐ │
│  │  CORS Middleware                               │ │
│  │  OpenTelemetry Instrumentation                 │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Chat Router │  │News Router  │  │Samples      │ │
│  │             │  │             │  │Router       │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                 │         │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐ │
│  │ Feedback    │  │ Telemetry   │  │             │ │
│  │ Router      │  │ Router      │  │             │ │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘ │
└─────────┼─────────────────┼──────────────────────────┘
          │                 │
          │                 │
    ┌─────▼─────┐     ┌─────▼─────┐
    │  OpenAI   │     │  MongoDB  │
    │  Agents   │     │  Database │
    │    SDK    │     │           │
    └─────┬─────┘     └─────┬─────┘
          │                 │
    ┌─────▼─────┐     ┌─────▼─────┐
    │  OpenAI   │     │  Vector   │
    │    API    │     │  Search   │
    │           │     │  Index    │
    └───────────┘     └───────────┘
          │
    ┌─────▼─────┐
    │   Arize   │
    │  Phoenix  │
    │(Observ.)  │
    └───────────┘
```

## Core Components

### 1. Main Application (`main.py`)

Entry point and application configuration.

**Responsibilities:**
- FastAPI application initialization
- CORS middleware configuration
- Router registration
- Health check endpoint
- OpenTelemetry instrumentation (commented out in current version)

**Key Configuration:**
```python
app = FastAPI(
    title="C# AI Buddy API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
```

**Environment Variables:**
- `PORT`: Server port (default: 8000)
- `ENVIRONMENT`: development/production (affects authentication)

### 2. Chat Router (`routers/chat.py`)

Core conversational AI functionality using OpenAI Agents SDK.

**Key Features:**
- Streaming responses using JSON-L format
- Magic key authentication (disabled in development)
- AI agent with custom tools
- Vector search integration
- OpenTelemetry span tracking
- Real-time tool call notifications

**AI Agent Configuration:**

```python
agent = Agent(
    name="C# AI Buddy",
    instructions="...",  # Detailed C#/.NET expertise instructions
    tools=[
        search_knowledge_base,  # Vector search
        WebSearchTool()         # Web search fallback
    ],
    mcp_servers=[docsserver]    # Microsoft Learn MCP integration
)
```

**Streaming Architecture:**

1. Client sends `POST /api/chat` with message and history
2. Server generates embedding for user query
3. Vector search retrieves relevant documentation
4. Agent processes request with tools
5. Responses stream in real-time as JSON-L:
   ```json
   {"type": "metadata", "span_id": "...", "timestamp": "..."}
   {"type": "content", "content": "Response chunk..."}
   {"type": "tool_call", "content": "Tool called"}
   {"type": "complete", "span_id": "...", "timestamp": "..."}
   ```

**Functions:**

- `validate_magic_key(magic_key)`: Validates user access keys against MongoDB
- `generate_embedding(text)`: Creates vector embeddings using OpenAI
- `search_knowledge_base(query, filters)`: Vector search with optional filtering
- `get_agent(mcp_servers, filters)`: Creates configured AI agent
- `generate_streaming_response(message, history, filters)`: Main streaming handler

**AI Filters:**

Optional filters to customize responses:
```python
class AIFilters(BaseModel):
    dotnetVersion: Optional[str]  # e.g., ".NET 9"
    aiLibrary: Optional[str]      # e.g., "Semantic Kernel"
    aiProvider: Optional[str]     # e.g., "OpenAI"
```

### 3. News Router (`routers/news.py`)

Serves .NET AI news and articles from RSS feeds.

**Endpoints:**

- `GET /api/news`: Paginated news list with search
  - Query params: `page`, `page_size`, `search`
  - Returns: NewsResponse with items, pagination metadata
  
- `GET /api/news/rss`: RSS feed output
  - Generates XML RSS feed of latest 50 items

**Features:**
- Automatic source detection from RSS feed URLs
- AI-generated summaries (300 chars)
- Date parsing and formatting
- Search across title, content, author

**Data Source:**
- MongoDB `documents` collection
- Filters for RSS items with proper metadata
- Sorted by published date (newest first)

### 4. Samples Router (`routers/samples.py`)

Code samples gallery with filtering and search.

**Endpoints:**

- `GET /api/samples`: Paginated samples with filtering
  - Query params: `page`, `page_size`, `search`, `tags`
  - Returns: SamplesResponse with samples, pagination metadata
  
- `GET /api/samples/tags`: Available tags list
  - Returns: Sorted list of all unique tags
  
- `GET /api/samples/{sample_id}`: Single sample details
  - Returns: Sample object

**Features:**
- Tag-based filtering (comma-separated)
- Full-text search across multiple fields
- Pagination support

**Data Model:**
```python
class Sample(BaseModel):
    id: str
    title: str
    description: str
    preview: Optional[str]
    authorUrl: str
    author: str
    source: str
    tags: List[str]
```

### 5. Feedback Router (`routers/feedback.py`)

User feedback collection with Arize integration.

**Endpoint:**

- `POST /api/feedback`: Submit feedback for AI response
  - Body: FeedbackRequest (span_id, feedback_type, comment)
  - Returns: FeedbackResponse (success, message)

**Feedback Flow:**

1. User provides thumbs up/down with optional comment
2. Feedback validated (span_id, type)
3. Convert to Arize annotation format:
   - Score: 1.0 (thumbs up) or 0.0 (thumbs down)
   - Label: "👍" or "👎"
4. Send to Arize using pandas DataFrame
5. Return success/failure to client

**Arize Integration:**

```python
annotation_data = {
    'context.span_id': [span_id],
    'annotation.rating.score': [score],
    'annotation.rating.label': [label],
    'annotation.rating.updated_by': ['Website user'],
    'annotation.notes': [comment or '']
}
annotations_df = pd.DataFrame(annotation_data)
arize_client.log_annotations(dataframe=annotations_df, ...)
```

### 6. Telemetry Router (`routers/telemetry.py`)

Event tracking for analytics and observability.

**Endpoint:**

- `POST /api/telemetry`: Record telemetry events
  - Body: TelemetryEvent (event_type, data, user_consent)

**Event Types:**
- `filter_used`: User applies filters
- `sample_viewed`: User views a code sample
- `external_click`: User clicks external link
- `search_no_results`: Search returns no results

**Processing:**
- Checks user consent before processing
- Logs events with structured metadata
- Records as OpenTelemetry span attributes
- Non-blocking (errors don't fail request)

### 7. NuGet Search Service (`nuget_search.py`)

Search and retrieve NuGet package information.

**Features:**
- Search NuGet.org packages
- Prioritize official/verified packages
- Retrieve package metadata
- Get package documentation/README
- Extract license information
- Async HTTP client with connection pooling

**Key Functions:**

- `search_nuget_packages(query, take, skip, prerelease)`: Search packages
- `get_nuget_package_details(package_id, version)`: Get package metadata
- `get_package_readme(package_id, version)`: Get documentation
- `get_package_license(package_id, version)`: Get license info

**API Integration:**
- Primary: `https://azuresearch-usnc.nuget.org/query`
- Secondary: `https://azuresearch-ussc.nuget.org/query` (fallback)
- Content: `https://api.nuget.org/v3-flatcontainer/`

### 8. Data Models (`models.py`)

Pydantic models for request/response validation.

**Core Models:**

```python
class Message(BaseModel):
    role: str
    content: str

class AIFilters(BaseModel):
    dotnetVersion: Optional[str]
    aiLibrary: Optional[str]
    aiProvider: Optional[str]

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []
    filters: Optional[AIFilters] = None
    magic_key: Optional[str] = None

class NewsItem(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    author: Optional[str]
    published_date: datetime
    url: str

class Sample(BaseModel):
    id: str
    title: str
    description: str
    preview: Optional[str]
    authorUrl: str
    author: str
    source: str
    tags: List[str]

class FeedbackRequest(BaseModel):
    span_id: str
    feedback_type: str  # 'thumbs_up' or 'thumbs_down'
    comment: Optional[str]

class TelemetryEvent(BaseModel):
    event_type: str
    data: Dict[str, Any]
    timestamp: Optional[str]
    user_consent: bool = True
```

## MongoDB Integration

### Collections

**document_chunks**: Vector search for documentation
```javascript
{
  _id: ObjectId(...),
  title: "Document Title",
  content: "Markdown content...",
  embeddings: [0.123, ...],  // 1536-dim vector (text-embedding-3-small)
  sourceUrl: "https://...",
  tags: ["Semantic Kernel", "OpenAI"],
  // ... additional metadata
}
```

**documents**: RSS news items and articles
```javascript
{
  documentId: "doc_20241020_123456",
  title: "Article Title",
  summary: "AI-generated summary...",
  content: "Full content...",
  sourceUrl: "https://...",
  publishedDate: ISODate("2024-10-20T..."),
  rss_feed_url: "https://...",
  rss_author: "Author Name",
  indexedDate: ISODate("2024-10-20T...")
}
```

**samples**: Code samples gallery
```javascript
{
  id: "sample_123",
  title: "Sample Title",
  description: "Sample description",
  preview: "Preview image URL",
  authorUrl: "https://...",
  author: "Author Name",
  source: "GitHub URL",
  tags: ["Semantic Kernel", "ML.NET"]
}
```

**userRegistrations**: Magic key authentication
```javascript
{
  _id: "user_magic_key_string",
  is_enabled: true,
  // ... additional user info
}
```

### Vector Search

**Index Configuration:**
- Index name: `vector_index`
- Field: `embeddings`
- Dimensions: 1536
- Similarity: cosine

**Search Pipeline:**
```python
pipeline = [
    {
        "$vectorSearch": {
            "index": "vector_index",
            "path": "embeddings",
            "queryVector": query_embedding,
            "numCandidates": 150,
            "limit": 5
        }
    },
    {
        "$project": {
            "source_url": 1,
            "title": 1,
            "content": 1,
            "score": {"$meta": "vectorSearchScore"}
        }
    }
]
```

## OpenTelemetry & Observability

### Tracing Architecture

**Instrumentation:**
- OpenTelemetry OTLP exporter
- Arize Phoenix backend
- FastAPI auto-instrumentation (commented out)
- OpenAI Agents instrumentation
- Custom span creation in routers

**Span Hierarchy:**
```
agent-call (root span)
├─ search_knowledge_base (tool)
│  ├─ generate_embedding
│  └─ mongodb_query
├─ llm_call (agent)
└─ response_streaming
```

**Key Attributes:**
- `event_type`: Telemetry event type
- `search_query`: User search terms
- `page`, `page_size`: Pagination params
- `total_results`, `returned_results`: Result counts
- Custom event data as span attributes

**Arize Configuration:**
```python
tracer_provider = register(
    space_id=os.getenv("ARIZE_SPACE_ID"),
    api_key=os.getenv("ARIZE_API_KEY"),
    project_name=os.getenv("ARIZE_PROJECT_NAME")
)
```

## Authentication & Security

### Magic Key System

**Purpose**: Early access control for beta users

**Flow:**
1. Client includes `magic_key` in ChatRequest
2. Server queries `userRegistrations` collection
3. Validates key exists and `is_enabled: true`
4. Allows/denies request based on validation

**Development Mode:**
- `ENVIRONMENT=development`: Skip validation
- `ENVIRONMENT=production`: Enforce validation

**Security Considerations:**
- Keys stored as document IDs in MongoDB
- Enable/disable via `is_enabled` flag
- No key expiration (manual management)
- Plain text keys (suitable for beta access control)

### CORS Configuration

```python
allow_origins=["*"]  # In production, specify exact origins
allow_credentials=True
allow_methods=["GET", "POST", "PUT", "DELETE"]
allow_headers=["*"]
```

## Streaming Architecture

### JSON-L Format

**Why JSON-L (JSON Lines)?**
- Each line is a complete JSON object
- Easy to parse incrementally
- Standard for streaming APIs

**Message Types:**

1. **Metadata**: Initial span tracking info
   ```json
   {"type": "metadata", "span_id": "abc123", "timestamp": "..."}
   ```

2. **Content**: LLM response chunks
   ```json
   {"type": "content", "content": "Response text..."}
   ```

3. **Tool Call**: Tool execution notification
   ```json
   {"type": "tool_call", "content": "Tool called"}
   ```

4. **Tool Output**: Tool results (optional)
   ```json
   {"type": "tool output", "content": "..."}
   ```

5. **Complete**: End of stream
   ```json
   {"type": "complete", "span_id": "abc123", "timestamp": "..."}
   ```

6. **Error**: Error occurred
   ```json
   {"type": "error", "content": "Error message", "timestamp": "..."}
   ```

### Streaming Implementation

```python
@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        generate_streaming_response(...),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

**Event Processing:**

1. `raw_response_event` + `ResponseTextDeltaEvent`: Stream LLM tokens
2. `run_item_stream_event` + `message_output_item`: Message completed
3. `run_item_stream_event` + `tool_call_item`: Tool invoked
4. `run_item_stream_event` + `tool_call_output_item`: Tool completed

## AI Agent Design

### Agent Instructions

**Core Identity:**
- C#/.NET development expert
- AI/ML specialization
- Microsoft documentation priority
- Practical, working code examples

**Tool Usage Strategy:**
1. Always search Microsoft Learn documentation first
2. Search knowledge base for relevant content
3. Use web search for up-to-date information
4. Create and test code in sandbox (if available)

**Code Generation Guidelines:**
- Use latest C# syntax
- Top-level statements for console apps
- Minimal examples (avoid unnecessary complexity)
- Proper error handling
- Security best practices

**Response Format:**
- Succinct and clear
- Cite sources: `[Document Title](URL)`
- Code blocks with language tags
- Avoid cloud provider requirements unless asked

### Tools Available

**Built-in Tools:**
1. `search_knowledge_base`: Vector search MongoDB
2. `WebSearchTool`: Fallback web search

**MCP Server Tools:**
- Microsoft Learn documentation search (via MCP)

**Sandbox Tools (mentioned in instructions, not implemented):**
- `execute_dotnet_command`
- `create_csharp_file`
- `read_sandbox_file`
- `list_sandbox_directory`

### Context-Aware Responses

When filters provided, agent instructions enhanced with:
```python
filter_context = f"""
**AIFilters (JSON):**
{filter_json}
Please use these filter values to tailor your responses.
"""
```

Agent adjusts recommendations based on:
- .NET version (e.g., .NET 9 features)
- AI library (e.g., Semantic Kernel specific)
- AI provider (e.g., OpenAI, Azure OpenAI)

## Error Handling

### Strategy

**Levels:**
1. **Validation**: Pydantic models validate requests
2. **Authentication**: Magic key validation with clear errors
3. **Database**: MongoDB connection errors with retry
4. **AI Agent**: Tool failures logged, don't break stream
5. **Streaming**: Errors sent as JSON-L error messages

**Error Response Format:**
```python
raise HTTPException(
    status_code=400/401/403/404/500,
    detail="Human-readable error message"
)
```

**Streaming Errors:**
```json
{"type": "error", "content": "Error message", "timestamp": "..."}
```

### Logging

**Configuration:**
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

**Log Levels:**
- `DEBUG`: Detailed debugging information
- `INFO`: General operational events
- `WARNING`: Non-critical issues (e.g., Arize unavailable)
- `ERROR`: Serious issues with exceptions

## Testing

### Test Structure

**Unit Tests** (`tests/`):
- `test_auth.py`: Magic key validation
- `test_feedback_unit.py`: Feedback logic
- `test_feedback.py`: Feedback integration
- `test_nuget_search.py`: NuGet API
- `test_streaming.py`: Streaming responses

**E2E Tests** (`e2eTests/`):
- `test_news_e2e.py`: News endpoint flow

**Evaluation Framework** (`evals/`):
- `prompt_evaluator.py`: LLM response evaluation
- `run_evaluations.py`: Test runner
- `test_cases/`: JSON test cases
  - `categorization_tests.json`
  - `csharp_ai_buddy_tests.json`

### Running Tests

```bash
# Unit tests
pytest tests/ -v

# E2E tests
cd e2eTests
pytest test_news_e2e.py -v

# Evaluations
cd evals
python run_evaluations.py
```

## Deployment

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your values

# Run server
python main.py
# or
uvicorn main:app --reload --port 8000
```

### Production Deployment

**Environment Variables:**
```env
# Required
OPENAI_API_KEY=sk-...
MONGODB_URI=mongodb+srv://...
DATABASE_NAME=csharpAIBuddy

# Observability
ARIZE_SPACE_ID=...
ARIZE_API_KEY=...
ARIZE_PROJECT_NAME=csharp-ai-buddy

# Optional
PORT=8000
ENVIRONMENT=production
```

**Recommendations:**
1. Use HTTPS
2. Configure specific CORS origins
3. Set up proper logging (e.g., CloudWatch, Datadog)
4. Enable OpenTelemetry instrumentation
5. Use connection pooling for MongoDB
6. Monitor memory usage (streaming can be intensive)
7. Set up health check monitoring
8. Use process manager (gunicorn, supervisor)

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Render Deployment

Uses `render.yaml` configuration:
```yaml
services:
  - type: web
    name: csharp-ai-buddy-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PORT
        value: 8000
```

## Performance Considerations

### Async Design

- FastAPI fully async
- `aiohttp` for external requests
- Non-blocking MongoDB queries
- Streaming reduces memory usage

### Optimization Strategies

1. **Vector Search**: Limit `numCandidates` and `limit`
2. **Pagination**: Always use page size limits
3. **Connection Pooling**: Reuse MongoDB/HTTP connections
4. **Caching**: Consider Redis for frequent queries
5. **Batch Operations**: Group MongoDB queries when possible

### Scalability

**Horizontal Scaling:**
- Stateless design (no server-side sessions)
- MongoDB handles concurrent connections
- Each instance independent

**Resource Usage:**
- Memory: ~200-500MB per instance
- CPU: Peaks during LLM streaming
- Network: High during streaming responses

## Future Enhancements

### Planned Features

1. **User Management**: Full user accounts with profiles
2. **Conversation History**: Persistent chat history
3. **Code Sandbox**: Execute C# code in isolated environment
4. **Rate Limiting**: Per-user/key rate limits
5. **Caching Layer**: Redis for frequent queries
6. **Analytics Dashboard**: Usage statistics and insights
7. **A/B Testing**: Experiment with different prompts
8. **Multi-Model Support**: Switch between different LLMs

### Known Limitations

1. **No Conversation Persistence**: History sent with each request
2. **Simple Authentication**: Magic key system is basic
3. **No Rate Limiting**: Can be abused
4. **Synchronous Vector Search**: Could benefit from async
5. **No Caching**: Every query hits MongoDB
6. **Single LLM**: Only OpenAI GPT-4

## API Documentation

### Interactive Docs

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Health Check

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

## Monitoring & Observability

### Metrics to Track

1. **API Metrics**:
   - Request rate (req/sec)
   - Response time (p50, p95, p99)
   - Error rate
   - Streaming duration

2. **AI Metrics**:
   - Tool usage frequency
   - Average tokens per response
   - LLM latency
   - Vector search relevance scores

3. **User Metrics**:
   - Feedback ratio (thumbs up/down)
   - Magic key validation success rate
   - Most common queries
   - Peak usage times

### Arize Dashboard

Track:
- Prompt templates
- Model performance
- User feedback trends
- Trace analysis
- Cost per request

### Alerts

Recommended alerts:
- High error rate (>5%)
- Slow responses (p95 >10s)
- MongoDB connection failures
- OpenAI API errors
- Low feedback scores

## Security Best Practices

1. **Environment Variables**: Never commit secrets
2. **CORS**: Restrict origins in production
3. **Input Validation**: Pydantic models validate all input
4. **Rate Limiting**: Implement per-key limits
5. **SQL Injection**: N/A (MongoDB + Pydantic)
6. **XSS**: Frontend responsibility
7. **HTTPS**: Required in production
8. **Secrets Rotation**: Regularly rotate API keys

## Troubleshooting

### Common Issues

**MongoDB Connection Failed:**
```
Fix: Check MONGODB_URI and network access
Verify: MongoDB Atlas IP whitelist includes server IP
```

**OpenAI API Errors:**
```
Fix: Verify OPENAI_API_KEY is valid
Check: API quota and billing status
```

**Streaming Stops Prematurely:**
```
Fix: Check nginx buffering (X-Accel-Buffering: no)
Verify: Client properly handles JSON-L format
```

**High Memory Usage:**
```
Fix: Reduce streaming buffer size
Check: MongoDB connection not leaking
```

**Arize Not Recording:**
```
Fix: Verify ARIZE_SPACE_ID and ARIZE_API_KEY
Check: Logs for Arize SDK errors
```
