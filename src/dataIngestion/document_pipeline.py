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

# Chunking utility
from utils.chunking import chunk_markdown

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
        self.chunks_collection = self.db[config.mongodb_chunks_collection]
        
        # Initialize MarkItDown
        self.markitdown = MarkItDown()
        
        # Chunking configuration - 4000 characters is reasonable for technical documentation
        # This allows for good context while staying within typical embedding model limits
        self.chunk_size = 4000
        
        # Create indexes for efficient querying
        self._create_indexes()
    
    def _create_indexes(self):
        """Create MongoDB indexes for efficient querying."""
        try:
            # Indexes for documents collection
            self.documents_collection.create_index("documentId", unique=True)
            self.documents_collection.create_index("tags")
            self.documents_collection.create_index("sourceUrl")
            self.documents_collection.create_index("createdDate")
            
            # Indexes for chunks collection
            self.chunks_collection.create_index("documentId")
            self.chunks_collection.create_index("original_document_id")
            self.chunks_collection.create_index("createdDate")
            
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
    
    def generate_summary(self, content: str, max_length: int = 140) -> str:
        """
        Generate a summary of the content using OpenAI.
        
        Args:
            content: Content to summarize
            max_length: Maximum length of the summary
            
        Returns:
            str: Generated summary
        """
        try:
            # If content is short enough, return as-is
            if len(content) <= max_length:
                return content
            
            # Use OpenAI to generate a summary
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are a helpful assistant that creates concise summaries. Generate a summary that is exactly {max_length} characters or less."
                    },
                    {
                        "role": "user", 
                        "content": f"Please summarize this article in {max_length} characters or less:\n\n{content[:2000]}"  # Limit input to avoid token limits
                    }
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Ensure summary doesn't exceed max_length
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            
            return summary
            
        except Exception as e:
            logger.warning(f"Error generating AI summary, falling back to truncation: {e}")
            # Fallback to simple truncation
            return content[:max_length-3] + "..." if len(content) > max_length else content
    
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
    
    def process_document_with_summary_and_chunks(self, 
                                           document: Document,
                                           use_ai_categorization: bool = True,
                                           additional_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a document using the new architecture: store summary in documents collection 
        and chunks in document_chunks collection.
        
        Args:
            document: Document to process
            use_ai_categorization: Whether to use AI for automatic categorization
            additional_metadata: Additional metadata to merge
            
        Returns:
            str: Document ID of the stored summary document
        """
        try:
            # Step 1: Convert content to markdown
            markdown_content = self.convert_to_markdown(document)
            
            # Step 2: Generate AI summary for the main document
            document.summary = self.generate_summary(markdown_content)
            logger.info(f"Generated summary for document {document.documentId}: {document.summary[:50]}...")
            
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
            
            # Step 6: Store the summary document in documents collection (without chunks)
            summary_doc = Document(
                documentId=document.documentId,
                title=document.title,
                content=document.content,  # Keep original content for search
                sourceUrl=document.sourceUrl,
                summary=document.summary,
                tags=document.tags,
                metadata=document.metadata,
                createdDate=document.createdDate,
                indexedDate=document.indexedDate,
                rss_feed_url=getattr(document, 'rss_feed_url', None),
                rss_item_id=getattr(document, 'rss_item_id', None),
                rss_title=getattr(document, 'rss_title', None),
                rss_published_date=getattr(document, 'rss_published_date', None),
                rss_author=getattr(document, 'rss_author', None),
                json_url=getattr(document, 'json_url', None)
            )
            
            # Store summary document
            self.documents_collection.insert_one(summary_doc.to_dict())
            logger.info(f"Stored summary document: {document.documentId}")
            
            # Step 7: Create and store chunks in chunks collection
            chunks = chunk_markdown(markdown_content, self.chunk_size)
            
            # If no chunks or content is small enough, treat as single chunk
            if not chunks:
                chunks = [markdown_content] if markdown_content.strip() else [""]
            
            # Process each chunk
            for i, chunk_content in enumerate(chunks):
                # Create a chunk document
                chunk_document = Document(
                    documentId=f"{document.documentId}#chunk_{i}" if len(chunks) > 1 else f"{document.documentId}#chunk_0",
                    title=document.title,
                    content=chunk_content,
                    sourceUrl=document.sourceUrl,
                    tags=document.tags.copy() if document.tags else [],
                    metadata={
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "chunk_size": len(chunk_content),
                        "original_document_id": document.documentId
                    },
                    createdDate=document.createdDate,
                    indexedDate=document.indexedDate
                )
                
                # Generate embeddings for this chunk
                if chunk_content.strip():
                    embeddings = self.generate_embeddings(chunk_content)
                    chunk_document.embeddings = embeddings
                else:
                    chunk_document.embeddings = []
                
                # Store chunk in chunks collection
                self.chunks_collection.insert_one(chunk_document.to_dict())
            
            logger.info(f"Successfully processed document into {len(chunks)} chunks: {document.documentId}")
            return document.documentId
            
        except Exception as e:
            logger.error(f"Error processing document {document.documentId}: {e}")
            raise
    
    def process_document_with_chunking(self,
                                     use_ai_categorization: bool = True,
                                     additional_metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Process a document through the full pipeline with chunking support.
        
        Args:
            document: Document to process
            use_ai_categorization: Whether to use AI for automatic categorization
            additional_metadata: Additional metadata to merge
            
        Returns:
            List[Document]: List of processed document chunks with embeddings and enriched metadata
        """
        try:
            # Step 1: Convert content to markdown
            markdown_content = self.convert_to_markdown(document)
            
            # Step 2: Chunk the markdown content
            chunks = chunk_markdown(markdown_content, self.chunk_size)
            
            # If no chunks or content is small enough, treat as single chunk
            if not chunks:
                chunks = [markdown_content] if markdown_content.strip() else [""]
            
            processed_documents = []
            
            # Step 3: Process each chunk
            for i, chunk_content in enumerate(chunks):
                # Create a new document for this chunk
                chunk_document = Document(
                    documentId=f"{document.documentId}#chunk_{i}" if len(chunks) > 1 else document.documentId,
                    title=document.title,
                    content=chunk_content,  # Keep original content
                    sourceUrl=document.sourceUrl,
                    createdDate=document.createdDate,
                    tags=document.tags.copy() if document.tags else [],
                    metadata=document.metadata.copy() if document.metadata else {},
                    # Copy RSS-specific fields if they exist
                    rss_feed_url=getattr(document, 'rss_feed_url', None),
                    rss_item_id=getattr(document, 'rss_item_id', None),
                    rss_title=getattr(document, 'rss_title', None),
                    rss_published_date=getattr(document, 'rss_published_date', None),
                    rss_author=getattr(document, 'rss_author', None)
                )
                
                # Add chunk-specific metadata
                chunk_metadata = {
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk_content),
                    "original_document_id": document.documentId
                }
                
                if chunk_document.metadata is None:
                    chunk_document.metadata = {}
                chunk_document.metadata.update(chunk_metadata)
                
                # Step 4: Generate embeddings for this chunk
                if chunk_content.strip():  # Only generate embeddings for non-empty chunks
                    embeddings = self.generate_embeddings(chunk_content)
                    chunk_document.embeddings = embeddings
                else:
                    chunk_document.embeddings = []
                
                # Step 5: Auto-categorize with AI if enabled (only for first chunk to avoid redundancy)
                if use_ai_categorization and i == 0:
                    categorized_tags = self.categorize_document(chunk_content, chunk_document.tags)
                    # Apply the same tags to all chunks
                    for doc in [chunk_document] + processed_documents:
                        doc.tags = categorized_tags
                
                # Step 6: Merge additional metadata
                if additional_metadata:
                    chunk_document.metadata.update(additional_metadata)
                
                # Step 7: Set processing timestamp
                chunk_document.indexedDate = datetime.now(timezone.utc)
                
                processed_documents.append(chunk_document)
            
            logger.info(f"Successfully processed document into {len(processed_documents)} chunks: {document.documentId}")
            return processed_documents
            
        except Exception as e:
            logger.error(f"Error processing document {document.documentId}: {e}")
            raise
    
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
    
    def store_document_chunks(self, document_chunks: List[Document]) -> List[str]:
        """
        Store multiple processed document chunks in MongoDB.
        
        Args:
            document_chunks: List of processed document chunks to store
            
        Returns:
            List[str]: List of document IDs of the stored chunks
        """
        try:
            stored_ids = []
            
            for chunk in document_chunks:
                try:
                    # Insert each chunk into MongoDB
                    result = self.documents_collection.insert_one(chunk.to_dict())
                    stored_ids.append(chunk.documentId)
                except DuplicateKeyError:
                    logger.warning(f"Document chunk with ID {chunk.documentId} already exists, skipping")
                    continue
            
            logger.info(f"Successfully stored {len(stored_ids)} document chunks")
            return stored_ids
            
        except Exception as e:
            logger.error(f"Error storing document chunks: {e}")
            raise
    
    def process_and_store_document(self, 
                                 document: Document,
                                 use_ai_categorization: bool = True,
                                 additional_metadata: Optional[Dict[str, Any]] = None,
                                 use_new_architecture: bool = True) -> List[str]:
        """
        Process and store a document. Uses new architecture by default (summary in documents, chunks in document_chunks).
        
        Args:
            document: Document to process and store
            use_ai_categorization: Whether to use AI for automatic categorization
            additional_metadata: Additional metadata to merge
            use_new_architecture: Whether to use new architecture (default: True)
            
        Returns:
            List[str]: List of document IDs of the stored documents/chunks
        """
        if use_new_architecture:
            # Use new architecture: summary in documents, chunks in document_chunks
            document_id = self.process_document_with_summary_and_chunks(
                document, use_ai_categorization, additional_metadata
            )
            return [document_id]
        else:
            # Legacy behavior: process with chunking and store all in documents collection
            processed_chunks = self.process_document_with_chunking(
                document, use_ai_categorization, additional_metadata
            )
            return self.store_document_chunks(processed_chunks)
    
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
        Searches in chunks collection for embeddings and returns corresponding documents.
        
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
            
            # Build aggregation pipeline for chunks collection
            pipeline = []
            
            # Filter by tags if provided
            if tags:
                pipeline.append({"$match": {"tags": {"$in": tags}}})
            
            # Add vector similarity search on chunks
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
                {"$limit": limit * 3},  # Get more chunks to deduplicate documents
                {
                    "$group": {
                        "_id": "$metadata.original_document_id",
                        "max_similarity": {"$max": "$similarity"},
                        "chunk_data": {"$first": "$$ROOT"}
                    }
                },
                {"$sort": {"max_similarity": -1}},
                {"$limit": limit},
                {"$replaceRoot": {"newRoot": {
                    "$mergeObjects": [
                        "$chunk_data",
                        {"similarity": "$max_similarity"}
                    ]
                }}},
                {"$project": {"_id": 0}}
            ])
            
            # Search in chunks collection
            chunk_results = list(self.chunks_collection.aggregate(pipeline))
            
            # Get corresponding documents from documents collection
            results = []
            for chunk_result in chunk_results:
                original_doc_id = chunk_result.get("metadata", {}).get("original_document_id")
                if original_doc_id:
                    doc_data = self.documents_collection.find_one({"documentId": original_doc_id})
                    if doc_data:
                        doc_data["similarity"] = chunk_result["similarity"]
                        results.append(doc_data)
            
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