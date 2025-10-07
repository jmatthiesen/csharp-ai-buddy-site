#!/usr/bin/env python3
"""
Core types for the refactored document processing pipeline.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class RawDocument:
    """Input to the pipeline - minimal, flexible structure"""

    content: str  # Raw content (HTML, text, markdown, etc.)
    source_url: str
    title: Optional[str] = None
    summary: Optional[str] = None
    content_type: str = "html"  # html, markdown, text, rss
    source_metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_date: Optional[datetime] = None


@dataclass
class ProcessingContext:
    """Mutable context that travels through pipeline stages"""

    # Source document
    raw_document: RawDocument

    # Processing options
    use_ai_categorization: bool = True
    chunk_size: int = 4000

    # Pipeline state (mutated by stages)
    markdown_content: Optional[str] = None
    chunks: List[str] = field(default_factory=list)
    chunk_embeddings: List[List[float]] = field(default_factory=list)
    extracted_links: List[Dict[str, str]] = field(default_factory=list)

    # Accumulated metadata and tags
    user_metadata: Dict[str, Any] = field(default_factory=dict)
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
    final_tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize final_tags with raw document tags"""
        self.final_tags.extend(self.raw_document.tags)

    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Processing history for debugging
    stages_completed: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add an error to the context"""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add a warning to the context"""
        self.warnings.append(warning)

    def mark_stage_complete(self, stage_name: str) -> None:
        """Mark a pipeline stage as completed"""
        self.stages_completed.append(stage_name)


@dataclass
class Chunk:
    """Final processed unit for MongoDB storage - streamlined for storage efficiency"""

    # Identifiers
    chunk_id: str

    # Content (only markdown content stored)
    title: str
    source_url: str
    content: str  # This is the markdown content
    embeddings: List[float] = field(default_factory=list)

    # Chunk metadata
    chunk_index: int = 0
    total_chunks: int = 1
    chunk_size: int = 0

    # Document metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    # Timestamps
    created_date: Optional[datetime] = None
    indexed_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings for MongoDB compatibility
        if data.get("created_date"):
            data["created_date"] = data["created_date"].isoformat()
        if data.get("indexed_date"):
            data["indexed_date"] = data["indexed_date"].isoformat()
        return data
