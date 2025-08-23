#!/usr/bin/env python3
"""
Source enricher framework for adding source-specific metadata and processing logic.
"""

from abc import ABC, abstractmethod
from pipeline_types import RawDocument, ProcessingContext
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SourceEnricher(ABC):
    """Base class for source-specific enrichment logic"""
    
    @abstractmethod
    def can_handle(self, raw_doc: RawDocument) -> bool:
        """Check if this enricher can handle the given document"""
        pass
    
    @abstractmethod
    def enrich(self, context: ProcessingContext) -> None:
        """Enrich the context with source-specific metadata and processing"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this enricher for logging"""
        pass


class RSSSourceEnricher(SourceEnricher):
    """Enricher for RSS feed documents"""
    
    @property
    def name(self) -> str:
        return "RSS"
    
    def can_handle(self, raw_doc: RawDocument) -> bool:
        return (raw_doc.content_type == "rss" or 
                "rss_feed_url" in raw_doc.source_metadata or
                "rss_item_id" in raw_doc.source_metadata)
    
    def enrich(self, context: ProcessingContext) -> None:
        """Add RSS-specific metadata and tags"""
        source_meta = context.raw_document.source_metadata
        
        # Add RSS-specific processing metadata
        rss_metadata = {
            "source_type": "rss",
            "rss_feed_url": source_meta.get("rss_feed_url"),
            "rss_item_id": source_meta.get("rss_item_id"),
            "rss_author": source_meta.get("rss_author"),
            "rss_published_date": source_meta.get("rss_published_date"),
            "rss_categories": source_meta.get("rss_categories", [])
        }
        
        # Only add non-None values
        for key, value in rss_metadata.items():
            if value is not None:
                context.processing_metadata[key] = value
        
        # Add RSS categories as tags
        rss_categories = source_meta.get("rss_categories", [])
        if rss_categories:
            context.final_tags.extend(rss_categories)
        
        # Add RSS-specific tags
        context.final_tags.append("rss-content")
        
        # Handle RSS feed name if available
        if source_meta.get("rss_feed_name"):
            context.processing_metadata["rss_feed_name"] = source_meta["rss_feed_name"]
        
        if source_meta.get("rss_feed_description"):
            context.processing_metadata["rss_feed_description"] = source_meta["rss_feed_description"]
        
        logger.debug(f"RSS enrichment completed for {context.raw_document.source_url}")


class WordPressSourceEnricher(SourceEnricher):
    """Enricher for WordPress API documents"""
    
    @property
    def name(self) -> str:
        return "WordPress"
    
    def can_handle(self, raw_doc: RawDocument) -> bool:
        return ("wordpress_post_id" in raw_doc.source_metadata or
                "wp-json" in raw_doc.source_url or
                raw_doc.content_type == "wordpress")
    
    def enrich(self, context: ProcessingContext) -> None:
        """Add WordPress-specific metadata and tags"""
        source_meta = context.raw_document.source_metadata
        
        # Add WordPress-specific processing metadata
        wp_metadata = {
            "source_type": "wordpress",
            "wordpress_post_id": source_meta.get("wordpress_post_id"),
            "wordpress_author": source_meta.get("wordpress_author"),
            "wordpress_json_url": source_meta.get("wordpress_json_url"),
            "wordpress_categories": source_meta.get("wordpress_categories", []),
            "wordpress_tags": source_meta.get("wordpress_tags", [])
        }
        
        # Only add non-None/non-empty values
        for key, value in wp_metadata.items():
            if value is not None and value != []:
                context.processing_metadata[key] = value
        
        # Add WordPress categories and tags
        wp_categories = source_meta.get("wordpress_categories", [])
        wp_tags = source_meta.get("wordpress_tags", [])
        if wp_categories:
            context.final_tags.extend(wp_categories)
        if wp_tags:
            context.final_tags.extend(wp_tags)
        
        # Add WordPress-specific tag
        context.final_tags.append("wordpress-content")
        
        logger.debug(f"WordPress enrichment completed for {context.raw_document.source_url}")


class HTMLSourceEnricher(SourceEnricher):
    """Enricher for general HTML documents"""
    
    @property
    def name(self) -> str:
        return "HTML"
    
    def can_handle(self, raw_doc: RawDocument) -> bool:
        return raw_doc.content_type == "html"
    
    def enrich(self, context: ProcessingContext) -> None:
        """Add HTML-specific metadata"""
        context.processing_metadata.update({
            "source_type": "html",
            "content_type": "web_page"
        })
        
        # Add generic HTML content tag
        context.final_tags.append("html-content")
        
        # Check if it might be WordPress based on URL patterns
        if "wp-" in context.raw_document.source_url or "/wp/" in context.raw_document.source_url:
            context.final_tags.append("potential-wordpress")
        
        logger.debug(f"HTML enrichment completed for {context.raw_document.source_url}")


class PlainTextSourceEnricher(SourceEnricher):
    """Enricher for plain text and markdown documents"""
    
    @property
    def name(self) -> str:
        return "PlainText" 
    
    def can_handle(self, raw_doc: RawDocument) -> bool:
        return raw_doc.content_type in ["text", "markdown"]
    
    def enrich(self, context: ProcessingContext) -> None:
        """Add text-specific metadata"""
        context.processing_metadata.update({
            "source_type": "text",
            "content_type": context.raw_document.content_type
        })
        
        # Add text content tag
        context.final_tags.append("text-content")
        
        # Add specific tag for markdown
        if context.raw_document.content_type == "markdown":
            context.final_tags.append("markdown")
        
        logger.debug(f"Text enrichment completed for {context.raw_document.source_url}")


class FallbackSourceEnricher(SourceEnricher):
    """Fallback enricher for unknown content types"""
    
    @property
    def name(self) -> str:
        return "Fallback"
    
    def can_handle(self, raw_doc: RawDocument) -> bool:
        # This enricher can handle any document as a fallback
        return True
    
    def enrich(self, context: ProcessingContext) -> None:
        """Add generic metadata for unknown content types"""
        # Only enrich if no other enricher has set source_type
        if "source_type" not in context.processing_metadata:
            context.processing_metadata.update({
                "source_type": "fallback",
                "original_content_type": context.raw_document.content_type
            })
            
            context.final_tags.append("fallback-content")
            
            logger.debug(f"Fallback enrichment applied for {context.raw_document.source_url}")