from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class Message(BaseModel):
    role: str
    content: str

class AIFilters(BaseModel):
    dotnetVersion: Optional[str] = None
    aiLibrary: Optional[str] = None
    aiProvider: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []
    filters: Optional[AIFilters] = None
    magic_key: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

# Sample-related models
class Sample(BaseModel):
    id: str
    title: str
    description: str
    preview: Optional[str] = None
    authorUrl: str
    author: str
    source: str
    tags: List[str]

class SamplesResponse(BaseModel):
    samples: List[Sample]
    total: int
    page: int
    pages: int
    page_size: int

# News-related models
class NewsItem(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    author: Optional[str] = None
    published_date: datetime
    url: str

class NewsResponse(BaseModel):
    news: List[NewsItem]
    total: int
    page: int
    pages: int
    page_size: int

class TelemetryEvent(BaseModel):
    event_type: str  # 'filter_used', 'sample_viewed', 'external_click', 'search_no_results'
    data: Dict[str, Any]
    timestamp: Optional[str] = None
    user_consent: bool = True
