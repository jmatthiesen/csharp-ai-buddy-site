#!/usr/bin/env python3
"""
Refactored document processing pipeline with clear stages and source enrichment.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import urljoin, urlparse

# External dependencies
from openai import OpenAI
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from markitdown import MarkItDown, StreamInfo

# Internal dependencies
from config import Config
from pipeline_types import RawDocument, ProcessingContext, Chunk
from document import Document
from source_enrichers import (
    SourceEnricher, RSSSourceEnricher, WordPressSourceEnricher, 
    HTMLSourceEnricher, PlainTextSourceEnricher, FallbackSourceEnricher
)
from host_handlers import (
    HostHandler, GitHubHostHandler, FallbackHostHandler
)
from utils.chunking import chunk_markdown

logger = logging.getLogger(__name__)

class DocumentPipeline:
    """Refactored document processing pipeline with clear stages and source enrichment"""
    
    def __init__(self, config: Config, what_if_mode: bool = False):
        """Initialize the pipeline with configuration and dependencies"""
        self.config = config
        self.what_if_mode = what_if_mode
        
        if what_if_mode:
            self.client = None
            self.mongo_client = None
            self.db = None
            self.documents_collection = None
            self.chunks_collection = None
        else:
            self.client = OpenAI(api_key=config.openai_api_key)
            self.mongo_client = MongoClient(config.mongodb_connection_string)
            self.db = self.mongo_client[config.mongodb_database]
            self.documents_collection = self.db[config.mongodb_collection]  # For document summaries
            self.chunks_collection = self.db[config.mongodb_chunks_collection]  # For document chunks
        
        # Initialize MarkItDown for content conversion
        self.markitdown = MarkItDown()
        
        # Default chunk size for technical documentation
        self.default_chunk_size = 4000

        # Default size to use for summaries, set to 300 to mimic social media posts
        self.default_summary_size = 300
        
        # Initialize source enrichers (order matters - more specific first)
        self.source_enrichers: List[SourceEnricher] = [
            RSSSourceEnricher(),
            WordPressSourceEnricher(),
            HTMLSourceEnricher(),  
            PlainTextSourceEnricher(),
            FallbackSourceEnricher()  # Always last as fallback
        ]
        
        # Initialize host handlers (order matters - more specific first)
        self.host_handlers: List[HostHandler] = [
            GitHubHostHandler(),
            FallbackHostHandler()  # Always last as fallback
        ]
        
        # Create indexes for efficient querying (skip in what-if mode)
        if not what_if_mode:
            self._create_indexes()
    
    def _create_indexes(self):
        """Create MongoDB indexes for efficient querying."""
        try:
            # Create indexes for documents collection
            self.documents_collection.create_index("documentId")
            self.documents_collection.create_index("sourceUrl") 
            self.documents_collection.create_index("tags")
            self.documents_collection.create_index("publishedDate")
            self.documents_collection.create_index([("tags", 1), ("indexedDate", -1)])
            
            # Create indexes for chunks collection  
            self.chunks_collection.create_index("chunk_id")  # Non-unique index for ObjectIDs
            self.chunks_collection.create_index("source_url") 
            self.chunks_collection.create_index("tags")
            self.chunks_collection.create_index("indexed_date")
            self.chunks_collection.create_index([("tags", 1), ("indexed_date", -1)])
            
            logger.info("Document pipeline indexes created successfully")
        except Exception as e:
            logger.warning(f"Error creating document pipeline indexes: {e}")
    
    # Main entry points
    def process_document(self, raw_doc: RawDocument, **options):
        """Process a raw document and immediately store chunks, return context with chunk IDs and extracted links"""
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

            self._stage_link_extraction(context)
            self._check_for_errors(context, "link extraction")

            self._stage_summary_creation(context)
            self._check_for_errors(context, "summary creation")
     
            self._stage_chunking(context)
            self._check_for_errors(context, "chunking")
            
            self._stage_embedding_generation(context)
            self._check_for_errors(context, "embedding generation")
            
            if context.use_ai_categorization:
                self._stage_ai_categorization(context)
                self._check_for_errors(context, "AI categorization")
            
            # Create and immediately store chunks
            chunk_ids = self._stage_finalization_and_storage(context)
            
            # Store chunk IDs in the context for return
            context.processing_metadata["stored_chunk_ids"] = chunk_ids
            
            logger.info(f"Successfully processed and stored {len(chunk_ids)} chunks: {raw_doc.source_url}")
            return context
            
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
    
    def _generate_summary(self, content: str, max_length: int = 140) -> str:
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
            
            # In what-if mode, just truncate without calling OpenAI
            if self.what_if_mode:
                print(f"📋 WHAT-IF: Would call OpenAI to generate summary (max {max_length} chars)")
                return content[:max_length-3] + "..." if len(content) > max_length else content
            
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

    def _stage_summary_creation(self, context: ProcessingContext) -> None:
        """Creates a summary version of the document"""
        try:
            context.raw_document.summary = self._generate_summary(context.markdown_content,
                                                                  self.default_summary_size)
            context.mark_stage_complete("summary_generation")
        except Exception as e:
            error_msg = f"Error in summary creation: {e}"
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
    
    def _stage_link_extraction(self, context: ProcessingContext) -> None:
        """Extract links from markdown content for potential crawling"""
        try:
            if not context.markdown_content:
                context.add_warning("No markdown content available for link extraction")
                context.mark_stage_complete("link_extraction")
                return
            
            # Extract links using the existing method
            extracted_links = self.extract_links_from_markdown(
                context.markdown_content, 
                context.raw_document.source_url
            )
            
            # Apply host-specific processing to extracted links
            processed_links = self._apply_host_handlers(extracted_links, context.raw_document.source_url)
            
            # Extract host-specific metadata
            host_metadata = self._extract_host_metadata(context.raw_document.source_url, context.markdown_content)
            if host_metadata:
                context.processing_metadata.update(host_metadata)
            
            context.extracted_links = processed_links
            context.processing_metadata["links_extracted"] = len(processed_links)
            context.mark_stage_complete("link_extraction")
            
            if processed_links:
                logger.info(f"Extracted {len(processed_links)} crawlable links from {context.raw_document.source_url}")
            else:
                logger.debug(f"No crawlable links found in {context.raw_document.source_url}")
            
        except Exception as e:
            error_msg = f"Error in link extraction: {e}"
            context.add_error(error_msg)
            logger.error(error_msg)
    
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
            
            if self.what_if_mode:
                print(f"📋 WHAT-IF: Would generate embeddings for {len(context.chunks)} chunks using {self.config.embedding_model}")
                # Create empty embeddings for what-if mode
                for chunk_content in context.chunks:
                    context.chunk_embeddings.append([])
                context.processing_metadata["embeddings_generated"] = len(context.chunks)
                context.mark_stage_complete("embedding_generation")
                return
            
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
            if self.what_if_mode:
                print(f"📋 WHAT-IF: Would call OpenAI for AI categorization of document content")
                context.mark_stage_complete("ai_categorization")
                return
            
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
        """Create and store both document summary and chunks"""
        try:
            stored_chunk_ids = []
            doc = context.raw_document
            source_url = context.raw_document.source_url
            total_chunks = len(context.chunks)

            if self.what_if_mode:
                print(f"📋 WHAT-IF: Would create document summary for: {doc.title}")
                print(f"📋 WHAT-IF: Would clean up existing chunks for document: {source_url}")
                print(f"📋 WHAT-IF: Would store {total_chunks} chunks in database")
                
                # Create mock chunk IDs for what-if mode
                for i in range(total_chunks):
                    mock_chunk_id = f"mock-chunk-{i}-{ObjectId()}"
                    stored_chunk_ids.append(mock_chunk_id)
                    print(f"📋 WHAT-IF: Would store chunk {i+1}/{total_chunks}: {mock_chunk_id}")
                
                context.mark_stage_complete("finalization_and_storage")
                return stored_chunk_ids

            summary_doc = {
                "title": doc.title,
                "summary": doc.summary,
                "tags": doc.tags,
                "publishedDate": doc.created_date,
                "indexedDate": datetime.now(timezone.utc),
                "sourceUrl": doc.source_url
            }

            self.documents_collection.insert_one(summary_doc)
            logger.info(f"Stored summary document: {summary_doc.get('_id', 'unknown')}")

            # Clean up any existing chunks for this document to avoid duplicates
            result = self.chunks_collection.delete_many({"source_url": source_url})
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} existing chunks for document before processing")
            
            # Check for length mismatch
            if len(context.chunks) != len(context.chunk_embeddings):
                logger.error(f"LENGTH MISMATCH: chunks={len(context.chunks)}, embeddings={len(context.chunk_embeddings)}")
                raise ValueError(f"Chunk/embedding length mismatch: {len(context.chunks)} vs {len(context.chunk_embeddings)}")
            
            # Create and store chunks
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
                    "source_url": source_url
                })
                
                # Create chunk
                chunk = Chunk(
                    chunk_id=chunk_id,
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
                
                # Store chunk in chunks collection
                try:
                    self.chunks_collection.insert_one(chunk.to_dict())
                    stored_chunk_ids.append(chunk_id)
                    logger.debug(f"Stored chunk: {chunk_id}")
                    
                except Exception as e:
                    error_msg = f"Failed to store chunk {chunk_id}: {e}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            
            context.mark_stage_complete("finalization_and_storage")
            logger.info(f"Successfully stored document summary and {len(stored_chunk_ids)} chunks for: {source_url}")
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
            chunk_data = self.chunks_collection.find_one({"chunk_id": chunk_id}, {"_id": 0})  # Exclude MongoDB _id
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
    
    def get_document_chunks(self, source_url: str) -> List[Chunk]:
        """Retrieve all chunks for a document"""
        try:
            chunks = []
            cursor = self.chunks_collection.find(
                {"source_url": source_url},
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
            logger.error(f"Error retrieving chunks for document {source_url}: {e}")
            return []
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a specific document by ID"""
        try:
            doc_data = self.documents_collection.find_one({"documentId": document_id}, {"_id": 0})  # Exclude MongoDB _id
            if doc_data:
                return Document.from_dict(doc_data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None
    
    def search_documents(self, 
                        query: str, 
                        tags: Optional[List[str]] = None,
                        limit: int = 10) -> List[Document]:
        """Search for documents (summaries) by text and tags"""
        try:
            # Build search filter
            filter_query = {}
            
            if query:
                search_regex = {"$regex": query, "$options": "i"}
                filter_query["$or"] = [
                    {"title": search_regex},
                    {"content": search_regex},
                    {"summary": search_regex}
                ]
            
            if tags:
                filter_query["tags"] = {"$in": tags}
            
            cursor = self.documents_collection.find(filter_query).sort("indexedDate", -1).limit(limit)
            
            documents = []
            for doc_data in cursor:
                documents.append(Document.from_dict(doc_data))
            
            logger.info(f"Found {len(documents)} documents matching query")
            return documents
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
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
            
            cursor = self.chunks_collection.find(filter_query).sort("indexed_date", -1).limit(limit)
            
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
    
    # Host handler methods
    def _apply_host_handlers(self, links: List[Dict[str, str]], source_url: str) -> List[Dict[str, str]]:
        """Apply host-specific processing to extracted links."""
        try:
            processed_links = links
            
            # Find the appropriate handler for the source URL
            for handler in self.host_handlers:
                if handler.can_handle(source_url):
                    processed_links = handler.process_extracted_links(processed_links, source_url)
                    logger.debug(f"Applied {handler.name} host handler to {len(links)} links")
                    # Only apply the first matching handler (except fallback)
                    if handler.name != "Fallback":
                        break
            
            return processed_links
        except Exception as e:
            logger.error(f"Error applying host handlers: {e}")
            return links
    
    def _extract_host_metadata(self, url: str, markdown_content: str) -> Dict[str, Any]:
        """Extract host-specific metadata using appropriate handler."""
        try:
            metadata = {}
            
            # Find the appropriate handler for the URL
            for handler in self.host_handlers:
                if handler.can_handle(url):
                    handler_metadata = handler.extract_host_metadata(url, markdown_content)
                    if handler_metadata:
                        metadata.update(handler_metadata)
                        logger.debug(f"Extracted metadata using {handler.name} handler")
                    # Only apply the first matching handler (except fallback)
                    if handler.name != "Fallback":
                        break
            
            return metadata
        except Exception as e:
            logger.error(f"Error extracting host metadata: {e}")
            return {}
    
    # Utility methods
    def cleanup_old_documents(self) -> Dict[str, int]:
        """Clean up old documents and indexes from previous architecture"""
        try:
            total_deleted = 0
            
            # Drop old indexes that might be causing conflicts in documents collection
            existing_indexes = list(self.documents_collection.list_indexes())
            for index in existing_indexes:
                index_name = index.get('name', '')
                if index_name in ['documentId_1', 'chunk_id_1'] and index.get('unique'):
                    logger.info(f"Dropping old index from documents collection: {index_name}")
                    try:
                        self.chunks_collection.drop_index(index_name)
                    except Exception as e:
                        logger.warning(f"Could not drop index {index_name}: {e}")
            
            # Drop old indexes that might be causing conflicts in chunks collection  
            existing_chunk_indexes = list(self.chunks_collection.list_indexes())
            for index in existing_chunk_indexes:
                index_name = index.get('name', '')
                if index_name in ['documentId_1', 'chunk_id_1'] and index.get('unique'):
                    logger.info(f"Dropping old index from chunks collection: {index_name}")
                    try:
                        self.chunks_collection.drop_index(index_name)
                    except Exception as e:
                        logger.warning(f"Could not drop index {index_name}: {e}")
            
            # Count old documents in documents collection (chunks stored with documentId instead of being in separate collection)
            old_chunks_in_docs = self.documents_collection.count_documents({"chunk_id": {"$exists": True}})
            
            # Count old documents in chunks collection that should be documents (no chunk_id field)
            old_docs_in_chunks = self.chunks_collection.count_documents({"chunk_id": None})
            
            logger.info(f"Found {old_chunks_in_docs} chunks incorrectly stored in documents collection")
            logger.info(f"Found {old_docs_in_chunks} documents incorrectly stored in chunks collection")
            
            # Delete chunks incorrectly stored in documents collection
            if old_chunks_in_docs > 0:
                result = self.documents_collection.delete_many({"chunk_id": {"$exists": True}})
                total_deleted += result.deleted_count
                logger.info(f"Deleted {result.deleted_count} chunks from documents collection")
                
            # Delete documents incorrectly stored in chunks collection
            if old_docs_in_chunks > 0:
                result = self.chunks_collection.delete_many({"chunk_id": None})
                total_deleted += result.deleted_count
                logger.info(f"Deleted {result.deleted_count} documents from chunks collection")
            
            # Recreate clean indexes
            self._create_indexes()
            
            if total_deleted == 0:
                return {"deleted": 0, "message": "No old documents found"}
            
            return {
                "deleted": total_deleted,
                "message": f"Successfully deleted {total_deleted} misplaced documents and cleaned up indexes"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up old documents: {e}")
            return {"deleted": 0, "error": str(e)}
    
    def extract_links_from_markdown(self, markdown_content: str, base_url: str) -> List[Dict[str, str]]:
        """
        Extract links from markdown content that are on the same domain and same path or deeper.
        
        Args:
            markdown_content: The markdown content to extract links from
            base_url: The source URL to compare against for filtering
            
        Returns:
            List of dictionaries with 'url', 'text', and 'title' keys
        """
        try:
            # Parse the base URL to get domain and path components
            base_parsed = urlparse(base_url)
            base_domain = base_parsed.netloc.lower()
            # Extract directory path, not including the filename
            base_path_parts = base_parsed.path.rstrip('/').split('/')
            if base_path_parts[-1] and '.' in base_path_parts[-1]:
                # Remove filename to get directory path
                base_path = '/'.join(base_path_parts[:-1])
            else:
                base_path = '/'.join(base_path_parts)
            
            # Regular expression to match markdown links: [text](url "optional title")
            link_pattern = r'\[([^\]]*)\]\(([^)]+?)(?:\s+"([^"]*)")?\)'
            links = []
            
            for match in re.finditer(link_pattern, markdown_content):
                link_text = match.group(1).strip()
                link_url = match.group(2).strip()
                link_title = match.group(3) if match.group(3) else ""
                
                # Skip empty URLs or non-HTTP URLs initially
                if not link_url:
                    continue

                # Skip URLs that reference anchors on the current page
                if link_url.startswith('#'):
                    continue

                # Convert relative URLs to absolute URLs
                if link_url.startswith('/'):
                    # Absolute path relative to domain
                    absolute_url = f"{base_parsed.scheme}://{base_parsed.netloc}{link_url}"
                elif link_url.startswith('./') or not link_url.startswith('http'):
                    # Relative path
                    absolute_url = urljoin(base_url, link_url)
                else:
                    # Already absolute URL
                    absolute_url = link_url
                
                # Parse the absolute URL for filtering
                try:
                    parsed_url = urlparse(absolute_url)
                    url_domain = parsed_url.netloc.lower()
                    url_path = parsed_url.path.rstrip('/')
                    
                    # Filter: same domain and same path or deeper
                    if (url_domain == base_domain and 
                        url_path.startswith(base_path) and
                        (absolute_url.endswith('.html') or 
                         absolute_url.endswith('.md') or 
                         absolute_url.endswith('.markdown') or
                         not parsed_url.path.split('/')[-1].count('.'))):  # No file extension (likely a page)
                        
                        links.append({
                            'url': absolute_url,
                            'text': link_text or absolute_url,
                            'title': link_title
                        })
                        
                except Exception as url_parse_error:
                    logger.warning(f"Could not parse URL {absolute_url}: {url_parse_error}")
                    continue
            
            # Remove duplicates while preserving order
            seen_urls = set()
            unique_links = []
            for link in links:
                if link['url'] not in seen_urls:
                    seen_urls.add(link['url'])
                    unique_links.append(link)
            
            logger.info(f"Extracted {len(unique_links)} crawlable links from {base_url}")
            return unique_links
            
        except Exception as e:
            logger.error(f"Error extracting links from markdown: {e}")
            return []