# Data Ingestion Pipeline

A modular Python pipeline for ingesting, processing, and indexing .NET AI development content from web pages and RSS feeds into MongoDB with vector embeddings. The system automatically converts content to Markdown, chunks it intelligently, generates OpenAI embeddings, and categorizes content using AI to identify relevant .NET frameworks. It features a pluggable architecture with source-specific enrichers and host handlers, supporting both manual document addition via CLI and automated RSS feed monitoring.

## Features

- **Multi-Source Ingestion**: Process content from web pages, WordPress sites, RSS/Atom feeds, and direct URLs
- **Intelligent Content Processing**: Automatic HTML-to-Markdown conversion with MarkItDown, smart chunking that preserves document structure
- **AI-Powered Categorization**: Automatic framework tagging (Semantic Kernel, ML.NET, AutoGen, etc.) using OpenAI
- **Vector Search Ready**: Generate and store OpenAI embeddings for semantic search capabilities  
- **Link Crawling**: Interactive link extraction and crawling with host-specific filtering (GitHub, WordPress, etc.)
- **RSS Feed Monitoring**: Automated daily checks of subscribed feeds with duplicate detection
- **Pluggable Architecture**: Extensible source enrichers and host handlers for different content types
- **MongoDB Storage**: Chunk-based storage optimized for retrieval with metadata and tags
- **What-If Mode**: Preview operations without making database changes
- **Comprehensive CLI**: Full command-line interface for all document and RSS operations

## Environment Setup

### Prerequisites

- **[Python 3.8+](https://www.python.org/downloads/)** with pip
- **[MongoDB](https://www.mongodb.com/docs/manual/installation/)** instance (local or cloud - [MongoDB Atlas](https://www.mongodb.com/atlas) recommended)
- **[OpenAI API Key](https://platform.openai.com/api-keys)** with access to embeddings and chat models

### Installation

1. **Navigate to the project directory:**
   ```bash
   cd src/dataIngestion
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
   cp env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # MongoDB Configuration
   MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net
   MONGODB_DATABASE=csharpAIBuddy
   MONGODB_COLLECTION=documents
   MONGODB_CHUNKS_COLLECTION=document_chunks
   
   # OpenAI Configuration
   OPENAI_API_KEY=sk-your-openai-api-key-here
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   
   # Pipeline Settings
   MAX_CONTENT_LENGTH=8192
   BATCH_SIZE=10
   ```

5. **Set up MongoDB indexes** (recommended):
   ```bash
   cd dbSetup
   python setup_document_pipeline_indexes.py
   python setup_rss_indexes.py
   ```

### Running the Pipeline

#### Document Management CLI

Add a document from a URL:
```bash
python cli.py add --source-url "https://example.com/article"
```

Add with link crawling (interactive selection):
```bash
python cli.py add --source-url "https://example.com/article" --crawl-links
```

Add with manual tags (disables AI categorization):
```bash
python cli.py add --source-url "https://example.com/article" --tags "Semantic Kernel" "ML.NET"
```

Preview without making changes:
```bash
python cli.py --what-if add --source-url "https://example.com/article"
```

Delete a document:
```bash
python cli.py delete --document-id "doc_20241020_123456"
```

Search documents:
```bash
python cli.py search --query "How to use Semantic Kernel" --limit 5
```

Search with tag filtering:
```bash
python cli.py search --query "embeddings" --tags "Semantic Kernel" "OpenAI SDK"
```

List recent documents:
```bash
python cli.py list --limit 20
```

Get statistics:
```bash
python cli.py stats
```

#### RSS Feed Monitoring

Add an RSS feed subscription:
```bash
python rss_feed_monitor.py add-subscription \
  --feed-url "https://devblogs.microsoft.com/dotnet/feed/" \
  --name "Microsoft .NET Blog" \
  --description "Official Microsoft .NET blog" \
  --tags "ML.NET" "Semantic Kernel"
```

List all subscriptions:
```bash
python rss_feed_monitor.py list-subscriptions
```

Check all feeds for new content:
```bash
python rss_feed_monitor.py check-feeds
```

Run daily check (for scheduled jobs):
```bash
python rss_feed_monitor.py daily-check
```

Remove a subscription:
```bash
python rss_feed_monitor.py remove-subscription \
  --feed-url "https://devblogs.microsoft.com/dotnet/feed/"
```

Clean up old processed items:
```bash
python rss_feed_monitor.py cleanup --days 30
```

Launch UI for running RSS monitoring commands:
```bash
python rss_feed_monitor.py launch-ui
```

## CLI Command Reference

### Document Management (`cli.py`)

| Command | Parameters | Description |
|---------|-----------|-------------|
| `add` | `--source-url URL` | Add document from URL |
| | `--tags TAG [TAG...]` | Manual tags (disables AI categorization) |
| | `--metadata JSON` | Additional metadata as JSON string |
| | `--no-ai-categorization` | Disable AI framework categorization |
| | `--crawl-links` | Enable interactive link crawling |
| `update` | `--document-id ID` | Update existing document |
| | `--tags TAG [TAG...]` | New tags |
| | `--metadata JSON` | New metadata |
| `delete` | `--document-id ID` | Delete all chunks for document |
| `get` | `--document-id ID` | Retrieve document chunks |
| `search` | `--query TEXT` | Search query text |
| | `--tags TAG [TAG...]` | Filter by tags |
| | `--limit N` | Maximum results (default: 10) |
| `list` | `--tags TAG [TAG...]` | Filter by tags |
| | `--limit N` | Maximum results (default: 50) |
| `stats` | | Get pipeline statistics |

**Global Options:**
- `--what-if`: Preview operations without making changes

### RSS Feed Monitor (`rss_feed_monitor.py`)

| Command | Parameters | Description |
|---------|-----------|-------------|
| `add-subscription` | `--feed-url URL` | RSS feed URL |
| | `--name NAME` | Human-readable feed name |
| | `--description TEXT` | Optional description |
| | `--tags TAG [TAG...]` | Tags to apply to all items |
| `remove-subscription` | `--feed-url URL` | Remove RSS subscription |
| `list-subscriptions` | | List all subscriptions |
| `check-feeds` | | Check all enabled feeds for new items |
| `daily-check` | | Run daily check (same as check-feeds) |
| `cleanup` | `--days N` | Clean up processed items older than N days (default: 30) |
| `launch-ui` | | Launch Streamlit web interface |

## Architecture

For detailed information about the pipeline architecture, data flow, and extension points, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Contributing

Contributions are welcome! Please see the architecture documentation for information on adding new source enrichers, host handlers, or framework categories.