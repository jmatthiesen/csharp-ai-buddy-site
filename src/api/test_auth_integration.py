#!/usr/bin/env python3
"""
Integration test for the authentication system.
This script tests the actual database interaction with a test MongoDB instance.

Note: This requires a MongoDB instance to be running and configured via environment variables.
For unit tests that don't require a database, see test_auth.py.
"""

import os
import asyncio
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set test environment variables if needed
os.environ["ARIZE_SPACE_ID"] = os.getenv("ARIZE_SPACE_ID", "test-space-id")
os.environ["ARIZE_API_KEY"] = os.getenv("ARIZE_API_KEY", "test-api-key")
os.environ["ARIZE_PROJECT_NAME"] = os.getenv("ARIZE_PROJECT_NAME", "test-project")

from routers.chat import validate_magic_key


async def setup_test_data(db):
    """
    Set up test data in the database.
    
    Args:
        db: Database object
    """
    user_registrations = db["userRegistrations"]
    
    # Clean up any existing test data
    user_registrations.delete_many({"_id": {"$regex": "^test-"}})
    
    # Insert test keys
    test_keys = [
        {
            "_id": "test-enabled-key-123",
            "is_enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "_id": "test-disabled-key-456",
            "is_enabled": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "_id": "test-legacy-key-789",
            "created_at": datetime.now(timezone.utc).isoformat()
            # Note: no is_enabled field to test backwards compatibility
        }
    ]
    
    user_registrations.insert_many(test_keys)
    print("✓ Test data inserted successfully")


async def cleanup_test_data(db):
    """
    Clean up test data from the database.
    
    Args:
        db: Database object
    """
    user_registrations = db["userRegistrations"]
    result = user_registrations.delete_many({"_id": {"$regex": "^test-"}})
    print(f"✓ Cleaned up {result.deleted_count} test keys")


async def run_integration_tests():
    """Run integration tests against a real database."""
    
    print("=" * 80)
    print("Authentication System Integration Tests")
    print("=" * 80)
    
    # Check environment variables
    mongodb_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("DATABASE_NAME")
    
    if not mongodb_uri or not database_name:
        print("\n❌ Error: MONGODB_URI and DATABASE_NAME must be set")
        print("Set these environment variables and try again.")
        return False
    
    print(f"\nConnecting to MongoDB...")
    print(f"Database: {database_name}")
    
    try:
        # Connect to database
        client = MongoClient(mongodb_uri)
        db = client[database_name]
        
        # Test connection
        db.command('ping')
        print("✓ Connected to MongoDB successfully")
        
        # Setup test data
        print("\nSetting up test data...")
        await setup_test_data(db)
        
        # Run tests
        print("\n" + "-" * 80)
        print("Running tests...")
        print("-" * 80)
        
        test_results = []
        
        # Test 1: Valid enabled key
        print("\n1. Testing valid enabled key...")
        result = await validate_magic_key("test-enabled-key-123")
        test_results.append(("Valid enabled key", result == True, result))
        if result:
            print("   ✓ PASSED: Key validated successfully")
        else:
            print("   ❌ FAILED: Expected True, got False")
        
        # Test 2: Valid disabled key
        print("\n2. Testing valid disabled key...")
        result = await validate_magic_key("test-disabled-key-456")
        test_results.append(("Valid disabled key", result == False, result))
        if not result:
            print("   ✓ PASSED: Disabled key rejected correctly")
        else:
            print("   ❌ FAILED: Expected False, got True")
        
        # Test 3: Non-existent key
        print("\n3. Testing non-existent key...")
        result = await validate_magic_key("test-nonexistent-key")
        test_results.append(("Non-existent key", result == False, result))
        if not result:
            print("   ✓ PASSED: Non-existent key rejected correctly")
        else:
            print("   ❌ FAILED: Expected False, got True")
        
        # Test 4: Legacy key (backwards compatibility)
        print("\n4. Testing legacy key (no is_enabled field)...")
        result = await validate_magic_key("test-legacy-key-789")
        test_results.append(("Legacy key backwards compatibility", result == True, result))
        if result:
            print("   ✓ PASSED: Legacy key accepted (backwards compatible)")
        else:
            print("   ❌ FAILED: Expected True, got False")
        
        # Cleanup
        print("\n" + "-" * 80)
        print("Cleaning up test data...")
        await cleanup_test_data(db)
        
        # Summary
        print("\n" + "=" * 80)
        print("Test Summary")
        print("=" * 80)
        
        passed = sum(1 for _, success, _ in test_results if success)
        total = len(test_results)
        
        for test_name, success, result in test_results:
            status = "✓ PASSED" if success else "❌ FAILED"
            print(f"{status}: {test_name} (result: {result})")
        
        print(f"\n{passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All integration tests passed!")
            return True
        else:
            print(f"\n❌ {total - passed} test(s) failed")
            return False
        
    except Exception as e:
        print(f"\n❌ Error during integration tests: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Always cleanup
        try:
            await cleanup_test_data(db)
        except:
            pass


async def main():
    """Main function."""
    success = await run_integration_tests()
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
