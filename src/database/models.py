from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class FeedItem(Base):
    __tablename__ = "feed_items"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Source info
    source = Column(String(50), nullable=False, index=True)  # "arxiv", "github", "reddit", "hackernews"
    source_id = Column(String(200), nullable=False, index=True)  # unique ID from source
    url = Column(Text, nullable=False)
    
    # Content
    title = Column(Text, nullable=False)
    description = Column(Text)  # summary, abstract, or snippet
    author = Column(String(200))
    
    # Metadata
    published_date = Column(DateTime, index=True)
    scraped_date = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Engagement metrics
    score = Column(Integer, default=0)  # upvotes, stars, citations, etc.
    comment_count = Column(Integer, default=0)
    
    # Signal classification
    signal_type = Column(String(10), nullable=False, index=True)  # "red", "yellow", "green"
    confidence_score = Column(Float, default=0.0)  # classifier confidence 0-1
    
    # Additional data
    tags = Column(Text)  # JSON string of tags/keywords
    extra_data = Column(Text)  # JSON string for source-specific fields
    
    # Processing flags
    is_processed = Column(Boolean, default=True)
    is_duplicate = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<FeedItem(id={self.id}, source={self.source}, signal={self.signal_type}, title='{self.title[:50]}...')>"

class ScrapingLog(Base):
    __tablename__ = "scraping_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(20), nullable=False)  # "running", "completed", "failed"
    items_scraped = Column(Integer, default=0)
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<ScrapingLog(source={self.source}, status={self.status}, items={self.items_scraped})>"