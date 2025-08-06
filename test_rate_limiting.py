#!/usr/bin/env python3
"""
Test script for rate limiting error handling.
This script simulates rate limiting errors to test the retry logic.
"""

import sys
import os
import time
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the API directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'api'))

from main import retry_with_exponential_backoff, async_retry_with_exponential_backoff, generate_embedding
import asyncio


class MockOpenAIError(Exception):
    """Mock OpenAI error for testing."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code
        if status_code == 429:
            # Mock response with headers
            self.response = Mock()
            self.response.headers = {'retry-after': '2'}


class TestRateLimitingRetry(unittest.TestCase):
    """Test cases for rate limiting and retry logic."""
    
    def test_retry_decorator_success_on_first_try(self):
        """Test that successful calls don't trigger retries."""
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)
    
    def test_retry_decorator_rate_limit_error(self):
        """Test retry logic for rate limiting errors."""
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=2, base_delay=0.1)
        def rate_limited_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MockOpenAIError("Rate limit exceeded", status_code=429)
            return "success after retries"
        
        start_time = time.time()
        result = rate_limited_function()
        end_time = time.time()
        
        self.assertEqual(result, "success after retries")
        self.assertEqual(call_count, 3)
        # Should have taken some time due to retries (at least 0.3 seconds for 2 retries)
        self.assertGreater(end_time - start_time, 0.2)
    
    def test_retry_decorator_max_retries_exceeded(self):
        """Test that errors are raised after max retries are exceeded."""
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=2, base_delay=0.1)
        def always_rate_limited_function():
            nonlocal call_count
            call_count += 1
            raise MockOpenAIError("Rate limit exceeded", status_code=429)
        
        with self.assertRaises(MockOpenAIError):
            always_rate_limited_function()
        
        self.assertEqual(call_count, 3)  # 1 initial + 2 retries
    
    def test_retry_decorator_non_rate_limit_error(self):
        """Test that non-rate-limit errors are not retried."""
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=3)
        def function_with_other_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Some other error")
        
        with self.assertRaises(ValueError):
            function_with_other_error()
        
        self.assertEqual(call_count, 1)  # Should not retry
    
    async def test_async_retry_decorator(self):
        """Test async retry decorator."""
        call_count = 0
        
        @async_retry_with_exponential_backoff(max_retries=2, base_delay=0.1)
        async def async_rate_limited_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MockOpenAIError("Rate limit exceeded", status_code=429)
            return "async success"
        
        result = await async_rate_limited_function()
        self.assertEqual(result, "async success")
        self.assertEqual(call_count, 3)
    
    @patch('main.OpenAI')
    def test_generate_embedding_with_retries(self, mock_openai_class):
        """Test that generate_embedding function uses retry logic."""
        # Mock the OpenAI client and its methods
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Mock embeddings response
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]
        
        # First call fails with rate limit, second succeeds
        mock_client.embeddings.create.side_effect = [
            MockOpenAIError("Rate limit exceeded", status_code=429),
            mock_response
        ]
        
        result = generate_embedding("test text")
        
        self.assertEqual(result, [0.1, 0.2, 0.3])
        self.assertEqual(mock_client.embeddings.create.call_count, 2)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestRateLimitingRetry)
    
    # Run sync tests
    runner = unittest.TextTestRunner(verbosity=2)
    sync_result = runner.run(suite)
    
    # Run async tests
    print("\nRunning async tests...")
    test_instance = TestRateLimitingRetry()
    
    async def run_async_tests():
        try:
            await test_instance.test_async_retry_decorator()
            print("✓ test_async_retry_decorator - PASSED")
        except Exception as e:
            print(f"✗ test_async_retry_decorator - FAILED: {e}")
            return False
        return True
    
    async_success = asyncio.run(run_async_tests())
    
    return sync_result.wasSuccessful() and async_success


if __name__ == "__main__":
    print("Testing Rate Limiting and Retry Logic")
    print("=" * 50)
    
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)