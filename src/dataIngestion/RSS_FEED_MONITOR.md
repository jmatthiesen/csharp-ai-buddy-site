# RSS Feed Monitor

The RSS Feed Monitor provides automated monitoring and human-in-the-loop approval for RSS feed content ingestion into the RAG pipeline.

## Overview

The RSS Feed Monitor allows you to:
- Subscribe to RSS feeds for automatic monitoring
- Queue new articles for human review and approval
- Approve or reject articles before ingestion
- Track processed items to avoid duplicates
- Manage subscriptions via CLI or Streamlit UI

## Key Features

### Human-in-the-Loop Approval Workflow

By default, new articles are **queued for approval** rather than automatically ingested. This prevents wasting resources on irrelevant articles.

- ✅ **Queue new items**: Daily checks place new articles in a pending queue
- 👀 **Review items**: Examine title, description, link, and metadata
- ✓ **Approve selected**: Choose which articles to ingest into the RAG system
- ✗ **Reject unwanted**: Mark articles as processed without ingesting

### Flexible Ingestion Modes

1. **Approval Mode (Default)**: Queue new items for manual review
2. **Auto-Ingest Mode**: Legacy behavior for automatic ingestion

## Setup

### Database Indexes

Before using the RSS Feed Monitor, create the required MongoDB indexes:

```bash
cd src/dataIngestion
python dbSetup/setup_rss_indexes.py
```

This creates indexes for:
- `rss_subscriptions` - Feed subscription information
- `rss_processed_items` - Tracking processed articles
- `rss_pending_items` - Articles awaiting approval

## Command Line Interface

### Managing Subscriptions

#### Add a Subscription

```bash
python rss_feed_monitor.py add-subscription \
  --feed-url "https://example.com/feed.xml" \
  --name "Example Blog" \
  --description "A blog about .NET and AI" \
  --tags ".NET" "AI"
```

#### List Subscriptions

```bash
python rss_feed_monitor.py list-subscriptions
```

#### Remove a Subscription

```bash
python rss_feed_monitor.py remove-subscription \
  --feed-url "https://example.com/feed.xml"
```

### Checking Feeds

#### Daily Check (Queue for Approval)

```bash
# Queue new items for approval (default behavior)
python rss_feed_monitor.py daily-check
```

Output:
```json
{
  "total_subscriptions": 3,
  "processed_subscriptions": 3,
  "total_items_queued": 5,
  "errors": []
}
```

#### Daily Check (Auto-Ingest)

```bash
# Auto-ingest without approval (legacy mode)
python rss_feed_monitor.py daily-check --auto-ingest
```

### Managing Pending Items

#### List Pending Items

```bash
python rss_feed_monitor.py list-pending
```

Output shows pending items with:
- Item ID
- Title
- Link
- Feed name
- Published date
- Description (truncated)

#### Approve Items (Interactive)

```bash
python rss_feed_monitor.py approve --interactive
```

This displays all pending items and prompts for selection:
```
Selection options:
  - Enter item numbers separated by commas (e.g., 1,3,5)
  - Enter 'all' to approve all items
  - Enter 'none' or just press Enter to cancel

Select items to approve: 1,3,5
```

#### Approve Specific Items

```bash
python rss_feed_monitor.py approve \
  --item-ids <item-id-1> <item-id-2> <item-id-3>
```

#### Approve All Items

```bash
python rss_feed_monitor.py approve --all
```

#### Reject Items

```bash
# Reject specific items
python rss_feed_monitor.py reject \
  --item-ids <item-id-1> <item-id-2>

# Reject all pending items
python rss_feed_monitor.py reject --all
```

### Cleanup

Remove old processed item records:

```bash
python rss_feed_monitor.py cleanup --days 30
```

## Streamlit User Interface

### Launch the UI

```bash
python rss_feed_monitor.py launch-ui
```

Or directly:

```bash
streamlit run rss_feed_monitor_ui.py
```

### UI Features

#### Subscriptions Management
- **List Subscriptions**: View all RSS feed subscriptions
- **Add Subscription**: Add new feeds with name, description, and tags
- **Remove Subscription**: Delete existing subscriptions

#### Feed Checking
- **Check Feeds**: Run daily check for all enabled feeds
- **Auto-ingest option**: Toggle between approval mode and auto-ingest

#### Pending Items Review
- **View all pending items**: See title, description, link, and metadata
- **Select/deselect items**: Use checkboxes to choose items
- **Select All / Deselect All**: Bulk selection controls
- **Approve Selected**: Ingest selected items into the RAG system
- **Reject Selected**: Mark items as processed without ingestion

#### Cleanup
- **Cleanup Old Items**: Remove old processed item records

## Workflow Example

### Daily Workflow

1. **Run Daily Check** (scheduled or manual):
   ```bash
   python rss_feed_monitor.py daily-check
   ```

