#!/usr/bin/env python3
"""
Document data transfer object for RAG Data Pipeline.
Represents the structure of documents stored in the MongoDB "documents" collection.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson.objectid import ObjectId


@dataclass
class Document:
    """Represents a document stored in the MongoDB documents collection."""

    # Core document fields
    documentId: str
    title: str
    content: str
    sourceUrl: str

    # Vector embeddings for similarity search
    embeddings: Optional[List[float]] = None

    # Categorization and filtering
    tags: Optional[List[str]] = None

    # Timestamps
    createdDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None
    indexedDate: Optional[datetime] = None

    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None

    # RSS-specific fields (when document comes from RSS feed)
    rss_feed_url: Optional[str] = None
    rss_item_id: Optional[str] = None
    rss_title: Optional[str] = None
    rss_published_date: Optional[str] = None
    rss_author: Optional[str] = None

    # WordPress-specific fields (when document comes from WordPress JSON API)
    json_url: Optional[str] = None

    # MongoDB ObjectId (internal use)
    _id: Optional[ObjectId] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = asdict(self)

        # Convert datetime objects to ISO strings for MongoDB
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

        # Remove None values to keep the document clean
        data = {k: v for k, v in data.items() if v is not None}

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """Create from dictionary from MongoDB."""

        # Convert ISO strings back to datetime objects
        datetime_fields = ["createdDate", "updatedDate", "indexedDate"]
        for field in datetime_fields:
            if field in data and data[field]:
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except (ValueError, TypeError):
                    data[field] = None

        # Handle MongoDB ObjectId
        if "_id" in data and data["_id"]:
            if isinstance(data["_id"], str):
                data["_id"] = ObjectId(data["_id"])

        return cls(**data)

    @classmethod
    def create_from_url(
        cls,
        url: str,
        title: str = "",
        content: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Document":
        """Create a new document from URL and basic information."""
        return cls(
            documentId=url,
            title=title,
            content=content,
            sourceUrl=url,
            tags=tags or [],
            metadata=metadata or {},
            createdDate=datetime.now(timezone.utc),
            indexedDate=datetime.now(timezone.utc),
        )

    @classmethod
    def create_from_rss_item(
        cls,
        item_url: str,
        title: str,
        content: str,
        feed_url: str,
        item_id: str,
        author: Optional[str] = None,
        published_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
    ) -> "Document":
        """Create a new document from RSS feed item."""
        return cls(
            documentId=item_url,
            title=title,
            content=content,
            sourceUrl=item_url,
            tags=tags or [],
            rss_feed_url=feed_url,
            rss_item_id=item_id,
            rss_title=title,
            rss_published_date=published_date.isoformat() if published_date else None,
            rss_author=author,
            createdDate=datetime.now(timezone.utc),
            indexedDate=datetime.now(timezone.utc),
        )

    def update_content(self, new_content: str):
        """Update the document content"""
        if new_content:
            self.content = new_content
        self.updatedDate = datetime.now(timezone.utc)

    def update_embeddings(self, embeddings: List[float]):
        """Update the document embeddings."""
        self.embeddings = embeddings
        self.updatedDate = datetime.now(timezone.utc)

    def update_tags(self, tags: List[str]):
        """Update the document tags."""
        self.tags = tags
        self.updatedDate = datetime.now(timezone.utc)

    def add_tags(self, tags: List[str]):
        """Add tags to the existing tags list."""
        if self.tags is None:
            self.tags = []
        self.tags.extend(tags)
        self.updatedDate = datetime.now(timezone.utc)

    def get_search_score(self) -> Optional[float]:
        """Get the similarity score if this document was returned from a search."""
        return getattr(self, "similarity", None)

    def set_search_score(self, score: float):
        """Set the similarity score for search results."""
        setattr(self, "similarity", score)

    def is_rss_item(self) -> bool:
        """Check if this document was created from an RSS feed item."""
        return self.rss_feed_url is not None and self.rss_item_id is not None

    def is_wordpress_item(self) -> bool:
        """Check if this document was created from a WordPress JSON API."""
        return self.json_url is not None

    def get_author(self) -> Optional[str]:
        """Get the author of the document, checking multiple sources."""
        if self.rss_author:
            return self.rss_author
        if self.metadata and "author" in self.metadata:
            return self.metadata["author"]
        return None

    def get_published_date(self) -> Optional[datetime]:
        """Get the published date of the document, checking multiple sources."""
        if self.rss_published_date:
            try:
                return datetime.fromisoformat(self.rss_published_date)
            except (ValueError, TypeError):
                pass
        return self.createdDate
