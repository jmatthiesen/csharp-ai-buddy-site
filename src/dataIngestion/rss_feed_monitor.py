#!/usr/bin/env python3
"""
RSS Feed Monitor for RAG Data Ingestion Pipeline
A module for monitoring RSS feeds and automatically indexing new content.
"""

import os
import json
import argparse
import logging
from typing import List, Dict, Optional, Any, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

# RSS parsing
import feedparser
from feedparser import FeedParserDict

# MongoDB
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId

# Configuration
from config import Config

# Use new pipeline structure
from document_pipeline_v2 import DocumentPipeline
from rss_feed_retriever import RSSFeedRetriever

# Document type
from pipeline_types import RawDocument

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RSSFeedSubscription:
    """Represents an RSS feed subscription."""
    _id: ObjectId
    feed_url: str
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled: bool = True
    last_checked: Optional[datetime] = None
    last_item_date: Optional[datetime] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings for MongoDB
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RSSFeedSubscription":
        """Create from dictionary from MongoDB."""
        
        # Convert ISO strings back to datetime objects
        for key, value in data.items():
            if isinstance(value, str) and key in ['last_checked', 'last_item_date', 'created_date', 'updated_date']:
                try:
                    data[key] = datetime.fromisoformat(value)
                except ValueError:
                    data[key] = None
        return cls(**data)


