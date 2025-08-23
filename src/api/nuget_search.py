"""
NuGet Package Search Module

This module provides functionality to search NuGet.org for packages,
prioritizing official and verified sources, and retrieving package documentation.
"""

import aiohttp
import logging
import atexit
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class NuGetPackage(BaseModel):
    """Model representing a NuGet package from search results."""
    id: str
    version: str
    title: str
    description: str
    authors: List[str]
    total_downloads: int
    verified: bool
    package_types: List[Dict[str, str]]
    versions: List[Dict[str, Any]]
    project_url: Optional[str] = None
    icon_url: Optional[str] = None
    tags: List[str] = []

class NuGetSearchResponse(BaseModel):
    """Model representing NuGet search API response."""
    total_hits: int
    packages: List[NuGetPackage]

class NuGetSearchService:
    """Service for searching NuGet packages and retrieving documentation."""
    
    def __init__(self):
        self.service_index_url = "https://api.nuget.org/v3/index.json"
        self.primary_search_url = "https://azuresearch-usnc.nuget.org/query"
        self.secondary_search_url = "https://azuresearch-ussc.nuget.org/query"
        self.base_content_url = "https://api.nuget.org/v3-flatcontainer/"
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a reusable HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                connector=aiohttp.TCPConnector(limit=100, limit_per_host=10)
            )
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def get_service_index(self) -> Dict[str, Any]:
        """Fetch the NuGet service index to get current API endpoints."""
        try:
            session = await self._get_session()
            async with session.get(self.service_index_url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Error fetching service index: {str(e)}")
            raise
    
    async def search_packages(
        self, 
        query: str, 
        take: int = 20, 
        skip: int = 0, 
        include_prerelease: bool = False,
        package_type: Optional[str] = None
    ) -> NuGetSearchResponse:
        """
        Search for NuGet packages with prioritization of official/verified packages.
        
        Args:
            query: Search query terms
            take: Number of results to return (max 1000)
            skip: Number of results to skip for pagination (max 3000)
            include_prerelease: Whether to include pre-release packages
            package_type: Filter by package type (e.g., "Dependency")
            
        Returns:
            NuGetSearchResponse containing search results
        """
        try:
            params = {
                'q': query,
                'take': min(take, 1000),
                'skip': min(skip, 3000),
                'prerelease': str(include_prerelease).lower()
            }
            
            if package_type:
                params['packageType'] = package_type
                
            # Try primary search endpoint first
            search_url = self.primary_search_url
            
            session = await self._get_session()
            try:
                async with session.get(search_url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
            except Exception as e:
                logger.warning(f"Primary search endpoint failed: {str(e)}, trying secondary")
                # Fallback to secondary search endpoint
                search_url = self.secondary_search_url
                async with session.get(search_url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
            
            # Parse and prioritize results
            packages = self._parse_search_results(data.get('data', []))
            
            # Sort packages: verified first, then by download count
            packages.sort(key=lambda p: (-int(p.verified), -p.total_downloads))
            
            return NuGetSearchResponse(
                total_hits=data.get('totalHits', 0),
                packages=packages
            )
            
        except Exception as e:
            logger.error(f"Error searching packages: {str(e)}")
            raise
    
    def _parse_search_results(self, data: List[Dict[str, Any]]) -> List[NuGetPackage]:
        """Parse raw search results into NuGetPackage objects."""
        packages = []
        
        for item in data:
            try:
                package = NuGetPackage(
                    id=item.get('id', ''),
                    version=item.get('version', ''),
                    title=item.get('title', item.get('id', '')),
                    description=item.get('description', ''),
                    authors=item.get('authors', []),
                    total_downloads=item.get('totalDownloads', 0),
                    verified=item.get('verified', False),
                    package_types=item.get('packageTypes', []),
                    versions=item.get('versions', []),
                    project_url=item.get('projectUrl'),
                    icon_url=item.get('iconUrl'),
                    tags=item.get('tags', [])
                )
                packages.append(package)
            except Exception as e:
                logger.warning(f"Error parsing package data: {str(e)}")
                continue
                
        return packages
    
    async def get_package_metadata(self, package_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve detailed metadata for a specific package.
        
        Args:
            package_id: The package identifier
            version: Specific version (if None, gets latest)
            
        Returns:
            Package metadata dictionary
        """
        try:
            session = await self._get_session()
            
            # First get package versions if no version specified
            if not version:
                versions_url = f"{self.base_content_url}{package_id.lower()}/index.json"
                async with session.get(versions_url) as response:
                    response.raise_for_status()
                    versions_data = await response.json()
                    versions = versions_data.get('versions', [])
                    if versions:
                        version = versions[-1]  # Get latest version
                    else:
                        raise ValueError(f"No versions found for package {package_id}")
            
            # Get package manifest (.nuspec)
            nuspec_url = f"{self.base_content_url}{package_id.lower()}/{version.lower()}/{package_id.lower()}.nuspec"
            
            async with session.get(nuspec_url) as response:
                response.raise_for_status()
                nuspec_content = await response.text()
                    
            return {
                'package_id': package_id,
                'version': version,
                'nuspec_content': nuspec_content,
                'download_url': f"{self.base_content_url}{package_id.lower()}/{version.lower()}/{package_id.lower()}.{version.lower()}.nupkg"
            }
            
        except Exception as e:
            logger.error(f"Error getting package metadata for {package_id}: {str(e)}")
            raise
    
    async def get_package_readme(self, package_id: str, version: Optional[str] = None) -> Optional[str]:
        """
        Attempt to retrieve README or documentation for a package.
        
        Args:
            package_id: The package identifier
            version: Specific version (if None, uses latest)
            
        Returns:
            README content if available, None otherwise
        """
        try:
            # This would require extracting the .nupkg file and looking for README files
            # For now, we'll return the description from search results
            search_results = await self.search_packages(package_id, take=1)
            if search_results.packages:
                package = search_results.packages[0]
                if package.id.lower() == package_id.lower():
                    return package.description
            return None
            
        except Exception as e:
            logger.error(f"Error getting README for {package_id}: {str(e)}")
            return None

# Global service instance
nuget_service = NuGetSearchService()

# Cleanup function for graceful shutdown
import atexit
import asyncio

def cleanup_service():
    """Cleanup function to close the service session on exit."""
    try:
        if nuget_service._session and not nuget_service._session.closed:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is running, schedule cleanup
                asyncio.create_task(nuget_service.close())
            else:
                # If event loop is not running, run cleanup synchronously
                loop.run_until_complete(nuget_service.close())
    except Exception:
        pass  # Ignore cleanup errors

atexit.register(cleanup_service)

# Function tools for the AI agent
try:
    from agents import function_tool
except ImportError:
    # For testing without agents library
    def function_tool(func):
        return func

@function_tool
async def search_nuget_packages(query: str, max_results: int = 10, include_prerelease: bool = False) -> str:
    """
    Search for NuGet packages with prioritization of official and verified sources.
    
    Args:
        query (str): Search terms for NuGet packages
        max_results (int): Maximum number of results to return (default 10)
        include_prerelease (bool): Whether to include pre-release packages
        
    Returns:
        str: Formatted search results with package information
    """
    try:
        logger.info(f"Searching NuGet packages for query: '{query}'")
        
        # Perform the search
        search_results = await nuget_service.search_packages(
            query=query,
            take=min(max_results, 20),  # Limit to reasonable number
            include_prerelease=include_prerelease
        )
        
        if not search_results.packages:
            return f"No NuGet packages found for query: '{query}'"
        
        # Format results for display
        results = []
        results.append(f"Found {search_results.total_hits} NuGet packages (showing top {len(search_results.packages)}):\n")
        
        for i, package in enumerate(search_results.packages, 1):
            verified_status = "✓ VERIFIED" if package.verified else ""
            authors = ", ".join(package.authors) if package.authors else "Unknown"
            
            package_info = f"""
{i}. **{package.title}** ({package.id}) {verified_status}
   Version: {package.version}
   Authors: {authors}
   Downloads: {package.total_downloads:,}
   Description: {package.description[:200]}{'...' if len(package.description) > 200 else ''}
   Package Types: {', '.join([pt.get('name', '') for pt in package.package_types])}
"""
            
            if package.project_url:
                package_info += f"   Project URL: {package.project_url}\n"
                
            results.append(package_info)
        
        formatted_results = "\n".join(results)
        logger.info(f"Successfully found {len(search_results.packages)} NuGet packages")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error searching NuGet packages: {str(e)}", exc_info=True)
        return f"Sorry, I encountered an error while searching NuGet packages: {str(e)}"

@function_tool
async def get_nuget_package_details(package_id: str, version: str = None) -> str:
    """
    Get detailed information and documentation for a specific NuGet package.
    
    Args:
        package_id (str): The NuGet package identifier (e.g., "Newtonsoft.Json")
        version (str): Specific version to get details for (optional, uses latest if not specified)
        
    Returns:
        str: Detailed package information including metadata and documentation
    """
    try:
        logger.info(f"Getting details for NuGet package: {package_id}, version: {version or 'latest'}")
        
        # Get package metadata
        metadata = await nuget_service.get_package_metadata(package_id, version)
        
        # Get README/description
        readme = await nuget_service.get_package_readme(package_id, version)
        
        # Format the detailed information
        details = f"""
**NuGet Package Details: {package_id}**

**Version:** {metadata['version']}
**Package ID:** {metadata['package_id']}
**Download URL:** {metadata['download_url']}

**Package Manifest (.nuspec):**
```xml
{metadata['nuspec_content'][:1000]}{'...' if len(metadata['nuspec_content']) > 1000 else ''}
```

**Documentation/Description:**
{readme if readme else 'No additional documentation available.'}
"""
        
        logger.info(f"Successfully retrieved details for NuGet package: {package_id}")
        return details
        
    except Exception as e:
        logger.error(f"Error getting NuGet package details for {package_id}: {str(e)}", exc_info=True)
        return f"Sorry, I encountered an error while getting details for NuGet package '{package_id}': {str(e)}"