#!/usr/bin/env python3
"""
Test script for the C# AI Buddy API streaming functionality.
This script tests the streaming chat endpoint to ensure it works correctly.
"""

import asyncio
import json
import httpx
import os
from typing import AsyncGenerator

# API endpoint
BASE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{BASE_URL}/api/chat"

async def test_streaming_chat():
    """Test the streaming chat endpoint."""
    
    print("Testing C# AI Buddy API streaming...")
    
    # Test message
    test_message = {
        "message": "How do I use ML.NET for image classification?",
        "history": []
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Make the request
            async with client.stream(
                "POST",
                CHAT_ENDPOINT,
                json=test_message,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                print("\nStreaming response:")
                print("-" * 50)
                
                # Read the streaming response
                async for chunk in response.aiter_lines():
                    if chunk.strip():
                        try:
                            data = json.loads(chunk)
                            if data.get("type") == "content":
                                print(data.get("content", ""), end="", flush=True)
                            elif data.get("type") == "tool_call":
                                print(f"\n[{data.get('content')}]", flush=True)
                            elif data.get("type") == "complete":
                                print(f"\n\n[Response completed at {data.get('timestamp')}]")
                            elif data.get("type") == "error":
                                print(f"\n[Error: {data.get('content')}]")
                        except json.JSONDecodeError as e:
                            print(f"\n[JSON decode error: {e}]")
                            print(f"[Raw chunk: {chunk}]")
                
                print("\n" + "-" * 50)
                print("Test completed!")
                
    except httpx.ConnectError:
        print("Error: Could not connect to the API server.")
        print("Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"Error during test: {str(e)}")

async def test_health_endpoint():
    """Test the health endpoint."""
    
    print("Testing health endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            print(f"Health status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()}")
            else:
                print(f"Error: {response.text}")
                
    except httpx.ConnectError:
        print("Error: Could not connect to the API server.")
        print("Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"Error during health check: {str(e)}")

async def main():
    """Main test function."""
    
    print("C# AI Buddy API Test Suite")
    print("=" * 50)
    
    # Check if required environment variables are set
    env_vars = ["MONGODB_URI", "DATABASE_NAME", "OPENAI_API_KEY"]
    missing_vars = [var for var in env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("Some tests may fail without proper configuration.")
        print()
    
    # Test health endpoint first
    await test_health_endpoint()
    print()
    
    # Test streaming chat
    await test_streaming_chat()

if __name__ == "__main__":
    asyncio.run(main())
