from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import os
import logging
from pymongo import MongoClient
from opentelemetry import trace

from models import SamplesResponse, Sample

router = APIRouter()
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

@router.get("/api/samples", response_model=SamplesResponse)
async def get_samples(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of samples per page"),
    search: Optional[str] = Query(None, description="Search query"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags to filter by")
):
    """
    Get samples with pagination, search, and filtering.
    """
    with tracer.start_as_current_span("get_samples") as span:
        try:
            span.set_attribute("page", page)
            span.set_attribute("page_size", page_size)
            if search:
                span.set_attribute("search_query", search)
            if tags:
                span.set_attribute("filter_tags", tags)

            # Connect to MongoDB
            mongodb_uri = os.getenv("MONGODB_URI")
            database_name = os.getenv("DATABASE_NAME")
            
            if not mongodb_uri or not database_name:
                raise HTTPException(status_code=500, detail="Database not configured")
            
            mongoClient = MongoClient(mongodb_uri)
            db = mongoClient[database_name]
            samples_collection = db["samples"]
            
            # Build query
            query = {}
            
            # Add tag filtering
            if tags:
                tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                if tag_list:
                    query["tags"] = {"$in": tag_list}
            
            # Add search functionality (simple text search for now)
            if search:
                search_regex = {"$regex": search, "$options": "i"}
                query["$or"] = [
                    {"title": search_regex},
                    {"description": search_regex},
                    {"author": search_regex},
                    {"tags": search_regex}
                ]
            
            # Count total documents
            total = samples_collection.count_documents(query)
            
            # Calculate pagination
            skip = (page - 1) * page_size
            pages = (total + page_size - 1) // page_size
            
            # Get samples
            cursor = samples_collection.find(query).skip(skip).limit(page_size)
            samples_data = list(cursor)
            
            # Convert MongoDB documents to Sample models
            samples = []
            for doc in samples_data:
                sample = Sample(
                    id=doc.get("id", str(doc.get("_id", ""))),
                    title=doc.get("title", ""),
                    description=doc.get("description", ""),
                    preview=doc.get("preview"),
                    authorUrl=doc.get("authorUrl", ""),
                    author=doc.get("author", ""),
                    source=doc.get("source", ""),
                    tags=doc.get("tags", [])
                )
                samples.append(sample)
            
            span.set_attribute("total_results", total)
            span.set_attribute("returned_results", len(samples))
            
            return SamplesResponse(
                samples=samples,
                total=total,
                page=page,
                pages=pages,
                page_size=page_size
            )
            
        except Exception as e:
            span.record_exception(e)
            logger.error(f"Error in get_samples: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/samples/tags")
async def get_available_tags():
    """
    Get all available tags from samples.
    """
    with tracer.start_as_current_span("get_available_tags"):
        try:
            # Connect to MongoDB
            mongodb_uri = os.getenv("MONGODB_URI")
            database_name = os.getenv("DATABASE_NAME")
            
            if not mongodb_uri or not database_name:
                raise HTTPException(status_code=500, detail="Database not configured")
            
            mongoClient = MongoClient(mongodb_uri)
            db = mongoClient[database_name]
            samples_collection = db["samples"]
            
            # Get all unique tags
            tags = samples_collection.distinct("tags")
            
            return {"tags": sorted(tags)}
            
        except Exception as e:
            logger.error(f"Error in get_available_tags: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/samples/{sample_id}")
async def get_sample(sample_id: str):
    """
    Get a specific sample by ID.
    """
    with tracer.start_as_current_span("get_sample") as span:
        try:
            span.set_attribute("sample_id", sample_id)
            
            # Connect to MongoDB
            mongodb_uri = os.getenv("MONGODB_URI")
            database_name = os.getenv("DATABASE_NAME")
            
            if not mongodb_uri or not database_name:
                raise HTTPException(status_code=500, detail="Database not configured")
            
            mongoClient = MongoClient(mongodb_uri)
            db = mongoClient[database_name]
            samples_collection = db["samples"]
            
            # Find sample by ID
            sample_doc = samples_collection.find_one({"id": sample_id})
            
            if not sample_doc:
                raise HTTPException(status_code=404, detail="Sample not found")
            
            sample = Sample(
                id=sample_doc.get("id", str(sample_doc.get("_id", ""))),
                title=sample_doc.get("title", ""),
                description=sample_doc.get("description", ""),
                preview=sample_doc.get("preview"),
                authorUrl=sample_doc.get("authorUrl", ""),
                author=sample_doc.get("author", ""),
                source=sample_doc.get("source", ""),
                tags=sample_doc.get("tags", [])
            )
            
            return sample
            
        except HTTPException:
            raise
        except Exception as e:
            span.record_exception(e)
            logger.error(f"Error in get_sample: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
