#!/usr/bin/env python3
"""
Comprehensive tests for the DocumentPipeline core logic and end-to-end processing.
Tests focus on stage execution, error handling, and MongoDB storage.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from bson import ObjectId

from document_pipeline_v2 import DocumentPipeline
from pipeline_types import RawDocument, ProcessingContext, Chunk
from config import Config


class TestDocumentPipelineV2(unittest.TestCase):
    """Test the core document pipeline functionality."""

    def setUp(self):
        """Set up test fixtures with mocked dependencies."""
        # Mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.openai_api_key = "test-key"
        self.mock_config.mongodb_connection_string = "mongodb://localhost:27017"
        self.mock_config.mongodb_database = "test_db"
        self.mock_config.mongodb_collection = "test_collection"
        self.mock_config.mongodb_chunks_collection = "test_chunks_collection"
        self.mock_config.embedding_model = "text-embedding-3-small"

    @patch('document_pipeline_v2.MongoClient')
    @patch('document_pipeline_v2.OpenAI')
    @patch('document_pipeline_v2.MarkItDown')
    def test_pipeline_initialization(self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class):
        """Test that pipeline initializes with all required components."""
        # Setup mocks
        mock_documents_collection = Mock()
        mock_chunks_collection = Mock()
        mock_db = MagicMock()
        # Return appropriate collection based on the collection name accessed
        def mock_getitem(key):
            if key == "test_collection":
                return mock_documents_collection
            elif key == "test_chunks_collection":
                return mock_chunks_collection
            return Mock()
        mock_db.__getitem__.side_effect = mock_getitem
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        # Create pipeline
        pipeline = DocumentPipeline(self.mock_config)

        # Verify initialization
        self.assertIsNotNone(pipeline.client)
        self.assertIsNotNone(pipeline.mongo_client)
        self.assertIsNotNone(pipeline.documents_collection)
        self.assertIsNotNone(pipeline.chunks_collection)
        self.assertEqual(pipeline.default_chunk_size, 4000)
        self.assertEqual(len(pipeline.source_enrichers), 5)  # All enrichers loaded

    @patch('document_pipeline_v2.MongoClient')
    @patch('document_pipeline_v2.OpenAI')
    @patch('document_pipeline_v2.MarkItDown')
    def test_end_to_end_document_processing(self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class):
        """Test complete document processing from RawDocument to stored Chunks."""
        # Setup MongoDB mock
        mock_documents_collection = Mock()
        mock_documents_collection.delete_many.return_value = Mock(deleted_count=0)
        mock_documents_collection.insert_one.return_value = Mock()
        mock_documents_collection.list_indexes.return_value = []
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_documents_collection
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        # Setup OpenAI mock
        mock_openai_client = Mock()
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 100)]  # 300 dims
        mock_openai_client.embeddings.create.return_value = mock_embedding_response
        mock_openai_class.return_value = mock_openai_client

        # Setup MarkItDown mock
        mock_markitdown = Mock()
        mock_markitdown.convert.return_value = Mock(markdown="# Test\n\nConverted content.")
        mock_markitdown_class.return_value = mock_markitdown

        # Create pipeline and test document
        pipeline = DocumentPipeline(self.mock_config)
        raw_doc = RawDocument(
            content="<h1>Test</h1><p>Test content</p>",
            source_url="https://example.com/test",
            title="Test Document",
            content_type="html"
        )

        # Process document
        chunk_ids = pipeline.process_document(raw_doc, use_ai_categorization=False)

        # Verify results
        self.assertIsInstance(chunk_ids, list)
        self.assertGreater(len(chunk_ids), 0)
        
        # Verify all chunk IDs are valid ObjectIDs
        for chunk_id in chunk_ids:
            self.assertTrue(ObjectId.is_valid(chunk_id))

        # Verify MongoDB operations were called
        mock_documents_collection.delete_many.assert_called()
        mock_documents_collection.insert_one.assert_called()

        # Verify OpenAI embedding was called
        mock_openai_client.embeddings.create.assert_called()

        # Verify MarkItDown was used for HTML conversion
        mock_markitdown.convert.assert_called()

    @patch('document_pipeline_v2.MongoClient')
    @patch('document_pipeline_v2.OpenAI')
    @patch('document_pipeline_v2.MarkItDown')
    def test_error_handling_stops_processing(self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class):
        """Test that pipeline stops on first error and reports properly."""
        # Setup mocks
        mock_documents_collection = Mock()
        mock_documents_collection.delete_many.return_value = Mock(deleted_count=0)
        mock_documents_collection.list_indexes.return_value = []
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_documents_collection
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        # Make OpenAI fail
        mock_openai_client = Mock()
        mock_openai_client.embeddings.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_openai_client

        mock_markitdown = Mock()
        mock_markitdown.convert.return_value = Mock(markdown="# Test\n\nTest content.")
        mock_markitdown_class.return_value = mock_markitdown

        # Create pipeline and test document
        pipeline = DocumentPipeline(self.mock_config)
        raw_doc = RawDocument(
            content="# Test Document\n\nThis is test content.",
            source_url="https://example.com/test",
            title="Test Document",
            content_type="markdown"
        )

        # Process document should raise error
        with self.assertRaises(Exception) as context:
            pipeline.process_document(raw_doc, use_ai_categorization=False)

        # Verify error contains useful information
        self.assertIn("embedding generation", str(context.exception))

        # Verify storage was NOT attempted after embedding failure
        mock_documents_collection.insert_one.assert_not_called()

    @patch('document_pipeline_v2.MongoClient')
    @patch('document_pipeline_v2.OpenAI')
    @patch('document_pipeline_v2.MarkItDown')
    def test_source_enricher_selection_and_application(self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class):
        """Test that appropriate source enricher is selected and applied."""
        # Setup mocks
        mock_documents_collection = Mock()
        mock_documents_collection.delete_many.return_value = Mock(deleted_count=0)
        mock_documents_collection.insert_one.return_value = Mock()
        mock_documents_collection.list_indexes.return_value = []
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_documents_collection
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        mock_openai_client = Mock()
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1] * 100)]
        mock_openai_client.embeddings.create.return_value = mock_embedding_response
        mock_openai_class.return_value = mock_openai_client

        mock_markitdown = Mock()
        mock_markitdown.convert.return_value = Mock(markdown="# Test\n\nTest content.")
        mock_markitdown_class.return_value = mock_markitdown

        # Create pipeline
        pipeline = DocumentPipeline(self.mock_config)

        # Test RSS document
        rss_doc = RawDocument(
            content="RSS content",
            source_url="https://example.com/feed-item",
            title="RSS Item",
            content_type="rss",
            source_metadata={"rss_feed_url": "https://example.com/feed.xml"}
        )

        # Process RSS document
        chunk_ids = pipeline.process_document(rss_doc, use_ai_categorization=False)

        # Should complete successfully
        self.assertGreater(len(chunk_ids), 0)

        # Verify storage was called with RSS-enriched data
        mock_documents_collection.insert_one.assert_called()
        stored_chunk = mock_documents_collection.insert_one.call_args[0][0]
        
        # Check that RSS enrichment was applied
        self.assertIn("tags", stored_chunk)
        self.assertIn("rss-content", stored_chunk["tags"])

    @patch('document_pipeline_v2.MongoClient')
    @patch('document_pipeline_v2.OpenAI')
    @patch('document_pipeline_v2.MarkItDown')
    def test_chunk_id_uniqueness_with_objectid(self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class):
        """Test that ObjectID generation ensures unique chunk IDs."""
        # Setup mocks
        mock_documents_collection = Mock()
        mock_documents_collection.delete_many.return_value = Mock(deleted_count=0)
        mock_documents_collection.insert_one.return_value = Mock()
        mock_documents_collection.list_indexes.return_value = []
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_documents_collection
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        mock_openai_client = Mock()
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1] * 100)]
        mock_openai_client.embeddings.create.return_value = mock_embedding_response
        mock_openai_class.return_value = mock_openai_client

        mock_markitdown = Mock()
        mock_markitdown.convert.return_value = Mock(markdown="# Test\n\nLong content that will be chunked into multiple pieces for testing purposes.")
        mock_markitdown_class.return_value = mock_markitdown

        # Create pipeline and test document that will create multiple chunks
        pipeline = DocumentPipeline(self.mock_config)
        raw_doc = RawDocument(
            content="Long document content",
            source_url="https://example.com/long-doc",
            title="Long Document",
            content_type="html"
        )

        # Process document with small chunk size to force multiple chunks
        chunk_ids = pipeline.process_document(raw_doc, use_ai_categorization=False, chunk_size=50)

        # Verify multiple chunks were created
        self.assertGreater(len(chunk_ids), 1)

        # Verify all chunk IDs are unique and valid ObjectIDs
        unique_ids = set(chunk_ids)
        self.assertEqual(len(chunk_ids), len(unique_ids), "All chunk IDs should be unique")
        
        for chunk_id in chunk_ids:
            self.assertTrue(ObjectId.is_valid(chunk_id), f"'{chunk_id}' is not a valid ObjectID")

    @patch('document_pipeline_v2.MongoClient')
    @patch('document_pipeline_v2.OpenAI')
    @patch('document_pipeline_v2.MarkItDown')
    def test_chunk_retrieval_functionality(self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class):
        """Test that chunks can be retrieved correctly after storage."""
        # Setup MongoDB mock for retrieval
        mock_documents_collection = Mock()
        mock_documents_collection.delete_many.return_value = Mock(deleted_count=0)
        mock_documents_collection.insert_one.return_value = Mock()
        mock_documents_collection.list_indexes.return_value = []
        
        # Mock find_one for get_chunk
        test_chunk_data = {
            "chunk_id": "507f1f77bcf86cd799439011",
            "original_document_id": "https://example.com/test",
            "title": "Test Document",
            "source_url": "https://example.com/test",
            "content": "Test content",
            "embeddings": [0.1, 0.2, 0.3],
            "chunk_index": 0,
            "total_chunks": 1,
            "chunk_size": 12,
            "metadata": {},
            "tags": [],
            "created_date": "2024-01-01T12:00:00",
            "indexed_date": "2024-01-01T12:00:00"
        }
        mock_documents_collection.find_one.return_value = test_chunk_data
        
        # Mock find for get_document_chunks  
        mock_cursor = Mock()
        mock_cursor.__iter__ = lambda x: iter([test_chunk_data])
        mock_cursor.sort.return_value = mock_cursor
        mock_documents_collection.find.return_value = mock_cursor
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_documents_collection
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        # Other mocks
        mock_openai_class.return_value = Mock()
        mock_markitdown_class.return_value = Mock()

        # Create pipeline
        pipeline = DocumentPipeline(self.mock_config)

        # Test get_chunk
        chunk = pipeline.get_chunk("507f1f77bcf86cd799439011")
        self.assertIsInstance(chunk, Chunk)
        self.assertEqual(chunk.chunk_id, "507f1f77bcf86cd799439011")
        self.assertEqual(chunk.content, "Test content")

        # Test get_document_chunks
        chunks = pipeline.get_document_chunks("https://example.com/test")
        self.assertEqual(len(chunks), 1)
        self.assertIsInstance(chunks[0], Chunk)
        self.assertEqual(chunks[0].original_document_id, "https://example.com/test")

    @patch('document_pipeline_v2.MongoClient')
    @patch('document_pipeline_v2.OpenAI')
    @patch('document_pipeline_v2.MarkItDown')
    def test_cleanup_existing_chunks_before_processing(self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class):
        """Test that existing chunks are cleaned up before processing new ones."""
        # Setup mocks
        mock_documents_collection = Mock()
        mock_documents_collection.delete_many.return_value = Mock(deleted_count=5)  # Simulate cleanup
        mock_documents_collection.insert_one.return_value = Mock()
        mock_documents_collection.list_indexes.return_value = []
        
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_documents_collection
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        mock_openai_client = Mock()
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1] * 100)]
        mock_openai_client.embeddings.create.return_value = mock_embedding_response
        mock_openai_class.return_value = mock_openai_client

        mock_markitdown = Mock()
        mock_markitdown.convert.return_value = Mock(markdown="# Test\n\nTest content.")
        mock_markitdown_class.return_value = mock_markitdown

        # Create pipeline and test document
        pipeline = DocumentPipeline(self.mock_config)
        raw_doc = RawDocument(
            content="Test content",
            source_url="https://example.com/test",
            title="Test Document",
            content_type="markdown"
        )

        # Process document
        pipeline.process_document(raw_doc, use_ai_categorization=False)

        # Verify cleanup was called before processing
        mock_documents_collection.delete_many.assert_called_with(
            {"original_document_id": "https://example.com/test"}
        )

        # Verify new chunks were inserted after cleanup
        mock_documents_collection.insert_one.assert_called()


if __name__ == '__main__':
    unittest.main()