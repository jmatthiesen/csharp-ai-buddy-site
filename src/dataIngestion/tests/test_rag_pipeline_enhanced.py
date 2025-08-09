#!/usr/bin/env python3
"""
Unit tests for Document Pipeline functionality.
Tests document processing with various input sources including pre-parsed content.
"""

import json
import unittest
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

# Configuration
from config import Config
from document import Document
# Pipeline components
from document_pipeline import DocumentPipeline
from web_page_retriever import WebPageRetriever


class TestDocumentPipeline(unittest.TestCase):
    """Test Document Pipeline functionality."""

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
        self.mock_documents_collection = Mock()

        # Mock MongoDB database
        self.mock_db = MagicMock()
        self.mock_db.__getitem__.return_value = self.mock_documents_collection

        # Mock MongoDB client
        self.mock_mongo_client = MagicMock()
        self.mock_mongo_client.__getitem__.return_value = self.mock_db

        # Mock OpenAI client
        self.mock_openai_client = Mock()
        self.mock_embedding_response = Mock()
        self.mock_embedding_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        self.mock_openai_client.embeddings.create.return_value = self.mock_embedding_response

        # Mock MarkItDown
        self.mock_markitdown = Mock()
        self.mock_markitdown.convert.return_value = Mock(
            markdown="# Test Markdown\n\nThis is test content."
        )

        # Mock web page responses
        self.mock_web_response = Mock()
        self.mock_web_response.text = "<html><head><title>Test Page</title></head><body><h1>Test Content</h1><p>Test paragraph</p></body></html>"
        self.mock_web_response.raise_for_status.return_value = None

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_process_document_with_pre_parsed_content(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test processing a document with pre-parsed HTML content."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        # Mock successful document insertion
        mock_result = Mock()
        mock_result.inserted_id = "test-doc-123"
        self.mock_documents_collection.insert_one.return_value = mock_result

        pipeline = DocumentPipeline(self.mock_config)

        # Create a document with pre-parsed content
        pre_parsed_content = "<h1>Test Article</h1><p>This is the full article content.</p>"
        document = Document(
            documentId="https://example.com/article",
            title="Test Article",
            content=pre_parsed_content,
            sourceUrl="https://example.com/article",
            tags=["test", "article"],
        )

        # Process the document
        processed_doc = pipeline.process_document(
            document=document,
            use_ai_categorization=False,
            additional_metadata={"author": "Test Author"},
        )

        # Store the document
        doc_id = pipeline.store_document(processed_doc)

        self.assertEqual(doc_id, "https://example.com/article")

        # Verify document was processed and stored correctly
        self.mock_documents_collection.insert_one.assert_called_once()
        inserted_doc = self.mock_documents_collection.insert_one.call_args[0][0]

        # Check that the pre-parsed content was used
        self.assertEqual(inserted_doc["content"], pre_parsed_content)
        self.assertEqual(inserted_doc["sourceUrl"], "https://example.com/article")
        self.assertEqual(inserted_doc["tags"], ["test", "article"])

        # Verify embeddings were generated
        self.mock_openai_client.embeddings.create.assert_called_once()

        # Verify markdown conversion was called
        self.mock_markitdown.convert.assert_called_once()

    @patch("web_page_retriever.requests")
    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_fetch_and_process_document_from_url(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class, mock_requests
    ):
        """Test fetching a document from URL and processing it through the pipeline."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown
        mock_requests.get.return_value = self.mock_web_response

        # Mock successful document insertion
        mock_result = Mock()
        mock_result.inserted_id = "test-doc-123"
        self.mock_documents_collection.insert_one.return_value = mock_result

        # Create components
        web_retriever = WebPageRetriever()
        pipeline = DocumentPipeline(self.mock_config)

        # Fetch document from URL
        document = web_retriever.fetch("https://example.com/article")

        # Add tags
        document.tags = ["test", "article"]

        # Process through pipeline
        processed_doc = pipeline.process_document(
            document=document,
            use_ai_categorization=False,
            additional_metadata={"author": "Test Author"},
        )

        # Store document
        doc_id = pipeline.store_document(processed_doc)

        self.assertEqual(doc_id, "https://example.com/article")

        # Verify web request was made
        mock_requests.get.assert_called_once_with("https://example.com/article", timeout=10)

        # Verify document was processed and stored
        self.mock_documents_collection.insert_one.assert_called_once()
        inserted_doc = self.mock_documents_collection.insert_one.call_args[0][0]

        # Check document properties
        self.assertEqual(inserted_doc["sourceUrl"], "https://example.com/article")
        self.assertEqual(inserted_doc["tags"], ["test", "article"])

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_process_document_with_empty_content(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test processing a document with empty content."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        # Mock empty markdown conversion
        mock_markitdown_empty = Mock()
        mock_markitdown_empty.convert.return_value = Mock(markdown="")
        mock_markitdown_class.return_value = mock_markitdown_empty

        # Mock successful document insertion
        mock_result = Mock()
        mock_result.inserted_id = "test-doc-123"
        self.mock_documents_collection.insert_one.return_value = mock_result

        pipeline = DocumentPipeline(self.mock_config)

        # Create document with empty content
        document = Document(
            documentId="https://example.com/article",
            title="Test Article",
            content="",  # Empty content
            sourceUrl="https://example.com/article",
            tags=["test", "article"],
        )

        # Process the document
        processed_doc = pipeline.process_document(document, use_ai_categorization=False)

        # Store document
        doc_id = pipeline.store_document(processed_doc)

        self.assertEqual(doc_id, "https://example.com/article")

        # Verify document was processed
        self.mock_documents_collection.insert_one.assert_called_once()
        inserted_doc = self.mock_documents_collection.insert_one.call_args[0][0]

        # Check that empty content was handled
        self.assertEqual(inserted_doc["content"], "")

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_process_document_with_ai_categorization(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test processing a document with AI categorization enabled."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        # Mock AI categorization
        with patch("document_pipeline.categorize_document") as mock_categorize_ai:
            mock_categorize_ai.return_value = ["csharp", "dotnet"]

            # Mock successful document insertion
            mock_result = Mock()
            mock_result.inserted_id = "test-doc-123"
            self.mock_documents_collection.insert_one.return_value = mock_result

            pipeline = DocumentPipeline(self.mock_config)

            # Create document with C# content
            document = Document(
                documentId="https://example.com/csharp-article",
                title="C# Article",
                content="<h1>C# Article</h1><p>This is about C# and .NET.</p>",
                sourceUrl="https://example.com/csharp-article",
                tags=["article"],  # Initial tags
            )

            # Process with AI categorization
            processed_doc = pipeline.process_document(
                document=document,
                use_ai_categorization=True,
                additional_metadata={"author": "Test Author"},
            )

            # Store document
            doc_id = pipeline.store_document(processed_doc)

            self.assertEqual(doc_id, "https://example.com/csharp-article")

            # Verify AI categorization was called
            mock_categorize_ai.assert_called_once()

            # Verify document was stored with combined tags
            self.mock_documents_collection.insert_one.assert_called_once()
            inserted_doc = self.mock_documents_collection.insert_one.call_args[0][0]
            self.assertEqual(inserted_doc["tags"], ["article", "csharp", "dotnet"])

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_store_document_duplicate_key_error(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test handling of duplicate key error when storing document."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        # Mock duplicate key error
        from pymongo.errors import DuplicateKeyError

        self.mock_documents_collection.insert_one.side_effect = DuplicateKeyError("Duplicate key")

        pipeline = DocumentPipeline(self.mock_config)

        document = Document(
            documentId="https://example.com/article",
            title="Test Article",
            content="<h1>Test Content</h1>",
            sourceUrl="https://example.com/article",
        )

        # Test storing document that already exists
        with self.assertRaises(DuplicateKeyError):
            pipeline.store_document(document)


if __name__ == "__main__":
    unittest.main()
