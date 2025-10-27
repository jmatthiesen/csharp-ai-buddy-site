# Data Ingestion Pipeline - Architecture

## Overview

The Data Ingestion Pipeline is a modular, stage-based system for processing documents from various sources (web pages, RSS feeds) and storing them in MongoDB with vector embeddings for semantic search. The architecture follows a clear separation of concerns with pluggable components for different content sources and host-specific processing.

## Core Architecture

### Pipeline Flow

```
Raw Document Input → Source Enrichment → Markdown Conversion → Link Extraction → 
Summary Creation → Chunking → Embedding Generation → AI Categorization → Storage
```

### Key Design Principles

1. **Stage-based Processing**: Each stage has a specific responsibility and can fail independently
2. **Pluggable Components**: Source enrichers and host handlers can be added/removed without affecting core pipeline
3. **Error Isolation**: Errors in one stage don't cascade to others; processing stops cleanly at first error
4. **Metadata Accumulation**: Each stage adds metadata to a shared context object
5. **Chunking-first Architecture**: Documents are split into chunks for better retrieval and embedding efficiency

## Core Components

### 1. Document Pipeline (`document_pipeline.py`)

The central orchestrator that manages document processing through all stages.

**Key Responsibilities:**
- Initialize and coordinate all pipeline stages
- Manage MongoDB connections and collections
- Handle OpenAI API interactions for embeddings and AI categorization
- Create and store document chunks with metadata

**Main Collections:**
- `document_chunks`: Stores individual document chunks with embeddings
- `documents`: Stores document summaries and metadata (legacy support)

**Pipeline Stages:**

1. **Source Enrichment**: Apply source-specific metadata and processing
2. **Markdown Conversion**: Convert HTML/other formats to markdown using MarkItDown
3. **Link Extraction**: Extract and classify links for potential crawling
4. **Summary Creation**: Generate AI-powered summaries (300 chars)
5. **Chunking**: Split content into manageable pieces (default 4000 chars)
6. **Embedding Generation**: Create vector embeddings using OpenAI
7. **AI Categorization**: Identify relevant .NET framework tags
8. **Finalization & Storage**: Create chunk objects and store in MongoDB

### 2. Data Types (`pipeline_types.py`)

**RawDocument**: Input to the pipeline
```python
- content: str              # Raw content (HTML, text, markdown)
- source_url: str          # Source URL
- title: Optional[str]     # Document title
- summary: Optional[str]   # Pre-generated summary (optional)
- content_type: str        # "html", "markdown", "text", "rss"
- source_metadata: Dict    # Source-specific metadata
- tags: List[str]          # Initial tags
- created_date: datetime   # Creation timestamp
```

**ProcessingContext**: Mutable state through pipeline
```python
- raw_document: RawDocument        # Source document
- markdown_content: str            # Converted markdown
- chunks: List[str]                # Text chunks
- chunk_embeddings: List[List[float]]  # Vector embeddings
- extracted_links: List[Dict]      # Links found in content
- final_tags: List[str]            # Accumulated tags
- user_metadata: Dict              # User-provided metadata
- processing_metadata: Dict        # Pipeline-generated metadata
- errors: List[str]                # Error tracking
- warnings: List[str]              # Warning tracking
- stages_completed: List[str]      # Processing history
```

**Chunk**: Final storage unit
```python
- chunk_id: str               # Unique identifier
- title: str                  # Document title
- source_url: str            # Source URL
- content: str               # Markdown content
- embeddings: List[float]    # Vector embedding
- tags: List[str]            # Framework tags
- chunk_index: int           # Position in document
- total_chunks: int          # Total chunks in document
- indexed_date: datetime     # Storage timestamp
- created_date: datetime     # Original creation date
- metadata: Dict             # Combined metadata
```

### 3. Source Enrichers (`source_enrichers.py`)

Pluggable components that add source-specific metadata and processing logic.

**Base Class**: `SourceEnricher`
- `can_handle(raw_doc)`: Check if enricher applies
- `enrich(context)`: Add metadata and tags
- `name`: Identifier for logging

**Implemented Enrichers:**

