"""
Unit tests for the news API endpoint.
Tests verify that news items are sorted correctly from newest to oldest.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import os

# Import the app from the parent package
from ..main import app

client = TestClient(app)


class TestNewsSorting:
    """Test cases for news API sorting functionality."""
    
    @patch('routers.news.MongoClient')
    @patch.dict(os.environ, {
        'MONGODB_URI': 'mongodb://test',
        'DATABASE_NAME': 'test_db'
    })
    def test_news_sorted_newest_first(self, mock_mongo_client):
        """Test that news items are returned sorted by date, newest first."""
        # Setup mock MongoDB
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_mongo_client.return_value = mock_client
        
        # Create test data with different dates
        test_news = [
            {
                "_id": "1",
                "documentId": "doc1",
                "title": "Newest Article",
                "content": "This is the newest article",
                "summary": "Newest article summary",
                "publishedDate": "2024-01-15T10:00:00Z",
                "indexedDate": "2024-01-15T10:00:00Z",
                "createdDate": "2024-01-15T10:00:00Z",
                "sourceUrl": "http://example.com/1",
                "rss_feed_url": "http://example.com/feed",
                "rss_author": "Author 1"
            },
            {
                "_id": "2",
                "documentId": "doc2",
                "title": "Middle Article",
                "content": "This is a middle article",
                "summary": "Middle article summary",
                "publishedDate": "2024-01-10T10:00:00Z",
                "indexedDate": "2024-01-10T10:00:00Z",
                "createdDate": "2024-01-10T10:00:00Z",
                "sourceUrl": "http://example.com/2",
                "rss_feed_url": "http://example.com/feed",
                "rss_author": "Author 2"
            },
            {
                "_id": "3",
                "documentId": "doc3",
                "title": "Oldest Article",
                "content": "This is the oldest article",
                "summary": "Oldest article summary",
                "publishedDate": "2024-01-05T10:00:00Z",
                "indexedDate": "2024-01-05T10:00:00Z",
                "createdDate": "2024-01-05T10:00:00Z",
                "sourceUrl": "http://example.com/3",
                "rss_feed_url": "http://example.com/feed",
                "rss_author": "Author 3"
            }
        ]
        
        # Setup mock collection behavior
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__ = MagicMock(return_value=iter(test_news))
        
        mock_sort = MagicMock(return_value=mock_cursor)
        mock_find = MagicMock(return_value=MagicMock(sort=mock_sort))
        mock_collection.find = mock_find
        mock_collection.count_documents = MagicMock(return_value=3)
        
        # Make the request
        response = client.get("/api/news?page=1&page_size=20")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify sorting was called with correct parameters
        mock_sort.assert_called_once()
        sort_args = mock_sort.call_args[0][0]
        
        # Verify sort order: publishedDate descending (-1), then indexedDate descending (-1)
        assert sort_args == [("publishedDate", -1), ("indexedDate", -1)], \
            f"Expected sort by [('publishedDate', -1), ('indexedDate', -1)], got {sort_args}"
        
        # Verify the response contains news items
        assert "news" in data
        assert len(data["news"]) == 3
        
        # Verify the order is newest to oldest based on the returned data
        news_dates = [item["published_date"] for item in data["news"]]
        assert news_dates[0] >= news_dates[1] >= news_dates[2], \
            "News items should be sorted from newest to oldest"
    
    @patch('routers.news.MongoClient')
    @patch.dict(os.environ, {
        'MONGODB_URI': 'mongodb://test',
        'DATABASE_NAME': 'test_db'
    })
    def test_rss_feed_sorted_newest_first(self, mock_mongo_client):
        """Test that RSS feed items are also sorted by date, newest first."""
        # Setup mock MongoDB
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_mongo_client.return_value = mock_client
        
        # Create test data
        test_news = [
            {
                "_id": "1",
                "documentId": "doc1",
                "title": "Newest RSS Item",
                "content": "Newest content",
                "publishedDate": "2024-01-15T10:00:00Z",
                "indexedDate": "2024-01-15T10:00:00Z",
                "createdDate": "2024-01-15T10:00:00Z",
                "sourceUrl": "http://example.com/1",
                "rss_feed_url": "http://example.com/feed",
                "rss_item_id": "item1"
            }
        ]
        
        # Setup mock collection behavior
        mock_cursor = MagicMock()
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__ = MagicMock(return_value=iter(test_news))
        
        mock_sort = MagicMock(return_value=mock_cursor)
        mock_find = MagicMock(return_value=MagicMock(sort=mock_sort))
        mock_collection.find = mock_find
        
        # Make the request
        response = client.get("/api/news/rss")
        
        # Verify sorting was called with correct parameters for RSS feed
        mock_sort.assert_called_once()
        sort_args = mock_sort.call_args[0][0]
        
        # Verify sort order matches the main news endpoint
        assert sort_args == [("publishedDate", -1), ("indexedDate", -1)], \
            f"RSS feed should use same sort order as news endpoint, got {sort_args}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
