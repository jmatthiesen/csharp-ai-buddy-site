#!/usr/bin/env python3
"""
Web Page Retriever for RAG Data Pipeline
Handles fetching and parsing content from web URLs.
"""

import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from document import Document

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

    def fetch(self, url: str) -> Document:
        """
        Fetch content from a URL, attempting to find WordPress JSON API if available.

        Args:
            url: URL to fetch content from

        Returns:
            Document: Document with fetched content and metadata
        """
        if not (url.startswith("http://") or url.startswith("https://")):
            return Document.create_from_url(url)

        try:
            # First, try to get the HTML page
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for WordPress JSON API link
            link = soup.find("link", rel="alternate", type="application/json")
            json_url = None

            if link and isinstance(link, Tag):
                href = link.get("href")
                if isinstance(href, str):
                    json_url = href

            # If we found a JSON API, try to fetch structured data
            if json_url:
                if not json_url.startswith("http"):
                    json_url = urljoin(url, json_url)

                try:
                    json_resp = requests.get(json_url, timeout=self.timeout)
                    json_resp.raise_for_status()
                    data = json_resp.json()

                    # Extract structured data from WordPress JSON API
                    title = data.get("title", {}).get("rendered", "")
                    content = data.get("content", {}).get("rendered", "")
                    created_date = self._get_iso_date(data.get("date_gmt"))
                    updated_date = self._get_iso_date(data.get("modified_gmt"))

                    document = Document(
                        documentId=url,
                        title=title,
                        content=content,
                        sourceUrl=url,
                        createdDate=created_date,
                        updatedDate=updated_date,
                        json_url=json_url,
                    )

                    logger.info(
                        f"Successfully fetched structured content from WordPress JSON API: {json_url}"
                    )
                    return document

                except Exception as e:
                    logger.warning(
                        f"Failed to fetch from JSON API {json_url}, falling back to HTML: {e}"
                    )

            # No JSON API found or JSON fetch failed, use HTML content
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()

            document = Document(documentId=url, title=title, content=resp.text, sourceUrl=url)

            return document

        except Exception as e:
            logger.error(f"Error fetching content from URL {url}: {e}")
            # Return empty document on error
            return Document.create_from_url(url)
