#!/usr/bin/env python3
"""
Integration test for rate limiting in streaming responses.
This script tests the streaming response functionality with simulated rate limit errors.
"""

import asyncio
import json
import logging
import sys
import os
from unittest.mock import AsyncMock, Mock, patch, MagicMock

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routers.chat import _generate_streaming_response_with_retry
from models import Message, AIFilters
from openai import RateLimitError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_streaming_response_with_rate_limit():
    """Test streaming response with simulated rate limit errors."""
    print("Testing streaming response with rate limit simulation...")
    
    # Mock the MCPServerStreamableHttp and related components
    call_count = 0
    
    async def mock_stream_events():
        """Mock the stream_events method with rate limiting simulation."""
        nonlocal call_count
        call_count += 1
        
        if call_count < 3:
            logger.info(f"Simulating rate limit error in stream on attempt {call_count}")
            raise RateLimitError("Rate limit exceeded in streaming", response=Mock(), body=None)
        
        # Simulate successful streaming events
        logger.info(f"Success in streaming on attempt {call_count}")
        
        # Mock ResponseTextDeltaEvent
        mock_event = Mock()
        mock_event.type = "raw_response_event"
        mock_event.data = Mock()
        mock_event.data.delta = "Hello "
        yield mock_event
        
        mock_event2 = Mock()
        mock_event2.type = "raw_response_event"
        mock_event2.data = Mock()
        mock_event2.data.delta = "World!"
        yield mock_event2
    
    def mock_run_streamed(*args, **kwargs):
        """Mock the Runner.run_streamed method."""
        mock_result = Mock()
        mock_result.stream_events = mock_stream_events
        return mock_result
    
    # Patch the necessary components
    with patch('routers.chat.MCPServerStreamableHttp') as mock_mcp, \
         patch('routers.chat.get_agent') as mock_get_agent, \
         patch('routers.chat.Runner.run_streamed', side_effect=mock_run_streamed) as mock_runner:
        
        # Configure mocks
        mock_mcp.return_value.__aenter__ = AsyncMock(return_value=Mock())
        mock_mcp.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_get_agent.return_value = Mock()
        
        # Test streaming response
        responses = []
        try:
            async for response in _generate_streaming_response_with_retry(
                message="Test message",
                history=[],
                filters=None,
                max_attempts=3,
                base_delay=0.1  # Short delay for testing
            ):
                responses.append(response)
                logger.info(f"Received response: {response.strip()}")
        except Exception as e:
            print(f"✗ Streaming test failed with exception: {e}")
            return False
        
        # Verify responses
        if len(responses) >= 3:  # Should have content responses + completion
            print(f"✓ Streaming test passed: Received {len(responses)} responses after {call_count} attempts")
            
            # Check that we got content responses
            content_responses = [r for r in responses if '"type": "content"' in r]
            if len(content_responses) >= 2:
                print(f"  ✓ Received {len(content_responses)} content responses")
            else:
                print(f"  ✗ Expected at least 2 content responses, got {len(content_responses)}")
                return False
                
            # Check for completion response
            completion_responses = [r for r in responses if '"type": "complete"' in r]
            if len(completion_responses) >= 1:
                print(f"  ✓ Received completion response")
            else:
                print(f"  ✗ Expected completion response")
                return False
                
            return True
        else:
            print(f"✗ Streaming test failed: Expected at least 3 responses, got {len(responses)}")
            return False

async def test_streaming_response_max_retries():
    """Test streaming response when max retries are exceeded."""
    print("Testing streaming response with persistent rate limiting...")
    
    call_count = 0
    
    async def always_fail_stream_events():
        """Mock that always raises rate limit errors."""
        nonlocal call_count
        call_count += 1
        logger.info(f"Simulating persistent rate limit error on attempt {call_count}")
        raise RateLimitError("Persistent rate limit in streaming", response=Mock(), body=None)
    
    def mock_run_streamed(*args, **kwargs):
        """Mock the Runner.run_streamed method that always fails."""
        mock_result = Mock()
        mock_result.stream_events = always_fail_stream_events
        return mock_result
    
    # Patch the necessary components
    with patch('routers.chat.MCPServerStreamableHttp') as mock_mcp, \
         patch('routers.chat.get_agent') as mock_get_agent, \
         patch('routers.chat.Runner.run_streamed', side_effect=mock_run_streamed) as mock_runner:
        
        # Configure mocks
        mock_mcp.return_value.__aenter__ = AsyncMock(return_value=Mock())
        mock_mcp.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_get_agent.return_value = Mock()
        
        # Test streaming response
        responses = []
        try:
            async for response in _generate_streaming_response_with_retry(
                message="Test message",
                history=[],
                filters=None,
                max_attempts=2,  # Only 2 attempts
                base_delay=0.1  # Short delay for testing
            ):
                responses.append(response)
                logger.info(f"Received response: {response.strip()}")
        except Exception as e:
            print(f"✗ Max retries test failed with exception: {e}")
            return False
        
        # Should receive an error response
        if len(responses) == 1:
            response_data = json.loads(responses[0])
            if response_data.get("type") == "error":
                print(f"✓ Max retries test passed: Received error response after {call_count} attempts")
                if "high demand" in response_data.get("message", "").lower():
                    print("  ✓ Error message mentions high demand")
                else:
                    print(f"  ✗ Error message doesn't mention high demand: {response_data.get('message')}")
                    return False
                return True
            else:
                print(f"✗ Expected error response, got: {response_data}")
                return False
        else:
            print(f"✗ Expected 1 error response, got {len(responses)} responses")
            return False

async def main():
    """Run all integration tests."""
    print("Rate Limiting Integration Test Suite")
    print("=" * 50)
    
    tests = [
        await test_streaming_response_with_rate_limit(),
        await test_streaming_response_max_retries()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print("\n" + "=" * 50)
    print(f"Integration tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All integration tests passed!")
        return True
    else:
        print("✗ Some integration tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)