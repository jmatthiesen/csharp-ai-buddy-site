#!/usr/bin/env python3
"""
Refactored document processing pipeline with clear stages and source enrichment.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from io import BytesIO

# External dependencies
from openai import OpenAI
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from markitdown import MarkItDown, StreamInfo

# Internal dependencies
from config import Config
from pipeline_types import RawDocument, ProcessingContext, Chunk
from source_enrichers import (
    SourceEnricher, RSSSourceEnricher, WordPressSourceEnricher, 
    HTMLSourceEnricher, PlainTextSourceEnricher, FallbackSourceEnricher
)
from utils.chunking import chunk_markdown

logger = logging.getLogger(__name__)


class DocumentPipeline:
    """Refactored document processing pipeline with clear stages and source enrichment"""
    
    def __init__(self, config: Config):
        """Initialize the pipeline with configuration and dependencies"""
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.mongo_client = MongoClient(config.mongodb_connection_string)
        self.db = self.mongo_client[config.mongodb_database]
        self.documents_collection = self.db[config.mongodb_collection]
        
        # Initialize MarkItDown for content conversion
        self.markitdown = MarkItDown()
        
        # Default chunk size for technical documentation
        self.default_chunk_size = 4000
        
        # Initialize source enrichers (order matters - more specific first)
        self.source_enrichers: List[SourceEnricher] = [
            RSSSourceEnricher(),
            WordPressSourceEnricher(),
            HTMLSourceEnricher(),  
            PlainTextSourceEnricher(),
            FallbackSourceEnricher()  # Always last as fallback
        ]
        
        # Create indexes for efficient querying
        self._create_indexes()
    
    def _create_indexes(self):
        """Create MongoDB indexes for efficient querying."""
        try:
            # Create indexes (these are safe to create multiple times)
            self.documents_collection.create_index("chunk_id")  # Non-unique index for ObjectIDs
            self.documents_collection.create_index("original_document_id")
            self.documents_collection.create_index("source_url") 
            self.documents_collection.create_index("tags")
            self.documents_collection.create_index("indexed_date")
            self.documents_collection.create_index([("tags", 1), ("indexed_date", -1)])
            
            logger.info("Document pipeline indexes created successfully")
        except Exception as e:
            logger.warning(f"Error creating document pipeline indexes: {e}")
    
    # Main entry points
    def process_document(self, raw_doc: RawDocument, **options) -> List[str]:
        """Process a raw document and immediately store chunks, return chunk IDs"""
        try:
            # Create processing context
            context = ProcessingContext(
                raw_document=raw_doc,
                use_ai_categorization=options.get('use_ai_categorization', True),
                chunk_size=options.get('chunk_size', self.default_chunk_size)
            )
            
            # Add user metadata if provided
            if 'additional_metadata' in options:
                context.user_metadata.update(options['additional_metadata'])
                        
            # Execute pipeline stages (stop on first error)
            self._stage_source_enrichment(context)
            self._check_for_errors(context, "source enrichment")
            
            self._stage_markdown_conversion(context)
            self._check_for_errors(context, "markdown conversion")
            
            self._stage_chunking(context)
            self._check_for_errors(context, "chunking")
            
            self._stage_embedding_generation(context)
            self._check_for_errors(context, "embedding generation")
            
            if context.use_ai_categorization:
                self._stage_ai_categorization(context)
                self._check_for_errors(context, "AI categorization")
            
            # Create and immediately store chunks
            chunk_ids = self._stage_finalization_and_storage(context)
            
            logger.info(f"Successfully processed and stored {len(chunk_ids)} chunks: {raw_doc.source_url}")
            return chunk_ids
            
        except Exception as e:
            logger.error(f"Error processing document {raw_doc.source_url}: {e}")
            raise
    
    def _check_for_errors(self, context: ProcessingContext, stage_name: str) -> None:
        """Check for errors and raise exception to stop processing"""
        if context.errors:
            error_msg = f"Errors in {stage_name}: {'; '.join(context.errors)}"
            raise ValueError(error_msg)
    
    # Pipeline stages
    def _stage_source_enrichment(self, context: ProcessingContext) -> None:
        """Add source-specific metadata and processing"""
        try:
            enrichers_applied = []
            
            for enricher in self.source_enrichers:
                if enricher.can_handle(context.raw_document):
                    enricher.enrich(context)
                    enrichers_applied.append(enricher.name)
                    
                    # Only apply the first matching enricher (except fallback)
                    if enricher.name != "Fallback":
                        break
            
            context.processing_metadata["enrichers_applied"] = enrichers_applied
            context.mark_stage_complete("source_enrichment")
            
            logger.debug(f"Applied enrichers: {enrichers_applied}")
            
        except Exception as e:
            error_msg = f"Error in source enrichment: {e}"
            context.add_error(error_msg)
            logger.error(error_msg)
    
    def _stage_markdown_conversion(self, context: ProcessingContext) -> None:
        """Convert raw content to markdown"""
        try:
            # Convert content to markdown based on content type
            if context.raw_document.content_type == "markdown":
                context.markdown_content = context.raw_document.content
            else:
                # Use MarkItDown for HTML and other formats
                html_content_bytes = BytesIO(context.raw_document.content.encode("utf-8"))
                result = self.markitdown.convert(
                    source=html_content_bytes,
                    stream_info=StreamInfo(extension=".html")
                )
                context.markdown_content = result.markdown
            
            context.processing_metadata["markdown_length"] = len(context.markdown_content) if context.markdown_content else 0
            context.mark_stage_complete("markdown_conversion")
            
        except Exception as e:
            error_msg = f"Error in markdown conversion: {e}"
            context.add_error(error_msg)
            logger.error(error_msg)
            # Fallback to raw content
            context.markdown_content = context.raw_document.content
    
    def _stage_chunking(self, context: ProcessingContext) -> None:
        """Split markdown into chunks"""
        try:
            if not context.markdown_content:
                context.add_error("No markdown content available for chunking")
                return
            
            # Use the chunking utility
            chunks = chunk_markdown(context.markdown_content, context.chunk_size)
            
            # If no chunks returned or content is small, treat as single chunk
            if not chunks:
                if context.markdown_content.strip():
                    context.chunks = [context.markdown_content]
                else:
                    context.chunks = [""]
            else:
                context.chunks = chunks
            
            context.processing_metadata["chunks_created"] = len(context.chunks)
            context.processing_metadata["total_content_length"] = sum(len(chunk) for chunk in context.chunks)
            context.mark_stage_complete("chunking")
            
        except Exception as e:
            error_msg = f"Error in chunking: {e}"
            context.add_error(error_msg)
            logger.error(error_msg)
    
    def _stage_embedding_generation(self, context: ProcessingContext) -> None:
        """Generate embeddings for each chunk"""
        try:
            context.chunk_embeddings = []
            
            for i, chunk_content in enumerate(context.chunks):
                if chunk_content.strip():  # Only generate embeddings for non-empty chunks
                    try:
                        response = self.client.embeddings.create(
                            model=self.config.embedding_model,
                            input=chunk_content
                        )
                        embeddings = response.data[0].embedding
                        context.chunk_embeddings.append(embeddings)
                    except Exception as e:
                        error_msg = f"Failed to generate embeddings for chunk {i}: {e}"
                        context.add_error(error_msg)
                        return
                else:
                    context.chunk_embeddings.append([])  # Empty embeddings for empty chunks
            
            context.processing_metadata["embeddings_generated"] = len([e for e in context.chunk_embeddings if e])
            context.mark_stage_complete("embedding_generation")
            
        except Exception as e:
            error_msg = f"Error in embedding generation: {e}"
            context.add_error(error_msg)
            logger.error(error_msg)
    
    def _stage_ai_categorization(self, context: ProcessingContext) -> None:
        """AI-based tagging and categorization"""
        try:
            # Only categorize the first chunk to avoid redundancy and API costs
            if context.chunks and context.chunks[0].strip():
                try:
                    from dotnet_sdk_tags import categorize_with_ai
                    
                    # Use the first chunk for categorization
                    ai_tags = categorize_with_ai(context.chunks[0], self.client)
                    if ai_tags:
                        context.final_tags.extend(ai_tags)
                        context.processing_metadata["ai_tags_added"] = ai_tags
                        logger.info(f"AI categorized document with tags: {ai_tags}")
                    else:
                        logger.info("AI categorization returned no tags")
                        
                except ImportError:
                    context.add_warning("AI categorization module not available, skipping categorization")
                    logger.warning("AI categorization module not available, skipping categorization")
                except Exception as e:
                    error_msg = f"AI categorization failed: {e}"
                    context.add_error(error_msg)
                    return
            
            context.mark_stage_complete("ai_categorization")
            
        except Exception as e:
            error_msg = f"Error in AI categorization: {e}"
            context.add_error(error_msg)
            logger.error(error_msg)
    
    def _stage_finalization_and_storage(self, context: ProcessingContext) -> List[str]:
        """Create chunks and immediately store them"""
        try:
            stored_chunk_ids = []
            
            # Clean up any existing chunks for this document to avoid duplicates
            original_doc_id = context.raw_document.source_url
            
            # Simple cleanup by original document ID
            result = self.documents_collection.delete_many({"original_document_id": original_doc_id})
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} existing chunks for document before processing")
            
            # Determine total chunks
            total_chunks = len(context.chunks)
            
            # Check for length mismatch
            if len(context.chunks) != len(context.chunk_embeddings):
                logger.error(f"LENGTH MISMATCH: chunks={len(context.chunks)}, embeddings={len(context.chunk_embeddings)}")
                raise ValueError(f"Chunk/embedding length mismatch: {len(context.chunks)} vs {len(context.chunk_embeddings)}")
            
            for i, (chunk_content, embeddings) in enumerate(zip(context.chunks, context.chunk_embeddings)):
                # Generate unique ObjectID for chunk
                chunk_id = str(ObjectId())
                
                logger.debug(f"Generated ObjectID chunk_id {i}: {chunk_id}")
                
                # Combine all metadata
                combined_metadata = {}
                combined_metadata.update(context.processing_metadata)
                combined_metadata.update(context.user_metadata)
                combined_metadata.update({
                    "chunk_index": i,
                    "total_chunks": total_chunks,
                    "chunk_size": len(chunk_content),
                    "original_document_id": original_doc_id
                })
                
                # Create chunk
                chunk = Chunk(
                    chunk_id=chunk_id,
                    original_document_id=original_doc_id,
                    title=context.raw_document.title or "Untitled",
                    source_url=context.raw_document.source_url,
                    content=chunk_content,  # Markdown content only
                    embeddings=embeddings,
                    chunk_index=i,
                    total_chunks=total_chunks,
                    chunk_size=len(chunk_content),
                    metadata=combined_metadata,
                    tags=list(set(context.final_tags)),  # Remove duplicates
                    created_date=context.raw_document.created_date,
                    indexed_date=datetime.now(timezone.utc)
                )
                
                # Store chunk (ObjectID ensures uniqueness)
                try:
                    self.documents_collection.insert_one(chunk.to_dict())
                    stored_chunk_ids.append(chunk_id)
                    logger.debug(f"Stored chunk: {chunk_id}")
                    
                except Exception as e:
                    error_msg = f"Failed to store chunk {chunk_id}: {e}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            
            context.mark_stage_complete("finalization_and_storage")
            return stored_chunk_ids
            
        except Exception as e:
            error_msg = f"Error in finalization and storage: {e}"
            context.add_error(error_msg)
            logger.error(error_msg)
            raise
    
    # Convenience methods
    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Retrieve a specific chunk by ID"""
        try:
            chunk_data = self.documents_collection.find_one({"chunk_id": chunk_id}, {"_id": 0})  # Exclude MongoDB _id
            if chunk_data:
                # Convert ISO strings back to datetime objects
                if chunk_data.get('created_date') and isinstance(chunk_data['created_date'], str):
                    chunk_data['created_date'] = datetime.fromisoformat(chunk_data['created_date'])
                if chunk_data.get('indexed_date') and isinstance(chunk_data['indexed_date'], str):
                    chunk_data['indexed_date'] = datetime.fromisoformat(chunk_data['indexed_date'])
                
                return Chunk(**chunk_data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving chunk {chunk_id}: {e}")
            return None
    
    def get_document_chunks(self, original_document_id: str) -> List[Chunk]:
        """Retrieve all chunks for a document"""
        try:
            chunks = []
            cursor = self.documents_collection.find(
                {"original_document_id": original_document_id}, 
                {"_id": 0}  # Exclude MongoDB _id
            ).sort("chunk_index", 1)
            
            for chunk_data in cursor:
                # Convert ISO strings back to datetime objects
                if chunk_data.get('created_date') and isinstance(chunk_data['created_date'], str):
                    chunk_data['created_date'] = datetime.fromisoformat(chunk_data['created_date'])
                if chunk_data.get('indexed_date') and isinstance(chunk_data['indexed_date'], str):
                    chunk_data['indexed_date'] = datetime.fromisoformat(chunk_data['indexed_date'])
                
                chunks.append(Chunk(**chunk_data))
            
            return chunks
        except Exception as e:
            logger.error(f"Error retrieving chunks for document {original_document_id}: {e}")
            return []
    
    def search_chunks(self, 
                     query: str, 
                     tags: Optional[List[str]] = None,
                     limit: int = 10) -> List[Dict[str, Any]]:
        """Search for chunks using vector similarity (placeholder for future implementation)"""
        # This would implement vector search in a real scenario
        # For now, return a simple text-based search
        try:
            # Generate query embedding
            response = self.client.embeddings.create(
                model=self.config.embedding_model,
                input=query
            )
            query_embedding = response.data[0].embedding
            
            # For now, just return recent chunks with matching tags
            filter_query = {}
            if tags:
                filter_query["tags"] = {"$in": tags}
            
            cursor = self.documents_collection.find(filter_query).sort("indexed_date", -1).limit(limit)
            
            results = []
            for chunk_data in cursor:
                results.append({
                    "chunk_id": chunk_data["chunk_id"],
                    "title": chunk_data["title"],
                    "source_url": chunk_data["source_url"],
                    "content": chunk_data["content"][:200] + "..." if len(chunk_data["content"]) > 200 else chunk_data["content"],
                    "tags": chunk_data["tags"],
                    "similarity": 0.8  # Placeholder similarity score
                })
            
            logger.info(f"Found {len(results)} chunks matching query")
            return results
            
        except Exception as e:
            logger.error(f"Error searching chunks: {e}")
            return []
    
    # Utility methods
    def cleanup_old_documents(self) -> Dict[str, int]:
        """Clean up old documents and indexes from previous architecture"""
        try:
            # Drop old indexes that might be causing conflicts
            existing_indexes = list(self.documents_collection.list_indexes())
            for index in existing_indexes:
                index_name = index.get('name', '')
                if index_name in ['documentId_1', 'chunk_id_1'] and index.get('unique'):
                    logger.info(f"Dropping old index: {index_name}")
                    try:
                        self.documents_collection.drop_index(index_name)
                    except Exception as e:
                        logger.warning(f"Could not drop index {index_name}: {e}")
            
            # Count documents without chunk_id (old documents)
            old_docs_count = self.documents_collection.count_documents({"chunk_id": None})
            
            # Count documents with documentId field (old documents)
            old_docs_with_documentId = self.documents_collection.count_documents({"documentId": {"$exists": True}})
            
            total_old_docs = old_docs_count + old_docs_with_documentId
            
            if total_old_docs == 0:
                return {"deleted": 0, "message": "No old documents found"}
            
            logger.info(f"Found {old_docs_count} documents without chunk_id and {old_docs_with_documentId} with old documentId field")
            
            # Delete old documents
            deleted_count = 0
            
            if old_docs_count > 0:
                result = self.documents_collection.delete_many({"chunk_id": None})
                deleted_count += result.deleted_count
                
            if old_docs_with_documentId > 0:
                result = self.documents_collection.delete_many({"documentId": {"$exists": True}})
                deleted_count += result.deleted_count
            
            logger.info(f"Deleted {deleted_count} old documents")
            
            # Recreate clean indexes
            self._create_indexes()
            
            return {
                "deleted": deleted_count,
                "message": f"Successfully deleted {deleted_count} old documents and cleaned up indexes"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up old documents: {e}")
            return {"deleted": 0, "error": str(e)}