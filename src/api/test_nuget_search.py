"""
Test script for NuGet search functionality.

This script tests the NuGet package search and details retrieval functionality
to ensure it works correctly with the NuGet.org API.
"""

import asyncio
from nuget_search import search_nuget_packages, get_nuget_package_details

async def test_nuget_search():
    """Test NuGet package search functionality."""
    print("=" * 60)
    print("Testing NuGet Package Search")
    print("=" * 60)
    
    # Test 1: Search for popular package
    print("Test 1: Searching for 'Newtonsoft.Json' (top 3 results)")
    print("-" * 50)
    result = await search_nuget_packages('Newtonsoft.Json', max_results=3)
    print(result)
    print()
    
    # Test 2: Search for Microsoft packages
    print("Test 2: Searching for 'Microsoft.Extensions' (top 5 results)")
    print("-" * 50)
    result = await search_nuget_packages('Microsoft.Extensions', max_results=5)
    print(result[:800] + "..." if len(result) > 800 else result)
    print()
    
    # Test 3: Search including prerelease packages
    print("Test 3: Searching for 'System.Text.Json' with prerelease (top 3 results)")
    print("-" * 50)
    result = await search_nuget_packages('System.Text.Json', max_results=3, include_prerelease=True)
    print(result[:800] + "..." if len(result) > 800 else result)
    print()

async def test_nuget_package_details():
    """Test NuGet package details retrieval."""
    print("=" * 60)
    print("Testing NuGet Package Details Retrieval")
    print("=" * 60)
    
    # Test 1: Get details for popular package
    print("Test 1: Getting details for 'Newtonsoft.Json'")
    print("-" * 50)
    details = await get_nuget_package_details('Newtonsoft.Json')
    print(details[:1000] + "..." if len(details) > 1000 else details)
    print()
    
    # Test 2: Get details for Microsoft package
    print("Test 2: Getting details for 'Microsoft.Extensions.DependencyInjection'")
    print("-" * 50)
    details = await get_nuget_package_details('Microsoft.Extensions.DependencyInjection')
    print(details[:1000] + "..." if len(details) > 1000 else details)
    print()
    
    # Test 3: Get details for specific version
    print("Test 3: Getting details for 'Newtonsoft.Json' version '12.0.3'")
    print("-" * 50)
    details = await get_nuget_package_details('Newtonsoft.Json', version='12.0.3')
    print(details[:1000] + "..." if len(details) > 1000 else details)
    print()

async def test_error_handling():
    """Test error handling for invalid inputs."""
    print("=" * 60)
    print("Testing Error Handling")
    print("=" * 60)
    
    # Test 1: Search for non-existent package
    print("Test 1: Searching for non-existent package 'ThisPackageDoesNotExist12345'")
    print("-" * 50)
    result = await search_nuget_packages('ThisPackageDoesNotExist12345')
    print(result)
    print()
    
    # Test 2: Get details for non-existent package
    print("Test 2: Getting details for non-existent package 'NonExistentPackage12345'")
    print("-" * 50)
    try:
        details = await get_nuget_package_details('NonExistentPackage12345')
        print(details)
    except Exception as e:
        print(f"Expected error occurred: {str(e)}")
    print()

async def run_all_tests():
    """Run all NuGet search tests."""
    print("Starting NuGet Search Tests...")
    print("This may take a few moments as we make API calls to NuGet.org")
    print()
    
    try:
        await test_nuget_search()
        await test_nuget_package_details()
        await test_error_handling()
        
        print("=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the tests
    asyncio.run(run_all_tests())