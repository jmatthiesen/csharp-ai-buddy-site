# Database Setup Scripts

This directory contains database setup scripts for the RAG Data Ingestion Pipeline.

## Scripts

### `setup_rss_indexes.py`

Creates MongoDB indexes for RSS feed monitoring collections (`rss_subscriptions` and `rss_processed_items`).

**Usage:**
```bash
# Basic usage with environment variables
python setup_rss_indexes.py

# With custom config file
python setup_rss_indexes.py --config-file /path/to/config.json

# Dry run to validate configuration
python setup_rss_indexes.py --dry-run

# Verbose output for debugging
python setup_rss_indexes.py --verbose
```

**Required Environment Variables:**
- `MONGODB_CONNECTION_STRING` - MongoDB connection string
- `MONGODB_DATABASE` - MongoDB database name

**Indexes Created:**

For `rss_subscriptions` collection:
- `feed_url` (unique) - Fast lookups for RSS feed URLs
- `enabled` - Filter by enabled/disabled status
- `last_checked` - Scheduling and ordering by last check time

For `rss_processed_items` collection:
- `(feed_url, item_id)` (unique compound) - Prevent duplicate processing
- `processed_date` - Cleanup old processed items

### `setup_document_pipeline_indexes.py`

Creates MongoDB indexes for document processing pipeline collections (`documents` and `document_chunks`).

**Usage:**
```bash
# Basic usage with environment variables
python setup_document_pipeline_indexes.py

# With custom config file
python setup_document_pipeline_indexes.py --config-file /path/to/config.json

# Dry run to validate configuration
python setup_document_pipeline_indexes.py --dry-run

# Verbose output for debugging
python setup_document_pipeline_indexes.py --verbose
```

**Required Environment Variables:**
- `MONGODB_CONNECTION_STRING` - MongoDB connection string
- `MONGODB_DATABASE` - MongoDB database name
- `MONGODB_COLLECTION` - Documents collection name (default: `documents`)
- `MONGODB_CHUNKS_COLLECTION` - Chunks collection name (default: `document_chunks`)

**Indexes Created:**

For documents collection (summaries):
- `documentId` - Fast lookups for document IDs
- `sourceUrl` - Deduplication and URL-based lookups
- `tags` - Filter by tags
- `publishedDate` - Time-based queries
- `(tags, indexedDate)` (compound) - Efficient filtered sorting

For document chunks collection:
- `chunk_id` - Fast lookups for chunk IDs
- `original_document_id` - Document-based queries
- `source_url` - URL-based lookups
- `tags` - Filter by tags
- `indexed_date` - Time-based queries
- `(tags, indexed_date)` (compound) - Efficient filtered sorting

## Setup Order

For a complete setup, run scripts in this order:

1. **Document Pipeline Indexes** (required for basic functionality):
   ```bash
   python setup_document_pipeline_indexes.py
   ```

2. **RSS Feed Indexes** (only if using RSS monitoring):
   ```bash
   python setup_rss_indexes.py
   ```

**When to Run:**
- Once during initial setup before using the data ingestion pipeline
- After database schema changes
- If indexes are accidentally dropped

## Prerequisites

1. MongoDB server running and accessible
2. Python environment with required packages:
   ```bash
   pip install pymongo
   ```
3. Valid configuration (environment variables or config file)

## Troubleshooting

### Connection Issues
- Verify MongoDB connection string
- Check network connectivity to MongoDB server
- Ensure database exists and user has appropriate permissions

### Index Creation Failures
- Check for existing data that might conflict with unique indexes
- Verify sufficient database permissions for index creation
- Use `--verbose` flag for detailed error information

### Configuration Issues
- Verify all required environment variables are set
- Check config file format if using `--config-file`
- Use `--dry-run` to validate configuration without making changes

## Vector Search Index

For the document chunks collection, you may also need to create a vector search index for semantic search functionality. This is typically done through your MongoDB Atlas console or using MongoDB's specific vector search commands:

```javascript
// Example vector search index creation (run in MongoDB shell)
db.document_chunks.createSearchIndex(
  "vector_index",
  {
    "fields": [
      {
        "type": "vector",
        "path": "embeddings",
        "numDimensions": 1536,
        "similarity": "cosine"
      }
    ]
  }
)
```

Note: Vector search indexes require MongoDB Atlas or MongoDB Enterprise and cannot be created through the standard Python scripts.