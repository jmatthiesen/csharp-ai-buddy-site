#!/usr/bin/env python3
"""
RAG Data Ingestion Pipeline (Legacy Compatibility Layer)
This module provides backward compatibility with the original interface while using the new refactored components.
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# New refactored components
from config import Config
from document import Document
from document_pipeline import DocumentPipeline
from web_page_retriever import WebPageRetriever

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGDataPipeline:
    """Legacy compatibility layer for the original RAG pipeline interface."""

    def __init__(self, config: Config):
        """Initialize the pipeline with configuration."""
        self.config = config

        # Use new refactored components
        self.document_pipeline = DocumentPipeline(config)
        self.web_retriever = WebPageRetriever()

        # Expose database collections for backward compatibility
        self.mongo_client = self.document_pipeline.mongo_client
        self.db = self.document_pipeline.db
        self.documents_collection = self.document_pipeline.documents_collection

    def _create_indexes(self):
        """Create MongoDB indexes (delegated to document pipeline)."""
        return self.document_pipeline._create_indexes()

    def _generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings (delegated to document pipeline)."""
        return self.document_pipeline.generate_embeddings(text)

    def _convert_to_markdown(self, document: Dict[str, Any]) -> str:
        """Convert content to markdown (legacy compatibility method)."""
        # Convert old dictionary format to Document object
        doc = Document(
            documentId=document.get("documentId", ""),
            title=document.get("title", ""),
            content=document.get("content", ""),
            sourceUrl=document.get("sourceUrl", ""),
            createdDate=document.get("createdDate"),
            updatedDate=document.get("updatedDate"),
            json_url=document.get("json_url"),
        )
        return self.document_pipeline.convert_to_markdown(doc)

    def _get_document(self, path_or_url: str) -> Dict[str, Any]:
        """Fetch document (legacy compatibility method)."""
        # Use new web retriever
        document = self.web_retriever.fetch(path_or_url)

        # Convert back to old dictionary format
        return {
            "documentId": document.documentId,
            "title": document.title,
            "content": document.content,
            "sourceUrl": document.sourceUrl,
            "createdDate": document.createdDate,
            "updatedDate": document.updatedDate,
            "json_url": document.json_url,
        }

    def _get_iso_date(self, source_date: str) -> Optional[datetime]:
        """Parse ISO date string."""
        if isinstance(source_date, str) and not source_date.endswith("Z"):
            created_gmt = source_date + "Z"
            if source_date:
                try:
                    return datetime.fromisoformat(created_gmt)
                except (ValueError, TypeError):
                    return None
        return None

    def add_document(
        self,
        source_url: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        use_ai_categorization: bool = True,
        pre_parsed_content: Optional[str] = None,
    ) -> str:
        """
        Add a new document to the RAG pipeline (legacy compatibility method).
        """
        try:
            if pre_parsed_content:
                # Create document from pre-parsed content
                document = Document(
                    documentId=source_url,
                    title="",
                    content=pre_parsed_content,
                    sourceUrl=source_url,
                    tags=tags or [],
                )
            else:
                # Fetch document from URL
                document = self.web_retriever.fetch(source_url)
                if tags:
                    if document.tags is None:
                        document.tags = []
                    document.tags.extend(tags)

            # Process through new pipeline
            processed_document = self.document_pipeline.process_document(
                document=document,
                use_ai_categorization=use_ai_categorization,
                additional_metadata=metadata,
            )

            # Store using new pipeline
            return self.document_pipeline.store_document(processed_document)

        except Exception as e:
            logger.error(f"Error adding document: {e}")
            raise

    def update_document(
        self,
        url_or_path: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update an existing document (legacy compatibility method).
        """
        try:
            # Get existing document
            existing_doc = self.document_pipeline.get_document(url_or_path)
            if not existing_doc:
                logger.warning(f"Document with ID {url_or_path} not found")
                return False

            # Re-fetch content from source URL
            updated_document = self.web_retriever.fetch(existing_doc.sourceUrl)

            # Preserve original document ID and dates
            updated_document.documentId = existing_doc.documentId
            updated_document.createdDate = existing_doc.createdDate

            # Update tags if provided
            if tags is not None:
                updated_document.tags = tags
            else:
                updated_document.tags = existing_doc.tags

            # Merge metadata
            if metadata is not None:
                if updated_document.metadata is None:
                    updated_document.metadata = {}
                updated_document.metadata.update(metadata)
            elif existing_doc.metadata:
                updated_document.metadata = existing_doc.metadata

            # Process through pipeline
            processed_document = self.document_pipeline.process_document(
                document=updated_document, use_ai_categorization=True
            )

            # Update in database
            return self.document_pipeline.update_document(processed_document)

        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise

    def delete_document(self, document_id: str) -> bool:
        """Delete a document (delegated to document pipeline)."""
        return self.document_pipeline.delete_document(document_id)

    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by ID (delegated to document pipeline)."""
        return self.document_pipeline.get_document(document_id)

    def search_documents(
        self, query: str, tags: Optional[List[str]] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search documents (delegated to document pipeline)."""
        return self.document_pipeline.search_documents(query=query, tags=tags, limit=limit)

    def list_documents(self, tags: Optional[List[str]] = None, limit: int = 50) -> List[Document]:
        """List documents (delegated to document pipeline)."""
        return self.document_pipeline.list_documents(tags=tags, limit=limit)

    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics (delegated to document pipeline)."""
        return self.document_pipeline.get_statistics()


def main():
    """Main function for command-line interface (legacy compatibility)."""
    # Delegate to the new CLI module
    from cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    import sys

    sys.exit(main())
