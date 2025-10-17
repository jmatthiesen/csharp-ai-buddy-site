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

**When to Run:**
- Once during initial setup before using RSS feed monitoring
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