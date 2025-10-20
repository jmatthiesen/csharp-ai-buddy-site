#!/usr/bin/env python3
"""
Comprehensive tests for source enricher framework and implementations.
Tests focus on enricher selection, metadata extraction, and tag generation.
"""

import unittest
from datetime import datetime

from source_enrichers import (
    RSSSourceEnricher, WordPressSourceEnricher, HTMLSourceEnricher,
    PlainTextSourceEnricher, FallbackSourceEnricher
)
from pipeline_types import RawDocument, ProcessingContext


class TestSourceEnrichers(unittest.TestCase):
    """Test the source enricher framework and individual enrichers."""

    def test_rss_source_enricher_detection(self):
        """Test RSS enricher can_handle logic for different RSS indicators."""
        enricher = RSSSourceEnricher()
        
        # Test content_type detection
        rss_doc1 = RawDocument(
            content="RSS content",
            source_url="https://example.com/item",
            content_type="rss"
        )
        self.assertTrue(enricher.can_handle(rss_doc1))
        
        # Test rss_feed_url metadata detection
        rss_doc2 = RawDocument(
            content="RSS content", 
            source_url="https://example.com/item",
            source_metadata={"rss_feed_url": "https://example.com/feed.xml"}
        )
        self.assertTrue(enricher.can_handle(rss_doc2))
        
        # Test rss_item_id metadata detection
        rss_doc3 = RawDocument(
            content="RSS content",
            source_url="https://example.com/item", 
            source_metadata={"rss_item_id": "item-123"}
        )
        self.assertTrue(enricher.can_handle(rss_doc3))
        
        # Test non-RSS document
        non_rss_doc = RawDocument(
            content="Regular content",
            source_url="https://example.com/page",
            content_type="html"
        )
        self.assertFalse(enricher.can_handle(non_rss_doc))

    def test_rss_enricher_metadata_extraction(self):
        """Test RSS enricher properly extracts and adds metadata."""
        enricher = RSSSourceEnricher()
        
        raw_doc = RawDocument(
            content="RSS item content",
            source_url="https://example.com/item-1",
            content_type="rss",
            source_metadata={
                "rss_feed_url": "https://example.com/feed.xml",
                "rss_item_id": "item-1", 
                "rss_author": "John Doe",
                "rss_published_date": "2024-01-01T12:00:00Z",
                "rss_categories": ["Technology", "Programming"],
                "rss_feed_name": "Tech Blog",
                "rss_feed_description": "A blog about technology"
            }
        )
        
        context = ProcessingContext(raw_document=raw_doc)
        enricher.enrich(context)
        
        # Check processing metadata
        self.assertEqual(context.processing_metadata["source_type"], "rss")
        self.assertEqual(context.processing_metadata["rss_feed_url"], "https://example.com/feed.xml")
        self.assertEqual(context.processing_metadata["rss_item_id"], "item-1")
        self.assertEqual(context.processing_metadata["rss_author"], "John Doe")
        self.assertEqual(context.processing_metadata["rss_categories"], ["Technology", "Programming"])
        self.assertEqual(context.processing_metadata["rss_feed_name"], "Tech Blog")
        
        # Check tags
        self.assertIn("Technology", context.final_tags)
        self.assertIn("Programming", context.final_tags)
        self.assertIn("rss-content", context.final_tags)

    def test_wordpress_source_enricher_detection(self):
        """Test WordPress enricher can_handle logic for different WordPress indicators."""
        enricher = WordPressSourceEnricher()
        
        # Test content_type detection
        wp_doc1 = RawDocument(
            content="WordPress content",
            source_url="https://example.com/post",
            content_type="wordpress"
        )
        self.assertTrue(enricher.can_handle(wp_doc1))
        
        # Test wp-json URL detection
        wp_doc2 = RawDocument(
            content="WordPress content",
            source_url="https://example.com/wp-json/wp/v2/posts/123"
        )
        self.assertTrue(enricher.can_handle(wp_doc2))
        
        # Test wordpress_post_id metadata detection
        wp_doc3 = RawDocument(
            content="WordPress content",
            source_url="https://example.com/post",
            source_metadata={"wordpress_post_id": 123}
        )
        self.assertTrue(enricher.can_handle(wp_doc3))
        
        # Test non-WordPress document
        non_wp_doc = RawDocument(
            content="Regular content",
            source_url="https://example.com/page",
            content_type="html"
        )
        self.assertFalse(enricher.can_handle(non_wp_doc))

    def test_wordpress_enricher_metadata_extraction(self):
        """Test WordPress enricher properly extracts and adds metadata."""
        enricher = WordPressSourceEnricher()
        
        raw_doc = RawDocument(
            content="<h1>WordPress Post</h1><p>Content here</p>",
            source_url="https://example.com/post",
            content_type="wordpress",
            source_metadata={
                "wordpress_post_id": 123,
                "wordpress_author": 5,
                "wordpress_categories": ["Tech", "Tutorial"],
                "wordpress_tags": ["Python", "API"],
                "wordpress_json_url": "https://example.com/wp-json/wp/v2/posts/123",
                "wordpress_modified_date": datetime(2024, 1, 2, 12, 0, 0)
            }
        )
        
        context = ProcessingContext(raw_document=raw_doc)
        enricher.enrich(context)
        
        # Check processing metadata
        self.assertEqual(context.processing_metadata["source_type"], "wordpress")
        self.assertEqual(context.processing_metadata["wordpress_post_id"], 123)
        self.assertEqual(context.processing_metadata["wordpress_author"], 5)
        self.assertEqual(context.processing_metadata["wordpress_json_url"], "https://example.com/wp-json/wp/v2/posts/123")
        
        # Check tags - should include categories and tags
        self.assertIn("Tech", context.final_tags)
        self.assertIn("Tutorial", context.final_tags)
        self.assertIn("Python", context.final_tags)
        self.assertIn("API", context.final_tags)
        self.assertIn("wordpress-content", context.final_tags)

    def test_html_source_enricher_detection(self):
        """Test HTML enricher can_handle logic."""
        enricher = HTMLSourceEnricher()
        
        # Test HTML content_type
        html_doc = RawDocument(
            content="<html><body>Content</body></html>",
            source_url="https://example.com/page",
            content_type="html"
        )
        self.assertTrue(enricher.can_handle(html_doc))
        
        # Test non-HTML document
        md_doc = RawDocument(
            content="# Markdown content",
            source_url="https://example.com/page.md",
            content_type="markdown"
        )
        self.assertFalse(enricher.can_handle(md_doc))

    def test_html_enricher_basic_functionality(self):
        """Test HTML enricher adds appropriate metadata."""
        enricher = HTMLSourceEnricher()
        
        raw_doc = RawDocument(
            content="<html><head><title>Test Page</title></head><body><h1>Content</h1></body></html>",
            source_url="https://example.com/page",
            content_type="html"
        )
        
        context = ProcessingContext(raw_document=raw_doc)
        enricher.enrich(context)
        
        # Check processing metadata
        self.assertEqual(context.processing_metadata["source_type"], "html")
        
        # Check tags
        self.assertIn("html-content", context.final_tags)

    def test_plain_text_enricher_detection(self):
        """Test PlainText enricher can_handle logic."""
        enricher = PlainTextSourceEnricher()
        
        # Test text content_type
        text_doc = RawDocument(
            content="Plain text content",
            source_url="https://example.com/page.txt",
            content_type="text"
        )
        self.assertTrue(enricher.can_handle(text_doc))
        
        # Test non-text document
        html_doc = RawDocument(
            content="<html>Content</html>",
            source_url="https://example.com/page",
            content_type="html"
        )
        self.assertFalse(enricher.can_handle(html_doc))

    def test_plain_text_enricher_basic_functionality(self):
        """Test PlainText enricher adds appropriate metadata."""
        enricher = PlainTextSourceEnricher()
        
        raw_doc = RawDocument(
            content="This is plain text content.",
            source_url="https://example.com/document.txt",
            content_type="text"
        )
        
        context = ProcessingContext(raw_document=raw_doc)
        enricher.enrich(context)
        
        # Check processing metadata
        self.assertEqual(context.processing_metadata["source_type"], "text")
        
        # Check tags
        self.assertIn("text-content", context.final_tags)

    def test_fallback_enricher_handles_anything(self):
        """Test Fallback enricher can handle any document type."""
        enricher = FallbackSourceEnricher()
        
        # Test various document types
        test_docs = [
            RawDocument(content="Test", source_url="https://example.com", content_type="html"),
            RawDocument(content="Test", source_url="https://example.com", content_type="unknown"),
            RawDocument(content="Test", source_url="https://example.com", content_type="pdf"),
            RawDocument(content="Test", source_url="https://example.com", content_type="")
        ]
        
        for doc in test_docs:
            self.assertTrue(enricher.can_handle(doc), f"Fallback should handle {doc.content_type}")

    def test_fallback_enricher_basic_functionality(self):
        """Test Fallback enricher adds basic metadata."""
        enricher = FallbackSourceEnricher()
        
        raw_doc = RawDocument(
            content="Unknown content type",
            source_url="https://example.com/unknown",
            content_type="unknown"
        )
        
        context = ProcessingContext(raw_document=raw_doc)
        enricher.enrich(context)
        
        # Check processing metadata
        self.assertEqual(context.processing_metadata["source_type"], "fallback")
        self.assertEqual(context.processing_metadata["original_content_type"], "unknown")
        
        # Check tags
        self.assertIn("fallback-content", context.final_tags)

    def test_enricher_selection_order_matters(self):
        """Test that more specific enrichers are selected before fallback."""
        enrichers = [
            RSSSourceEnricher(),
            WordPressSourceEnricher(),
            HTMLSourceEnricher(),
            PlainTextSourceEnricher(),
            FallbackSourceEnricher()
        ]
        
        # Test RSS document - should be handled by RSS enricher, not fallback
        rss_doc = RawDocument(
            content="RSS content",
            source_url="https://example.com/item",
            content_type="rss"
        )
        
        selected_enricher = None
        for enricher in enrichers:
            if enricher.can_handle(rss_doc):
                selected_enricher = enricher
                break
        
        self.assertIsInstance(selected_enricher, RSSSourceEnricher)
        self.assertEqual(selected_enricher.name, "RSS")

    def test_multiple_enricher_metadata_accumulation(self):
        """Test that metadata properly accumulates when multiple enrichers could apply."""
        # This tests the enricher framework behavior, not specific enricher logic
        
        # Create a document that could match multiple enrichers conceptually
        raw_doc = RawDocument(
            content="Content with tags",
            source_url="https://example.com/test",
            content_type="html",
            tags=["initial-tag"]
        )
        
        context = ProcessingContext(raw_document=raw_doc)
        
        # Apply HTML enricher
        html_enricher = HTMLSourceEnricher()
        if html_enricher.can_handle(raw_doc):
            html_enricher.enrich(context)
        
        # Check that initial tags are preserved and new ones added
        self.assertIn("initial-tag", context.final_tags)
        self.assertIn("html-content", context.final_tags)
        
        # Check processing metadata
        self.assertEqual(context.processing_metadata["source_type"], "html")

    def test_enricher_error_handling_graceful(self):
        """Test that enrichers handle edge cases gracefully."""
        enricher = RSSSourceEnricher()
        
        # Test with minimal metadata
        raw_doc = RawDocument(
            content="Minimal RSS content",
            source_url="https://example.com/item",
            content_type="rss",
            source_metadata={}  # Empty metadata
        )
        
        context = ProcessingContext(raw_document=raw_doc)
        
        # Should not raise exception
        enricher.enrich(context)
        
        # Should still add basic RSS metadata
        self.assertEqual(context.processing_metadata["source_type"], "rss")
        self.assertIn("rss-content", context.final_tags)

    def test_enricher_names_are_defined(self):
        """Test that all enrichers have proper names for logging."""
        enrichers = [
            RSSSourceEnricher(),
            WordPressSourceEnricher(), 
            HTMLSourceEnricher(),
            PlainTextSourceEnricher(),
            FallbackSourceEnricher()
        ]
        
        expected_names = ["RSS", "WordPress", "HTML", "PlainText", "Fallback"]
        
        for enricher, expected_name in zip(enrichers, expected_names):
            self.assertEqual(enricher.name, expected_name)

    def test_processing_context_state_preservation(self):
        """Test that enrichers don't corrupt existing context state."""
        raw_doc = RawDocument(
            content="Test content",
            source_url="https://example.com/test",
            content_type="html"
        )
        
        context = ProcessingContext(
            raw_document=raw_doc,
            use_ai_categorization=True,
            chunk_size=2000
        )
        
        # Add some existing state
        context.final_tags.extend(["existing-tag-1", "existing-tag-2"])
        context.processing_metadata["existing_key"] = "existing_value"
        context.user_metadata["user_key"] = "user_value"
        
        # Apply enricher
        enricher = HTMLSourceEnricher()
        enricher.enrich(context)
        
        # Check that existing state is preserved
        self.assertIn("existing-tag-1", context.final_tags)
        self.assertIn("existing-tag-2", context.final_tags)
        self.assertEqual(context.processing_metadata["existing_key"], "existing_value")
        self.assertEqual(context.user_metadata["user_key"], "user_value")
        self.assertTrue(context.use_ai_categorization)
        self.assertEqual(context.chunk_size, 2000)
        
        # Check that new enricher data was added
        self.assertIn("html-content", context.final_tags)
        self.assertEqual(context.processing_metadata["source_type"], "html")


if __name__ == '__main__':
    unittest.main()