#!/usr/bin/env python3
"""
Unit tests for DocumentPipeline functionality.
"""

import unittest
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock, Mock, patch

from config import Config
from document import Document
from document_pipeline import DocumentPipeline


class TestDocumentPipeline(unittest.TestCase):
    """Test DocumentPipeline functionality."""

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

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_convert_to_markdown(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test markdown conversion functionality."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        pipeline = DocumentPipeline(self.mock_config)

        # Create test document
        document = Document(
            documentId="https://example.com/test",
            title="Test Document",
            content="<h1>Test Content</h1><p>This is test content.</p>",
            sourceUrl="https://example.com/test",
        )

        # Convert to markdown
        markdown_result = pipeline.convert_to_markdown(document)

        # Verify conversion was called
        self.mock_markitdown.convert.assert_called_once()
        self.assertEqual(markdown_result, "# Test Markdown\n\nThis is test content.")

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_generate_embeddings(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test embedding generation functionality."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        pipeline = DocumentPipeline(self.mock_config)

        # Generate embeddings
        embeddings = pipeline.generate_embeddings("Test content for embedding")

        # Verify OpenAI was called
        self.mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input="Test content for embedding"
        )
        self.assertEqual(embeddings, [0.1, 0.2, 0.3])

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_process_document_full_pipeline(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test full document processing pipeline."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        pipeline = DocumentPipeline(self.mock_config)

        # Create test document
        document = Document(
            documentId="https://example.com/test",
            title="Test Document",
            content="# Test Markdown\n\nThis is test content.",
            sourceUrl="https://example.com/test",
            tags=["test"],
        )

        # Process document
        processed_doc = pipeline.process_document(
            document=document,
            use_ai_categorization=False,
            additional_metadata={"author": "Test Author"},
        )

        # Verify processing steps
        self.mock_markitdown.convert.assert_called_once()
        self.mock_openai_client.embeddings.create.assert_called_once()

        # Verify processed document properties
        self.assertEqual(processed_doc.content, "# Test Markdown\n\nThis is test content.")
        self.assertEqual(processed_doc.embeddings, [0.1, 0.2, 0.3])
        self.assertEqual(processed_doc.tags, ["test"])
        self.assertEqual(processed_doc.metadata["author"], "Test Author")
        self.assertIsInstance(processed_doc.indexedDate, datetime)

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_store_document(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test document storage functionality."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        # Mock successful insertion
        mock_result = Mock()
        mock_result.inserted_id = "test-doc-123"
        self.mock_documents_collection.insert_one.return_value = mock_result

        pipeline = DocumentPipeline(self.mock_config)

        # Create test document
        document = Document(
            documentId="https://example.com/test",
            title="Test Document",
            content="<h1>Test Content</h1>",
            sourceUrl="https://example.com/test",
        )

        # Store document
        doc_id = pipeline.store_document(document)

        # Verify storage
        self.assertEqual(doc_id, "https://example.com/test")
        self.mock_documents_collection.insert_one.assert_called_once()

        # Verify document data
        stored_data = self.mock_documents_collection.insert_one.call_args[0][0]
        self.assertEqual(stored_data["documentId"], "https://example.com/test")
        self.assertEqual(stored_data["title"], "Test Document")

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_get_document(self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class):
        """Test document retrieval functionality."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        # Mock document data from database
        mock_doc_data = {
            "documentId": "https://example.com/test",
            "title": "Test Document",
            "content": "<h1>Test Content</h1>",
            "sourceUrl": "https://example.com/test",
            "createdDate": "2024-01-01T12:00:00+00:00",
            "tags": ["test"],
        }
        self.mock_documents_collection.find_one.return_value = mock_doc_data

        pipeline = DocumentPipeline(self.mock_config)

        # Get document
        document = pipeline.get_document("https://example.com/test")

        # Verify retrieval
        self.mock_documents_collection.find_one.assert_called_once_with(
            {"documentId": "https://example.com/test"}
        )
        self.assertIsNotNone(document)
        self.assertEqual(document.documentId, "https://example.com/test")
        self.assertEqual(document.title, "Test Document")
        self.assertEqual(document.tags, ["test"])

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_search_documents(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test document search functionality."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        # Mock search results
        mock_results = [
            {
                "documentId": "https://example.com/test1",
                "title": "Test Document 1",
                "similarity": 0.85,
            },
            {
                "documentId": "https://example.com/test2",
                "title": "Test Document 2",
                "similarity": 0.75,
            },
        ]
        self.mock_documents_collection.aggregate.return_value = mock_results

        pipeline = DocumentPipeline(self.mock_config)

        # Search documents
        results = pipeline.search_documents(query="test query", tags=["test"], limit=10)

        # Verify search was performed
        self.mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input="test query"
        )
        self.mock_documents_collection.aggregate.assert_called_once()

        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["documentId"], "https://example.com/test1")
        self.assertEqual(results[0]["similarity"], 0.85)

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

        # Verify processing steps
        self.mock_markitdown.convert.assert_called_once()
        self.mock_openai_client.embeddings.create.assert_called_once()

        # Verify processed document properties
        self.assertEqual(processed_doc.sourceUrl, "https://example.com/article")
        self.assertEqual(processed_doc.tags, ["test", "article"])
        self.assertEqual(processed_doc.content, "# Test Markdown\n\nThis is test content.")
        self.assertEqual(processed_doc.embeddings, [0.1, 0.2, 0.3])
        self.assertEqual(processed_doc.metadata["author"], "Test Author")

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

        # Mock empty markdown conversion
        mock_markitdown_empty = Mock()
        mock_markitdown_empty.convert.return_value = Mock(markdown="")
        mock_markitdown_class.return_value = mock_markitdown_empty

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

        # Verify empty content was handled correctly
        self.assertEqual(processed_doc.content, "")
        self.assertEqual(processed_doc.embeddings, [0.1, 0.2, 0.3])

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

        # Mock AI categorization by patching the import
        with patch("dotnet_sdk_tags.categorize_with_ai") as mock_categorize_ai:
            mock_categorize_ai.return_value = ["csharp", "dotnet"]

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

            # Verify AI categorization was called
            mock_categorize_ai.assert_called_once()

            # Verify document was processed with combined tags
            self.assertEqual(processed_doc.tags, ["article", "csharp", "dotnet"])
            self.assertEqual(processed_doc.metadata["author"], "Test Author")

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

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    @patch("document_pipeline.chunk_markdown")
    def test_process_document_with_chunking(
        self, mock_chunk_markdown, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test document processing with chunking functionality."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        # Mock chunking to return multiple chunks
        mock_chunk_markdown.return_value = [
            "# Chapter 1\n\nThis is the first chunk of content.",
            "# Chapter 2\n\nThis is the second chunk of content.",
        ]

        pipeline = DocumentPipeline(self.mock_config)

        # Create test document
        document = Document(
            documentId="https://example.com/long-document",
            title="Long Document",
            content="<h1>Chapter 1</h1><p>Content...</p><h1>Chapter 2</h1><p>More content...</p>",
            sourceUrl="https://example.com/long-document",
            tags=["documentation"],
        )

        # Process document with chunking
        processed_chunks = pipeline.process_document_with_chunking(
            document=document,
            use_ai_categorization=False,
            additional_metadata={"author": "Test Author"},
        )

        # Verify chunking was called
        mock_chunk_markdown.assert_called_once()

        # Verify we got the expected number of chunks
        self.assertEqual(len(processed_chunks), 2)

        # Verify first chunk
        chunk1 = processed_chunks[0]
        self.assertEqual(chunk1.documentId, "https://example.com/long-document#chunk_0")
        self.assertEqual(chunk1.title, "Long Document")
        self.assertEqual(
            chunk1.markdownContent, "# Chapter 1\n\nThis is the first chunk of content."
        )
        self.assertEqual(chunk1.metadata["chunk_index"], 0)
        self.assertEqual(chunk1.metadata["total_chunks"], 2)
        self.assertEqual(
            chunk1.metadata["original_document_id"], "https://example.com/long-document"
        )
        self.assertEqual(chunk1.metadata["author"], "Test Author")
        self.assertEqual(chunk1.embeddings, [0.1, 0.2, 0.3])

        # Verify second chunk
        chunk2 = processed_chunks[1]
        self.assertEqual(chunk2.documentId, "https://example.com/long-document#chunk_1")
        self.assertEqual(
            chunk2.markdownContent, "# Chapter 2\n\nThis is the second chunk of content."
        )
        self.assertEqual(chunk2.metadata["chunk_index"], 1)
        self.assertEqual(chunk2.metadata["total_chunks"], 2)

        # Verify embeddings were generated for both chunks
        self.assertEqual(self.mock_openai_client.embeddings.create.call_count, 2)

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    def test_store_document_chunks(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test storing multiple document chunks."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        # Mock successful insertions
        mock_result1 = Mock()
        mock_result1.inserted_id = "chunk1-id"
        mock_result2 = Mock()
        mock_result2.inserted_id = "chunk2-id"
        self.mock_documents_collection.insert_one.side_effect = [mock_result1, mock_result2]

        pipeline = DocumentPipeline(self.mock_config)

        # Create test document chunks
        chunk1 = Document(
            documentId="https://example.com/doc#chunk_0",
            title="Test Document",
            content="Original content",
            sourceUrl="https://example.com/doc",
            markdownContent="# Chapter 1\n\nFirst chunk",
        )

        chunk2 = Document(
            documentId="https://example.com/doc#chunk_1",
            title="Test Document",
            content="Original content",
            sourceUrl="https://example.com/doc",
            markdownContent="# Chapter 2\n\nSecond chunk",
        )

        chunks = [chunk1, chunk2]

        # Store chunks
        stored_ids = pipeline.store_document_chunks(chunks)

        # Verify both chunks were stored
        self.assertEqual(len(stored_ids), 2)
        self.assertIn("https://example.com/doc#chunk_0", stored_ids)
        self.assertIn("https://example.com/doc#chunk_1", stored_ids)
        self.assertEqual(self.mock_documents_collection.insert_one.call_count, 2)

    @patch("document_pipeline.MongoClient")
    @patch("document_pipeline.OpenAI")
    @patch("document_pipeline.MarkItDown")
    @patch("document_pipeline.chunk_markdown")
    def test_process_and_store_document_with_chunking(
        self, mock_chunk_markdown, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test the convenience method that processes and stores with chunking."""
        # Setup mocks
        mock_mongo_client_class.return_value = self.mock_mongo_client
        mock_openai_class.return_value = self.mock_openai_client
        mock_markitdown_class.return_value = self.mock_markitdown

        # Mock chunking to return single chunk (content small enough)
        mock_chunk_markdown.return_value = ["# Test Document\n\nThis is a small document."]

        # Mock successful insertion
        mock_result = Mock()
        mock_result.inserted_id = "test-doc-id"
        self.mock_documents_collection.insert_one.return_value = mock_result

        pipeline = DocumentPipeline(self.mock_config)

        # Create test document
        document = Document(
            documentId="https://example.com/test",
            title="Test Document",
            content="<h1>Test Document</h1><p>This is a small document.</p>",
            sourceUrl="https://example.com/test",
        )

        # Process and store with chunking
        stored_ids = pipeline.process_and_store_document(
            document=document, use_ai_categorization=False, use_chunking=True
        )

        # Verify single chunk was processed and stored
        self.assertEqual(len(stored_ids), 1)
        self.assertEqual(
            stored_ids[0], "https://example.com/test"
        )  # No chunk suffix for single chunk
        self.mock_documents_collection.insert_one.assert_called_once()


if __name__ == "__main__":
    unittest.main()