1. **RSSSourceEnricher**: 
   - Handles RSS feed items
   - Adds RSS metadata (feed URL, item ID, author, categories)
   - Converts RSS categories to tags

2. **WordPressSourceEnricher**:
   - Handles WordPress blog content
   - Extracts WordPress-specific metadata
   - Identifies WordPress REST API responses

3. **HTMLSourceEnricher**:
   - Default HTML content handler
   - Extracts meta tags, OpenGraph data
   - Identifies generic HTML documents

4. **PlainTextSourceEnricher**:
   - Handles plain text documents
   - Minimal processing

5. **FallbackSourceEnricher**:
   - Always matches as last resort
   - Provides basic metadata defaults

**Processing Order**: More specific enrichers first, fallback last

### 4. Host Handlers (`host_handlers.py`)

Handle host-specific URL processing and link filtering during crawling.

**Base Class**: `HostHandler`
- `can_handle(url)`: Check if handler applies to URL
- `process_extracted_links(links, source_url)`: Filter/modify links
- `get_url_with_fallback(url)`: Test URL and provide alternatives
- `extract_host_metadata(url, markdown)`: Extract host-specific data

**Implemented Handlers:**

1. **GitHubHostHandler**:
   - Handles github.com URLs
   - Converts HTML URLs to raw content URLs
   - Filters out non-content links (issues, pull requests, etc.)
   - Provides fallback to blob URLs

2. **FallbackHostHandler**:
   - Default handler for all hosts
   - Minimal processing

**Processing Order**: More specific handlers first, fallback last

### 5. Content Retrievers

**WebPageRetriever (`web_page_retriever.py`)**:
- Fetches content from HTTP/HTTPS URLs
- Attempts WordPress REST API discovery
- Falls back to HTML parsing
- Extracts metadata from various sources

**RSSFeedRetriever (`rss_feed_retriever.py`)**:
- Parses RSS/Atom feeds using feedparser
- Extracts feed metadata
- Processes individual feed items

### 6. AI Categorization (`dotnet_sdk_tags.py`)

Intelligent framework tagging using OpenAI.

**Supported Frameworks:**
- Microsoft.Extensions.AI
- ML.NET
- AutoGen
- Semantic Kernel
- Semantic Kernel Agents
- Semantic Kernel Process Framework
- OpenAI SDK
- Azure AI Services
- Microsoft Agent Framework

**Key Features:**
- AI-powered content analysis
- Automatic parent tag inclusion (e.g., "Semantic Kernel Agents" → ["Semantic Kernel Agents", "Semantic Kernel"])
- Validation against known framework list

### 7. Markdown Processing (`utils/chunking.py`)

Smart markdown chunking that preserves document structure.

**Features:**
- Respects markdown headers and sections
- Maintains header hierarchy across chunks
- Enforces strict size limits
- Preserves code blocks and formatting

