#!/usr/bin/env python3
"""
Host-specific handlers for different domains during link extraction and processing.
"""

import logging
import re
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)


class HostHandler(ABC):
    """Abstract base class for host-specific link processing and metadata extraction."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this host handler."""
        pass
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this handler can process URLs from this host."""
        pass
    
    def process_extracted_links(self, links: List[Dict[str, str]], source_url: str) -> List[Dict[str, str]]:
        """
        Process extracted links before presenting to user.
        
        Args:
            links: List of link dictionaries with 'url', 'text', 'title' keys
            source_url: The source URL where links were extracted from
            
        Returns:
            Modified list of link dictionaries
        """
        return links
    
    def get_url_with_fallback(self, url: str) -> Optional[str]:
        """
        Test a URL and provide fallback options if it doesn't exist.
        
        Args:
            url: The URL to test
            
        Returns:
            The working URL (original or fallback), or None if no working URL found
        """
        # Default implementation: just return the original URL
        return url if self._test_url_exists(url) else None
    
    def _test_url_exists(self, url: str) -> bool:
        """
        Test if a URL exists and returns content.
        
        Args:
            url: The URL to test
            
        Returns:
            True if URL exists and returns content, False otherwise
        """
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"URL test failed for {url}: {e}")
            return False
    
    def extract_host_metadata(self, url: str, markdown_content: str) -> Dict[str, Any]:
        """
        Extract host-specific metadata from the content.
        
        Args:
            url: The source URL
            markdown_content: The markdown content
            
        Returns:
            Dictionary of host-specific metadata
        """
        return {}


class GitHubHostHandler(HostHandler):
    """Handler for GitHub URLs with special processing for repositories and documentation."""
    
    @property
    def name(self) -> str:
        return "GitHub"
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is from GitHub domain."""
        parsed = urlparse(url)
        return parsed.netloc.lower() in ['github.com', 'raw.githubusercontent.com']
    
    def process_extracted_links(self, links: List[Dict[str, str]], source_url: str) -> List[Dict[str, str]]:
        """Process GitHub links with special handling for raw URLs and directories."""
        processed_links = []
        
        for link in links:
            processed_link = link.copy()
            original_url = link['url']
            
            # Convert github.com URLs to raw.githubusercontent.com when appropriate
            if 'github.com' in original_url and '/blob/' in original_url:
                raw_url = self._convert_to_raw_url(original_url)
                if raw_url:
                    processed_link['url'] = raw_url
                    processed_link['text'] = f"{link['text']} (raw)"
                    logger.debug(f"Converted GitHub URL to raw: {original_url} -> {raw_url}")
            
            # Handle github.com directory URLs (repository root or folder)
            elif 'github.com' in original_url and self._is_github_directory(original_url):
                readme_url = self._convert_directory_to_readme(original_url)
                if readme_url:
                    processed_link['url'] = readme_url
                    processed_link['text'] = f"{link['text']} (README.md)"
                    logger.debug(f"Converted GitHub directory to README: {original_url} -> {readme_url}")
            
            processed_links.append(processed_link)
        
        return processed_links
    
    def get_url_with_fallback(self, url: str) -> Optional[str]:
        """
        Test GitHub URL and provide README.md fallback for raw.githubusercontent.com directories.
        
        Args:
            url: The URL to test
            
        Returns:
            The working URL (original or with /README.md), or None if no working URL found
        """
        # First, try the URL as-is
        if self._test_url_exists(url):
            logger.debug(f"GitHub URL exists as-is: {url}")
            return url
        
        # If it's a raw.githubusercontent.com URL that failed, try appending README.md
        if 'raw.githubusercontent.com' in url:
            # Ensure the URL ends with /README.md
            if url.endswith('/'):
                readme_url = url + 'README.md'
            elif not url.endswith('/README.md'):
                readme_url = url + '/README.md'
            else:
                # Already ends with /README.md and failed, no fallback
                return None
            
            if self._test_url_exists(readme_url):
                logger.debug(f"GitHub directory fallback successful: {url} -> {readme_url}")
                return readme_url
        
        logger.debug(f"No working GitHub URL found for: {url}")
        return None
    
    def extract_host_metadata(self, url: str, markdown_content: str) -> Dict[str, Any]:
        """Extract GitHub-specific metadata like repository info, stars, etc."""
        metadata = {}
        
        # Extract repository information from URL
        repo_info = self._extract_repo_info(url)
        if repo_info:
            metadata.update(repo_info)
        
        # Look for GitHub-specific badges or information in content
        if 'github.com' in url.lower():
            # Extract star count if present in markdown
            star_match = re.search(r'(\d+)\s*star', markdown_content, re.IGNORECASE)
            if star_match:
                metadata['github_stars'] = int(star_match.group(1))
            
            # Extract license information
            license_match = re.search(r'license[:\s]+([a-zA-Z0-9\s\-\.]+)', markdown_content, re.IGNORECASE)
            if license_match:
                metadata['license'] = license_match.group(1).strip()
        
        return metadata
    
    def _convert_to_raw_url(self, github_url: str) -> str:
        """
        Convert github.com blob URL to raw.githubusercontent.com URL.
        
        Example:
        https://github.com/user/repo/blob/main/README.md
        -> https://raw.githubusercontent.com/user/repo/main/README.md
        """
        try:
            # Pattern: github.com/user/repo/blob/branch/path
            pattern = r'https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)'
            match = re.match(pattern, github_url)
            
            if match:
                user, repo, branch, path = match.groups()
                raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"
                return raw_url
            
            return None
        except Exception as e:
            logger.warning(f"Error converting GitHub URL to raw: {e}")
            return None
    
    def _is_github_directory(self, url: str) -> bool:
        """Check if the GitHub URL points to a directory (not a file)."""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            # Basic repository URL: github.com/user/repo
            if len(path_parts) == 2:
                return True
            
            # Tree URL: github.com/user/repo/tree/branch/path
            if len(path_parts) >= 4 and path_parts[2] == 'tree':
                # Check if the last part doesn't have a file extension
                last_part = path_parts[-1]
                return '.' not in last_part or last_part.endswith('.md') == False
            
            return False
        except Exception:
            return False
    
    def _convert_directory_to_readme(self, github_url: str) -> str:
        """
        Convert GitHub directory URL to raw README.md URL.
        
        Examples:
        https://github.com/user/repo -> https://raw.githubusercontent.com/user/repo/main/README.md
        https://github.com/user/repo/tree/branch/folder -> https://raw.githubusercontent.com/user/repo/branch/folder/README.md
        """
        try:
            parsed = urlparse(github_url)
            path_parts = parsed.path.strip('/').split('/')
            
            if len(path_parts) >= 2:
                user = path_parts[0]
                repo = path_parts[1]
                
                # Basic repo URL: assume main branch
                if len(path_parts) == 2:
                    return f"https://raw.githubusercontent.com/{user}/{repo}/main/README.md"
                
                # Tree URL with branch and path
                elif len(path_parts) >= 4 and path_parts[2] == 'tree':
                    branch = path_parts[3]
                    folder_path = '/'.join(path_parts[4:]) if len(path_parts) > 4 else ''
                    
                    if folder_path:
                        return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{folder_path}/README.md"
                    else:
                        return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/README.md"
            
            return None
        except Exception as e:
            logger.warning(f"Error converting GitHub directory to README: {e}")
            return None
    
    def _extract_repo_info(self, url: str) -> Dict[str, Any]:
        """Extract repository information from GitHub URL."""
        try:
            parsed = urlparse(url)
            if parsed.netloc.lower() in ['github.com', 'raw.githubusercontent.com']:
                path_parts = parsed.path.strip('/').split('/')
                
                if len(path_parts) >= 2:
                    return {
                        'github_user': path_parts[0],
                        'github_repo': path_parts[1],
                        'github_url': f"https://github.com/{path_parts[0]}/{path_parts[1]}"
                    }
            
            return {}
        except Exception:
            return {}


class FallbackHostHandler(HostHandler):
    """Fallback handler that applies to all URLs."""
    
    @property
    def name(self) -> str:
        return "Fallback"
    
    def can_handle(self, url: str) -> bool:
        """This handler can process any URL as a fallback."""
        return True
    
    def process_extracted_links(self, links: List[Dict[str, str]], source_url: str) -> List[Dict[str, str]]:
        """No special processing for fallback handler."""
        return links
    
    def extract_host_metadata(self, url: str, markdown_content: str) -> Dict[str, Any]:
        """Extract basic metadata that applies to any host."""
        metadata = {}
        
        # Extract domain information
        try:
            parsed = urlparse(url)
            metadata['host_domain'] = parsed.netloc.lower()
            metadata['url_scheme'] = parsed.scheme
        except Exception:
            pass
        
        return metadata