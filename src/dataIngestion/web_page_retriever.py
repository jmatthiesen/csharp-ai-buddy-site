#!/usr/bin/env python3
"""
Web Page Retriever for RAG Data Pipeline
Handles fetching and parsing content from web URLs.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from urllib.parse import urljoin

from pipeline_types import RawDocument

logger = logging.getLogger(__name__)


class WebPageRetriever:
    """Handles fetching content from web URLs."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def _get_iso_date(self, source_date: str) -> Optional[datetime]:
        """Parse ISO date string."""
        if isinstance(source_date, str) and not source_date.endswith("Z"):
            created_gmt = source_date + "Z"
            if source_date:
                try:
                    return datetime.fromisoformat(created_gmt)
                except (ValueError, TypeError):
                    return None
        return None
    
    def fetch(self, url: str) -> RawDocument:
        """
        Fetch content from a URL, attempting to find WordPress JSON API if available.
        
        Args:
            url: URL to fetch content from
            
        Returns:
            RawDocument: Raw document with fetched content and metadata
        """
        if not (url.startswith('http://') or url.startswith('https://')):
            # For non-HTTP URLs, return a basic raw document
            return RawDocument(
                content="",
                source_url=url,
                title="",
                content_type="html"
            )
            
        try:
            # First, try to get the HTML page
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            
            # Check if the URL is a markdown file
            if url.endswith('.md') or url.endswith('.markdown'):
                title = ""
                lines = resp.text.splitlines()
                if lines and lines[0].strip().startswith("#"):
                    title = lines[0].lstrip("#").strip()
                content = resp.text
                raw_document = RawDocument(
                        content=content,
                        source_url=url,
                        title=title,
                        content_type="markdown"
                    )
                    
                logger.info(f"Successfully fetched structured content from Markdown file: {url}")
                return raw_document

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Look for WordPress JSON API link
            link = soup.find('link', rel='alternate', type='application/json')
            json_url = None
            
            if link and isinstance(link, Tag):
                href = link.get('href')
                if isinstance(href, str):
                    json_url = href
            
            # If we found a JSON API, try to fetch structured data
            if json_url:
                if not json_url.startswith('http'):
                    json_url = urljoin(url, json_url)
                
                try:
                    json_resp = requests.get(json_url, timeout=self.timeout)
                    json_resp.raise_for_status()
                    data = json_resp.json()
                    
                    # Extract structured data from WordPress JSON API
                    title = data.get('title', {}).get('rendered', '')
                    content = data.get('content', {}).get('rendered', '')
                    created_date = self._get_iso_date(data.get('date_gmt'))
                    
                    # Extract WordPress metadata
                    wp_metadata = {
                        "wordpress_post_id": data.get('id'),
                        "wordpress_author": data.get('author'),
                        "wordpress_categories": [cat.get('name', '') for cat in data.get('categories', [])],
                        "wordpress_tags": [tag.get('name', '') for tag in data.get('tags', [])],
                        "wordpress_json_url": json_url,
                        "wordpress_modified_date": self._get_iso_date(data.get('modified_gmt'))
                    }
                    
                    # Remove None values
                    wp_metadata = {k: v for k, v in wp_metadata.items() if v is not None}
                    
                    raw_document = RawDocument(
                        content=content,
                        source_url=url,
                        title=title,
                        content_type="wordpress",
                        source_metadata=wp_metadata,
                        tags=wp_metadata.get("wordpress_categories", []) + wp_metadata.get("wordpress_tags", []),
                        created_date=created_date
                    )
                    
                    logger.info(f"Successfully fetched structured content from WordPress JSON API: {json_url}")
                    return raw_document
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch from JSON API {json_url}, falling back to HTML: {e}")
            
            # No JSON API found or JSON fetch failed, use HTML content
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            raw_document = RawDocument(
                content=resp.text,
                source_url=url,
                title=title,
                content_type="html",
                created_date=datetime.now()
            )
            
            return raw_document
                
        except Exception as e:
            logger.error(f"Error fetching content from URL {url}: {e}")
            # Return empty document on error
            return RawDocument(
                content="",
                source_url=url,
                title="Error fetching content",
                content_type="html"
            )