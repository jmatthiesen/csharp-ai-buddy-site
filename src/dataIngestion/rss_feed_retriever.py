#!/usr/bin/env python3
"""
RSS Feed Retriever for RAG Data Pipeline
Handles parsing RSS feeds and creating documents from feed items.
"""

import hashlib
import logging
from datetime import datetime
from typing import List, Optional

import feedparser
from document import Document
from feedparser import FeedParserDict

logger = logging.getLogger(__name__)


class RSSFeedRetriever:
    """Handles parsing RSS feeds and creating documents from feed items."""

    def __init__(self):
        pass

    def fetch_feed_items(self, feed_url: str) -> List[Document]:
        """
        Fetch all items from an RSS feed and convert them to Document objects.

        Args:
            feed_url: URL of the RSS feed

        Returns:
            List[Document]: List of documents created from feed items
        """
        try:
            logger.info(f"Fetching RSS feed: {feed_url}")

            # Parse the RSS feed
            feed = feedparser.parse(feed_url)
            if feed.bozo:
                logger.error(f"Error parsing RSS feed: {feed_url}")
                return []

            documents = []

            # Process each item in the feed
            for feed_item in feed.entries:
                document = self._create_document_from_feed_item(feed_item, feed_url)
                if document:
                    documents.append(document)

            logger.info(f"Successfully parsed {len(documents)} items from RSS feed")
            return documents

        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_url}: {e}")
            return []

    def _create_document_from_feed_item(
        self, feed_item: FeedParserDict, feed_url: str
    ) -> Optional[Document]:
        """
        Create a Document from an RSS feed item.

        Args:
            feed_item: Parsed feed item from feedparser
            feed_url: URL of the RSS feed

        Returns:
            Document: Document created from the feed item, or None if creation fails
        """
        try:
            # Generate a unique ID for the item
            item_id = hashlib.md5(
                f"{feed_url}:{feed_item.get('id', feed_item.get('link', ''))}".encode()
            ).hexdigest()

            # Parse published date
            published_date = None
            if hasattr(feed_item, "published_parsed") and feed_item.published_parsed:
                published_date = datetime(*feed_item.published_parsed[:6])

            # Extract author - try creator first, then author
            author = None
            if hasattr(feed_item, "creator"):
                author = feed_item.creator
            elif hasattr(feed_item, "author"):
                author = feed_item.author

            # Extract content - try different content fields
            content = None
            if hasattr(feed_item, "content") and feed_item.content:
                # Some feeds have content in a list
                if isinstance(feed_item.content, list) and len(feed_item.content) > 0:
                    content = feed_item.content[0].get("value", "")
                else:
                    content = feed_item.content
            elif hasattr(feed_item, "summary"):
                content = feed_item.summary
            elif hasattr(feed_item, "description"):
                content = feed_item.description

            # Extract categories
            categories = []
            if hasattr(feed_item, "tags"):
                categories = [tag.term for tag in feed_item.tags if hasattr(tag, "term")]

            # Create RSS metadata
            rss_metadata = {
                "rss_feed_url": feed_url,
                "rss_item_id": item_id,
                "rss_title": feed_item.get("title", ""),
                "rss_published_date": published_date.isoformat() if published_date else None,
                "rss_author": author,
                "rss_categories": categories,
            }

            # Create the document
            document = Document(
                documentId=feed_item.get("link", item_id),
                title=feed_item.get("title", ""),
                content=content or "",
                sourceUrl=feed_item.get("link", ""),
                createdDate=published_date,
                metadata=rss_metadata,
                rss_feed_url=feed_url,
                rss_item_id=item_id,
                rss_title=feed_item.get("title", ""),
                rss_published_date=published_date.isoformat() if published_date else None,
                rss_author=author,
            )

            return document

        except Exception as e:
            logger.error(f"Error creating document from RSS item: {e}")
            return None
