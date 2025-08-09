#!/usr/bin/env python3
"""
Unit tests for WebPageRetriever functionality.
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from web_page_retriever import WebPageRetriever


class TestWebPageRetriever(unittest.TestCase):
    """Test WebPageRetriever functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.retriever = WebPageRetriever()

        # Mock web response
        self.mock_response = Mock()
        self.mock_response.text = (
            "<html><head><title>Test Page</title></head><body><h1>Test Content</h1></body></html>"
        )
        self.mock_response.raise_for_status.return_value = None

    @patch("web_page_retriever.requests")
    def test_fetch_simple_html_page(self, mock_requests):
        """Test fetching a simple HTML page."""
        # Setup mock
        mock_requests.get.return_value = self.mock_response

        # Fetch document
        document = self.retriever.fetch("https://example.com/test")

        # Verify request was made
        mock_requests.get.assert_called_once_with("https://example.com/test", timeout=10)

        # Verify document properties
        self.assertEqual(document.documentId, "https://example.com/test")
        self.assertEqual(document.sourceUrl, "https://example.com/test")
        self.assertEqual(document.title, "Test Page")
        self.assertEqual(document.content, self.mock_response.text)

    @patch("web_page_retriever.requests")
    def test_fetch_wordpress_json_api(self, mock_requests):
        """Test fetching from WordPress with JSON API."""
        # Setup HTML response with JSON API link
        html_response = Mock()
        html_response.text = """
        <html>
        <head>
            <title>WordPress Post</title>
            <link rel="alternate" type="application/json" href="/wp-json/wp/v2/posts/123">
        </head>
        <body><h1>WordPress Content</h1></body>
        </html>
        """
        html_response.raise_for_status.return_value = None

        # Setup JSON API response
        json_response = Mock()
        json_response.json.return_value = {
            "title": {"rendered": "WordPress Article"},
            "content": {"rendered": "<h1>Rich Content</h1><p>Article content here.</p>"},
            "date_gmt": "2024-01-01T12:00:00",
            "modified_gmt": "2024-01-02T12:00:00",
        }
        json_response.raise_for_status.return_value = None

        # Mock requests to return different responses
        mock_requests.get.side_effect = [html_response, json_response]

        # Fetch document
        document = self.retriever.fetch("https://example.com/post")

        # Verify requests were made
        self.assertEqual(mock_requests.get.call_count, 2)
        mock_requests.get.assert_any_call("https://example.com/post", timeout=10)
        mock_requests.get.assert_any_call("https://example.com/wp-json/wp/v2/posts/123", timeout=10)

        # Verify document properties from JSON API
        self.assertEqual(document.documentId, "https://example.com/post")
        self.assertEqual(document.title, "WordPress Article")
        self.assertEqual(document.content, "<h1>Rich Content</h1><p>Article content here.</p>")
        self.assertEqual(document.json_url, "https://example.com/wp-json/wp/v2/posts/123")
        self.assertIsInstance(document.createdDate, datetime)
        self.assertIsInstance(document.updatedDate, datetime)

    @patch("web_page_retriever.requests")
    def test_fetch_non_http_url(self, mock_requests):
        """Test fetching from non-HTTP URL returns empty document."""
        # Fetch document from non-HTTP URL
        document = self.retriever.fetch("file:///local/file.txt")

        # Verify no HTTP request was made
        mock_requests.get.assert_not_called()

        # Verify empty document was returned
        self.assertEqual(document.documentId, "file:///local/file.txt")
        self.assertEqual(document.sourceUrl, "file:///local/file.txt")
        self.assertEqual(document.content, "")
        self.assertEqual(document.title, "")

    @patch("web_page_retriever.requests")
    def test_fetch_request_error(self, mock_requests):
        """Test handling of HTTP request errors."""
        # Setup mock to raise exception
        mock_requests.get.side_effect = Exception("Network error")

        # Fetch document
        document = self.retriever.fetch("https://example.com/error")

        # Verify request was attempted
        mock_requests.get.assert_called_once_with("https://example.com/error", timeout=10)

        # Verify empty document was returned on error
        self.assertEqual(document.documentId, "https://example.com/error")
        self.assertEqual(document.sourceUrl, "https://example.com/error")
        self.assertEqual(document.content, "")
        self.assertEqual(document.title, "")

    @patch("web_page_retriever.requests")
    def test_fetch_json_api_error_fallback(self, mock_requests):
        """Test fallback to HTML when JSON API fails."""
        # Setup HTML response with JSON API link
        html_response = Mock()
        html_response.text = """
        <html>
        <head><title>Test Page</title>
        <link rel="alternate" type="application/json" href="/api/post/123">
        </head>
        <body><h1>HTML Content</h1></body>
        </html>
        """
        html_response.raise_for_status.return_value = None

        # Setup JSON API to fail
        def side_effect(url, timeout):
            if url.endswith("/api/post/123"):
                raise Exception("JSON API error")
            return html_response

        mock_requests.get.side_effect = side_effect

        # Fetch document
        document = self.retriever.fetch("https://example.com/post")

        # Verify fallback to HTML content
        self.assertEqual(document.documentId, "https://example.com/post")
        self.assertEqual(document.title, "Test Page")
        self.assertEqual(document.content, html_response.text)
        self.assertIsNone(document.json_url)

    @patch("web_page_retriever.requests")
    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_fetch_and_process_document_integration(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class, mock_requests
    ):
        """Test integration of web page retrieval with document pipeline processing."""
        from config import Config
        from document_pipeline import DocumentPipeline

        # Setup mocks for pipeline
        mock_config = Mock(spec=Config)
        mock_config.mongodb_connection_string = "mongodb://localhost:27017"
        mock_config.mongodb_database = "test_db"
        mock_config.mongodb_collection = "test_collection"
        mock_config.openai_api_key = "test-key"
        mock_config.embedding_model = "text-embedding-3-small"

        # Mock MongoDB components
        mock_documents_collection = Mock()
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_documents_collection
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        # Mock OpenAI client
        mock_openai_client = Mock()
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_openai_client.embeddings.create.return_value = mock_embedding_response
        mock_openai_class.return_value = mock_openai_client

        # Mock MarkItDown
        mock_markitdown = Mock()
        mock_markitdown.convert.return_value = Mock(
            markdown="# Test Markdown\n\nThis is test content."
        )
        mock_markitdown_class.return_value = mock_markitdown

        # Mock web response
        mock_response = Mock()
        mock_response.text = "<html><head><title>Integration Test</title></head><body><h1>Test Content</h1></body></html>"
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response

        # Mock successful document insertion
        mock_result = Mock()
        mock_result.inserted_id = "test-doc-123"
        mock_documents_collection.insert_one.return_value = mock_result

        # Create components
        web_retriever = WebPageRetriever()
        pipeline = DocumentPipeline(mock_config)

        # Fetch document from URL
        document = web_retriever.fetch("https://example.com/integration-test")

        # Add tags
        document.tags = ["integration", "test"]

        # Process through pipeline
        processed_doc = pipeline.process_document(
            document=document,
            use_ai_categorization=False,
            additional_metadata={"test_type": "integration"},
        )

        # Store document
        doc_id = pipeline.store_document(processed_doc)

        # Verify integration worked correctly
        self.assertEqual(doc_id, "https://example.com/integration-test")

        # Verify web request was made
        mock_requests.get.assert_called_once_with(
            "https://example.com/integration-test", timeout=10
        )

        # Verify document processing steps
        mock_markitdown.convert.assert_called_once()
        mock_openai_client.embeddings.create.assert_called_once()

        # Verify document was stored
        mock_documents_collection.insert_one.assert_called_once()
        stored_doc = mock_documents_collection.insert_one.call_args[0][0]

        # Check integrated document properties
        self.assertEqual(stored_doc["documentId"], "https://example.com/integration-test")
        self.assertEqual(stored_doc["title"], "Integration Test")
        self.assertEqual(stored_doc["tags"], ["integration", "test"])
        self.assertEqual(stored_doc["metadata"]["test_type"], "integration")


if __name__ == "__main__":
    unittest.main()
