#!/usr/bin/env python3
"""
Document Processing Pipeline for RAG Data Ingestion
Core pipeline that processes documents through various stages: markdown conversion, embeddings, categorization.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from io import BytesIO

# MongoDB
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# OpenAI for embeddings
from openai import OpenAI

# MarkItDown for conversion
from markitdown import MarkItDown, StreamInfo

# Configuration
from config import Config

# Document type
from document import Document

logger = logging.getLogger(__name__)


class DocumentPipeline:
    """Core document processing pipeline."""
    
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
    
    def convert_to_markdown(self, document: Document) -> str:
        """
        Convert document content to markdown using MarkItDown.
        
        Args:
            document: Document to convert
            
        Returns:
            str: Markdown content
        """
        if not document.content:
            return ""
            
        try:
            html_content_bytes = BytesIO(document.content.encode("utf-8"))
            
            # Pass HTML string to markitdown
            result = self.markitdown.convert(
                source=html_content_bytes,
                stream_info=StreamInfo(extension=".html")
            )
            return result.markdown
            
        except Exception as e:
            logger.warning(f"Error converting to markdown, falling back to document ID conversion: {e}")
            try:
                # Fallback to document ID based conversion
                result = self.markitdown.convert(document.documentId)
                return result.markdown
            except Exception as fallback_error:
                logger.error(f"Fallback markdown conversion also failed: {fallback_error}")
                return ""
    
    def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for text using OpenAI.
        
        Args:
            text: Text to generate embeddings for
            
        Returns:
            List[float]: Vector embeddings
        """
        try:
            response = self.client.embeddings.create(
                model=self.config.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def categorize_document(self, markdown_content: str, existing_tags: Optional[List[str]] = None) -> List[str]:
        """
        Categorize document using AI or simple keyword matching.
        
        Args:
            markdown_content: Document content in markdown format
            existing_tags: Any existing tags to include
            
        Returns:
            List[str]: List of tags for the document
        """
        final_tags = existing_tags or []
        
        try:
            from dotnet_sdk_tags import categorize_with_ai, suggest_tags_simple
            
            # Try AI categorization first
            ai_tags = categorize_with_ai(markdown_content, self.client)
            if ai_tags:
                final_tags += ai_tags
                logger.info(f"AI categorized document with tags: {ai_tags}")
            else:
                # Fallback to simple keyword matching
                simple_tags = suggest_tags_simple(markdown_content)
                final_tags += simple_tags
                logger.info(f"Used simple categorization with tags: {simple_tags}")
                
        except ImportError:
            logger.warning("AI categorization module not available, skipping categorization")
        except Exception as e:
            logger.error(f"Error during categorization: {e}")
        
        return final_tags
    
    def process_document(self, 
                        document: Document,
                        use_ai_categorization: bool = True,
                        additional_metadata: Optional[Dict[str, Any]] = None) -> Document:
        """
        Process a document through the full pipeline.
        
        Args:
            document: Document to process
            use_ai_categorization: Whether to use AI for automatic categorization
            additional_metadata: Additional metadata to merge
            
        Returns:
            Document: Processed document with embeddings and enriched metadata
        """
        try:
            # Step 1: Convert content to markdown
            markdown_content = self.convert_to_markdown(document)
            document.markdownContent = markdown_content
            
            # Step 2: Generate embeddings
            embeddings = self.generate_embeddings(markdown_content)
            document.embeddings = embeddings
            
            # Step 3: Auto-categorize with AI if enabled
            if use_ai_categorization:
                categorized_tags = self.categorize_document(markdown_content, document.tags)
                document.tags = categorized_tags
            
            # Step 4: Merge additional metadata
            if additional_metadata:
                if document.metadata is None:
                    document.metadata = {}
                document.metadata.update(additional_metadata)
            
            # Step 5: Set processing timestamp
            document.indexedDate = datetime.now(timezone.utc)
            
            logger.info(f"Successfully processed document: {document.documentId}")
            return document
            
        except Exception as e:
            logger.error(f"Error processing document {document.documentId}: {e}")
            raise
    
    def store_document(self, document: Document) -> str:
        """
        Store a processed document in MongoDB.
        
        Args:
            document: Processed document to store
            
        Returns:
            str: Document ID of the stored document
        """
        try:
            # Insert into MongoDB
            result = self.documents_collection.insert_one(document.to_dict())
            
            logger.info(f"Document stored successfully with ID: {document.documentId}")
            return document.documentId
            
        except DuplicateKeyError:
            logger.error(f"Document with ID {document.documentId} already exists")
            raise
        except Exception as e:
            logger.error(f"Error storing document: {e}")
            raise
    
    def update_document(self, document: Document) -> bool:
        """
        Update an existing document in MongoDB.
        
        Args:
            document: Document with updated content
            
        Returns:
            bool: True if update was successful
        """
        try:
            document.updatedDate = datetime.now(timezone.utc)
            
            result = self.documents_collection.update_one(
                {"documentId": document.documentId},
                {"$set": document.to_dict()}
            )
            
            if result.matched_count == 0:
                logger.warning(f"Document with ID {document.documentId} not found")
                return False
            
            logger.info(f"Document {document.documentId} updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from MongoDB.
        
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
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by ID."""
        try:
            document_data = self.documents_collection.find_one({"documentId": document_id})
            if document_data:
                return Document.from_dict(document_data)
            return None
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
            query_embeddings = self.generate_embeddings(query)
            
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
                      limit: int = 50) -> List[Document]:
        """List documents with optional tag filtering."""
        try:
            filter_query = {}
            if tags:
                filter_query["tags"] = {"$in": tags}
            
            documents_data = list(self.documents_collection.find(
                filter_query
            ).sort("createdDate", -1).limit(limit))
            
            return [Document.from_dict(doc) for doc in documents_data]
            
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