**Algorithm:**
1. Split by headers (##, ###, etc.)
2. Group sections into chunks respecting size limits
3. Include parent headers for context
4. Handle oversized sections by paragraph splitting

## Data Flow Examples

### Adding a Web Page

```
1. User provides URL via CLI
2. WebPageRetriever fetches content
   - Attempts WordPress API
   - Falls back to HTML parsing
3. Create RawDocument with fetched content
4. Pipeline processes document:
   - HTMLSourceEnricher adds metadata
   - MarkItDown converts to markdown
   - Extract links (filtered by GitHubHostHandler if applicable)
   - Generate AI summary
   - Split into chunks
   - Generate embeddings
   - AI categorizes frameworks
5. Store chunks in MongoDB
6. Return chunk IDs and extracted links
7. Optional: Prompt user to crawl links
```

### RSS Feed Monitoring

```
1. User adds RSS subscription
2. Scheduled job runs daily check
3. For each subscription:
   - Parse RSS feed
   - Check each item against processed_items collection
   - Skip already processed items
4. For new items:
   - RSSFeedRetriever creates RawDocument
   - RSSSourceEnricher adds RSS metadata
   - Pipeline processes (same stages as web page)
   - Mark item as processed
5. Update subscription last_checked timestamp
```

## MongoDB Collections

### document_chunks

Primary collection for chunk-based storage.

**Indexes:**
- `chunk_id`: Unique identifier
- `sourceUrl`: For finding all chunks of a document
- `tags`: For tag-based filtering
- `indexed_date`: For chronological queries

**Schema:**
```javascript
{
  chunk_id: "doc_20241020_123456_0001",
  title: "Document Title",
  sourceUrl: "https://example.com/doc",
  content: "Markdown content...",
  embeddings: [0.123, -0.456, ...],  // 1536-dim vector
  tags: ["Semantic Kernel", "OpenAI SDK"],
  chunk_index: 0,
  total_chunks: 5,
  indexed_date: ISODate("2024-10-20T12:34:56Z"),
  created_date: ISODate("2024-10-15T10:00:00Z"),
  metadata: {
    source_type: "wordpress",
    author: "John Doe",
    // ... additional metadata
  }
}
```

### rss_subscriptions

RSS feed configuration.

**Schema:**
```javascript
{
  _id: ObjectId(...),
  feed_url: "https://example.com/feed",
  name: "Example Blog",
  description: "Blog about .NET AI",
  tags: ["Semantic Kernel"],
  enabled: true,
  last_checked: ISODate("2024-10-20T08:00:00Z"),
  last_item_date: ISODate("2024-10-19T15:30:00Z"),
  created_date: ISODate("2024-10-01T12:00:00Z"),
  updated_date: ISODate("2024-10-20T08:00:00Z")
}
```

### rss_processed_items

Tracks processed RSS items to avoid duplicates.

**Schema:**
```javascript
{
  _id: ObjectId(...),
  feed_url: "https://example.com/feed",
  item_id: "abc123...",  // MD5 hash of feed_url:item_id
  processed_date: ISODate("2024-10-20T08:05:00Z")
}
```

## Configuration (`config.py`)

Environment-based configuration with validation.

**Required Settings:**
- `MONGODB_CONNECTION_STRING`: MongoDB connection string
- `MONGODB_DATABASE`: Database name
- `MONGODB_COLLECTION`: Documents collection (legacy)
- `MONGODB_CHUNKS_COLLECTION`: Chunks collection (default: "document_chunks")
- `OPENAI_API_KEY`: OpenAI API key for embeddings and AI categorization

**Optional Settings:**
- `OPENAI_EMBEDDING_MODEL`: Model for embeddings (default: "text-embedding-3-small")
- `MAX_CONTENT_LENGTH`: Maximum content length (default: 8192)
- `BATCH_SIZE`: Batch size for operations (default: 10)

## CLI Architecture (`cli.py`)

**Design Pattern**: Command pattern with subparsers

**Key Features:**
- What-if mode: Preview operations without making changes
- Link crawling: Interactive link selection with recursive processing
- URL fallback: Host-specific URL testing and alternatives

**Commands:**
- `add`: Add document from URL
- `update`: Update existing document
- `delete`: Delete all chunks for a document
- `get`: Retrieve document chunks
- `search`: Semantic search with tag filtering
- `list`: List recent chunks
- `stats`: Get collection statistics

## RSS Monitor Architecture (`rss_feed_monitor.py`)

**Design Pattern**: Monitor/subscription pattern

**Key Components:**
1. **RSSFeedSubscription**: Feed configuration and state
2. **RSSFeedItem**: Individual feed item metadata
3. **RSSFeedMonitor**: Orchestrator for feed processing

**Features:**
- Daily batch processing
- Duplicate detection via MD5 hash
- Subscription enable/disable
- Automatic cleanup of old processed items

## Error Handling

### Strategy

1. **Stage-level**: Each stage catches exceptions and adds to context.errors
2. **Pipeline-level**: Pipeline checks for errors after each stage and stops processing
3. **Component-level**: Individual components (enrichers, handlers) log errors but don't fail pipeline

### Error Types

- **Configuration Errors**: Missing API keys, invalid connection strings (fail fast)
- **Network Errors**: HTTP failures, timeouts (retry with backoff)
- **Processing Errors**: Markdown conversion, chunking failures (log and continue with fallback)
- **Storage Errors**: MongoDB failures (fail and report)

## Extension Points

### Adding a New Source Enricher

1. Create class inheriting from `SourceEnricher`
2. Implement `can_handle()`, `enrich()`, and `name` property
3. Add to `source_enrichers` list in `DocumentPipeline.__init__()`
4. Place before `FallbackSourceEnricher` in the list

### Adding a New Host Handler

1. Create class inheriting from `HostHandler`
2. Implement `can_handle()`, `name` property
3. Optionally override `process_extracted_links()` and `get_url_with_fallback()`
4. Add to `host_handlers` list in `DocumentPipeline.__init__()`
5. Place before `FallbackHostHandler` in the list

### Adding a New Framework Category

1. Add framework name to `FRAMEWORK_CATEGORIES` in `dotnet_sdk_tags.py`
2. If sub-framework of Semantic Kernel, add to `SEMANTIC_KERNEL_FRAMEWORKS`
3. Update AI categorization prompt with framework description

## Testing

### Test Structure

- **Unit Tests** (`tests/`): Legacy tests for AI categorization
- **Integration Tests** (`tests2/`): Comprehensive pipeline tests
  - `test_document_pipeline_v2.py`: End-to-end pipeline tests
  - `test_chunking.py`: Markdown chunking tests
  - `test_source_enrichers.py`: Enricher tests
  - `test_web_page_retriever.py`: Web fetching tests
  - `test_rss_feed_*.py`: RSS functionality tests

### Running Tests

```bash
# Run all tests
cd src/dataIngestion
python tests2/run_tests.py --verbose

# Run specific test module
python -m pytest tests2/test_document_pipeline_v2.py -v
```

## Performance Considerations

### Chunking Strategy

- **Default chunk size**: 4000 characters
- **Reason**: Balance between context preservation and embedding efficiency
- **Trade-offs**: Larger chunks = more context but slower search; smaller chunks = faster but fragmented

### Embedding Caching

- Embeddings are generated once per chunk
- Stored in MongoDB for reuse
- No regeneration unless content changes (requires re-adding document)

### MongoDB Indexing

- Index on `sourceUrl` for document retrieval
- Index on `tags` for filtered searches
- Index on `indexed_date` for chronological queries
- Compound index on `tags` + `indexed_date` for common query pattern

### Batch Processing

- RSS feeds processed in parallel by subscription
- Bulk insert operations for chunks (future optimization)
- Connection pooling for MongoDB

## Future Enhancements

### Planned Features

1. **Update Support**: Re-process documents when source content changes
2. **Incremental Updates**: Update only changed chunks
3. **Batch Import**: CLI command for bulk document import
4. **Custom Chunking Strategies**: Per-content-type chunking rules
5. **Embedding Model Selection**: Support for multiple embedding models
6. **Multi-language Support**: Content in languages beyond English
7. **Document Versioning**: Track document changes over time
8. **Advanced Link Filtering**: ML-based relevance scoring for crawled links

### Known Limitations

1. **No Update Mechanism**: Must delete and re-add to update content
2. **Single Embedding Model**: Cannot mix embedding models in same collection
3. **No Incremental Crawling**: Link crawling is all-or-nothing
4. **Limited Error Recovery**: Failed stages don't retry automatically
5. **No Distributed Processing**: Single-machine processing only

## Security Considerations

- API keys stored in environment variables or .env file
- MongoDB connection string should use authentication
- No sensitive data logged in production
- Input URLs should be validated before fetching
- Content size limits enforced to prevent memory issues

## Monitoring and Observability

### Logging

- **Level**: INFO for normal operations, DEBUG for detailed tracing
- **Format**: Structured logging with timestamps and context
- **Output**: Console (can be redirected to file)

### Metrics

Available via `stats` command:
- Total chunks stored
- Unique documents
- Tag distribution
- Most common tags

### What-If Mode

Preview mode for testing without actual database operations:
```bash
python cli.py --what-if add --source-url https://example.com
```

Shows what would happen without making changes.
