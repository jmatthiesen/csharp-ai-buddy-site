#!/usr/bin/env python3
"""
Command Line Interface for RAG Data Pipeline
Provides CLI commands for document management operations.
"""

import json
import argparse
import logging
from typing import Optional, List, Dict, Any

from config import Config
from dataIngestion.document_pipeline import DocumentPipeline
from web_page_retriever import WebPageRetriever
from pipeline_types import RawDocument

logger = logging.getLogger(__name__)


class RAGDataPipelineCLI:
    """Command line interface for RAG data pipeline operations."""

    def __init__(self, what_if_mode: bool = False):
        self.what_if_mode = what_if_mode
        if what_if_mode:
            print("🔍 Running in WHAT-IF mode - no actual changes will be made")
            # Create a minimal config for what-if mode
            self.config = Config(
                mongodb_connection_string="dummy-connection",
                mongodb_database="dummy-db",
                mongodb_collection="dummy-collection",
                openai_api_key="dummy-key",
            )
            self.config.mongodb_chunks_collection = "dummy-chunks"
            self.config.embedding_model = "text-embedding-ada-002"
        else:
            self.config = Config.load()

        self.pipeline = DocumentPipeline(self.config, what_if_mode=what_if_mode)
        self.web_retriever = WebPageRetriever()

    def add_document_from_url(
        self,
        source_url: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        use_ai_categorization: bool = True,
        crawl_links: bool = False,
        processed_urls: Optional[set] = None,
    ) -> str:
        """
        Add a new document from a URL.

        Args:
            source_url: URL to fetch content from
            tags: Optional tags for the document
            metadata: Optional metadata dictionary
            use_ai_categorization: Whether to use AI for categorization
            crawl_links: Whether to crawl links found in the document
            processed_urls: Set of URLs already processed (for crawling)

        Returns:
            str: Document ID of the added document
        """
        try:
            # Initialize processed URLs set if not provided
            if processed_urls is None:
                processed_urls = set()

            # Skip if URL already processed
            if source_url in processed_urls:
                logger.info(f"Skipping already processed URL: {source_url}")
                return None

            # Add current URL to processed set
            processed_urls.add(source_url)

            print(f"Processing: {source_url}")

            # Test URL with host-specific fallback logic
            tested_url = self._test_url_with_fallback(source_url)
            if tested_url != source_url:
                print(f"Using fallback URL: {tested_url}")
                source_url = tested_url

            # Fetch content from URL
            raw_document = self.web_retriever.fetch(source_url)

            # Add any provided tags
            if tags:
                raw_document.tags.extend(tags)

            # Process and store through pipeline with chunking
            processing_context = self.pipeline.process_document(
                raw_doc=raw_document,
                use_ai_categorization=use_ai_categorization,
                additional_metadata=metadata,
            )

            stored_chunk_ids = processing_context.processing_metadata.get(
                "stored_chunk_ids", []
            )
            document_id = stored_chunk_ids[0] if stored_chunk_ids else None
            logger.info(f"Successfully added document from URL: {source_url}")
            print(f"✓ Document processed successfully: {source_url}")

            # Handle link crawling if enabled
            if crawl_links and processing_context.extracted_links:
                print(
                    f"\nFound {len(processing_context.extracted_links)} crawlable links:"
                )

                # Display links for user selection
                selected_links = self._prompt_user_for_link_selection(
                    processing_context.extracted_links
                )

                if selected_links:
                    print(f"\nCrawling {len(selected_links)} selected links...")

                    # Recursively process selected links
                    for link in selected_links:
                        try:
                            self.add_document_from_url(
                                source_url=link["url"],
                                tags=tags,
                                metadata=metadata,
                                use_ai_categorization=use_ai_categorization,
                                crawl_links=crawl_links,
                                processed_urls=processed_urls,
                            )
                        except Exception as link_error:
                            print(
                                f"⚠ Error processing link {link['url']}: {link_error}"
                            )
                            logger.error(
                                f"Error processing link {link['url']}: {link_error}"
                            )
                else:
                    print("No links selected for crawling.")
            elif crawl_links:
                print("No crawlable links found in this document.")

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
            logger.warning("Update functionality not supported in new architecture")
            logger.info(
                "To update a document, delete the old chunks and re-add the document"
            )
            return False

        except Exception as e:
            logger.error(f"Error updating document {document_id}: {e}")
            raise

    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document."""
        try:
            # Delete all chunks for this document
            chunks = self.pipeline.get_document_chunks(document_id)
            if not chunks:
                logger.warning(f"No chunks found for document: {document_id}")
                return False

            # Delete each chunk
            deleted_count = 0
            for chunk in chunks:
                try:
                    result = self.pipeline.chunks_collection.delete_one(
                        {"chunk_id": chunk.chunk_id}
                    )
                    if result.deleted_count > 0:
                        deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting chunk {chunk.chunk_id}: {e}")

            logger.info(f"Deleted {deleted_count} chunks for document: {document_id}")
            return deleted_count > 0

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document."""
        chunks = self.pipeline.get_document_chunks(document_id)
        return [chunk.to_dict() for chunk in chunks]

    def search_documents(
        self, query: str, tags: Optional[List[str]] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search document chunks."""
        return self.pipeline.search_chunks(query=query, tags=tags, limit=limit)

    def list_document_chunks(
        self, tags: Optional[List[str]] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List recent document chunks."""
        try:
            filter_query = {}
            if tags:
                filter_query["tags"] = {"$in": tags}

            cursor = (
                self.pipeline.chunks_collection.find(filter_query)
                .sort("indexed_date", -1)
                .limit(limit)
            )

            results = []
            for chunk_data in cursor:
                results.append(
                    {
                        "chunk_id": chunk_data["chunk_id"],
                        "title": chunk_data["title"],
                        "source_url": chunk_data["source_url"],
                        "tags": chunk_data["tags"],
                        "indexed_date": chunk_data["indexed_date"],
                        "chunk_index": chunk_data.get("chunk_index", 0),
                        "total_chunks": chunk_data.get("total_chunks", 1),
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error listing chunks: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        try:
            # Get basic statistics from the chunks collection
            total_chunks = self.pipeline.chunks_collection.count_documents({})

            # Get unique document count
            unique_docs = len(self.pipeline.chunks_collection.distinct("sourceUrl"))

            # Get tag statistics
            all_tags = []
            for doc in self.pipeline.chunks_collection.find({}, {"tags": 1}):
                all_tags.extend(doc.get("tags", []))

            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            return {
                "total_chunks": total_chunks,
                "unique_documents": unique_docs,
                "total_tags": len(tag_counts),
                "most_common_tags": sorted(
                    tag_counts.items(), key=lambda x: x[1], reverse=True
                )[:10],
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}

    def cleanup_old_documents(self) -> Dict[str, Any]:
        """Clean up old documents from previous architecture."""
        return self.pipeline.cleanup_old_documents()

    def _prompt_user_for_link_selection(
        self, links: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Prompt user to select which links to crawl.

        Args:
            links: List of link dictionaries with 'url', 'text', 'title' keys

        Returns:
            List of selected link dictionaries
        """
        try:
            if not links:
                return []

            print("\nAvailable links to crawl:")
            print("=" * 60)

            # Display links with numbers
            for i, link in enumerate(links, 1):
                text_display = (
                    link["text"][:50] + "..."
                    if len(link["text"]) > 50
                    else link["text"]
                )
                print(f"{i:2d}. {text_display}")
                print(f"    URL: {link['url']}")
                if link.get("title"):
                    print(f"    Title: {link['title']}")
                print()

            print("Selection options:")
            print("  - Enter link numbers separated by commas (e.g., 1,3,5)")
            print("  - Enter 'all' to select all links")
            print("  - Enter 'none' or just press Enter to skip crawling")
            print("  - Enter 'stop' to stop crawling entirely")

            while True:
                try:
                    user_input = input("\nSelect links to crawl: ").strip().lower()

                    if not user_input or user_input == "none":
                        return []

                    if user_input == "stop":
                        print("Stopping crawling process.")
                        return []

                    if user_input == "all":
                        print(f"Selected all {len(links)} links for crawling.")
                        return links

                    # Parse comma-separated numbers
                    try:
                        selected_indices = [
                            int(x.strip()) for x in user_input.split(",")
                        ]
                        selected_links = []

                        for index in selected_indices:
                            if 1 <= index <= len(links):
                                selected_links.append(links[index - 1])
                            else:
                                print(
                                    f"Invalid link number: {index}. Please use numbers 1-{len(links)}."
                                )
                                break
                        else:
                            # All indices were valid
                            print(f"Selected {len(selected_links)} links for crawling.")
                            return selected_links

                    except ValueError:
                        print(
                            "Invalid input. Please enter numbers separated by commas, 'all', 'none', or 'stop'."
                        )

                except KeyboardInterrupt:
                    print("\nCrawling cancelled by user.")
                    return []
                except EOFError:
                    print("\nNo input received. Skipping crawling.")
                    return []

        except Exception as e:
            logger.error(f"Error in user link selection: {e}")
            return []

    def _test_url_with_fallback(self, url: str) -> str:
        """
        Test URL with host-specific fallback logic.

        Args:
            url: The URL to test

        Returns:
            The working URL (original or fallback)
        """
        try:
            # Find the appropriate host handler for the URL
            for handler in self.pipeline.host_handlers:
                if handler.can_handle(url):
                    tested_url = handler.get_url_with_fallback(url)
                    if tested_url:
                        return tested_url
                    # Only apply the first matching handler (except fallback)
                    if handler.name != "Fallback":
                        break

            # If no handler found a working URL, return original
            return url
        except Exception as e:
            logger.warning(f"Error testing URL with fallback: {e}")
            return url


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(description="RAG Data Ingestion Pipeline CLI")
    parser.add_argument(
        "--what-if",
        action="store_true",
        help="Run in what-if mode - show what would happen without making actual changes",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add document command
    add_parser = subparsers.add_parser("add", help="Add a new document from URL")
    add_parser.add_argument("--source-url", required=True, help="Source URL")
    add_parser.add_argument("--tags", nargs="+", help="Framework tags for the document")
    add_parser.add_argument("--metadata", help="JSON metadata string")
    add_parser.add_argument(
        "--no-ai-categorization", action="store_true", help="Disable AI categorization"
    )
    add_parser.add_argument(
        "--crawl-links", action="store_true", help="Crawl links found in the document"
    )

    # Update document command
    update_parser = subparsers.add_parser("update", help="Update an existing document")
    update_parser.add_argument(
        "--document-id", required=True, help="Document ID to update"
    )
    update_parser.add_argument("--tags", nargs="+", help="New tags")
    update_parser.add_argument("--metadata", help="JSON metadata string")

    # Delete document command
    delete_parser = subparsers.add_parser("delete", help="Delete a document")
    delete_parser.add_argument(
        "--document-id", required=True, help="Document ID to delete"
    )

    # Get document command
    get_parser = subparsers.add_parser("get", help="Get a document")
    get_parser.add_argument(
        "--document-id", required=True, help="Document ID to retrieve"
    )

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
    cli = RAGDataPipelineCLI(what_if_mode=args.what_if)

    try:
        if args.command == "add":
            metadata = json.loads(args.metadata) if args.metadata else {}
            doc_id = cli.add_document_from_url(
                source_url=args.source_url,
                tags=args.tags,
                metadata=metadata,
                use_ai_categorization=not args.no_ai_categorization,
                crawl_links=args.crawl_links,
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
            results = cli.search_documents(
                query=args.query, tags=args.tags, limit=args.limit
            )
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
