#!/usr/bin/env python3
"""
Migration script to move from single magic key in chatFeatures collection 
to multiple keys in userRegistrations collection.

This script:
1. Reads the existing magic key from chatFeatures collection (if exists)
2. Migrates it to the userRegistrations collection as an enabled key
3. Optionally removes the old magic_key_config document
4. Provides utilities to add new keys and manage existing ones

Usage:
    # Migrate existing key
    python migrate_keys_to_user_registrations.py --migrate
    
    # Add a new key
    python migrate_keys_to_user_registrations.py --add-key "new-key-123" --notes "Optional notes"
    
    # Disable a key
    python migrate_keys_to_user_registrations.py --disable-key "old-key-456"
    
    # Enable a key
    python migrate_keys_to_user_registrations.py --enable-key "old-key-456"
    
    # List all keys
    python migrate_keys_to_user_registrations.py --list
"""

import os
import sys
import argparse
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv


def get_db_connection():
    """
    Get MongoDB database connection.
    
    Returns:
        Database object
    """
    # Load environment variables
    load_dotenv()
    
    mongodb_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("DATABASE_NAME")
    
    if not mongodb_uri or not database_name:
        print("Error: MONGODB_URI and DATABASE_NAME must be set in environment variables")
        sys.exit(1)
    
    client = MongoClient(mongodb_uri)
    return client[database_name]


def migrate_existing_key(db, remove_old=False):
    """
    Migrate existing magic key from chatFeatures to userRegistrations.
    
    Args:
        db: Database object
        remove_old (bool): Whether to remove the old magic_key_config document
    
    Returns:
        bool: True if migration was successful
    """
    print("Starting migration of existing magic key...")
    
    chat_features = db["chatFeatures"]
    user_registrations = db["userRegistrations"]
    
    # Find existing magic key configuration
    config_doc = chat_features.find_one({"_id": "magic_key_config"})
    
    if not config_doc:
        print("No existing magic key configuration found in chatFeatures collection")
        return False
    
    magic_key = config_doc.get("magic_key")
    
    if not magic_key:
        print("Warning: magic_key_config document exists but has no magic_key field")
        return False
    
    # Check if key already exists in userRegistrations
    existing_key = user_registrations.find_one({"_id": magic_key})
    
    if existing_key:
        print(f"Key already exists in userRegistrations collection")
        print(f"  Key: {magic_key[:10]}...")
        print(f"  Enabled: {existing_key.get('is_enabled', True)}")
        return True
    
    # Create new document in userRegistrations
    new_doc = {
        "_id": magic_key,
        "is_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "migrated_from": "chatFeatures",
        "notes": "Migrated from legacy magic_key_config"
    }
    
    user_registrations.insert_one(new_doc)
    print(f"✓ Successfully migrated key to userRegistrations collection")
    print(f"  Key: {magic_key[:10]}...")
    
    if remove_old:
        chat_features.delete_one({"_id": "magic_key_config"})
        print("✓ Removed old magic_key_config document from chatFeatures")
    else:
        print("ℹ Old magic_key_config document preserved in chatFeatures (use --remove-old to delete)")
    
    return True


def add_key(db, key, notes=None):
    """
    Add a new API key to userRegistrations.
    
    Args:
        db: Database object
        key (str): The API key to add
        notes (str, optional): Additional notes
    
    Returns:
        bool: True if key was added successfully
    """
    user_registrations = db["userRegistrations"]
    
    # Check if key already exists
    existing_key = user_registrations.find_one({"_id": key})
    
    if existing_key:
        print(f"Error: Key already exists")
        print(f"  Key: {key[:10]}...")
        print(f"  Enabled: {existing_key.get('is_enabled', True)}")
        return False
    
    # Create new document
    new_doc = {
        "_id": key,
        "is_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if notes:
        new_doc["notes"] = notes
    
    user_registrations.insert_one(new_doc)
    print(f"✓ Successfully added new key")
    print(f"  Key: {key[:10]}...")
    print(f"  Enabled: True")
    
    return True


def disable_key(db, key):
    """
    Disable an existing API key.
    
    Args:
        db: Database object
        key (str): The API key to disable
    
    Returns:
        bool: True if key was disabled successfully
    """
    user_registrations = db["userRegistrations"]
    
    result = user_registrations.update_one(
        {"_id": key},
        {"$set": {"is_enabled": False, "disabled_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        print(f"Error: Key not found")
        print(f"  Key: {key[:10]}...")
        return False
    
    print(f"✓ Successfully disabled key")
    print(f"  Key: {key[:10]}...")
    
    return True


def enable_key(db, key):
    """
    Enable an existing API key.
    
    Args:
        db: Database object
        key (str): The API key to enable
    
    Returns:
        bool: True if key was enabled successfully
    """
    user_registrations = db["userRegistrations"]
    
    result = user_registrations.update_one(
        {"_id": key},
        {"$set": {"is_enabled": True}, "$unset": {"disabled_at": ""}}
    )
    
    if result.matched_count == 0:
        print(f"Error: Key not found")
        print(f"  Key: {key[:10]}...")
        return False
    
    print(f"✓ Successfully enabled key")
    print(f"  Key: {key[:10]}...")
    
    return True


def list_keys(db):
    """
    List all API keys in userRegistrations.
    
    Args:
        db: Database object
    """
    user_registrations = db["userRegistrations"]
    
    keys = list(user_registrations.find())
    
    if not keys:
        print("No keys found in userRegistrations collection")
        return
    
    print(f"\nFound {len(keys)} key(s) in userRegistrations collection:")
    print("-" * 80)
    
    for i, key_doc in enumerate(keys, 1):
        key_id = key_doc.get("_id", "N/A")
        enabled = key_doc.get("is_enabled", True)
        created = key_doc.get("created_at", "N/A")
        notes = key_doc.get("notes", "")
        
        print(f"\n{i}. Key: {key_id[:10]}... (full key hidden)")
        print(f"   Enabled: {enabled}")
        print(f"   Created: {created}")
        if notes:
            print(f"   Notes: {notes}")
    
    print("\n" + "-" * 80)


def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(
        description="Manage API keys in userRegistrations collection"
    )
    
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Migrate existing magic key from chatFeatures to userRegistrations"
    )
    
    parser.add_argument(
        "--remove-old",
        action="store_true",
        help="Remove old magic_key_config document after migration"
    )
    
    parser.add_argument(
        "--add-key",
        type=str,
        help="Add a new API key"
    )
    
    parser.add_argument(
        "--notes",
        type=str,
        help="Additional notes for the key (for --add-key)"
    )
    
    parser.add_argument(
        "--disable-key",
        type=str,
        help="Disable an existing API key"
    )
    
    parser.add_argument(
        "--enable-key",
        type=str,
        help="Enable an existing API key"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all API keys"
    )
    
    args = parser.parse_args()
    
    # Check if any command was specified
    if not any([args.migrate, args.add_key, args.disable_key, args.enable_key, args.list]):
        parser.print_help()
        sys.exit(0)
    
    # Get database connection
    db = get_db_connection()
    
    # Execute commands
    if args.migrate:
        migrate_existing_key(db, remove_old=args.remove_old)
    
    if args.add_key:
        add_key(db, args.add_key, notes=args.notes)
    
    if args.disable_key:
        disable_key(db, args.disable_key)
    
    if args.enable_key:
        enable_key(db, args.enable_key)
    
    if args.list:
        list_keys(db)


if __name__ == "__main__":
    main()