2. **Review Pending Items**:
   ```bash
   # CLI: Interactive approval
   python rss_feed_monitor.py approve --interactive
   
   # OR UI: Use Streamlit for visual review
   streamlit run rss_feed_monitor_ui.py
   ```

3. **Approve/Reject Items**:
   - In CLI: Select item numbers to approve
   - In UI: Check boxes next to items and click "Approve Selected"

4. **Cleanup Periodically**:
   ```bash
   python rss_feed_monitor.py cleanup --days 30
   ```

## Data Storage

### Collections

#### `rss_subscriptions`
Stores feed subscription information:
- `feed_url`: RSS feed URL (unique)
- `name`: Human-readable name
- `description`: Optional description
- `tags`: List of tags for categorization
- `enabled`: Whether the subscription is active
- `last_checked`: Last check timestamp
- `last_item_date`: Date of most recent item
- `created_date`, `updated_date`: Timestamps

#### `rss_pending_items`
Items awaiting approval:
- `feed_url`: Source feed URL
- `item_id`: Unique item identifier (MD5 hash)
- `title`: Article title
- `link`: Article URL
- `description`: Article summary/description
- `content`: Full article content
- `author`: Article author
- `published_date`: Publication date
- `categories`: Article categories/tags
- `feed_name`, `feed_description`: Feed metadata
- `feed_tags`: Tags from subscription
- `queued_date`: When item was queued

#### `rss_processed_items`
Tracking processed items (both approved and rejected):
- `feed_url`: Source feed URL
- `item_id`: Unique item identifier
- `processed_date`: When item was processed

## Configuration

The RSS Feed Monitor uses the same configuration as the main data ingestion pipeline:

```env
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net
MONGODB_DATABASE=csharpAIBuddy
MONGODB_COLLECTION=documents

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## Scheduling

### Automated Daily Checks

To schedule automated daily checks, use cron (Linux/Mac) or Task Scheduler (Windows):

#### Linux/Mac (cron)

```bash
# Add to crontab (run daily at 6 AM)
0 6 * * * cd /path/to/src/dataIngestion && /path/to/python rss_feed_monitor.py daily-check
```

#### Windows (Task Scheduler)

Create a scheduled task to run:
```
Program: C:\path\to\python.exe
Arguments: rss_feed_monitor.py daily-check
Start in: C:\path\to\src\dataIngestion
```

## API Integration

### Programmatic Usage

```python
from config import Config
from rss_feed_monitor import RSSFeedMonitor

# Initialize monitor
config = Config.load()
monitor = RSSFeedMonitor(config)

# Add subscription
monitor.add_subscription(
    feed_url="https://example.com/feed.xml",
    name="Example Blog",
    description="A blog about .NET and AI",
    tags=[".NET", "AI"]
)

# Run daily check (queue for approval)
stats = monitor.run_daily_check(auto_ingest=False)
print(f"Queued {stats['total_items_queued']} items")

# Get pending items
pending_items = monitor.get_pending_items()
for item in pending_items:
    print(f"- {item['title']}")

# Approve specific items
item_ids = [item['item_id'] for item in pending_items[:3]]
result = monitor.approve_items(item_ids)
print(f"Approved {result['approved_count']} items")

# Reject items
reject_ids = [item['item_id'] for item in pending_items[3:]]
result = monitor.reject_items(reject_ids)
print(f"Rejected {result['rejected_count']} items")
```

## Troubleshooting

### Issue: Items not appearing in pending queue

**Check:**
1. Run daily check: `python rss_feed_monitor.py daily-check`
2. Verify subscriptions are enabled: `python rss_feed_monitor.py list-subscriptions`
3. Check for errors in the daily check output

### Issue: Unable to approve items

**Check:**
1. Verify items are in pending queue: `python rss_feed_monitor.py list-pending`
2. Check MongoDB connection
3. Ensure OpenAI API key is valid for embeddings

### Issue: Duplicate items being queued

**Solution:** Run the database setup script to ensure proper indexes:
```bash
python dbSetup/setup_rss_indexes.py
```

## Migration from Auto-Ingest

If you were previously using auto-ingest mode:

1. **No changes required**: The default behavior now queues items for approval
2. **To maintain auto-ingest**: Use `--auto-ingest` flag with `daily-check` command
3. **Gradual transition**: Start with auto-ingest, gradually move to approval mode

## Best Practices

1. **Review Regularly**: Check pending items at least weekly to prevent queue buildup
2. **Use Tags**: Add meaningful tags to subscriptions for better organization
3. **Cleanup Often**: Run cleanup monthly to remove old processed item records
4. **Monitor Errors**: Check daily-check output for feed parsing errors
5. **Disable Inactive Feeds**: Disable rather than delete subscriptions you might reuse

## Testing

Run the test suite:

```bash
cd src/dataIngestion
python -m unittest tests2.test_rss_feed_monitor -v
```

## Support

For issues and questions:
- Check the [main README](README.md) for general pipeline documentation
- Review error logs for detailed error messages
- Open an issue in the repository
