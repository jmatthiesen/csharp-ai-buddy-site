"""
Configuration management for RAG Data Ingestion Pipeline.
"""

import os
import json
from typing import Optional
from dataclasses import dataclass

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not available, continue without it
    pass


@dataclass
class Config:
    """Configuration class for RAG pipeline settings."""
    
    # MongoDB settings
    mongodb_connection_string: str
    mongodb_database: str
    mongodb_collection: str
    
    # OpenAI settings
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    
    # Pipeline settings
    max_content_length: int = 8192  # Maximum content length for embeddings
    batch_size: int = 10  # Batch size for bulk operations
    
    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from JSON file (deprecated, use from_env instead)."""
        print("Warning: JSON config files are deprecated. Please use environment variables or .env files.")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        return cls(**config_data)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            mongodb_connection_string=os.getenv("MONGODB_CONNECTION_STRING", "mongodb://localhost:27017"),
            mongodb_database=os.getenv("MONGODB_DATABASE", "rag_pipeline"),
            mongodb_collection=os.getenv("MONGODB_COLLECTION", "documents"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", "8192")),
            batch_size=int(os.getenv("BATCH_SIZE", "10"))
        )
    
    @classmethod
    def load(cls) -> "Config":
        """Load configuration with priority: environment variables > .env file > JSON file."""
        # Try environment variables first
        config = cls.from_env()
        
        # Validate the configuration
        config.validate()
        
        return config
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "mongodb_connection_string": self.mongodb_connection_string,
            "mongodb_database": self.mongodb_database,
            "mongodb_collection": self.mongodb_collection,
            "openai_api_key": self.openai_api_key,
            "embedding_model": self.embedding_model,
            "max_content_length": self.max_content_length,
            "batch_size": self.batch_size
        }
    
    def save_to_file(self, config_path: str):
        """Save configuration to JSON file."""
        config_dict = self.to_dict()
        # Don't save sensitive data
        config_dict["openai_api_key"] = "***"
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        if not self.mongodb_connection_string:
            raise ValueError("MongoDB connection string is required. Set MONGODB_CONNECTION_STRING environment variable.")
        
        if not self.mongodb_database:
            raise ValueError("MongoDB database name is required. Set MONGODB_DATABASE environment variable.")
        
        if not self.mongodb_collection:
            raise ValueError("MongoDB collection name is required. Set MONGODB_COLLECTION environment variable.")
        
        return True 