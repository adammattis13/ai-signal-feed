from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging

from .models import Base, FeedItem, ScrapingLog
from config.settings import DATABASE_URL

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database engine
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DatabaseManager:
    def __init__(self):
        self.engine = engine
        
    def get_session(self) -> Session:
        """Get a database session"""
        return SessionLocal()
    
    def add_feed_item(self, item_data: Dict[str, Any]) -> Optional[FeedItem]:
        """Add a new feed item to database"""
        with self.get_session() as db:
            try:
                # Check for duplicates
                existing = db.query(FeedItem).filter(
                    FeedItem.source == item_data.get("source"),
                    FeedItem.source_id == item_data.get("source_id")
                ).first()
                
                if existing:
                    logger.debug(f"Duplicate item found: {item_data.get('title', '')[:50]}")
                    return None
                
                # Create new item
                feed_item = FeedItem(
                    source=item_data.get("source"),
                    source_id=item_data.get("source_id"), 
                    url=item_data.get("url"),
                    title=item_data.get("title"),
                    description=item_data.get("description"),
                    author=item_data.get("author"),
                    published_date=item_data.get("published_date"),
                    score=item_data.get("score", 0),
                    comment_count=item_data.get("comment_count", 0),
                    signal_type=item_data.get("signal_type", "green"),
                    confidence_score=item_data.get("confidence_score", 0.0),
                    tags=json.dumps(item_data.get("tags", [])) if item_data.get("tags") else None,
                    extra_data=json.dumps(item_data.get("extra_data", {})) if item_data.get("extra_data") else None
                )
                
                db.add(feed_item)
                db.commit()
                db.refresh(feed_item)
                
                logger.info(f"Added item: {feed_item.title[:50]}...")
                return feed_item
                
            except IntegrityError as e:
                db.rollback()
                logger.error(f"Database integrity error: {e}")
                return None
            except Exception as e:
                db.rollback()
                logger.error(f"Error adding feed item: {e}")
                return None
    
    def get_feed_items(self, 
                      limit: int = 50, 
                      offset: int = 0,
                      source: Optional[str] = None,
                      signal_type: Optional[str] = None,
                      hours_back: Optional[int] = None) -> List[FeedItem]:
        """Get feed items with filters"""
        with self.get_session() as db:
            query = db.query(FeedItem)
            
            # Apply filters
            if source:
                query = query.filter(FeedItem.source == source)
            if signal_type:
                query = query.filter(FeedItem.signal_type == signal_type)
            if hours_back:
                cutoff = datetime.utcnow() - timedelta(hours=hours_back)
                query = query.filter(FeedItem.scraped_date >= cutoff)
            
            # Order and paginate
            items = query.order_by(FeedItem.scraped_date.desc())\
                        .offset(offset)\
                        .limit(limit)\
                        .all()
            
            return items
    
    def get_item_count(self, 
                      source: Optional[str] = None,
                      signal_type: Optional[str] = None) -> int:
        """Get count of items with filters"""
        with self.get_session() as db:
            query = db.query(FeedItem)
            
            if source:
                query = query.filter(FeedItem.source == source)
            if signal_type:
                query = query.filter(FeedItem.signal_type == signal_type)
                
            return query.count()
    
    def log_scraping_start(self, source: str) -> ScrapingLog:
        """Log the start of a scraping session"""
        with self.get_session() as db:
            log_entry = ScrapingLog(
                source=source,
                status="running"
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return log_entry
    
    def log_scraping_end(self, log_id: int, items_scraped: int, error: Optional[str] = None):
        """Log the end of a scraping session"""
        with self.get_session() as db:
            log_entry = db.query(ScrapingLog).filter(ScrapingLog.id == log_id).first()
            if log_entry:
                log_entry.completed_at = datetime.utcnow()
                log_entry.status = "failed" if error else "completed"
                log_entry.items_scraped = items_scraped
                log_entry.error_message = error
                db.commit()
    
    def cleanup_old_items(self, days_to_keep: int = 30):
        """Remove old feed items"""
        with self.get_session() as db:
            cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
            deleted = db.query(FeedItem).filter(FeedItem.scraped_date < cutoff).delete()
            db.commit()
            logger.info(f"Cleaned up {deleted} old items")
            return deleted

# Global database manager instance
db_manager = DatabaseManager()