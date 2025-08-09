#!/usr/bin/env python3
"""
Unit tests for Document data transfer object.
"""

import unittest
from datetime import datetime, timezone

# MongoDB ObjectId
from bson.objectid import ObjectId

# Document type
from document import Document


class TestDocument(unittest.TestCase):
    """Test Document dataclass functionality."""

    def setUp(self):
        """Set up test data."""
        self.test_document = Document(
            documentId="https://example.com/article",
            title="Test Article",
            sourceUrl="https://example.com/article",
            content="# Test Content\n\nThis is test content.",
            embeddings=[0.1, 0.2, 0.3],
            tags=["test", "article"],
            createdDate=datetime.now(timezone.utc),
            updatedDate=datetime.now(timezone.utc),
            indexedDate=datetime.now(timezone.utc),
            metadata={"author": "Test Author", "category": "test"},
        )

    def test_to_dict_converts_datetime_to_iso(self):
        """Test that datetime objects are converted to ISO strings."""
        data = self.test_document.to_dict()

        # Check that datetime fields are ISO strings
        self.assertIsInstance(data["createdDate"], str)
        self.assertIsInstance(data["updatedDate"], str)
        self.assertIsInstance(data["indexedDate"], str)

        # Check that non-datetime fields remain unchanged
        self.assertEqual(data["documentId"], "https://example.com/article")
        self.assertEqual(data["title"], "Test Article")
        self.assertEqual(data["tags"], ["test", "article"])

    def test_to_dict_removes_none_values(self):
        """Test that None values are removed from the dictionary."""
        document = Document(
            documentId="https://example.com/article",
            title="Test Article",
            content="Test content",
            sourceUrl="https://example.com/article",
            embeddings=None,
            tags=None,
        )

        data = document.to_dict()

        # Check that None values are not in the dictionary
        self.assertNotIn("embeddings", data)
        self.assertNotIn("tags", data)

        # Check that non-None values are present
        self.assertIn("documentId", data)
        self.assertIn("title", data)
        self.assertIn("content", data)
        self.assertIn("sourceUrl", data)

    def test_from_dict_converts_iso_to_datetime(self):
        """Test that ISO strings are converted back to datetime objects."""
        data = {
            "documentId": "https://example.com/article",
            "title": "Test Article",
            "content": "Test content",
            "sourceUrl": "https://example.com/article",
            "createdDate": "2024-01-01T12:00:00+00:00",
            "updatedDate": "2024-01-01T12:00:00+00:00",
            "indexedDate": "2024-01-01T12:00:00+00:00",
            "tags": ["test", "article"],
        }

        document = Document.from_dict(data)

        # Check that datetime fields are datetime objects
        self.assertIsInstance(document.createdDate, datetime)
        self.assertIsInstance(document.updatedDate, datetime)
        self.assertIsInstance(document.indexedDate, datetime)

        # Check that non-datetime fields remain unchanged
        self.assertEqual(document.documentId, "https://example.com/article")
        self.assertEqual(document.title, "Test Article")
        self.assertEqual(document.tags, ["test", "article"])

    def test_from_dict_handles_invalid_datetime(self):
        """Test that invalid datetime strings are handled gracefully."""
        data = {
            "documentId": "https://example.com/article",
            "title": "Test Article",
            "content": "Test content",
            "sourceUrl": "https://example.com/article",
            "createdDate": "invalid-date",
            "updatedDate": None,
            "indexedDate": "2024-01-01T12:00:00+00:00",
        }

        document = Document.from_dict(data)

        # Invalid datetime should be None
        self.assertIsNone(document.createdDate)
        self.assertIsNone(document.updatedDate)

        # Valid datetime should be parsed
        self.assertIsInstance(document.indexedDate, datetime)

    def test_from_dict_handles_objectid(self):
        """Test that MongoDB ObjectId is handled correctly."""
        data = {
            "documentId": "https://example.com/article",
            "title": "Test Article",
            "content": "Test content",
            "sourceUrl": "https://example.com/article",
            "_id": "507f1f77bcf86cd799439011",
        }

        document = Document.from_dict(data)

        # Check that ObjectId is properly converted
        self.assertIsInstance(document._id, ObjectId)
        self.assertEqual(str(document._id), "507f1f77bcf86cd799439011")

    def test_create_from_url(self):
        """Test creating a document from URL."""
        document = Document.create_from_url(
            url="https://example.com/article",
            title="Test Article",
            content="Test content",
            tags=["test", "article"],
            metadata={"author": "Test Author"},
        )

        self.assertEqual(document.documentId, "https://example.com/article")
        self.assertEqual(document.title, "Test Article")
        self.assertEqual(document.content, "Test content")
        self.assertEqual(document.sourceUrl, "https://example.com/article")
        self.assertEqual(document.tags, ["test", "article"])
        self.assertEqual(document.metadata, {"author": "Test Author"})
        self.assertIsInstance(document.createdDate, datetime)
        self.assertIsInstance(document.indexedDate, datetime)

    def test_create_from_rss_item(self):
        """Test creating a document from RSS feed item."""
        published_date = datetime.now(timezone.utc)
        document = Document.create_from_rss_item(
            item_url="https://example.com/article",
            title="RSS Article",
            content="<h1>RSS Content</h1>",
            feed_url="https://example.com/feed.xml",
            item_id="rss-item-123",
            author="RSS Author",
            published_date=published_date,
            tags=["rss", "article"],
        )

        self.assertEqual(document.documentId, "https://example.com/article")
        self.assertEqual(document.title, "RSS Article")
        self.assertEqual(document.content, "<h1>RSS Content</h1>")
        self.assertEqual(document.sourceUrl, "https://example.com/article")
        self.assertEqual(document.rss_feed_url, "https://example.com/feed.xml")
        self.assertEqual(document.rss_item_id, "rss-item-123")
        self.assertEqual(document.rss_title, "RSS Article")
        self.assertEqual(document.rss_author, "RSS Author")
        self.assertEqual(document.rss_published_date, published_date.isoformat())
        self.assertEqual(document.tags, ["rss", "article"])
        self.assertIsInstance(document.createdDate, datetime)
        self.assertIsInstance(document.indexedDate, datetime)

    def test_update_content(self):
        """Test updating document content."""
        original_updated = self.test_document.updatedDate

        # Update content
        new_content = "# Updated Content"
        self.test_document.update_content(new_content)

        self.assertEqual(self.test_document.content, new_content)
        self.assertGreater(self.test_document.updatedDate, original_updated)

    def test_update_embeddings(self):
        """Test updating document embeddings."""
        original_embeddings = self.test_document.embeddings
        original_updated = self.test_document.updatedDate

        # Update embeddings
        new_embeddings = [0.4, 0.5, 0.6]
        self.test_document.update_embeddings(new_embeddings)

        self.assertEqual(self.test_document.embeddings, new_embeddings)
        self.assertGreater(self.test_document.updatedDate, original_updated)

    def test_update_tags(self):
        """Test updating document tags."""
        original_tags = self.test_document.tags
        original_updated = self.test_document.updatedDate

        # Update tags
        new_tags = ["updated", "tags"]
        self.test_document.update_tags(new_tags)

        self.assertEqual(self.test_document.tags, new_tags)
        self.assertGreater(self.test_document.updatedDate, original_updated)

    def test_add_tags(self):
        """Test adding tags to existing tags."""
        original_tags = self.test_document.tags.copy()
        original_updated = self.test_document.updatedDate

        # Add tags
        new_tags = ["additional", "tags"]
        self.test_document.add_tags(new_tags)

        expected_tags = original_tags + new_tags
        self.assertEqual(self.test_document.tags, expected_tags)
        self.assertGreater(self.test_document.updatedDate, original_updated)

    def test_add_tags_to_none_tags(self):
        """Test adding tags when tags is None."""
        document = Document(
            documentId="https://example.com/article",
            title="Test Article",
            content="Test content",
            sourceUrl="https://example.com/article",
            tags=None,
        )

        # Add tags
        new_tags = ["new", "tags"]
        document.add_tags(new_tags)

        self.assertEqual(document.tags, new_tags)

    def test_search_score(self):
        """Test search score functionality."""
        document = Document(
            documentId="https://example.com/article",
            title="Test Article",
            content="Test content",
            sourceUrl="https://example.com/article",
        )

        # Initially no search score
        self.assertIsNone(document.get_search_score())

        # Set search score
        document.set_search_score(0.85)
        self.assertEqual(document.get_search_score(), 0.85)

    def test_is_rss_item(self):
        """Test RSS item detection."""
        # Regular document
        regular_doc = Document(
            documentId="https://example.com/article",
            title="Test Article",
            content="Test content",
            sourceUrl="https://example.com/article",
        )
        self.assertFalse(regular_doc.is_rss_item())

        # RSS document
        rss_doc = Document(
            documentId="https://example.com/article",
            title="RSS Article",
            content="RSS content",
            sourceUrl="https://example.com/article",
            rss_feed_url="https://example.com/feed.xml",
            rss_item_id="rss-item-123",
        )
        self.assertTrue(rss_doc.is_rss_item())

    def test_is_wordpress_item(self):
        """Test WordPress item detection."""
        # Regular document
        regular_doc = Document(
            documentId="https://example.com/article",
            title="Test Article",
            content="Test content",
            sourceUrl="https://example.com/article",
        )
        self.assertFalse(regular_doc.is_wordpress_item())

        # WordPress document
        wp_doc = Document(
            documentId="https://example.com/article",
            title="WordPress Article",
            content="WordPress content",
            sourceUrl="https://example.com/article",
            json_url="https://example.com/wp-json/wp/v2/posts/123",
        )
        self.assertTrue(wp_doc.is_wordpress_item())

    def test_get_author(self):
        """Test author retrieval from multiple sources."""
        # Document with RSS author
        rss_doc = Document(
            documentId="https://example.com/article",
            title="RSS Article",
            content="RSS content",
            sourceUrl="https://example.com/article",
            rss_author="RSS Author",
        )
        self.assertEqual(rss_doc.get_author(), "RSS Author")

        # Document with metadata author
        metadata_doc = Document(
            documentId="https://example.com/article",
            title="Metadata Article",
            content="Metadata content",
            sourceUrl="https://example.com/article",
            metadata={"author": "Metadata Author"},
        )
        self.assertEqual(metadata_doc.get_author(), "Metadata Author")

        # Document with no author
        no_author_doc = Document(
            documentId="https://example.com/article",
            title="No Author Article",
            content="No author content",
            sourceUrl="https://example.com/article",
        )
        self.assertIsNone(no_author_doc.get_author())

    def test_get_published_date(self):
        """Test published date retrieval from multiple sources."""
        # Document with RSS published date
        rss_date = datetime.now(timezone.utc)
        rss_doc = Document(
            documentId="https://example.com/article",
            title="RSS Article",
            content="RSS content",
            sourceUrl="https://example.com/article",
            rss_published_date=rss_date.isoformat(),
        )
        self.assertEqual(rss_doc.get_published_date(), rss_date)

        # Document with created date
        created_date = datetime.now(timezone.utc)
        created_doc = Document(
            documentId="https://example.com/article",
            title="Created Article",
            content="Created content",
            sourceUrl="https://example.com/article",
            createdDate=created_date,
        )
        self.assertEqual(created_doc.get_published_date(), created_date)

        # Document with no dates
        no_date_doc = Document(
            documentId="https://example.com/article",
            title="No Date Article",
            content="No date content",
            sourceUrl="https://example.com/article",
        )
        self.assertIsNone(no_date_doc.get_published_date())


if __name__ == "__main__":
    unittest.main()
