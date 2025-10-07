#!/usr/bin/env python3
"""
Simple test runner for RAG Data Ingestion Pipeline tests.
"""

import os
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_ai_categorization import run_tests


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run RAG Data Ingestion Pipeline tests")
    parser.add_argument("--openai", action="store_true", 
                       help="Enable OpenAI evaluation tests (requires OPENAI_API_KEY)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Set environment variable for OpenAI tests if requested
    if args.openai and not os.getenv("OPENAI_API_KEY"):
        print("Warning: --openai specified but OPENAI_API_KEY not set")
        print("OpenAI evaluation tests will be skipped")
    
    print("=" * 60)
    print("RAG Data Ingestion Pipeline - Test Suite")
    print("=" * 60)
    
    # Run tests
    success = run_tests()
    
    print("=" * 60)
    if success:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 