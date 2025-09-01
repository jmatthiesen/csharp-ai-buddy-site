#!/usr/bin/env python3
"""
Test script for rate limiting functionality.
This script tests the retry logic for rate limiting errors.
"""

import asyncio
import logging
import sys
import os
from unittest.mock import AsyncMock, Mock, patch

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routers.chat import retry_on_rate_limit, generate_embedding
from openai import RateLimitError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sync_retry_decorator():
    """Test the sync retry decorator with simulated rate limit errors."""
    print("Testing sync retry decorator...")
    
    call_count = 0
    
    @retry_on_rate_limit(max_attempts=3, base_delay=0.1)  # Short delay for testing
    def mock_openai_call():
        nonlocal call_count
        call_count += 1
        
        if call_count < 3:
            logger.info(f"Simulating rate limit error on call {call_count}")
            raise RateLimitError("Rate limit exceeded", response=Mock(), body=None)
        
        logger.info(f"Success on call {call_count}")
        return "Success!"
    
    try:
        result = mock_openai_call()
        print(f"✓ Sync retry test passed: {result}")
        print(f"  Total calls made: {call_count}")
        assert call_count == 3, f"Expected 3 calls, got {call_count}"
    except Exception as e:
        print(f"✗ Sync retry test failed: {e}")
        return False
    
    return True

async def test_async_retry_decorator():
    """Test the async retry decorator with simulated rate limit errors."""
    print("Testing async retry decorator...")
    
    call_count = 0
    
    @retry_on_rate_limit(max_attempts=3, base_delay=0.1)  # Short delay for testing
    async def mock_async_openai_call():
        nonlocal call_count
        call_count += 1
        
        if call_count < 3:
            logger.info(f"Simulating rate limit error on async call {call_count}")
            raise RateLimitError("Rate limit exceeded", response=Mock(), body=None)
        
        logger.info(f"Success on async call {call_count}")
        return "Async Success!"
    
    try:
        result = await mock_async_openai_call()
        print(f"✓ Async retry test passed: {result}")
        print(f"  Total calls made: {call_count}")
        assert call_count == 3, f"Expected 3 calls, got {call_count}"
    except Exception as e:
        print(f"✗ Async retry test failed: {e}")
        return False
    
    return True

async def test_max_retries_exceeded():
    """Test that the decorator properly fails after max retries."""
    print("Testing max retries exceeded...")
    
    call_count = 0
    
    @retry_on_rate_limit(max_attempts=2, base_delay=0.1)  # Only 2 attempts
    async def always_fails():
        nonlocal call_count
        call_count += 1
        logger.info(f"Simulating persistent rate limit error on call {call_count}")
        raise RateLimitError("Persistent rate limit", response=Mock(), body=None)
    
    try:
        await always_fails()
        print("✗ Max retries test failed: Should have raised exception")
        return False
    except RateLimitError:
        print(f"✓ Max retries test passed: Exception raised after {call_count} attempts")
        assert call_count == 2, f"Expected 2 calls, got {call_count}"
        return True
    except Exception as e:
        print(f"✗ Max retries test failed with unexpected exception: {e}")
        return False

def test_non_rate_limit_exception():
    """Test that non-rate-limit exceptions are not retried."""
    print("Testing non-rate-limit exception handling...")
    
    call_count = 0
    
    @retry_on_rate_limit(max_attempts=3, base_delay=0.1)
    def raises_other_exception():
        nonlocal call_count
        call_count += 1
        raise ValueError("Not a rate limit error")
    
    try:
        raises_other_exception()
        print("✗ Non-rate-limit test failed: Should have raised exception")
        return False
    except ValueError:
        print(f"✓ Non-rate-limit test passed: ValueError raised immediately after {call_count} attempts")
        assert call_count == 1, f"Expected 1 call, got {call_count}"
        return True
    except Exception as e:
        print(f"✗ Non-rate-limit test failed with unexpected exception: {e}")
        return False

async def main():
    """Run all tests."""
    print("Rate Limiting Test Suite")
    print("=" * 50)
    
    tests = [
        test_sync_retry_decorator(),
        await test_async_retry_decorator(),
        await test_max_retries_exceeded(),
        test_non_rate_limit_exception()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print("\n" + "=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)