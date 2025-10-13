"""
Unit tests for the authentication functionality.
Tests the multiple API key authentication system using userRegistrations collection.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

# Set dummy environment variables before importing the module
os.environ["ARIZE_SPACE_ID"] = "test-space-id"
os.environ["ARIZE_API_KEY"] = "test-api-key"
os.environ["ARIZE_PROJECT_NAME"] = "test-project"

from routers.chat import validate_magic_key


@pytest.mark.asyncio
@patch('routers.chat.MongoClient')
@patch('routers.chat.os.getenv')
async def test_validate_magic_key_valid_enabled(mock_getenv, mock_mongo_client):
    """Test validation with a valid and enabled key"""
    # Setup mock environment variables
    mock_getenv.side_effect = lambda key, default=None: {
        "MONGODB_URI": "mongodb://localhost:27017",
        "DATABASE_NAME": "test_db"
    }.get(key, default)
    
    # Setup mock MongoDB
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_mongo_client.return_value.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    
    # Mock finding an enabled key
    mock_collection.find_one.return_value = {
        "_id": "test-key-123",
        "is_enabled": True,
        "created_at": "2025-10-10T00:00:00Z"
    }
    
    result = await validate_magic_key("test-key-123")
    
    assert result is True
    mock_collection.find_one.assert_called_once_with({"_id": "test-key-123"})


@pytest.mark.asyncio
@patch('routers.chat.MongoClient')
@patch('routers.chat.os.getenv')
async def test_validate_magic_key_valid_disabled(mock_getenv, mock_mongo_client):
    """Test validation with a valid but disabled key"""
    # Setup mock environment variables
    mock_getenv.side_effect = lambda key, default=None: {
        "MONGODB_URI": "mongodb://localhost:27017",
        "DATABASE_NAME": "test_db"
    }.get(key, default)
    
    # Setup mock MongoDB
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_mongo_client.return_value.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    
    # Mock finding a disabled key
    mock_collection.find_one.return_value = {
        "_id": "test-key-456",
        "is_enabled": False,
        "created_at": "2025-10-10T00:00:00Z"
    }
    
    result = await validate_magic_key("test-key-456")
    
    assert result is False
    mock_collection.find_one.assert_called_once_with({"_id": "test-key-456"})


@pytest.mark.asyncio
@patch('routers.chat.MongoClient')
@patch('routers.chat.os.getenv')
async def test_validate_magic_key_not_found(mock_getenv, mock_mongo_client):
    """Test validation with a key that doesn't exist"""
    # Setup mock environment variables
    mock_getenv.side_effect = lambda key, default=None: {
        "MONGODB_URI": "mongodb://localhost:27017",
        "DATABASE_NAME": "test_db"
    }.get(key, default)
    
    # Setup mock MongoDB
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_mongo_client.return_value.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    
    # Mock key not found
    mock_collection.find_one.return_value = None
    
    result = await validate_magic_key("non-existent-key")
    
    assert result is False
    mock_collection.find_one.assert_called_once_with({"_id": "non-existent-key"})


@pytest.mark.asyncio
@patch('routers.chat.MongoClient')
@patch('routers.chat.os.getenv')
async def test_validate_magic_key_missing_mongodb_uri(mock_getenv, mock_mongo_client):
    """Test validation when MongoDB URI is missing"""
    # Setup mock environment variables with missing URI
    mock_getenv.side_effect = lambda key, default=None: {
        "DATABASE_NAME": "test_db"
    }.get(key, default)
    
    result = await validate_magic_key("test-key-123")
    
    assert result is False
    # MongoDB client should not be called
    mock_mongo_client.assert_not_called()


@pytest.mark.asyncio
@patch('routers.chat.MongoClient')
@patch('routers.chat.os.getenv')
async def test_validate_magic_key_missing_database_name(mock_getenv, mock_mongo_client):
    """Test validation when database name is missing"""
    # Setup mock environment variables with missing database name
    mock_getenv.side_effect = lambda key, default=None: {
        "MONGODB_URI": "mongodb://localhost:27017"
    }.get(key, default)
    
    result = await validate_magic_key("test-key-123")
    
    assert result is False
    # MongoDB client should not be called
    mock_mongo_client.assert_not_called()


@pytest.mark.asyncio
@patch('routers.chat.MongoClient')
@patch('routers.chat.os.getenv')
async def test_validate_magic_key_database_error(mock_getenv, mock_mongo_client):
    """Test validation when database raises an exception"""
    # Setup mock environment variables
    mock_getenv.side_effect = lambda key, default=None: {
        "MONGODB_URI": "mongodb://localhost:27017",
        "DATABASE_NAME": "test_db"
    }.get(key, default)
    
    # Setup mock MongoDB to raise an exception
    mock_mongo_client.side_effect = Exception("Database connection error")
    
    result = await validate_magic_key("test-key-123")
    
    assert result is False


@pytest.mark.asyncio
@patch('routers.chat.MongoClient')
@patch('routers.chat.os.getenv')
async def test_validate_magic_key_multiple_keys_scenario(mock_getenv, mock_mongo_client):
    """Test validation scenario with multiple different keys"""
    # Setup mock environment variables
    mock_getenv.side_effect = lambda key, default=None: {
        "MONGODB_URI": "mongodb://localhost:27017",
        "DATABASE_NAME": "test_db"
    }.get(key, default)
    
    # Setup mock MongoDB
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_mongo_client.return_value.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    
    # Simulate multiple keys in the database
    def mock_find_one(query):
        key_id = query.get("_id")
        keys_db = {
            "user-1-key": {"_id": "user-1-key", "is_enabled": True},
            "user-2-key": {"_id": "user-2-key", "is_enabled": True},
            "user-3-key": {"_id": "user-3-key", "is_enabled": False},
        }
        return keys_db.get(key_id)
    
    mock_collection.find_one.side_effect = mock_find_one
    
    # Test user 1 (enabled)
    result1 = await validate_magic_key("user-1-key")
    assert result1 is True
    
    # Test user 2 (enabled)
    result2 = await validate_magic_key("user-2-key")
    assert result2 is True
    
    # Test user 3 (disabled)
    result3 = await validate_magic_key("user-3-key")
    assert result3 is False
    
    # Test non-existent key
    result4 = await validate_magic_key("invalid-key")
    assert result4 is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
