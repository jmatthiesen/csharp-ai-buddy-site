#!/usr/bin/env python3
"""
RSS Feed Database Setup Script
Creates MongoDB indexes for RSS feed monitoring collections.

This script sets up the required database indexes for the RSS feed monitoring system.
Run this script once during initial setup or after database schema changes.

Usage:
    python setup_rss_indexes.py [--config-file path/to/config.json]

Environment Variables:
    MONGODB_CONNECTION_STRING - MongoDB connection string
    MONGODB_DATABASE - MongoDB database name
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Optional

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


def create_rss_indexes(mongo_client: MongoClient, database_name: str) -> bool:
    """
    Create MongoDB indexes for RSS feed monitoring collections.
    
    Args:
        mongo_client: MongoDB client instance
        database_name: Name of the database
        
    Returns:
        bool: True if indexes were created successfully
    """
    try:
        db = mongo_client[database_name]
        
        # Get collections
        subscriptions_collection = db["rss_subscriptions"]
        processed_items_collection = db["rss_processed_items"]
        
        logger.info("Creating RSS feed monitoring indexes...")
        
        # RSS Subscriptions Collection Indexes
        logger.info("Creating indexes for rss_subscriptions collection...")
        
        # Index on feed_url for fast lookups (unique)
        subscriptions_collection.create_index("feed_url", unique=True)
        logger.info("✓ Created unique index on feed_url")
        
        # Index on enabled status for filtering
        subscriptions_collection.create_index("enabled")
        logger.info("✓ Created index on enabled")
        
        # Index on last_checked for scheduling
        subscriptions_collection.create_index("last_checked")
        logger.info("✓ Created index on last_checked")
        
        # RSS Processed Items Collection Indexes
        logger.info("Creating indexes for rss_processed_items collection...")
        
        # Compound index on processed items to avoid duplicates (unique)
        processed_items_collection.create_index([("feed_url", 1), ("item_id", 1)], unique=True)
        logger.info("✓ Created unique compound index on feed_url + item_id")
        
        # Index on processed date for cleanup
        processed_items_collection.create_index("processed_date")
        logger.info("✓ Created index on processed_date")
        
        logger.info("✅ RSS feed monitor indexes created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating RSS indexes: {e}")
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


def main():
    """Main function for RSS database setup."""
    parser = argparse.ArgumentParser(
        description="Set up MongoDB indexes for RSS feed monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use default configuration
    python setup_rss_indexes.py
    
    # Use custom config file
    python setup_rss_indexes.py --config-file /path/to/config.json
    
    # Use environment variables
    export MONGODB_CONNECTION_STRING="mongodb://localhost:27017"
    export MONGODB_DATABASE="rag_pipeline"
    python setup_rss_indexes.py
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
        logger.info("RSS Feed Database Setup")
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
        
        # Validate MongoDB connection
        if not validate_mongodb_connection(config):
            logger.error("❌ MongoDB connection validation failed")
            return 1
        
        if args.dry_run:
            logger.info("✅ Dry run completed successfully - configuration and connection are valid")
            return 0
        
        # Create indexes
        client = MongoClient(config.mongodb_connection_string)
        try:
            success = create_rss_indexes(client, config.mongodb_database)
            
            if success:
                logger.info("\n🎉 RSS feed database setup completed successfully!")
                logger.info("\nNext steps:")
                logger.info("  1. Start using the RSS feed monitor with: python rss_feed_monitor.py")
                logger.info("  2. Add RSS subscriptions with: python rss_feed_monitor.py add-subscription")
                logger.info("  3. Launch the UI with: python rss_feed_monitor.py launch-ui")
                return 0
            else:
                logger.error("\n❌ RSS feed database setup failed!")
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