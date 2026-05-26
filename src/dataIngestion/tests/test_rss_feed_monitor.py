#!/usr/bin/env python3
"""
Unit tests for RSS Feed Monitor functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json
import hashlib
from typing import Dict, Any

# RSS feed monitor classes
from rss_feed_monitor import RSSFeedSubscription, RSSFeedItem, RSSFeedMonitor

# Configuration
from config import Config


class TestRSSFeedSubscription(unittest.TestCase):
    """Test RSSFeedSubscription dataclass functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.test_subscription = RSSFeedSubscription(
            _id="test-subscription-123",
            feed_url="https://example.com/feed.xml",
            name="Test Feed",
            description="A test RSS feed",
            tags=["test", "example"],
            enabled=True,
            last_checked=datetime.now(timezone.utc),
            last_item_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
            updated_date=datetime.now(timezone.utc)
        )
    
    def test_from_dict_converts_iso_to_datetime(self):
        """Test that ISO strings are converted back to datetime objects."""
        # Create data with ISO strings
        data = {
            "_id": "test-subscription-123",
            "feed_url": "https://example.com/feed.xml",
            "name": "Test Feed",
            "description": "A test RSS feed",
            "tags": ["test", "example"],
            "enabled": True,
            "last_checked": "2024-01-01T12:00:00+00:00",
            "last_item_date": "2024-01-01T12:00:00+00:00",
            "created_date": "2024-01-01T12:00:00+00:00",
            "updated_date": "2024-01-01T12:00:00+00:00"
        }
        
        subscription = RSSFeedSubscription.from_dict(data)
        
        # Check that datetime fields are datetime objects
        self.assertIsInstance(subscription.last_checked, datetime)
        self.assertIsInstance(subscription.last_item_date, datetime)
        self.assertIsInstance(subscription.created_date, datetime)
        self.assertIsInstance(subscription.updated_date, datetime)
        
        # Check that non-datetime fields remain unchanged
        self.assertEqual(subscription.feed_url, "https://example.com/feed.xml")
        self.assertEqual(subscription.name, "Test Feed")
        self.assertEqual(subscription.tags, ["test", "example"])
    
    def test_from_dict_handles_invalid_datetime(self):
        """Test that invalid datetime strings are handled gracefully."""
        data = {
            "_id": "test-subscription-456",
            "feed_url": "https://example.com/feed.xml",
            "name": "Test Feed",
            "last_checked": "invalid-date",
            "last_item_date": None,
            "created_date": "2024-01-01T12:00:00+00:00",
            "updated_date": "2024-01-01T12:00:00+00:00"
        }
        
        subscription = RSSFeedSubscription.from_dict(data)
        
        # Invalid datetime should be None
        self.assertIsNone(subscription.last_checked)
        self.assertIsNone(subscription.last_item_date)
        
        # Valid datetime should be parsed
        self.assertIsInstance(subscription.created_date, datetime)
        self.assertIsInstance(subscription.updated_date, datetime)


