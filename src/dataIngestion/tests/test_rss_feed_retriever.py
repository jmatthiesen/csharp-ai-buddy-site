#!/usr/bin/env python3
"""
Unit tests for RSSFeedRetriever functionality.
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from rss_feed_retriever import RSSFeedRetriever


class TestRSSFeedRetriever(unittest.TestCase):
    """Test RSSFeedRetriever functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.retriever = RSSFeedRetriever()

    @patch("rss_feed_retriever.feedparser")
    def test_fetch_feed_items_success(self, mock_feedparser):
        """Test successful RSS feed parsing."""
        # Setup mock feed data
        mock_feed = Mock()
        mock_feed.bozo = False

        # Create mock feed entries
        mock_entry1 = Mock()
        mock_entry1.get.side_effect = lambda key, default="": {
            "id": "item-1",
            "title": "Test Article 1",
            "link": "https://example.com/article1",
            "description": "Description of article 1",
        }.get(key, default)
        mock_entry1.published_parsed = (2024, 1, 1, 12, 0, 0, 0, 1, 0)
        mock_entry1.author = "Test Author 1"
        mock_entry1.tags = [Mock(term="tag1"), Mock(term="tag2")]
        mock_entry1.content = "<h1>Full Content 1</h1><p>Article content here.</p>"
        # entry1 has no creator attribute - delete it from the mock
        if hasattr(mock_entry1, "creator"):
            delattr(mock_entry1, "creator")

        mock_entry2 = Mock()
        mock_entry2.get.side_effect = lambda key, default="": {
            "id": "item-2",
            "title": "Test Article 2",
            "link": "https://example.com/article2",
            "description": "Description of article 2",
        }.get(key, default)
        mock_entry2.published_parsed = (2024, 1, 2, 12, 0, 0, 0, 2, 0)
        mock_entry2.creator = "Test Creator 2"
        mock_entry2.tags = [Mock(term="tag3")]
        mock_entry2.summary = "<p>Summary content 2</p>"
        # entry2 has no author or content attributes - delete them from the mock
        if hasattr(mock_entry2, "author"):
            delattr(mock_entry2, "author")
        if hasattr(mock_entry2, "content"):
            delattr(mock_entry2, "content")

        mock_feed.entries = [mock_entry1, mock_entry2]
        mock_feedparser.parse.return_value = mock_feed

        # Fetch feed items
        documents = self.retriever.fetch_feed_items("https://example.com/feed.xml")

        # Verify parsing was called
        mock_feedparser.parse.assert_called_once_with("https://example.com/feed.xml")

        # Verify results
        self.assertEqual(len(documents), 2)

        # Check first document
        doc1 = documents[0]
        self.assertEqual(doc1.documentId, "https://example.com/article1")
        self.assertEqual(doc1.title, "Test Article 1")
        self.assertEqual(doc1.content, "<h1>Full Content 1</h1><p>Article content here.</p>")
        self.assertEqual(doc1.sourceUrl, "https://example.com/article1")
        self.assertEqual(doc1.rss_feed_url, "https://example.com/feed.xml")
        self.assertEqual(doc1.rss_author, "Test Author 1")
        self.assertIsInstance(doc1.createdDate, datetime)
        self.assertIn("tag1", doc1.metadata["rss_categories"])
        self.assertIn("tag2", doc1.metadata["rss_categories"])

        # Check second document
        doc2 = documents[1]
        self.assertEqual(doc2.documentId, "https://example.com/article2")
        self.assertEqual(doc2.title, "Test Article 2")
        self.assertEqual(doc2.content, "<p>Summary content 2</p>")  # Should use summary
        self.assertEqual(doc2.rss_author, "Test Creator 2")  # Should use creator
        self.assertIn("tag3", doc2.metadata["rss_categories"])

    @patch("rss_feed_retriever.feedparser")
    def test_fetch_feed_items_with_content_list(self, mock_feedparser):
        """Test RSS feed parsing with content as a list."""
        # Setup mock feed data
        mock_feed = Mock()
        mock_feed.bozo = False

        # Create mock feed entry with content as list
        mock_entry = Mock()
        mock_entry.get.side_effect = lambda key, default="": {
            "id": "item-1",
            "title": "Test Article",
            "link": "https://example.com/article",
            "description": "Description",
        }.get(key, default)
        mock_entry.published_parsed = (2024, 1, 1, 12, 0, 0, 0, 1, 0)
        mock_entry.author = "Test Author"
        mock_entry.tags = []
        mock_entry.content = [{"value": "<h1>Content from list</h1>"}]

        mock_feed.entries = [mock_entry]
        mock_feedparser.parse.return_value = mock_feed

        # Fetch feed items
        documents = self.retriever.fetch_feed_items("https://example.com/feed.xml")

        # Verify content was extracted from list
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].content, "<h1>Content from list</h1>")

    @patch("rss_feed_retriever.feedparser")
    def test_fetch_feed_items_invalid_feed(self, mock_feedparser):
        """Test handling of invalid RSS feed."""
        # Setup mock for invalid feed
        mock_feed = Mock()
        mock_feed.bozo = True  # Indicates parsing error
        mock_feedparser.parse.return_value = mock_feed

        # Fetch feed items
        documents = self.retriever.fetch_feed_items("https://invalid-feed.com/feed.xml")

        # Verify empty result for invalid feed
        self.assertEqual(len(documents), 0)
        mock_feedparser.parse.assert_called_once_with("https://invalid-feed.com/feed.xml")

    @patch("rss_feed_retriever.feedparser")
    def test_fetch_feed_items_exception_handling(self, mock_feedparser):
        """Test handling of exceptions during feed parsing."""
        # Setup mock to raise exception
        mock_feedparser.parse.side_effect = Exception("Network error")

        # Fetch feed items
        documents = self.retriever.fetch_feed_items("https://error-feed.com/feed.xml")

        # Verify empty result on exception
        self.assertEqual(len(documents), 0)

    @patch("rss_feed_retriever.feedparser")
    def test_create_document_from_feed_item_minimal_data(self, mock_feedparser):
        """Test creating document from feed item with minimal data."""
        # Setup mock feed with minimal data
        mock_feed = Mock()
        mock_feed.bozo = False

        # Create a custom mock entry class that only has the attributes we set
        class MinimalMockEntry:
            def get(self, key, default=""):
                return {"link": "https://example.com/minimal", "title": "", "description": ""}.get(
                    key, default
                )

            published_parsed = None

        mock_feed.entries = [MinimalMockEntry()]
        mock_feedparser.parse.return_value = mock_feed

        # Fetch feed items
        documents = self.retriever.fetch_feed_items("https://example.com/feed.xml")

        # Verify document was created with minimal data
        self.assertEqual(len(documents), 1)
        doc = documents[0]
        self.assertEqual(doc.documentId, "https://example.com/minimal")
        self.assertEqual(doc.title, "")
        self.assertEqual(doc.content, "")
        self.assertIsNone(doc.createdDate)
        self.assertEqual(doc.rss_author, None)
        self.assertEqual(doc.metadata["rss_categories"], [])

    @patch("rss_feed_retriever.feedparser")
    def test_create_document_from_feed_item_error_handling(self, mock_feedparser):
        """Test error handling in document creation from feed item."""
        # Setup mock feed
        mock_feed = Mock()
        mock_feed.bozo = False

        # Create mock entry that will cause an error during processing
        mock_entry = Mock()
        mock_entry.get.side_effect = Exception("Error processing entry")

        mock_feed.entries = [mock_entry]
        mock_feedparser.parse.return_value = mock_feed

        # Fetch feed items
        documents = self.retriever.fetch_feed_items("https://example.com/feed.xml")

        # Verify error was handled gracefully
        self.assertEqual(len(documents), 0)


if __name__ == "__main__":
    unittest.main()
