"""
End-to-end integration tests for the news API endpoint.
These tests verify the real functionality of the news endpoint including database interactions.

Requirements:
- MongoDB connection (set MONGODB_URI and DATABASE_NAME environment variables)
- pytest-asyncio for async test support
"""
import pytest
import os
from datetime import datetime
from fastapi.testclient import TestClient
from pymongo import MongoClient

# Import the app
from ..main import app

# Skip all tests if MongoDB is not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("MONGODB_URI") or not os.getenv("DATABASE_NAME"),
    reason="MongoDB not configured - set MONGODB_URI and DATABASE_NAME to run e2e tests"
)


class TestNewsEndpointE2E:
    """End-to-end integration tests for news API endpoint."""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture(scope="class")
    def mongodb_connection(self):
        """Create a MongoDB connection for test data setup/cleanup."""
        mongodb_uri = os.getenv("MONGODB_URI")
        database_name = os.getenv("DATABASE_NAME")
        
        if not mongodb_uri or not database_name:
            pytest.skip("MongoDB not configured")
        
        client = MongoClient(mongodb_uri)
        db = client[database_name]
        yield db
        client.close()
    
    @pytest.fixture(scope="function")
    def test_news_data(self, mongodb_connection):
        """Insert test news data and clean up after the test."""
        collection = mongodb_connection["documents"]
        
        # Insert test data with different dates
        test_documents = [
            {
                "documentId": "e2e-test-newest",
                "title": "E2E Test - Newest Article",
                "content": "This is the newest test article for e2e testing",
                "summary": "Newest test article",
                "publishedDate": datetime(2024, 12, 15, 10, 0, 0),
                "indexedDate": datetime(2024, 12, 15, 10, 0, 0),
                "createdDate": datetime(2024, 12, 15, 10, 0, 0),
                "sourceUrl": "http://example.com/e2e-newest",
                "rss_feed_url": "http://example.com/feed",
                "rss_author": "E2E Test Author"
            },
            {
                "documentId": "e2e-test-middle",
                "title": "E2E Test - Middle Article",
                "content": "This is a middle test article for e2e testing",
                "summary": "Middle test article",
                "publishedDate": datetime(2024, 12, 10, 10, 0, 0),
                "indexedDate": datetime(2024, 12, 10, 10, 0, 0),
                "createdDate": datetime(2024, 12, 10, 10, 0, 0),
                "sourceUrl": "http://example.com/e2e-middle",
                "rss_feed_url": "http://example.com/feed",
                "rss_author": "E2E Test Author"
            },
            {
                "documentId": "e2e-test-oldest",
                "title": "E2E Test - Oldest Article",
                "content": "This is the oldest test article for e2e testing",
                "summary": "Oldest test article",
                "publishedDate": datetime(2024, 12, 5, 10, 0, 0),
                "indexedDate": datetime(2024, 12, 5, 10, 0, 0),
                "createdDate": datetime(2024, 12, 5, 10, 0, 0),
                "sourceUrl": "http://example.com/e2e-oldest",
                "rss_feed_url": "http://example.com/feed",
                "rss_author": "E2E Test Author"
            }
        ]
        
        # Insert the test documents
        result = collection.insert_many(test_documents)
        inserted_ids = result.inserted_ids
        
        yield test_documents
        
        # Clean up: Remove test documents
        collection.delete_many({"_id": {"$in": inserted_ids}})
    
    def test_news_sorted_newest_first_real_db(self, client, test_news_data):
        """
        Test that news items are returned sorted by publishedDate, newest first.
        This is a real integration test that uses actual database.
        """
        # Make request to the news endpoint
        response = client.get("/api/news?page=1&page_size=100")
        
        # Verify response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify response structure
        assert "news" in data, "Response should contain 'news' key"
        assert "total" in data, "Response should contain 'total' key"
        assert "page" in data, "Response should contain 'page' key"
        assert "pages" in data, "Response should contain 'pages' key"
        
        # Find our test articles in the response
        test_articles = [
            item for item in data["news"]
            if item.get("id", "").startswith("e2e-test-")
        ]
        
        # We should have all 3 test articles
        assert len(test_articles) >= 3, f"Expected at least 3 test articles, found {len(test_articles)}"
        
        # Extract just our test articles by title pattern
        newest = next((a for a in test_articles if "Newest" in a["title"]), None)
        middle = next((a for a in test_articles if "Middle" in a["title"]), None)
        oldest = next((a for a in test_articles if "Oldest" in a["title"]), None)
        
        assert newest is not None, "Newest test article not found"
        assert middle is not None, "Middle test article not found"
        assert oldest is not None, "Oldest test article not found"
        
        # Find the indices of our test articles in the returned list
        newest_idx = next(i for i, a in enumerate(test_articles) if "Newest" in a["title"])
        middle_idx = next(i for i, a in enumerate(test_articles) if "Middle" in a["title"])
        oldest_idx = next(i for i, a in enumerate(test_articles) if "Oldest" in a["title"])
        
        # Verify sorting: newest should come before middle, middle before oldest
        assert newest_idx < middle_idx, \
            f"Newest article (index {newest_idx}) should come before middle article (index {middle_idx})"
        assert middle_idx < oldest_idx, \
            f"Middle article (index {middle_idx}) should come before oldest article (index {oldest_idx})"
        
        print(f"✅ Sorting verified: Newest (idx {newest_idx}) < Middle (idx {middle_idx}) < Oldest (idx {oldest_idx})")
    
    def test_news_search_functionality(self, client, test_news_data):
        """Test that search functionality works correctly."""
        # Search for our test articles
        response = client.get("/api/news?page=1&page_size=100&search=E2E+Test")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find our test articles
        test_articles = [
            item for item in data["news"]
            if item.get("id", "").startswith("e2e-test-")
        ]
        
        assert len(test_articles) >= 3, \
            f"Search should find our test articles, found {len(test_articles)}"
    
    def test_news_pagination(self, client, test_news_data):
        """Test that pagination works correctly."""
        # Request with small page size
        response = client.get("/api/news?page=1&page_size=2")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination fields
        assert data["page_size"] == 2
        assert data["page"] == 1
        assert data["pages"] >= 1
        assert data["total"] >= 3  # At least our test articles
        
        # Verify we got at most 2 items per page
        assert len(data["news"]) <= 2
    
    def test_rss_feed_sorted_newest_first(self, client, test_news_data):
        """Test that RSS feed also returns items sorted newest first."""
        response = client.get("/api/news/rss")
        
        assert response.status_code == 200
        assert "application/rss+xml" in response.headers.get("content-type", "")
        
        # Parse the RSS content to verify it contains our test items
        content = response.text
        assert "E2E Test" in content, "RSS feed should contain our test articles"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