class TestRSSFeedItem(unittest.TestCase):
    """Test RSSFeedItem dataclass functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.test_item = RSSFeedItem(
            _id="test-item-123",
            feed_url="https://example.com/feed.xml",
            item_id="test-item-123",
            title="Test Article",
            link="https://example.com/article",
            description="This is a test article",
            published_date=datetime.now(timezone.utc),
            author="Test Author",
            categories=["test", "article"]
        )
    
    def test_from_dict_converts_iso_to_datetime(self):
        """Test that ISO strings are converted back to datetime objects."""
        data = {
            "_id": "test-item-123",
            "feed_url": "https://example.com/feed.xml",
            "item_id": "test-item-123",
            "title": "Test Article",
            "link": "https://example.com/article",
            "description": "This is a test article",
            "published_date": "2024-01-01T12:00:00+00:00",
            "author": "Test Author",
            "categories": ["test", "article"]
        }
        
        item = RSSFeedItem.from_dict(data)
        
        # Check that published_date is a datetime object
        self.assertIsInstance(item.published_date, datetime)
        
        # Check that non-datetime fields remain unchanged
        self.assertEqual(item.feed_url, "https://example.com/feed.xml")
        self.assertEqual(item.title, "Test Article")
        self.assertEqual(item.categories, ["test", "article"])
    
    def test_from_dict_handles_none_published_date(self):
        """Test that None published_date is handled correctly."""
        data = {
            "_id": "test-item-123",
            "feed_url": "https://example.com/feed.xml",
            "item_id": "test-item-123",
            "title": "Test Article",
            "link": "https://example.com/article",
            "description": "This is a test article",
            "published_date": None,
            "author": "Test Author",
            "categories": ["test", "article"]
        }
        
        item = RSSFeedItem.from_dict(data)
        self.assertIsNone(item.published_date)


class TestRSSFeedMonitor(unittest.TestCase):
    """Test RSSFeedMonitor class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.mongodb_connection_string = "mongodb://localhost:27017"
        self.mock_config.mongodb_database = "test_db"
        self.mock_config.mongodb_collection = "test_collection"
        self.mock_config.openai_api_key = "test-key"
        self.mock_config.embedding_model = "text-embedding-3-small"
        
        # Mock MongoDB collections
        self.mock_subscriptions_collection = Mock()
        self.mock_processed_items_collection = Mock()
        self.mock_pending_items_collection = Mock()
        
        # Mock MongoDB database
        self.mock_db = MagicMock()
        self.mock_db.__getitem__.side_effect = lambda x: {
            "rss_subscriptions": self.mock_subscriptions_collection,
            "rss_processed_items": self.mock_processed_items_collection,
            "rss_pending_items": self.mock_pending_items_collection
        }[x]
        
        # Mock MongoDB client
        self.mock_mongo_client = MagicMock()
        self.mock_mongo_client.__getitem__.return_value = self.mock_db
        
        # Mock document pipeline
        self.mock_document_pipeline = Mock()
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_init_creates_collections(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test that initialization accesses required MongoDB collections."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Create monitor instance
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Verify monitor has access to required collections
        self.assertIsNotNone(monitor.subscriptions_collection)
        self.assertIsNotNone(monitor.processed_items_collection)
        self.assertIsNotNone(monitor.pending_items_collection)
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    @patch('rss_feed_monitor.feedparser')
    def test_add_subscription_validates_feed_url(self, mock_feedparser, mock_document_pipeline_class, mock_mongo_client_class):
        """Test that adding a subscription validates the RSS feed URL."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock feedparser to return invalid feed
        mock_feed = Mock()
        mock_feed.bozo = True
        mock_feedparser.parse.return_value = mock_feed
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test adding invalid feed
        result = monitor.add_subscription(
            feed_url="https://invalid-feed.com/feed.xml",
            name="Invalid Feed"
        )
        
        self.assertFalse(result)
        mock_feedparser.parse.assert_called_with("https://invalid-feed.com/feed.xml")
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    @patch('rss_feed_monitor.feedparser')
    def test_add_subscription_success(self, mock_feedparser, mock_document_pipeline_class, mock_mongo_client_class):
        """Test successful subscription addition."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock feedparser to return valid feed
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feedparser.parse.return_value = mock_feed
        
        # Mock successful MongoDB insert
        mock_insert_result = Mock()
        mock_insert_result.inserted_id = "test-subscription-id"
        self.mock_subscriptions_collection.insert_one.return_value = mock_insert_result
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test adding valid feed
        result = monitor.add_subscription(
            feed_url="https://valid-feed.com/feed.xml",
            name="Valid Feed",
            description="A valid RSS feed",
            tags=["valid", "test"]
        )
        
        self.assertTrue(result)
        self.mock_subscriptions_collection.insert_one.assert_called_once()
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    @patch('rss_feed_monitor.feedparser')
    def test_add_subscription_duplicate_key_error(self, mock_feedparser, mock_document_pipeline_class, mock_mongo_client_class):
        """Test handling of duplicate subscription."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock feedparser to return valid feed
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feedparser.parse.return_value = mock_feed
        
        # Mock duplicate key error
        from pymongo.errors import DuplicateKeyError
        self.mock_subscriptions_collection.insert_one.side_effect = DuplicateKeyError("Duplicate key")
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test adding duplicate feed
        result = monitor.add_subscription(
            feed_url="https://duplicate-feed.com/feed.xml",
            name="Duplicate Feed"
        )
        
        self.assertFalse(result)
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_remove_subscription_success(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test successful subscription removal."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock successful MongoDB delete
        mock_result = Mock()
        mock_result.deleted_count = 1
        self.mock_subscriptions_collection.delete_one.return_value = mock_result
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test removing subscription
        result = monitor.remove_subscription("https://test-feed.com/feed.xml")
        
        self.assertTrue(result)
        self.mock_subscriptions_collection.delete_one.assert_called_with({"feed_url": "https://test-feed.com/feed.xml"})
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_remove_subscription_not_found(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test subscription removal when not found."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock unsuccessful MongoDB delete
        mock_result = Mock()
        mock_result.deleted_count = 0
        self.mock_subscriptions_collection.delete_one.return_value = mock_result
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test removing non-existent subscription
        result = monitor.remove_subscription("https://nonexistent-feed.com/feed.xml")
        
        self.assertFalse(result)
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_list_subscriptions(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test listing subscriptions."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock MongoDB documents
        mock_docs = [
            {
                "_id": 22,
                "feed_url": "https://feed1.com/feed.xml",
                "name": "Feed 1",
                "description": "First test feed",
                "tags": ["test1"],
                "enabled": True,
                "last_checked": "2024-01-01T12:00:00+00:00",
                "last_item_date": "2024-01-01T12:00:00+00:00",
                "created_date": "2024-01-01T12:00:00+00:00",
                "updated_date": "2024-01-01T12:00:00+00:00"
            },
            {
                "_id": 2,
                "feed_url": "https://feed2.com/feed.xml",
                "name": "Feed 2",
                "description": "Second test feed",
                "tags": ["test2"],
                "enabled": False,
                "last_checked": "2024-01-01T12:00:00+00:00",
                "last_item_date": "2024-01-01T12:00:00+00:00",
                "created_date": "2024-01-01T12:00:00+00:00",
                "updated_date": "2024-01-01T12:00:00+00:00"
            }
        ]
        
        self.mock_subscriptions_collection.find.return_value = mock_docs
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test listing subscriptions
        subscriptions = monitor.list_subscriptions()
        
        self.assertEqual(len(subscriptions), 2)
        self.assertEqual(subscriptions[0].name, "Feed 1")
        self.assertEqual(subscriptions[1].name, "Feed 2")
        self.assertTrue(subscriptions[0].enabled)
        self.assertFalse(subscriptions[1].enabled)
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_is_item_processed(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test checking if an item has been processed."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock processed item found
        self.mock_processed_items_collection.find_one.return_value = {"item_id": "test-123"}
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test checking processed item
        result = monitor._is_item_processed("https://feed.com/feed.xml", "test-123")
        
        self.assertTrue(result)
        self.mock_processed_items_collection.find_one.assert_called_with({
            "feed_url": "https://feed.com/feed.xml",
            "item_id": "test-123"
        })
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_mark_item_processed(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test marking an item as processed."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test marking item as processed
        monitor._mark_item_processed("https://feed.com/feed.xml", "test-123")
        
        self.mock_processed_items_collection.insert_one.assert_called_once()
        call_args = self.mock_processed_items_collection.insert_one.call_args[0][0]
        self.assertEqual(call_args["feed_url"], "https://feed.com/feed.xml")
        self.assertEqual(call_args["item_id"], "test-123")
        self.assertIn("processed_date", call_args)
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_get_item_id(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test generating unique item ID from feed item."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock feedparser item
        mock_feed_item = Mock()
        mock_feed_item.get.side_effect = lambda key, default="": {
            "id": "test-item-id",
            "link": "https://example.com/article"
        }.get(key, default)
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test getting item ID
        item_id = monitor._get_item_id(mock_feed_item, "https://feed.com/feed.xml")
        
        # Should return a consistent hash
        self.assertIsInstance(item_id, str)
        self.assertEqual(len(item_id), 32)  # MD5 hash length
    
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_process_feed_integration(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test that RSS feed monitor integrates with document pipeline correctly."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock document pipeline methods - process_document now returns context
        mock_context = Mock()
        mock_context.processing_metadata = {"stored_chunk_ids": ["test-chunk-id"]}
        self.mock_document_pipeline.process_document.return_value = mock_context
        self.mock_document_pipeline.store_document.return_value = "test-doc-id"
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Verify that monitor has access to document pipeline
        self.assertIsNotNone(monitor.document_pipeline)
        self.assertIsNotNone(monitor.rss_retriever)
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_cleanup_old_processed_items(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test cleaning up old processed items."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock successful cleanup
        mock_result = Mock()
        mock_result.deleted_count = 5
        self.mock_processed_items_collection.delete_many.return_value = mock_result
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test cleanup
        deleted_count = monitor.cleanup_old_processed_items(days_to_keep=30)
        
        self.assertEqual(deleted_count, 5)
        self.mock_processed_items_collection.delete_many.assert_called_once()


class TestRSSApprovalWorkflow(unittest.TestCase):
    """Test RSS feed approval workflow functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.mongodb_connection_string = "mongodb://localhost:27017"
        self.mock_config.mongodb_database = "test_db"
        self.mock_config.mongodb_collection = "test_collection"
        self.mock_config.openai_api_key = "test-key"
        self.mock_config.embedding_model = "text-embedding-3-small"
        
        # Mock MongoDB collections
        self.mock_subscriptions_collection = Mock()
        self.mock_processed_items_collection = Mock()
        self.mock_pending_items_collection = Mock()
        
        # Mock MongoDB database
        self.mock_db = MagicMock()
        self.mock_db.__getitem__.side_effect = lambda x: {
            "rss_subscriptions": self.mock_subscriptions_collection,
            "rss_processed_items": self.mock_processed_items_collection,
            "rss_pending_items": self.mock_pending_items_collection
        }[x]
        
        # Mock MongoDB client
        self.mock_mongo_client = MagicMock()
        self.mock_mongo_client.__getitem__.return_value = self.mock_db
        
        # Mock document pipeline
        self.mock_document_pipeline = Mock()
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_is_item_pending(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test checking if an item is pending approval."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock pending item found
        self.mock_pending_items_collection.find_one.return_value = {"item_id": "test-123"}
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test checking pending item
        result = monitor._is_item_pending("https://feed.com/feed.xml", "test-123")
        
        self.assertTrue(result)
        self.mock_pending_items_collection.find_one.assert_called_with({
            "feed_url": "https://feed.com/feed.xml",
            "item_id": "test-123"
        })
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_get_pending_items(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test getting pending items."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock pending items
        mock_items = [
            {
                "item_id": "test-1",
                "title": "Test Article 1",
                "link": "https://example.com/article1",
                "feed_name": "Test Feed"
            },
            {
                "item_id": "test-2",
                "title": "Test Article 2",
                "link": "https://example.com/article2",
                "feed_name": "Test Feed"
            }
        ]
        
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_items
        self.mock_pending_items_collection.find.return_value = mock_cursor
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test getting pending items
        pending_items = monitor.get_pending_items()
        
        self.assertEqual(len(pending_items), 2)
        self.mock_pending_items_collection.find.assert_called_with({})
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_approve_items(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test approving pending items."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock pending item
        pending_item = {
            "item_id": "test-123",
            "feed_url": "https://feed.com/feed.xml",
            "title": "Test Article",
            "link": "https://example.com/article",
            "content": "Test content",
            "feed_name": "Test Feed",
            "feed_tags": ["test"],
            "categories": []
        }
        self.mock_pending_items_collection.find_one.return_value = pending_item
        
        # Mock subscription
        subscription_data = {
            "_id": 1,
            "feed_url": "https://feed.com/feed.xml",
            "name": "Test Feed",
            "enabled": True,
            "tags": ["test"]
        }
        self.mock_subscriptions_collection.find_one.return_value = subscription_data
        
        # Mock document pipeline
        mock_context = Mock()
        mock_context.processing_metadata = {"stored_chunk_ids": ["chunk-1"]}
        self.mock_document_pipeline.process_document.return_value = mock_context
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test approving item
        result = monitor.approve_items(["test-123"])
        
        self.assertEqual(result["approved_count"], 1)
        self.assertEqual(result["failed_count"], 0)
        self.mock_processed_items_collection.insert_one.assert_called_once()
        self.mock_pending_items_collection.delete_one.assert_called_once()
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    def test_reject_items(self, mock_document_pipeline_class, mock_mongo_client_class):
        """Test rejecting pending items."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock pending item
        pending_item = {
            "item_id": "test-123",
            "feed_url": "https://feed.com/feed.xml",
            "title": "Test Article"
        }
        self.mock_pending_items_collection.find_one.return_value = pending_item
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Test rejecting item
        result = monitor.reject_items(["test-123"])
        
        self.assertEqual(result["rejected_count"], 1)
        self.assertEqual(result["failed_count"], 0)
        self.mock_processed_items_collection.insert_one.assert_called_once()
        self.mock_pending_items_collection.delete_one.assert_called_once()
    
    @patch('rss_feed_monitor.MongoClient')
    @patch('rss_feed_monitor.DocumentPipeline')
    @patch('rss_feed_monitor.feedparser')
    def test_check_feed_with_queuing(self, mock_feedparser, mock_document_pipeline_class, mock_mongo_client_class):
        """Test that check_feed queues items when auto_ingest is False."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_document_pipeline_class.return_value = self.mock_document_pipeline
        
        # Mock RSS feed with one item - use proper FeedParserDict-like object
        mock_feed = Mock()
        mock_feed.bozo = False
        
        # Create a proper mock entry with attributes
        mock_entry = Mock()
        mock_entry.title = "Test Article"
        mock_entry.link = "https://example.com/article"
        mock_entry.id = "test-id"
        mock_entry.summary = "Test summary"
        mock_entry.get = lambda key, default="": {
            "title": "Test Article",
            "link": "https://example.com/article",
            "id": "test-id",
            "summary": "Test summary"
        }.get(key, default)
        # Mock tags as empty list
        mock_entry.tags = []
        # Mock no published_parsed
        mock_entry.published_parsed = None
        
        mock_feed.entries = [mock_entry]
        mock_feedparser.parse.return_value = mock_feed
        
        # Mock that item is not processed or pending
        self.mock_processed_items_collection.find_one.return_value = None
        self.mock_pending_items_collection.find_one.return_value = None
        
        # Mock successful insert
        self.mock_pending_items_collection.insert_one.return_value = Mock()
        
        monitor = RSSFeedMonitor(self.mock_config)
        
        # Create subscription
        subscription = RSSFeedSubscription(
            _id="test-sub",
            feed_url="https://feed.com/feed.xml",
            name="Test Feed",
            description="A test feed",
            tags=["test"],
            enabled=True
        )
        
        # Test checking feed with auto_ingest=False (default)
        count = monitor.check_feed(subscription, auto_ingest=False)
        
        # Verify item was queued, not processed
        self.assertEqual(count, 1)
        self.mock_pending_items_collection.insert_one.assert_called_once()
        self.mock_document_pipeline.process_document.assert_not_called()


if __name__ == "__main__":
    unittest.main()
