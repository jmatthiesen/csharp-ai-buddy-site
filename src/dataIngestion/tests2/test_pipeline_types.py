#!/usr/bin/env python3
"""
Comprehensive tests for pipeline data types and serialization.
Tests focus on data validation, defaults, and MongoDB compatibility.
"""

import unittest
from datetime import datetime, timezone

from pipeline_types import RawDocument, ProcessingContext, Chunk


class TestPipelineTypes(unittest.TestCase):
    """Test the core pipeline data types."""

    def test_raw_document_required_fields(self):
        """Test RawDocument creation with required fields."""
        # Minimum required fields
        raw_doc = RawDocument(
            content="Test content",
            source_url="https://example.com/test"
        )
        
        self.assertEqual(raw_doc.content, "Test content")
        self.assertEqual(raw_doc.source_url, "https://example.com/test")
        
        # Verify defaults
        self.assertIsNone(raw_doc.title)
        self.assertEqual(raw_doc.content_type, "html")
        self.assertEqual(raw_doc.source_metadata, {})
        self.assertEqual(raw_doc.tags, [])
        self.assertIsNone(raw_doc.created_date)


    def test_raw_document_mutable_fields(self):
        """Test that mutable fields in RawDocument work correctly."""
        raw_doc = RawDocument(
            content="Test content",
            source_url="https://example.com/test"
        )
        
        # Test that we can modify mutable fields
        raw_doc.tags.append("new-tag")
        raw_doc.source_metadata["new_key"] = "new_value"
        
        self.assertIn("new-tag", raw_doc.tags)
        self.assertEqual(raw_doc.source_metadata["new_key"], "new_value")

    def test_processing_context_initialization(self):
        """Test ProcessingContext creation and defaults."""
        raw_doc = RawDocument(
            content="Context test",
            source_url="https://example.com/context-test"
        )
        
        context = ProcessingContext(raw_document=raw_doc)
        
        # Verify required field
        self.assertEqual(context.raw_document, raw_doc)
        
        # Verify defaults
        self.assertTrue(context.use_ai_categorization)
        self.assertEqual(context.chunk_size, 4000)
        self.assertIsNone(context.markdown_content)
        self.assertEqual(context.chunks, [])
        self.assertEqual(context.chunk_embeddings, [])
        self.assertEqual(context.user_metadata, {})
        self.assertEqual(context.processing_metadata, {})
        self.assertEqual(context.final_tags, [])
        self.assertEqual(context.errors, [])
        self.assertEqual(context.warnings, [])
        self.assertEqual(context.stages_completed, [])

    def test_processing_context_mutable_collections(self):
        """Test that ProcessingContext collections can be modified."""
        raw_doc = RawDocument(content="Mutation test", source_url="https://example.com/mutation")
        context = ProcessingContext(raw_document=raw_doc)
        
        # Test modifying collections
        context.chunks.append("First chunk")
        context.chunks.append("Second chunk")
        
        context.chunk_embeddings.append([0.1, 0.2, 0.3])
        context.chunk_embeddings.append([0.4, 0.5, 0.6])
        
        context.final_tags.extend(["tag1", "tag2"])
        
        context.user_metadata["user_key"] = "user_value"
        context.processing_metadata["processing_key"] = "processing_value"
        
        # Verify modifications
        self.assertEqual(len(context.chunks), 2)
        self.assertEqual(len(context.chunk_embeddings), 2)
        self.assertEqual(len(context.final_tags), 2)
        self.assertEqual(context.user_metadata["user_key"], "user_value")
        self.assertEqual(context.processing_metadata["processing_key"], "processing_value")

    def test_chunk_to_dict_mongodb_serialization(self):
        """Test Chunk to_dict() method for MongoDB compatibility."""
        test_created_date = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        test_indexed_date = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        chunk = Chunk(
            chunk_id="507f1f77bcf86cd799439011",
            title="Serialization Test",
            source_url="https://example.com/serialization", 
            content="Content for serialization testing.",
            embeddings=[0.1, 0.2, 0.3],
            chunk_index=1,
            total_chunks=3,
            chunk_size=35,
            metadata={"test_key": "test_value"},
            tags=["test-tag"],
            created_date=test_created_date,
            indexed_date=test_indexed_date
        )
        
        # Convert to dict
        chunk_dict = chunk.to_dict()
        
        # Verify structure
        self.assertIsInstance(chunk_dict, dict)
        
        # Verify all fields present
        expected_keys = {
            'chunk_id', 'title', 'source_url', 'content',
            'embeddings', 'chunk_index', 'total_chunks', 'chunk_size',
            'metadata', 'tags', 'created_date', 'indexed_date'
        }
        self.assertEqual(set(chunk_dict.keys()), expected_keys)
        
        # Verify data types and values
        self.assertEqual(chunk_dict['chunk_id'], "507f1f77bcf86cd799439011")
        self.assertEqual(chunk_dict['source_url'], "https://example.com/serialization")
        self.assertEqual(chunk_dict['title'], "Serialization Test")
        self.assertEqual(chunk_dict['content'], "Content for serialization testing.")
        self.assertEqual(chunk_dict['embeddings'], [0.1, 0.2, 0.3])
        self.assertEqual(chunk_dict['chunk_index'], 1)
        self.assertEqual(chunk_dict['total_chunks'], 3)
        self.assertEqual(chunk_dict['chunk_size'], 35)
        self.assertEqual(chunk_dict['metadata'], {"test_key": "test_value"})
        self.assertEqual(chunk_dict['tags'], ["test-tag"])
        
        # Verify datetime conversion to ISO strings
        self.assertEqual(chunk_dict['created_date'], test_created_date.isoformat())
        self.assertEqual(chunk_dict['indexed_date'], test_indexed_date.isoformat())

    def test_chunk_to_dict_with_none_dates(self):
        """Test Chunk to_dict() with None date values."""
        chunk = Chunk(
            chunk_id="507f1f77bcf86cd799439011",
            title="None Dates Test",
            source_url="https://example.com/none-dates",
            content="Testing with None dates.",
            created_date=None,  # Explicitly None
            indexed_date=None   # Explicitly None
        )
        
        chunk_dict = chunk.to_dict()
        
        # None dates should remain None in the dict
        self.assertIsNone(chunk_dict['created_date'])
        self.assertIsNone(chunk_dict['indexed_date'])

    def test_chunk_mutable_fields_modification(self):
        """Test that Chunk mutable fields can be modified."""
        chunk = Chunk(
            chunk_id="507f1f77bcf86cd799439011",
            title="Mutable Test",
            source_url="https://example.com/mutable",
            content="Testing mutable fields."
        )
        
        # Modify mutable fields
        chunk.embeddings.extend([0.1, 0.2, 0.3])
        chunk.metadata["new_key"] = "new_value"
        chunk.tags.append("new-tag")
        
        # Verify modifications
        self.assertEqual(chunk.embeddings, [0.1, 0.2, 0.3])
        self.assertEqual(chunk.metadata["new_key"], "new_value")
        self.assertIn("new-tag", chunk.tags)

if __name__ == '__main__':
    unittest.main()