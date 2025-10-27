from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import os
import logging
from pymongo import MongoClient
from opentelemetry import trace
from datetime import datetime

from models import NewsResponse, NewsItem

router = APIRouter()
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

@router.get("/api/news", response_model=NewsResponse)
async def get_news(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of news items per page"),
    search: Optional[str] = Query(None, description="Search query")
):
    """
    Get latest news items from RSS feeds with pagination and search.
    """
    with tracer.start_as_current_span("get_news") as span:
        try:
            span.set_attribute("page", page)
            span.set_attribute("page_size", page_size)
            if search:
                span.set_attribute("search_query", search)

            # Connect to MongoDB
            mongodb_uri = os.getenv("MONGODB_URI")
            database_name = os.getenv("DATABASE_NAME")
            
            if not mongodb_uri or not database_name:
                raise HTTPException(status_code=500, detail="Database not configured")
            
            mongoClient = MongoClient(mongodb_uri)
            db = mongoClient[database_name]
            documents_collection = db["documents"]
            
            # Build query to get all articles (not limited to RSS items)
            query = {}
            
            # Add search functionality
            if search:
                search_regex = {"$regex": search, "$options": "i"}
                query["$or"] = [
                    {"title": search_regex},
                    {"content": search_regex},
                    {"rss_author": search_regex}
                ]
            
            # Count total documents
            total = documents_collection.count_documents(query)
            
            # Calculate pagination
            skip = (page - 1) * page_size
            pages = (total + page_size - 1) // page_size
            
            # Get news items sorted by published date (newest first)
            cursor = documents_collection.find(query).sort([
                ("publishedDate", -1),  # Sort by published date (newest first)
                ("indexedDate", -1)     # Fall back to indexed date
            ]).skip(skip).limit(page_size)
            
            news_data = list(cursor)
            
            # Convert MongoDB documents to NewsItem models
            news_items = []
            for doc in news_data:
                # Use pre-generated summary, fall back to content truncation if not available
                summary = doc.get("summary")
                if not summary:
                    content = doc.get("content", "")
                    summary = content[:140] + "..." if len(content) > 140 else content
                
                # Parse published date
                published_date = doc.get("publishedDate") or doc.get("createdDate", "")
                if isinstance(published_date, str):
                    # Try to parse and reformat if it's a string
                    try:
                        from datetime import datetime
                        parsed_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                        published_date = parsed_date.strftime("%Y-%m-%d")
                    except:
                        published_date = published_date[:10] if len(published_date) >= 10 else published_date
                
                # Extract source from RSS feed URL
                rss_url = doc.get("rss_feed_url", "")
                source = "Unknown"
                if rss_url:
                    if "devblogs.microsoft.com" in rss_url:
                        source = "Microsoft DevBlogs"
                    elif "microsoft.com" in rss_url:
                        source = "Microsoft"
                    else:
                        # Extract domain name
                        try:
                            from urllib.parse import urlparse
                            source = urlparse(rss_url).netloc.replace("www.", "")
                        except:
                            source = "RSS Feed"
                
                news_item = NewsItem(
                    id=doc.get("documentId", str(doc.get("_id", ""))),
                    title=doc.get("title", ""),
                    summary=summary,
                    source=source,
                    author=doc.get("rss_author"),
                    published_date=published_date,
                    url=doc.get("sourceUrl", "")
                )
                news_items.append(news_item)
            
            span.set_attribute("total_results", total)
            span.set_attribute("returned_results", len(news_items))
            
            return NewsResponse(
                news=news_items,
                total=total,
                page=page,
                pages=pages,
                page_size=page_size
            )
            
        except Exception as e:
            span.record_exception(e)
            logger.error(f"Error in get_news: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/news/rss")
async def get_news_rss():
    """
    Get latest news items as RSS feed.
    """
    try:
        # Connect to MongoDB
        mongodb_uri = os.getenv("MONGODB_URI")
        database_name = os.getenv("DATABASE_NAME")
        
        if not mongodb_uri or not database_name:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        mongoClient = MongoClient(mongodb_uri)
        db = mongoClient[database_name]
        documents_collection = db["documents"]
        
        # Get latest 50 RSS items
        query = {
            "rss_feed_url": {"$exists": True, "$ne": None},
            "rss_item_id": {"$exists": True, "$ne": None}
        }
        
        cursor = documents_collection.find(query).sort([
            ("publishedDate", -1),
            ("indexedDate", -1)
        ]).limit(50)
        
        news_data = list(cursor)
        
        # Generate RSS XML
        from datetime import datetime
        import xml.etree.ElementTree as ET
        
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        
        # Channel info
        ET.SubElement(channel, "title").text = "C# AI Buddy - Latest .NET AI News"
        ET.SubElement(channel, "description").text = "Latest news and articles about .NET and AI development"
        ET.SubElement(channel, "link").text = "https://csharp-ai-buddy.com"
        ET.SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        # Add items
        for doc in news_data:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = doc.get("title", "")
            ET.SubElement(item, "link").text = doc.get("sourceUrl", "")
            ET.SubElement(item, "guid").text = doc.get("documentId", str(doc.get("_id", "")))
            
            # Summary as description
            content = doc.get("content", "")
            summary = content[:140] + "..." if len(content) > 140 else content
            ET.SubElement(item, "description").text = summary
            
            # Published date
            pub_date = doc.get("publishedDate") or doc.get("createdDate", "")
            if pub_date:
                try:
                    if isinstance(pub_date, str):
                        parsed_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    else:
                        parsed_date = pub_date
                    ET.SubElement(item, "pubDate").text = parsed_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                except:
                    pass
            
            # Author
            if doc.get("rss_author"):
                ET.SubElement(item, "author").text = doc.get("rss_author")
        
        # Convert to string
        ET.indent(rss, space="  ")
        rss_content = ET.tostring(rss, encoding="unicode")
        
        from fastapi import Response
        return Response(
            content=f'<?xml version="1.0" encoding="UTF-8"?>\n{rss_content}',
            media_type="application/rss+xml",
            headers={"Content-Type": "application/rss+xml; charset=utf-8"}
        )
        
    except Exception as e:
        logger.error(f"Error in get_news_rss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
