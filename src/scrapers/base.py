from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, source_name: str, rate_limit: float = 1.0):
        """
        Initialize scraper
        
        Args:
            source_name: Name of the source (e.g., "arxiv", "github")
            rate_limit: Minimum seconds between requests
        """
        self.source_name = source_name
        self.rate_limit = rate_limit
        self.last_request_time = 0
        
        # Setup requests session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # User agent
        self.session.headers.update({
            'User-Agent': 'AI-Signal-Feed/1.0 (Research Feed Aggregator)'
        })
        
        logger.info(f"Initialized {source_name} scraper")
    
    def _rate_limit_wait(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, timeout: int = 15, **kwargs) -> requests.Response:
        """Make HTTP request with rate limiting and error handling"""
        self._rate_limit_wait()
        
        try:
            response = self.session.get(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise
    
    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape items from source
        
        Returns:
            List of dictionaries with item data
        """
        pass
    
    def _create_item_dict(self, 
                         source_id: str,
                         url: str,
                         title: str,
                         description: Optional[str] = None,
                         author: Optional[str] = None,
                         published_date: Optional[datetime] = None,
                         score: int = 0,
                         comment_count: int = 0,
                         tags: Optional[List[str]] = None,
                         extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create standardized item dictionary
        
        Args:
            source_id: Unique identifier from source
            url: Link to item
            title: Item title
            description: Item description/summary
            author: Author/creator
            published_date: When item was published
            score: Engagement score (upvotes, stars, etc.)
            comment_count: Number of comments
            tags: List of tags/keywords
            extra_data: Additional source-specific data
            
        Returns:
            Standardized item dictionary
        """
        return {
            "source": self.source_name,
            "source_id": source_id,
            "url": url,
            "title": title,
            "description": description,
            "author": author,
            "published_date": published_date,
            "score": score,
            "comment_count": comment_count,
            "tags": tags or [],
            "extra_data": extra_data or {}
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        text = " ".join(text.split())
        
        # Remove common HTML entities
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#x27;", "'")
        
        return text.strip()
    
    def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validate that item has required fields
        
        Args:
            item: Item dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["source_id", "url", "title"]
        
        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Item missing required field '{field}': {item}")
                return False
        
        return True