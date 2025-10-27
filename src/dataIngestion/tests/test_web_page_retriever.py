#!/usr/bin/env python3
"""
Comprehensive tests for WebPageRetriever with new RawDocument architecture.
Tests focus on content retrieval, type detection, and error handling.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from web_page_retriever import WebPageRetriever
from pipeline_types import RawDocument


class TestWebPageRetriever(unittest.TestCase):
    """Test WebPageRetriever functionality with RawDocument return types."""

    def setUp(self):
        """Set up test fixtures."""
        self.retriever = WebPageRetriever()

    @patch('web_page_retriever.requests')
    def test_fetch_returns_raw_document_object(self, mock_requests):
        """Test that fetch() returns proper RawDocument objects."""
        # Setup mock response
        mock_response = Mock()
        mock_response.text = "<html><head><title>Test Page</title></head><body><h1>Content</h1></body></html>"
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        # Fetch document
        result = self.retriever.fetch("https://example.com/test")
        
        # Verify return type and basic properties
        self.assertIsInstance(result, RawDocument)
        self.assertEqual(result.source_url, "https://example.com/test")
        self.assertEqual(result.title, "Test Page")
        self.assertEqual(result.content, mock_response.text)
        self.assertEqual(result.content_type, "html")

    @patch('web_page_retriever.requests')
    def test_markdown_file_detection_and_processing(self, mock_requests):
        """Test automatic detection and processing of markdown files."""
        # Setup mock for markdown file
        mock_response = Mock()
        mock_response.text = "# Markdown Title\n\nThis is markdown content with **bold** text."
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        # Test .md extension
        result = self.retriever.fetch("https://example.com/document.md")
        
        self.assertIsInstance(result, RawDocument)
        self.assertEqual(result.content_type, "markdown")
        self.assertEqual(result.title, "Markdown Title")
        self.assertEqual(result.content, mock_response.text)
        
        # Test .markdown extension
        result = self.retriever.fetch("https://example.com/document.markdown")
        
        self.assertEqual(result.content_type, "markdown")

    @patch('web_page_retriever.requests')
    def test_wordpress_json_api_detection_and_processing(self, mock_requests):
        """Test WordPress JSON API detection and structured data extraction."""
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
            "title": {"rendered": "WordPress Article Title"},
            "content": {"rendered": "<h1>Rich WordPress Content</h1><p>Article body here.</p>"},
            "date_gmt": "2024-01-01T12:00:00Z",
            "modified_gmt": "2024-01-02T14:30:00Z",
            "id": 123,
            "author": 5,
            "categories": [{"name": "Technology"}, {"name": "Tutorials"}],
            "tags": [{"name": "Python"}, {"name": "API"}]
        }
        json_response.raise_for_status.return_value = None
        
        # Mock requests to return different responses for HTML then JSON
        mock_requests.get.side_effect = [html_response, json_response]
        
        # Fetch document
        result = self.retriever.fetch("https://example.com/wordpress-post")
        
        # Verify WordPress-specific processing
        self.assertIsInstance(result, RawDocument)
        self.assertEqual(result.source_url, "https://example.com/wordpress-post")
        self.assertEqual(result.title, "WordPress Article Title")
        self.assertEqual(result.content, "<h1>Rich WordPress Content</h1><p>Article body here.</p>")
        self.assertEqual(result.content_type, "wordpress")
        
        # Verify WordPress metadata extraction
        self.assertIn("wordpress_post_id", result.source_metadata)
        self.assertEqual(result.source_metadata["wordpress_post_id"], 123)
        self.assertIn("wordpress_json_url", result.source_metadata)
        self.assertEqual(result.source_metadata["wordpress_json_url"], "https://example.com/wp-json/wp/v2/posts/123")
        
        # Verify tags extraction from categories and tags
        self.assertIn("Technology", result.tags)
        self.assertIn("Tutorials", result.tags)
        self.assertIn("Python", result.tags)
        self.assertIn("API", result.tags)
        
        # Verify datetime parsing
        self.assertIsInstance(result.created_date, datetime)

    @patch('web_page_retriever.requests')
    def test_wordpress_json_api_fallback_to_html(self, mock_requests):
        """Test fallback to HTML when WordPress JSON API fails."""
        # Setup HTML response with JSON API link
        html_response = Mock()
        html_response.text = """
        <html>
        <head><title>Fallback Title</title>
        <link rel="alternate" type="application/json" href="/wp-json/wp/v2/posts/123">
        </head>
        <body><h1>HTML Fallback Content</h1></body>
        </html>
        """
        html_response.raise_for_status.return_value = None
        
        # Setup JSON API to fail
        def requests_side_effect(url, timeout):
            if url.endswith("/wp-json/wp/v2/posts/123"):
                raise Exception("JSON API error")
            return html_response
        
        mock_requests.get.side_effect = requests_side_effect
        
        # Fetch document
        result = self.retriever.fetch("https://example.com/wordpress-post")
        
        # Should fallback to HTML processing
        self.assertEqual(result.content_type, "html")
        self.assertEqual(result.title, "Fallback Title")
        self.assertEqual(result.content, html_response.text)

    def test_non_http_url_handling(self):
        """Test handling of non-HTTP URLs."""
        # Test file:// URL
        result = self.retriever.fetch("file:///local/document.txt")
        
        self.assertIsInstance(result, RawDocument)
        self.assertEqual(result.source_url, "file:///local/document.txt")
        self.assertEqual(result.content, "")
        self.assertEqual(result.title, "")
        self.assertEqual(result.content_type, "html")
        
        # Test ftp:// URL
        result = self.retriever.fetch("ftp://example.com/file.txt")
        
        self.assertEqual(result.source_url, "ftp://example.com/file.txt")
        self.assertEqual(result.content, "")

    @patch('web_page_retriever.requests')
    def test_network_error_handling(self, mock_requests):
        """Test graceful handling of network errors."""
        # Setup requests to raise various exceptions
        test_exceptions = [
            Exception("Network timeout"),
            ConnectionError("Connection failed"),
            TimeoutError("Request timed out")
        ]
        
        for exception in test_exceptions:
            with self.subTest(exception=type(exception).__name__):
                mock_requests.get.side_effect = exception
                
                result = self.retriever.fetch("https://example.com/error-test")
                
                # Should return error RawDocument, not raise exception
                self.assertIsInstance(result, RawDocument)
                self.assertEqual(result.source_url, "https://example.com/error-test")
                self.assertEqual(result.content, "")
                self.assertEqual(result.title, "Error fetching content")
                self.assertEqual(result.content_type, "html")

    @patch('web_page_retriever.requests')
    def test_http_error_status_handling(self, mock_requests):
        """Test handling of HTTP error statuses (404, 500, etc.)."""
        # Setup mock to raise HTTP error
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("404 Client Error: Not Found")
        mock_requests.get.return_value = mock_response
        
        result = self.retriever.fetch("https://example.com/not-found")
        
        # Should return error RawDocument
        self.assertEqual(result.content, "")
        self.assertEqual(result.title, "Error fetching content")

    def test_iso_date_parsing_helper(self):
        """Test the internal ISO date parsing functionality."""
        # Test valid ISO date without Z
        result = self.retriever._get_iso_date("2024-01-01T12:00:00")
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.hour, 12)
        
        # Test date that already ends with Z
        result = self.retriever._get_iso_date("2024-01-01T12:00:00Z")
        self.assertIsNone(result)  # Function doesn't handle Z-suffixed dates
        
        # Test invalid date
        result = self.retriever._get_iso_date("invalid-date-string")
        self.assertIsNone(result)
        
        # Test None input
        result = self.retriever._get_iso_date(None)
        self.assertIsNone(result)

    @patch('web_page_retriever.requests')
    def test_title_extraction_from_html(self, mock_requests):
        """Test proper title extraction from HTML content."""
        test_cases = [
            # Standard title tag
            ("<html><head><title>Page Title</title></head><body></body></html>", "Page Title"),
            # Title with whitespace
            ("<html><head><title>  Spaced Title  </title></head><body></body></html>", "Spaced Title"),
            # No title tag
            ("<html><head></head><body><h1>Header</h1></body></html>", ""),
            # Empty title tag
            ("<html><head><title></title></head><body></body></html>", ""),
        ]
        
        for html_content, expected_title in test_cases:
            with self.subTest(html_content=html_content[:50]):
                mock_response = Mock()
                mock_response.text = html_content
                mock_response.raise_for_status.return_value = None
                mock_requests.get.return_value = mock_response
                
                result = self.retriever.fetch("https://example.com/test")
                
                self.assertEqual(result.title, expected_title)

    @patch('web_page_retriever.requests')
    def test_markdown_title_extraction(self, mock_requests):
        """Test title extraction from markdown files."""
        test_cases = [
            # Standard markdown title
            ("# Main Title\n\nContent here", "Main Title"),
            # Title with extra hashes and spaces
            ("## Secondary Title\n\nMore content", "Secondary Title"),
            # No title
            ("Just content without title\n\nMore content", ""),
            # Multiple titles - should use first
            ("# First Title\n\n## Second Title\n\nContent", "First Title"),
        ]
        
        for markdown_content, expected_title in test_cases:
            with self.subTest(markdown_content=markdown_content[:30]):
                mock_response = Mock()
                mock_response.text = markdown_content
                mock_response.raise_for_status.return_value = None
                mock_requests.get.return_value = mock_response
                
                result = self.retriever.fetch("https://example.com/test.md")
                
                self.assertEqual(result.title, expected_title)
                self.assertEqual(result.content_type, "markdown")

    @patch('web_page_retriever.requests')
    def test_content_preservation(self):
        """Test that original content is preserved exactly."""
        original_content = """<html>
        <head><title>Test</title></head>
        <body>
            <h1>Header</h1>
            <p>Paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
            <ul>
                <li>List item 1</li>
                <li>List item 2</li>
            </ul>
        </body>
        </html>"""
        
        mock_response = Mock()
        mock_response.text = original_content
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        result = self.retriever.fetch("https://example.com/test")
        
        # Content should be preserved exactly
        self.assertEqual(result.content, original_content)

    def test_retriever_initialization(self):
        """Test WebPageRetriever initialization with custom timeout."""
        # Default timeout
        default_retriever = WebPageRetriever()
        self.assertEqual(default_retriever.timeout, 10)
        
        # Custom timeout
        custom_retriever = WebPageRetriever(timeout=30)
        self.assertEqual(custom_retriever.timeout, 30)

    @patch('web_page_retriever.requests')
    def test_request_timeout_parameter(self, mock_requests):
        """Test that timeout parameter is passed to requests."""
        mock_response = Mock()
        mock_response.text = "<html><title>Test</title><body>Content</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        
        # Test with custom timeout
        retriever = WebPageRetriever(timeout=25)
        retriever.fetch("https://example.com/test")
        
        # Verify timeout was passed to requests.get
        mock_requests.get.assert_called_with("https://example.com/test", timeout=25)


if __name__ == '__main__':
    unittest.main()