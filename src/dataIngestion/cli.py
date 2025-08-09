#!/usr/bin/env python3
"""
Command Line Interface for RAG Data Pipeline
Provides CLI commands for document management operations.
"""

import argparse
import json
import logging
from typing import Any, Dict, List, Optional

from config import Config
from document import Document
from document_pipeline import DocumentPipeline
from web_page_retriever import WebPageRetriever

logger = logging.getLogger(__name__)


class RAGDataPipelineCLI:
    """Command line interface for RAG data pipeline operations."""

    def __init__(self):
        self.config = Config.load()
        self.pipeline = DocumentPipeline(self.config)
        self.web_retriever = WebPageRetriever()

    def add_document_from_url(
        self,
        source_url: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        use_ai_categorization: bool = True,
    ) -> str:
        """
        Add a new document from a URL.

        Args:
            source_url: URL to fetch content from
            tags: Optional tags for the document
            metadata: Optional metadata dictionary
            use_ai_categorization: Whether to use AI for categorization

        Returns:
            str: Document ID of the added document
        """
        try:
            # Fetch content from URL
            document = self.web_retriever.fetch(source_url)

            # Add any provided tags
            if tags:
                if document.tags is None:
                    document.tags = []
                document.tags.extend(tags)

            # Process and store through pipeline with chunking
            stored_ids = self.pipeline.process_and_store_document(
                document=document,
                use_ai_categorization=use_ai_categorization,
                additional_metadata=metadata,
                use_chunking=True,
            )

            document_id = stored_ids[0] if stored_ids else None

            logger.info(f"Successfully added document from URL: {source_url}")
            return document_id

        except Exception as e:
            logger.error(f"Error adding document from URL {source_url}: {e}")
            raise

    def update_document_from_url(
        self,
        document_id: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update an existing document by re-fetching from its source URL.

        Args:
            document_id: Document ID to update
            tags: New tags (if provided)
            metadata: New metadata (if provided)

        Returns:
            bool: True if update was successful
        """
        try:
            # Get existing document
            existing_doc = self.pipeline.get_document(document_id)
            if not existing_doc:
                logger.error(f"Document {document_id} not found")
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

            # For updates, use non-chunking approach to maintain document integrity
            processed_document = self.pipeline.process_document(
                document=updated_document, use_ai_categorization=True
            )

            # Update in database
            success = self.pipeline.update_document(processed_document)

            if success:
                logger.info(f"Successfully updated document: {document_id}")

            return success

        except Exception as e:
            logger.error(f"Error updating document {document_id}: {e}")
            raise

    def delete_document(self, document_id: str) -> bool:
        """Delete a document."""
        return self.pipeline.delete_document(document_id)

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self.pipeline.get_document(document_id)

    def search_documents(
        self, query: str, tags: Optional[List[str]] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search documents."""
        return self.pipeline.search_documents(query=query, tags=tags, limit=limit)

    def list_documents(self, tags: Optional[List[str]] = None, limit: int = 50) -> List[Document]:
        """List documents."""
        return self.pipeline.list_documents(tags=tags, limit=limit)

    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return self.pipeline.get_statistics()


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(description="RAG Data Ingestion Pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add document command
    add_parser = subparsers.add_parser("add", help="Add a new document from URL")
    add_parser.add_argument("--source-url", required=True, help="Source URL")
    add_parser.add_argument("--tags", nargs="+", help="Framework tags for the document")
    add_parser.add_argument("--metadata", help="JSON metadata string")
    add_parser.add_argument(
        "--no-ai-categorization", action="store_true", help="Disable AI categorization"
    )

    # Update document command
    update_parser = subparsers.add_parser("update", help="Update an existing document")
    update_parser.add_argument("--document-id", required=True, help="Document ID to update")
    update_parser.add_argument("--tags", nargs="+", help="New tags")
    update_parser.add_argument("--metadata", help="JSON metadata string")

    # Delete document command
    delete_parser = subparsers.add_parser("delete", help="Delete a document")
    delete_parser.add_argument("--document-id", required=True, help="Document ID to delete")

    # Get document command
    get_parser = subparsers.add_parser("get", help="Get a document")
    get_parser.add_argument("--document-id", required=True, help="Document ID to retrieve")

    # Search documents command
    search_parser = subparsers.add_parser("search", help="Search documents")
    search_parser.add_argument("--query", required=True, help="Search query")
    search_parser.add_argument("--tags", nargs="+", help="Filter by tags")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum results")

    # List documents command
    list_parser = subparsers.add_parser("list", help="List documents")
    list_parser.add_argument("--tags", nargs="+", help="Filter by tags")
    list_parser.add_argument("--limit", type=int, default=50, help="Maximum results")

    # Statistics command
    stats_parser = subparsers.add_parser("stats", help="Get pipeline statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize CLI
    cli = RAGDataPipelineCLI()

    try:
        if args.command == "add":
            metadata = json.loads(args.metadata) if args.metadata else {}
            doc_id = cli.add_document_from_url(
                source_url=args.source_url,
                tags=args.tags,
                metadata=metadata,
                use_ai_categorization=not args.no_ai_categorization,
            )
            print(f"Document added with ID: {doc_id}")

        elif args.command == "update":
            metadata = json.loads(args.metadata) if args.metadata else None
            success = cli.update_document_from_url(
                document_id=args.document_id, tags=args.tags, metadata=metadata
            )
            print(f"Update {'successful' if success else 'failed'}")

        elif args.command == "delete":
            success = cli.delete_document(args.document_id)
            print(f"Deletion {'successful' if success else 'failed'}")

        elif args.command == "get":
            document = cli.get_document(args.document_id)
            if document:
                print(json.dumps(document.to_dict(), indent=2, default=str))
            else:
                print("Document not found")

        elif args.command == "search":
            results = cli.search_documents(query=args.query, tags=args.tags, limit=args.limit)
            print(json.dumps(results, indent=2, default=str))

        elif args.command == "list":
            documents = cli.list_documents(tags=args.tags, limit=args.limit)
            doc_dicts = [doc.to_dict() for doc in documents]
            print(json.dumps(doc_dicts, indent=2, default=str))

        elif args.command == "stats":
            stats = cli.get_statistics()
            print(json.dumps(stats, indent=2, default=str))

    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
