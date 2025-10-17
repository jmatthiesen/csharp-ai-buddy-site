#!/usr/bin/env python3
"""
Document Pipeline Database Setup Script
Creates MongoDB indexes for document processing pipeline collections.

This script sets up the required database indexes for the document processing pipeline system.
Run this script once during initial setup or after database schema changes.

Usage:
    python setup_document_pipeline_indexes.py [--config-file path/to/config.json]

Environment Variables:
    MONGODB_CONNECTION_STRING - MongoDB connection string
    MONGODB_DATABASE - MongoDB database name
    MONGODB_COLLECTION - Documents collection name (default: documents)
    MONGODB_CHUNKS_COLLECTION - Chunks collection name (default: document_chunks)
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# MongoDB
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Configuration
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_document_pipeline_indexes(mongo_client: MongoClient, database_name: str, 
                                   documents_collection_name: str = "documents",
                                   chunks_collection_name: str = "document_chunks") -> bool:
    """
    Create MongoDB indexes for document pipeline collections.
    
    Args:
        mongo_client: MongoDB client instance
        database_name: Name of the database
        documents_collection_name: Name of the documents collection
        chunks_collection_name: Name of the chunks collection
        
    Returns:
        bool: True if indexes were created successfully
    """
    try:
        db = mongo_client[database_name]
        
        # Get collections
        documents_collection = db[documents_collection_name]
        chunks_collection = db[chunks_collection_name]
        
        logger.info("Creating document pipeline indexes...")
        
        # Documents Collection Indexes
        logger.info(f"Creating indexes for {documents_collection_name} collection...")
        
        # Index on documentId for fast lookups
        documents_collection.create_index("documentId")
        logger.info("✓ Created index on documentId")
        
        # Index on sourceUrl for deduplication and lookups
        documents_collection.create_index("sourceUrl")
        logger.info("✓ Created index on sourceUrl")
        
        # Index on tags for filtering
        documents_collection.create_index("tags")
        logger.info("✓ Created index on tags")
        
        # Index on publishedDate for time-based queries
        documents_collection.create_index("publishedDate")
        logger.info("✓ Created index on publishedDate")
        
        # Compound index on tags and indexedDate for efficient filtered sorting
        documents_collection.create_index([("tags", 1), ("indexedDate", -1)])
        logger.info("✓ Created compound index on tags + indexedDate")
        
        # Chunks Collection Indexes
        logger.info(f"Creating indexes for {chunks_collection_name} collection...")
        
        # Index on chunk_id for fast lookups (non-unique for ObjectIDs)
        chunks_collection.create_index("chunk_id")
        logger.info("✓ Created index on chunk_id")
        
        # Index on original_document_id for document-based queries
        chunks_collection.create_index("original_document_id")
        logger.info("✓ Created index on original_document_id")
        
        # Index on source_url for URL-based lookups
        chunks_collection.create_index("source_url")
        logger.info("✓ Created index on source_url")
        
        # Index on tags for filtering
        chunks_collection.create_index("tags")
        logger.info("✓ Created index on tags")
        
        # Index on indexed_date for time-based queries
        chunks_collection.create_index("indexed_date")
        logger.info("✓ Created index on indexed_date")
        
        # Compound index on tags and indexed_date for efficient filtered sorting
        chunks_collection.create_index([("tags", 1), ("indexed_date", -1)])
        logger.info("✓ Created compound index on tags + indexed_date")
        
        logger.info("✅ Document pipeline indexes created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating document pipeline indexes: {e}")
        return False


def validate_mongodb_connection(config: Config) -> bool:
    """
    Validate MongoDB connection and database access.
    
    Args:
        config: Configuration object with MongoDB settings
        
    Returns:
        bool: True if connection is valid
    """
    try:
        logger.info("Validating MongoDB connection...")
        
        client = MongoClient(config.mongodb_connection_string)
        
        # Test connection with ping
        client.admin.command('ping')
        logger.info("✓ MongoDB connection successful")
        
        # Test database access
        db = client[config.mongodb_database]
        collections = db.list_collection_names()
        logger.info(f"✓ Database '{config.mongodb_database}' accessible")
        logger.info(f"  Found {len(collections)} existing collections: {collections}")
        
        client.close()
        return True
        
    except PyMongoError as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error validating connection: {e}")
        return False


def check_existing_data(mongo_client: MongoClient, config: Config) -> Dict[str, int]:
    """
    Check for existing documents and chunks in the collections.
    
    Args:
        mongo_client: MongoDB client instance
        config: Configuration object
        
    Returns:
        Dict with counts of existing documents and chunks
    """
    try:
        db = mongo_client[config.mongodb_database]
        documents_collection = db[config.mongodb_collection]
        chunks_collection = db[config.mongodb_chunks_collection]
        
        doc_count = documents_collection.count_documents({})
        chunk_count = chunks_collection.count_documents({})
        
        logger.info(f"Existing data: {doc_count} documents, {chunk_count} chunks")
        
        return {
            "documents": doc_count,
            "chunks": chunk_count
        }
        
    except Exception as e:
        logger.warning(f"Could not check existing data: {e}")
        return {"documents": 0, "chunks": 0}


def main():
    """Main function for document pipeline database setup."""
    parser = argparse.ArgumentParser(
        description="Set up MongoDB indexes for document processing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use default configuration
    python setup_document_pipeline_indexes.py
    
    # Use custom config file
    python setup_document_pipeline_indexes.py --config-file /path/to/config.json
    
    # Use environment variables
    export MONGODB_CONNECTION_STRING="mongodb://localhost:27017"
    export MONGODB_DATABASE="rag_pipeline"
    export MONGODB_COLLECTION="documents"
    export MONGODB_CHUNKS_COLLECTION="document_chunks"
    python setup_document_pipeline_indexes.py
        """
    )
    
    parser.add_argument(
        "--config-file",
        help="Path to configuration file (JSON format)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and connection without creating indexes"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        logger.info("Document Pipeline Database Setup")
        logger.info("=" * 50)
        
        # Load configuration
        if args.config_file:
            logger.info(f"Loading configuration from: {args.config_file}")
            config = Config.from_file(args.config_file)
        else:
            logger.info("Loading configuration from environment variables")
            config = Config.load()
        
        # Validate configuration
        logger.info("Validating configuration...")
        config.validate()
        logger.info("✓ Configuration is valid")
        
        # Display collection names that will be used
        logger.info(f"Documents collection: {config.mongodb_collection}")
        logger.info(f"Chunks collection: {config.mongodb_chunks_collection}")
        
        # Validate MongoDB connection
        if not validate_mongodb_connection(config):
            logger.error("❌ MongoDB connection validation failed")
            return 1
        
        # Check existing data
        client = MongoClient(config.mongodb_connection_string)
        try:
            data_counts = check_existing_data(client, config)
            
            if args.dry_run:
                logger.info("✅ Dry run completed successfully - configuration and connection are valid")
                logger.info(f"Collections would be indexed: {config.mongodb_collection}, {config.mongodb_chunks_collection}")
                return 0
            
            # Create indexes
            success = create_document_pipeline_indexes(
                client, 
                config.mongodb_database,
                config.mongodb_collection,
                config.mongodb_chunks_collection
            )
            
            if success:
                logger.info("\n🎉 Document pipeline database setup completed successfully!")
                logger.info("\nIndexes created for:")
                logger.info(f"  📄 Documents collection: {config.mongodb_collection}")
                logger.info(f"  📝 Chunks collection: {config.mongodb_chunks_collection}")
                logger.info("\nNext steps:")
                logger.info("  1. Start using the document pipeline with: python document_pipeline_v2.py")
                logger.info("  2. Add documents with the CLI: python cli.py add-document <url>")
                logger.info("  3. Process RSS feeds: python rss_feed_monitor.py")
                return 0
            else:
                logger.error("\n❌ Document pipeline database setup failed!")
                return 1
                
        finally:
            client.close()
    
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if args.verbose:
            logger.exception("Full error details:")
        return 1


if __name__ == "__main__":
    exit(main())