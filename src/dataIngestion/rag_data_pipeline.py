#!/usr/bin/env python3
"""
RAG Data Ingestion Pipeline
A Python script for managing documents in a RAG (Retrieval-Augmented Generation) solution.
Supports adding, updating, and deleting documents with MongoDB storage and OpenAI embeddings.
"""

import os
import json
import argparse
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
import logging
from io import BytesIO

# MongoDB
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# OpenAI for embeddings
import openai
from openai import OpenAI

# MarkItDown for conversion
from markitdown import MarkItDown, StreamInfo

# Vector operations
import numpy as np
from urllib3.util import url

# Configuration
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag


class RAGDataPipeline:
    """Main class for managing RAG document pipeline operations."""
    
    def __init__(self, config: Config):
        """Initialize the pipeline with configuration."""
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.mongo_client = MongoClient(config.mongodb_connection_string)
        self.db = self.mongo_client[config.mongodb_database]
        self.documents_collection = self.db[config.mongodb_collection]
        
        # Initialize MarkItDown
        self.markitdown = MarkItDown()
        
        # Create indexes for efficient querying
        self._create_indexes()
    
    def _create_indexes(self):
        """Create MongoDB indexes for efficient querying."""
        try:
            # Index on document_id for fast lookups
            self.documents_collection.create_index("documentId", unique=True)
            
            # Index on tags for filtering
            self.documents_collection.create_index("tags")
            
            # Index on source_url for deduplication
            self.documents_collection.create_index("sourceUrl")
            
            # Index on created_at for time-based queries
            self.documents_collection.create_index("createdDate")
            
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")
    
    def _generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text using OpenAI."""
        try:
            response = self.client.embeddings.create(
                model=self.config.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def _convert_to_markdown(self, document: Dict[str, Any]) -> str:
        """Convert content to markdown using MarkItDown, with support for alternate JSON if available."""
        if document["content"] and document["documentId"]:
            try:
                html_content_bytes = BytesIO(document["content"].encode("utf-8"))
                            
                # Pass HTML string to markitdown
                return self.markitdown.convert(source=html_content_bytes,
                    stream_info=StreamInfo(extension=".html")).markdown
            except Exception as e:
                logger.warning(f"Error checking for alternate JSON or parsing, falling back to default.")
            # Fallback to default logic
            result = self.markitdown.convert(document["documentId"])
            return result.markdown
        else:
            return ""
    
    def _get_document(self, path_or_url: str) -> Dict[str, Any]:
        """
        Fetch and parse a document from a URL or path, extracting metadata if available.
        Returns a dictionary with at least: documentId, title, content, sourceUrl.
        """
        document: Dict[str, Any] = {
            "documentId": path_or_url,
            "title": "",
            "content": "",
            "sourceUrl": path_or_url
        }
        if isinstance(path_or_url, str) and (path_or_url.startswith('http://') or path_or_url.startswith('https://')):
            try:
                resp = requests.get(path_or_url, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
                link = soup.find('link', rel='alternate', type='application/json')
                json_url = None
                if link and isinstance(link, Tag):
                    href = link.get('href')
                    if isinstance(href, str):
                        json_url = href
                if json_url:
                    if not json_url.startswith('http'):
                        from urllib.parse import urljoin
                        json_url = urljoin(path_or_url, json_url)
                    json_resp = requests.get(json_url, timeout=10)
                    json_resp.raise_for_status()
                    data = json_resp.json()
                    # Extract title and content
                    document["title"] = data.get('title', {}).get('rendered', '')
                    document["content"] = data.get('content', {}).get('rendered', '')
                    document["createdDate"] = self._get_iso_date(data.get('date_gmt'))
                    document["updatedDate"] = self._get_iso_date(data.get('modified_gmt'))
                    document["json_url"] = json_url
            except Exception as e:
                logger.warning(f"_get_document: Error checking for alternate JSON or parsing, falling back to minimal document. Error: {e}")
        return document
    
    def _get_iso_date(self, source_date: str) -> datetime | None:
        if isinstance(source_date, str) and not source_date.endswith("Z"):
            created_gmt = source_date + "Z"
            if source_date:
                # Try parsing as ISO 8601 string
                return datetime.fromisoformat(created_gmt)

    def add_document(self, 
                    source_url: str,
                    tags: Optional[List[str]] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    use_ai_categorization: bool = True) -> str:
        """
        Add a new document to the RAG pipeline.
        
        Args:
            source_url: URL where the content was sourced from
            tags: List of tags for filtering (e.g., framework names)
            metadata: Additional metadata dictionary
            use_ai_categorization: Whether to use AI for automatic framework categorization
            
        Returns:
            document_id: The unique identifier for the added document
        """
        try:
            # Get info about the URL that was passed in
            document = self._get_document(source_url)

            # Convert content to markdown (with alternate JSON support handled inside)
            markdown_content = self._convert_to_markdown(document)
            
            # Generate embeddings
            embeddings = self._generate_embeddings(markdown_content)
            
            # Auto-categorize with AI if enabled and no tags provided
            final_tags = tags or []
            if use_ai_categorization:
                from dotnet_sdk_tags import categorize_with_ai, suggest_tags_simple
                
                # Try AI categorization first
                ai_tags = categorize_with_ai(markdown_content, self.client)
                if ai_tags:
                    final_tags += ai_tags
                    logger.info(f"AI categorized document with tags: {ai_tags}")
                else:
                    # Fallback to simple keyword matching
                    final_tags += suggest_tags_simple(markdown_content)
                    logger.info(f"Used simple categorization with tags: {final_tags}")
            
            document["markdownContent"]=markdown_content
            document["embeddings"]=embeddings
            document["tags"]=final_tags,
            document["indexedDate"]=datetime.now(timezone.utc)
            
            # Insert into MongoDB
            result = self.documents_collection.insert_one(document)
            
            logger.info(f"Document added successfully with ID: {document["documentId"]}")
            return document["documentId"]
            
        except DuplicateKeyError:
            logger.error("Document with this ID already exists")
            raise
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            raise
    
    def update_document(self, 
                       url_or_path: str,
                       tags: Optional[List[str]] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an existing document.
        
        Args:
            document_id: The document ID to update
            content: New content (if provided)
            tags: New tags (if provided)
            metadata: New metadata (if provided)
            
        Returns:
            bool: True if update was successful
        """
        try:            
            if url_or_path is not None:
                document = self._get_document(url_or_path)
                markdown_content = self._convert_to_markdown(document)
                embeddings = self._generate_embeddings(markdown_content)
                update_data = {
                    "markdown_content": markdown_content,
                    "embeddings": embeddings,
                    "updated_at": datetime.now(timezone.utc)
                }
            
            if tags is not None:
                update_data["tags"] = tags
            
            if metadata is not None:
                update_data["metadata"] = metadata
            
            result = self.documents_collection.update_one(
                {"documentId": url_or_path},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                logger.warning(f"Document with ID {url_or_path} not found")
                return False
            
            logger.info(f"Document {url_or_path} updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the pipeline.
        
        Args:
            document_id: The document ID to delete
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            result = self.documents_collection.delete_one({"documentId": document_id})
            
            if result.deleted_count == 0:
                logger.warning(f"Document with ID {document_id} not found")
                return False
            
            logger.info(f"Document {document_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        try:
            document = self.documents_collection.find_one({"documentId": document_id})
            if document:
                # Remove MongoDB ObjectId for JSON serialization
                document.pop("_id", None)
            return document
        except Exception as e:
            logger.error(f"Error retrieving document: {e}")
            raise
    
    def search_documents(self, 
                        query: str,
                        tags: Optional[List[str]] = None,
                        limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search documents using vector similarity and optional tag filtering.
        
        Args:
            query: Search query text
            tags: Optional tags to filter by
            limit: Maximum number of results
            
        Returns:
            List of matching documents with similarity scores
        """
        try:
            # Generate embeddings for the query
            query_embeddings = self._generate_embeddings(query)
            
            # Build aggregation pipeline
            pipeline = []
            
            # Filter by tags if provided
            if tags:
                pipeline.append({"$match": {"tags": {"$in": tags}}})
            
            # Add vector similarity search
            pipeline.extend([
                {
                    "$addFields": {
                        "similarity": {
                            "$reduce": {
                                "input": {"$range": [0, {"$size": "$embeddings"}]},
                                "initialValue": 0,
                                "in": {
                                    "$add": [
                                        "$$value",
                                        {
                                            "$multiply": [
                                                {"$arrayElemAt": ["$embeddings", "$$this"]},
                                                {"$arrayElemAt": [query_embeddings, "$$this"]}
                                            ]
                                        }
                                    ]
                                }
                            }
                        }
                    }
                },
                {"$sort": {"similarity": -1}},
                {"$limit": limit},
                {"$project": {"_id": 0}}
            ])
            
            results = list(self.documents_collection.aggregate(pipeline))
            logger.info(f"Found {len(results)} documents matching query")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    def list_documents(self, 
                      tags: Optional[List[str]] = None,
                      limit: int = 50) -> List[Dict[str, Any]]:
        """List documents with optional tag filtering."""
        try:
            filter_query = {}
            if tags:
                filter_query["tags"] = {"$in": tags}
            
            documents = list(self.documents_collection.find(
                filter_query,
                {"_id": 0}
            ).sort("created_at", -1).limit(limit))
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        try:
            total_documents = self.documents_collection.count_documents({})
            
            # Get tag statistics
            tag_stats = list(self.documents_collection.aggregate([
                {"$unwind": "$tags"},
                {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]))
            
            # Get source type statistics
            source_stats = list(self.documents_collection.aggregate([
                {"$group": {"_id": "$source_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]))
            
            return {
                "total_documents": total_documents,
                "tag_statistics": tag_stats,
                "source_type_statistics": source_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            raise


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(description="RAG Data Ingestion Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add document command
    add_parser = subparsers.add_parser("add", help="Add a new document")
    add_parser.add_argument("--source-url", help="Source URL")
    add_parser.add_argument("--tags", nargs="+", help="Framework tags for the document")
    add_parser.add_argument("--metadata", help="JSON metadata string")
    add_parser.add_argument("--no-ai-categorization", action="store_true", help="Disable AI categorization")
    
    # Update document command
    update_parser = subparsers.add_parser("update", help="Update an existing document")
    update_parser.add_argument("--url-or-path", required=True, help="URL or path to document to update")
    update_parser.add_argument("--tags", nargs="+", help="New tags")
    update_parser.add_argument("--metadata", help="JSON metadata string")
    
    # Delete document command
    delete_parser = subparsers.add_parser("delete", help="Delete a document")
    delete_parser.add_argument("--url-or-path", required=True, help="URL or path of document to delete")
    
    # Get document command
    get_parser = subparsers.add_parser("get", help="Get a document")
    get_parser.add_argument("--url-or-path", required=True, help="URL or path of document to retrieve")
    
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
    
    # Load configuration
    config = Config.load()
    pipeline = RAGDataPipeline(config)
    
    try:
        if args.command == "add":
            metadata = json.loads(args.metadata) if args.metadata else {}
            doc_id = pipeline.add_document(
                source_url=args.source_url,
                tags=args.tags,
                metadata=metadata,
                use_ai_categorization=True
            )
            print(f"Document added with ID: {doc_id}")
            
        elif args.command == "update":
            metadata = json.loads(args.metadata) if args.metadata else None
            success = pipeline.update_document(
                url_or_path=args.url_or_path,
                tags=args.tags,
                metadata=metadata
            )
            print(f"Update {'successful' if success else 'failed'}")
            
        elif args.command == "delete":
            success = pipeline.delete_document(args.document_id)
            print(f"Deletion {'successful' if success else 'failed'}")
            
        elif args.command == "get":
            document = pipeline.get_document(args.document_id)
            if document:
                print(json.dumps(document, indent=2, default=str))
            else:
                print("Document not found")
                
        elif args.command == "search":
            results = pipeline.search_documents(
                query=args.query,
                tags=args.tags,
                limit=args.limit
            )
            print(json.dumps(results, indent=2, default=str))
            
        elif args.command == "list":
            documents = pipeline.list_documents(
                tags=args.tags,
                limit=args.limit
            )
            print(json.dumps(documents, indent=2, default=str))
            
        elif args.command == "stats":
            stats = pipeline.get_statistics()
            print(json.dumps(stats, indent=2, default=str))
            
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 