@dataclass
class RSSFeedItem:
    """Represents an RSS feed item."""
    
    _id: ObjectId
    feed_url: str
    item_id: str
    title: str
    link: str
    description: str
    content: Optional[str] = None
    published_date: Optional[datetime] = None
    author: Optional[str] = None
    categories: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings for MongoDB
        if data.get('published_date'):
            data['published_date'] = data['published_date'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RSSFeedItem":
        """Create from dictionary from MongoDB."""
        
        # Convert ISO string back to datetime object
        if data.get('published_date'):
            try:
                data['published_date'] = datetime.fromisoformat(data['published_date'])
            except ValueError:
                data['published_date'] = None
        return cls(**data)


class RSSFeedMonitor:
    """Main class for managing RSS feed monitoring and indexing."""
    
    def __init__(self, config: Config):
        """Initialize the RSS feed monitor with configuration."""
        self.config = config
        self.mongo_client = MongoClient(config.mongodb_connection_string)
        self.db = self.mongo_client[config.mongodb_database]
        
        # Collections
        self.subscriptions_collection = self.db["rss_subscriptions"]
        self.processed_items_collection = self.db["rss_processed_items"]
        self.pending_items_collection = self.db["rss_pending_items"]
        
        # Initialize document pipeline and RSS retriever for content processing
        self.document_pipeline = DocumentPipeline(config)
        self.rss_retriever = RSSFeedRetriever()
        
    def add_subscription(self, 
                        feed_url: str,
                        name: str,
                        description: Optional[str] = None,
                        tags: Optional[List[str]] = None) -> bool:
        """
        Add a new RSS feed subscription.
        
        Args:
            feed_url: URL of the RSS feed
            name: Human-readable name for the feed
            description: Optional description
            tags: Optional tags for categorization
            
        Returns:
            bool: True if subscription was added successfully
        """
        try:
            # Validate feed URL by attempting to parse it
            feed = feedparser.parse(feed_url)
            if feed.bozo:
                logger.error(f"Invalid RSS feed URL: {feed_url}")
                return False
            
            subscription = RSSFeedSubscription(
                _id=None,  # Will be set by MongoDB
                feed_url=feed_url,
                name=name,
                description=description,
                tags=tags or [],
                created_date=datetime.now(timezone.utc),
                updated_date=datetime.now(timezone.utc)
            )
            
            # Insert into MongoDB
            self.subscriptions_collection.insert_one(subscription.to_dict())
            
            logger.info(f"RSS subscription added successfully: {name} ({feed_url})")
            return True
            
        except DuplicateKeyError:
            logger.error(f"RSS feed subscription already exists: {feed_url}")
            return False
        except Exception as e:
            logger.error(f"Error adding RSS subscription: {e}")
            return False
    
    def remove_subscription(self, feed_url: str) -> bool:
        """
        Remove an RSS feed subscription.
        
        Args:
            feed_url: URL of the RSS feed to remove
            
        Returns:
            bool: True if subscription was removed successfully
        """
        try:
            result = self.subscriptions_collection.delete_one({"feed_url": feed_url})
            
            if result.deleted_count == 0:
                logger.warning(f"RSS subscription not found: {feed_url}")
                return False
            
            logger.info(f"RSS subscription removed successfully: {feed_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing RSS subscription: {e}")
            return False
    
    def list_subscriptions(self) -> List[RSSFeedSubscription]:
        """List all RSS feed subscriptions."""
        try:
            subscriptions = []
            cursor = self.subscriptions_collection.find({})
            
            for doc in cursor:
                subscription = RSSFeedSubscription.from_dict(doc)
                subscriptions.append(subscription)
            
            return subscriptions
            
        except Exception as e:
            logger.error(f"Error listing RSS subscriptions: {e}")
            return []
    
    def _is_item_processed(self, feed_url: str, item_id: str) -> bool:
        """Check if an RSS item has already been processed."""
        try:
            doc = self.processed_items_collection.find_one({
                "feed_url": feed_url,
                "item_id": item_id
            })
            return doc is not None
        except Exception as e:
            logger.error(f"Error checking if item is processed: {e}")
            return False
    
    def _mark_item_processed(self, feed_url: str, item_id: str):
        """Mark an RSS item as processed."""
        try:
            self.processed_items_collection.insert_one({
                "feed_url": feed_url,
                "item_id": item_id,
                "processed_date": datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.error(f"Error marking item as processed: {e}")
    
    def _get_item_id(self, feed_item: FeedParserDict, feed_url: str) -> str:
        """Generate a unique ID for a feed item."""
        unique_string = f"{feed_url}:{feed_item.get('id', feed_item.get('link', ''))}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def _process_feed_item(self, feed_item: FeedParserDict, subscription: RSSFeedSubscription) -> bool:
        """
        Process a single RSS feed item by adding it to the document pipeline.
        
        Args:
            feed_item: The parsed RSS feed item
            subscription: The subscription this item belongs to
            
        Returns:
            bool: True if item was processed successfully
        """
        try:
            # Generate item ID
            item_id = self._get_item_id(feed_item, subscription.feed_url)
            
            # Check if already processed
            if self._is_item_processed(subscription.feed_url, item_id):
                logger.debug(f"Item already processed: {feed_item.get('title', '')}")
                return True
            
            # Create raw document directly from the feed item
            # Extract categories from feed item
            categories = []
            if hasattr(feed_item, 'tags'):
                categories = [tag.term for tag in feed_item.tags if hasattr(tag, 'term')]
            
            # Parse published date
            published_date = None
            if hasattr(feed_item, 'published_parsed') and feed_item.published_parsed:
                published_date = datetime(*feed_item.published_parsed[:6])
            
            # Extract author
            author = None
            if hasattr(feed_item, 'creator'):
                author = feed_item.creator
            elif hasattr(feed_item, 'author'):
                author = feed_item.author
            
            # Extract content
            content = None
            if hasattr(feed_item, 'content') and feed_item.content:
                if isinstance(feed_item.content, list) and len(feed_item.content) > 0:
                    content = feed_item.content[0].get('value', '')
                else:
                    content = feed_item.content
            elif hasattr(feed_item, 'summary'):
                content = feed_item.summary
            elif hasattr(feed_item, 'description'):
                content = feed_item.description
            
            # Create RSS metadata
            rss_metadata = {
                "rss_feed_url": subscription.feed_url,
                "rss_item_id": item_id,
                "rss_author": author,
                "rss_published_date": published_date.isoformat() if published_date else None,
                "rss_categories": categories,
                "rss_feed_name": subscription.name,
                "rss_feed_description": subscription.description
            }
            
            # Remove None values
            rss_metadata = {k: v for k, v in rss_metadata.items() if v is not None}
            
            # Combine subscription tags with item categories
            subscription_tags = subscription.tags or []
            combined_tags = subscription_tags + categories
            
            # Create raw document
            raw_document = RawDocument(
                content=content or '',
                source_url=feed_item.get('link', ''),
                title=feed_item.get('title', ''),
                content_type="rss",
                source_metadata=rss_metadata,
                tags=combined_tags,
                created_date=published_date
            )
            
            # Process and store through document pipeline with chunking
            processing_context = self.document_pipeline.process_document(
                raw_doc=raw_document,
                use_ai_categorization=True,
                additional_metadata={
                    "rss_feed_name": subscription.name,
                    "rss_feed_description": subscription.description
                }
            )
            
            stored_ids = processing_context.processing_metadata.get("stored_chunk_ids", [])
            
            # Mark as processed
            self._mark_item_processed(subscription.feed_url, item_id)
            
            logger.info(f"Processed RSS item into {len(stored_ids)} chunks: {raw_document.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing RSS item {feed_item.get('title', 'Unknown')}: {e}")
            return False
    
    def check_feed(self, subscription: RSSFeedSubscription, auto_ingest: bool = False) -> int:
        """
        Check a single RSS feed for new items.
        
        Args:
            subscription: The RSS feed subscription to check
            auto_ingest: If True, automatically ingest items. If False, queue for approval.
            
        Returns:
            int: Number of new items queued or processed
        """
        try:
            logger.info(f"Checking RSS feed: {subscription.name} ({subscription.feed_url})")
            
            # Parse the RSS feed
            feed = feedparser.parse(subscription.feed_url)
            if feed.bozo:
                logger.error(f"Error parsing RSS feed: {subscription.feed_url}")
                return 0
            
            processed_count = 0
            latest_item_date = subscription.last_item_date
            
            # Process each item in the feed
            for feed_item in feed.entries:
                # Generate item ID for checking
                item_id = self._get_item_id(feed_item, subscription.feed_url)
                
                # Skip if already processed or pending approval
                if self._is_item_processed(subscription.feed_url, item_id):
                    continue
                if self._is_item_pending(subscription.feed_url, item_id):
                    continue
                
                # Queue or process the item based on auto_ingest flag
                if auto_ingest:
                    # Legacy behavior: process immediately
                    if self._process_feed_item(feed_item, subscription):
                        processed_count += 1
                else:
                    # New behavior: queue for approval
                    if self._queue_feed_item(feed_item, subscription):
                        processed_count += 1
                    
                # Track the latest item date
                published_date = None
                if hasattr(feed_item, 'published_parsed') and feed_item.published_parsed:
                    published_date = datetime(*feed_item.published_parsed[:6])
                
                if published_date and (latest_item_date is None or published_date > latest_item_date):
                    latest_item_date = published_date
            
            # Update subscription with last check time and latest item date
            self.subscriptions_collection.update_one(
                {"feed_url": subscription.feed_url},
                {
                    "$set": {
                        "last_checked": datetime.now(timezone.utc),
                        "last_item_date": latest_item_date.isoformat() if latest_item_date else None,
                        "updated_date": datetime.now(timezone.utc)
                    }
                }
            )
            
            action = "processed" if auto_ingest else "queued"
            logger.info(f"{action.capitalize()} {processed_count} new items from {subscription.name}")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error checking RSS feed {subscription.feed_url}: {e}")
            return 0
    
    def _is_item_pending(self, feed_url: str, item_id: str) -> bool:
        """Check if an RSS item is pending approval."""
        try:
            doc = self.pending_items_collection.find_one({
                "feed_url": feed_url,
                "item_id": item_id
            })
            return doc is not None
        except Exception as e:
            logger.error(f"Error checking if item is pending: {e}")
            return False
    
    def _queue_feed_item(self, feed_item: FeedParserDict, subscription: RSSFeedSubscription) -> bool:
        """
        Queue an RSS feed item for approval.
        
        Args:
            feed_item: The parsed RSS feed item
            subscription: The subscription this item belongs to
            
        Returns:
            bool: True if item was queued successfully
        """
        try:
            # Generate item ID
            item_id = self._get_item_id(feed_item, subscription.feed_url)
            
            # Extract categories from feed item
            categories = []
            if hasattr(feed_item, 'tags'):
                categories = [tag.term for tag in feed_item.tags if hasattr(tag, 'term')]
            
            # Parse published date
            published_date = None
            if hasattr(feed_item, 'published_parsed') and feed_item.published_parsed:
                published_date = datetime(*feed_item.published_parsed[:6])
            
            # Extract author
            author = None
            if hasattr(feed_item, 'creator'):
                author = feed_item.creator
            elif hasattr(feed_item, 'author'):
                author = feed_item.author
            
            # Extract content
            content = None
            if hasattr(feed_item, 'content') and feed_item.content:
                if isinstance(feed_item.content, list) and len(feed_item.content) > 0:
                    content = feed_item.content[0].get('value', '')
                else:
                    content = feed_item.content
            elif hasattr(feed_item, 'summary'):
                content = feed_item.summary
            elif hasattr(feed_item, 'description'):
                content = feed_item.description
            
            # Store pending item with all necessary data
            pending_item = {
                "feed_url": subscription.feed_url,
                "item_id": item_id,
                "title": feed_item.get('title', ''),
                "link": feed_item.get('link', ''),
                "description": feed_item.get('summary', feed_item.get('description', '')),
                "content": content or '',
                "author": author,
                "published_date": published_date.isoformat() if published_date else None,
                "categories": categories,
                "feed_name": subscription.name,
                "feed_description": subscription.description,
                "feed_tags": subscription.tags or [],
                "queued_date": datetime.now(timezone.utc)
            }
            
            # Insert into pending items collection
            self.pending_items_collection.insert_one(pending_item)
            
            logger.info(f"Queued RSS item for approval: {feed_item.get('title', '')}")
            return True
            
        except Exception as e:
            logger.error(f"Error queuing RSS item {feed_item.get('title', 'Unknown')}: {e}")
            return False
    
    def get_pending_items(self, feed_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all pending items awaiting approval.
        
        Args:
            feed_url: Optional filter by specific feed URL
            
        Returns:
            List of pending items
        """
        try:
            query = {}
            if feed_url:
                query["feed_url"] = feed_url
            
            cursor = self.pending_items_collection.find(query).sort("queued_date", -1)
            
            pending_items = []
            for doc in cursor:
                pending_items.append(doc)
            
            return pending_items
            
        except Exception as e:
            logger.error(f"Error getting pending items: {e}")
            return []
    
    def approve_items(self, item_ids: List[str]) -> Dict[str, Any]:
        """
        Approve and ingest selected pending items.
        
        Args:
            item_ids: List of item IDs to approve and ingest
            
        Returns:
            Dict with statistics about approved items
        """
        try:
            approved_count = 0
            failed_count = 0
            errors = []
            
            for item_id in item_ids:
                # Find the pending item
                pending_item = self.pending_items_collection.find_one({"item_id": item_id})
                
                if not pending_item:
                    logger.warning(f"Pending item not found: {item_id}")
                    failed_count += 1
                    errors.append(f"Item not found: {item_id}")
                    continue
                
                # Get the subscription
                subscription_data = self.subscriptions_collection.find_one({"feed_url": pending_item["feed_url"]})
                if not subscription_data:
                    logger.error(f"Subscription not found for feed: {pending_item['feed_url']}")
                    failed_count += 1
                    errors.append(f"Subscription not found for item: {item_id}")
                    continue
                
                subscription = RSSFeedSubscription.from_dict(subscription_data)
                
                # Create a raw document for processing
                published_date = None
                if pending_item.get('published_date'):
                    try:
                        published_date = datetime.fromisoformat(pending_item['published_date'])
                    except ValueError:
                        pass
                
                # Create RSS metadata
                rss_metadata = {
                    "rss_feed_url": pending_item["feed_url"],
                    "rss_item_id": item_id,
                    "rss_author": pending_item.get("author"),
                    "rss_published_date": pending_item.get("published_date"),
                    "rss_categories": pending_item.get("categories", []),
                    "rss_feed_name": pending_item["feed_name"],
                    "rss_feed_description": pending_item.get("feed_description")
                }
                
                # Remove None values
                rss_metadata = {k: v for k, v in rss_metadata.items() if v is not None}
                
                # Combine subscription tags with item categories
                combined_tags = pending_item.get("feed_tags", []) + pending_item.get("categories", [])
                
                # Create raw document
                raw_document = RawDocument(
                    content=pending_item.get("content", ""),
                    source_url=pending_item.get("link", ""),
                    title=pending_item.get("title", ""),
                    content_type="rss",
                    source_metadata=rss_metadata,
                    tags=combined_tags,
                    created_date=published_date
                )
                
                try:
                    # Process and store through document pipeline
                    processing_context = self.document_pipeline.process_document(
                        raw_doc=raw_document,
                        use_ai_categorization=True,
                        additional_metadata={
                            "rss_feed_name": pending_item["feed_name"],
                            "rss_feed_description": pending_item.get("feed_description")
                        }
                    )
                    
                    stored_ids = processing_context.processing_metadata.get("stored_chunk_ids", [])
                    
                    # Mark as processed
                    self._mark_item_processed(pending_item["feed_url"], item_id)
                    
                    # Remove from pending
                    self.pending_items_collection.delete_one({"item_id": item_id})
                    
                    logger.info(f"Approved and processed RSS item into {len(stored_ids)} chunks: {raw_document.title}")
                    approved_count += 1
                    
                except Exception as process_error:
                    logger.error(f"Error processing approved item {item_id}: {process_error}")
                    failed_count += 1
                    errors.append(f"Processing error for {item_id}: {str(process_error)}")
            
            return {
                "approved_count": approved_count,
                "failed_count": failed_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error approving items: {e}")
            return {
                "approved_count": 0,
                "failed_count": len(item_ids),
                "errors": [str(e)]
            }
    
    def reject_items(self, item_ids: List[str]) -> Dict[str, Any]:
        """
        Reject selected pending items (mark as processed without ingesting).
        
        Args:
            item_ids: List of item IDs to reject
            
        Returns:
            Dict with statistics about rejected items
        """
        try:
            rejected_count = 0
            failed_count = 0
            errors = []
            
            for item_id in item_ids:
                # Find the pending item
                pending_item = self.pending_items_collection.find_one({"item_id": item_id})
                
                if not pending_item:
                    logger.warning(f"Pending item not found: {item_id}")
                    failed_count += 1
                    errors.append(f"Item not found: {item_id}")
                    continue
                
                # Mark as processed (rejected)
                self._mark_item_processed(pending_item["feed_url"], item_id)
                
                # Remove from pending
                self.pending_items_collection.delete_one({"item_id": item_id})
                
                logger.info(f"Rejected RSS item: {pending_item.get('title', '')}")
                rejected_count += 1
            
            return {
                "rejected_count": rejected_count,
                "failed_count": failed_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error rejecting items: {e}")
            return {
                "rejected_count": 0,
                "failed_count": len(item_ids),
                "errors": [str(e)]
            }
    
    def run_daily_check(self, auto_ingest: bool = False) -> Dict[str, Any]:
        """
        Run the daily RSS feed check for all enabled subscriptions.
        
        Args:
            auto_ingest: If True, automatically ingest items. If False, queue for approval.
        
        Returns:
            Dict containing statistics about the check
        """
        try:
            action = "ingesting" if auto_ingest else "queuing"
            logger.info(f"Starting daily RSS feed check ({action} new items)")
            
            # Get all enabled subscriptions
            enabled_subscriptions = []
            cursor = self.subscriptions_collection.find({"enabled": True})
            
            for doc in cursor:
                subscription = RSSFeedSubscription.from_dict(doc)
                enabled_subscriptions.append(subscription)
            
            if not enabled_subscriptions:
                logger.info("No enabled RSS subscriptions found")
                return {
                    "total_subscriptions": 0,
                    "processed_subscriptions": 0,
                    "total_items_queued": 0,
                    "errors": []
                }
            
            total_items_processed = 0
            processed_subscriptions = 0
            errors = []
            
            # Check each subscription
            for subscription in enabled_subscriptions:
                try:
                    items_processed = self.check_feed(subscription, auto_ingest=auto_ingest)
                    total_items_processed += items_processed
                    processed_subscriptions += 1
                except Exception as e:
                    error_msg = f"Error processing subscription {subscription.name}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            stats = {
                "total_subscriptions": len(enabled_subscriptions),
                "processed_subscriptions": processed_subscriptions,
                "total_items_queued": total_items_processed,
                "errors": errors
            }
            
            logger.info(f"Daily RSS check completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during daily RSS check: {e}")
            return {
                "total_subscriptions": 0,
                "processed_subscriptions": 0,
                "total_items_queued": 0,
                "errors": [str(e)]
            }
    
    def cleanup_old_processed_items(self, days_to_keep: int = 30) -> int:
        """
        Clean up old processed item records to prevent database bloat.
        
        Args:
            days_to_keep: Number of days of processed items to keep
            
        Returns:
            int: Number of records deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            result = self.processed_items_collection.delete_many({
                "processed_date": {"$lt": cutoff_date}
            })
            
            deleted_count = result.deleted_count
            logger.info(f"Cleaned up {deleted_count} old processed item records")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old processed items: {e}")
            return 0


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(description="RSS Feed Monitor for RAG Data Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add subscription command
    add_parser = subparsers.add_parser("add-subscription", help="Add a new RSS feed subscription")
    add_parser.add_argument("--feed-url", required=True, help="RSS feed URL")
    add_parser.add_argument("--name", required=True, help="Human-readable name for the feed")
    add_parser.add_argument("--description", help="Optional description")
    add_parser.add_argument("--tags", nargs="+", help="Tags for categorization")
    
    # Remove subscription command
    remove_parser = subparsers.add_parser("remove-subscription", help="Remove an RSS feed subscription")
    remove_parser.add_argument("--feed-url", required=True, help="RSS feed URL to remove")
    
    # List subscriptions command
    list_parser = subparsers.add_parser("list-subscriptions", help="List all RSS feed subscriptions")
    
    # Check feeds command
    check_parser = subparsers.add_parser("check-feeds", help="Check all enabled RSS feeds")
    
    # Daily check command
    daily_parser = subparsers.add_parser("daily-check", help="Run daily RSS feed check")
    daily_parser.add_argument("--auto-ingest", action="store_true", help="Automatically ingest items without approval")
    
    # List pending items command
    list_pending_parser = subparsers.add_parser("list-pending", help="List items pending approval")
    list_pending_parser.add_argument("--feed-url", help="Filter by specific feed URL")
    
    # Approve items command
    approve_parser = subparsers.add_parser("approve", help="Approve and ingest pending items")
    approve_parser.add_argument("--item-ids", nargs="+", help="Item IDs to approve (space-separated)")
    approve_parser.add_argument("--all", action="store_true", help="Approve all pending items")
    approve_parser.add_argument("--interactive", action="store_true", help="Interactive mode - select items to approve")
    
    # Reject items command
    reject_parser = subparsers.add_parser("reject", help="Reject pending items")
    reject_parser.add_argument("--item-ids", nargs="+", help="Item IDs to reject (space-separated)")
    reject_parser.add_argument("--all", action="store_true", help="Reject all pending items")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old processed items")
    cleanup_parser.add_argument("--days", type=int, default=30, help="Days of processed items to keep")

    # Launch Streamlit UI command
    ui_parser = subparsers.add_parser("launch-ui", help="Launch the Streamlit UI for RSS Feed Monitor")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load configuration
    config = Config.load()
    monitor = RSSFeedMonitor(config)
    
    try:
        if args.command == "add-subscription":
            success = monitor.add_subscription(
                feed_url=args.feed_url,
                name=args.name,
                description=args.description,
                tags=args.tags
            )
            print(f"Subscription {'added' if success else 'failed to add'}")

        elif args.command == "remove-subscription":
            success = monitor.remove_subscription(args.feed_url)
            print(f"Subscription {'removed' if success else 'failed to remove'}")

        elif args.command == "list-subscriptions":
            subscriptions = monitor.list_subscriptions()
            for sub in subscriptions:
                print(f"{sub.name}: {sub.feed_url} ({'enabled' if sub.enabled else 'disabled'})")

        elif args.command == "check-feeds":
            stats = monitor.run_daily_check()
            print(json.dumps(stats, indent=2, default=str))

        elif args.command == "daily-check":
            stats = monitor.run_daily_check(auto_ingest=args.auto_ingest)
            print(json.dumps(stats, indent=2, default=str))

        elif args.command == "list-pending":
            pending_items = monitor.get_pending_items(feed_url=args.feed_url)
            if not pending_items:
                print("No pending items found.")
            else:
                print(f"\n{len(pending_items)} pending items:\n")
                for item in pending_items:
                    print(f"ID: {item['item_id']}")
                    print(f"Title: {item['title']}")
                    print(f"Link: {item['link']}")
                    print(f"Feed: {item['feed_name']}")
                    print(f"Published: {item.get('published_date', 'Unknown')}")
                    print(f"Description: {item.get('description', '')[:200]}...")
                    print("-" * 80)

        elif args.command == "approve":
            if args.interactive:
                # Interactive mode - show items and let user select
                pending_items = monitor.get_pending_items()
                if not pending_items:
                    print("No pending items found.")
                else:
                    print(f"\n{len(pending_items)} pending items:\n")
                    for i, item in enumerate(pending_items, 1):
                        print(f"{i}. {item['title']}")
                        print(f"   Feed: {item['feed_name']}")
                        print(f"   Link: {item['link']}")
                        print(f"   Description: {item.get('description', '')[:150]}...")
                        print()
                    
                    print("\nSelection options:")
                    print("  - Enter item numbers separated by commas (e.g., 1,3,5)")
                    print("  - Enter 'all' to approve all items")
                    print("  - Enter 'none' or just press Enter to cancel")
                    
                    user_input = input("\nSelect items to approve: ").strip().lower()
                    
                    if not user_input or user_input == 'none':
                        print("Approval cancelled.")
                        return 0
                    
                    if user_input == 'all':
                        item_ids = [item['item_id'] for item in pending_items]
                    else:
                        try:
                            selected_indices = [int(x.strip()) for x in user_input.split(',')]
                            item_ids = []
                            for index in selected_indices:
                                if 1 <= index <= len(pending_items):
                                    item_ids.append(pending_items[index - 1]['item_id'])
                                else:
                                    print(f"Invalid item number: {index}")
                                    return 1
                        except ValueError:
                            print("Invalid input. Please enter numbers separated by commas.")
                            return 1
                    
                    result = monitor.approve_items(item_ids)
                    print(json.dumps(result, indent=2, default=str))
            elif args.all:
                # Approve all pending items
                pending_items = monitor.get_pending_items()
                item_ids = [item['item_id'] for item in pending_items]
                if not item_ids:
                    print("No pending items found.")
                else:
                    result = monitor.approve_items(item_ids)
                    print(json.dumps(result, indent=2, default=str))
            elif args.item_ids:
                # Approve specific items
                result = monitor.approve_items(args.item_ids)
                print(json.dumps(result, indent=2, default=str))
            else:
                print("Please specify --item-ids, --all, or --interactive")

        elif args.command == "reject":
            if args.all:
                # Reject all pending items
                pending_items = monitor.get_pending_items()
                item_ids = [item['item_id'] for item in pending_items]
                if not item_ids:
                    print("No pending items found.")
                else:
                    result = monitor.reject_items(item_ids)
                    print(json.dumps(result, indent=2, default=str))
            elif args.item_ids:
                # Reject specific items
                result = monitor.reject_items(args.item_ids)
                print(json.dumps(result, indent=2, default=str))
            else:
                print("Please specify --item-ids or --all")

        elif args.command == "cleanup":
            deleted_count = monitor.cleanup_old_processed_items(args.days)
            print(f"Cleaned up {deleted_count} old processed item records")

        elif args.command == "launch-ui":
            import subprocess
            ui_path = os.path.join(os.path.dirname(__file__), "rss_feed_monitor_ui.py")
            print("Launching Streamlit UI...")
            subprocess.run(["streamlit", "run", ui_path])

    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main()) 