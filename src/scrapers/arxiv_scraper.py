from typing import List, Dict, Any
from datetime import datetime, timedelta
import feedparser
import logging
import re

from .base import BaseScraper
from config.settings import ARXIV_CATEGORIES, ARXIV_MAX_RESULTS

logger = logging.getLogger(__name__)

class ArxivScraper(BaseScraper):
    """Scraper for arXiv research papers"""
    
    def __init__(self):
        super().__init__("arxiv", rate_limit=1.0)  # Be respectful to arXiv
        self.base_url = "http://export.arxiv.org/api/query"
        
    def _build_search_query(self, categories: List[str], days_back: int = 1) -> str:
        """
        Build arXiv API search query
        
        Args:
            categories: List of arXiv categories to search
            days_back: Number of days back to search
            
        Returns:
            Search query string
        """
        # Create category search (cat:cs.AI OR cat:cs.LG OR ...)
        cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
        
        # Add date filter for recent papers
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # arXiv date format: YYYYMMDDHHMMSS
        date_filter = f" AND submittedDate:[{start_date.strftime('%Y%m%d0000')} TO {end_date.strftime('%Y%m%d2359')}]"
        
        query = f"({cat_query}){date_filter}"
        logger.info(f"arXiv search query: {query}")
        return query
    
    def _parse_arxiv_entry(self, entry) -> Dict[str, Any]:
        """
        Parse a single arXiv entry from feedparser
        
        Args:
            entry: feedparser entry object
            
        Returns:
            Parsed item dictionary
        """
        # Extract arXiv ID from link
        arxiv_id = entry.id.split("/")[-1]  # e.g., "http://arxiv.org/abs/2301.12345v1" -> "2301.12345v1"
        arxiv_id = re.sub(r'v\d+$', '', arxiv_id)  # Remove version number
        
        # Clean title and abstract
        title = self._clean_text(entry.title)
        abstract = self._clean_text(entry.summary) if hasattr(entry, 'summary') else ""
        
        # Extract authors
        authors = []
        if hasattr(entry, 'authors'):
            authors = [author.name for author in entry.authors]
        author_str = ", ".join(authors) if authors else "Unknown"
        
        # Extract categories/tags
        tags = []
        if hasattr(entry, 'arxiv_primary_category'):
            tags.append(entry.arxiv_primary_category.get('term', ''))
        if hasattr(entry, 'tags'):
            tags.extend([tag.term for tag in entry.tags if tag.term not in tags])
        
        # Parse published date
        published_date = None
        if hasattr(entry, 'published_parsed'):
            published_date = datetime(*entry.published_parsed[:6])
        
        # Create URL
        url = f"https://arxiv.org/abs/{arxiv_id}"
        
        # Extra data
        extra_data = {
            "arxiv_id": arxiv_id,
            "categories": tags,
            "authors_list": authors,
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        }
        
        return self._create_item_dict(
            source_id=f"arxiv_{arxiv_id}",
            url=url,
            title=title,
            description=abstract[:500] + "..." if len(abstract) > 500 else abstract,  # Truncate long abstracts
            author=author_str,
            published_date=published_date,
            score=0,  # arXiv doesn't have scores
            comment_count=0,  # arXiv doesn't have comments
            tags=tags,
            extra_data=extra_data
        )
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape recent papers from arXiv
        
        Returns:
            List of paper items
        """
        logger.info(f"Starting arXiv scrape for categories: {ARXIV_CATEGORIES}")
        
        items = []
        
        try:
            # Build search query
            query = self._build_search_query(ARXIV_CATEGORIES, days_back=1)
            
            # Prepare API request parameters
            params = {
                'search_query': query,
                'start': 0,
                'max_results': ARXIV_MAX_RESULTS,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }
            
            # Make request to arXiv API
            logger.info("Fetching from arXiv API...")
            response = self._make_request(self.base_url, params=params)
            
            # Parse XML response with feedparser
            feed = feedparser.parse(response.text)
            
            logger.info(f"Found {len(feed.entries)} entries from arXiv")
            
            # Process each entry
            for entry in feed.entries:
                try:
                    item = self._parse_arxiv_entry(entry)
                    
                    if self.validate_item(item):
                        items.append(item)
                        logger.debug(f"Parsed arXiv paper: {item['title'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error parsing arXiv entry: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(items)} items from arXiv")
            
        except Exception as e:
            logger.error(f"Error scraping arXiv: {e}")
            raise
        
        return items
    
    def get_paper_details(self, arxiv_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific arXiv paper
        
        Args:
            arxiv_id: arXiv paper ID (e.g., "2301.12345")
            
        Returns:
            Detailed paper information
        """
        try:
            params = {
                'search_query': f'id:{arxiv_id}',
                'start': 0,
                'max_results': 1
            }
            
            response = self._make_request(self.base_url, params=params)
            feed = feedparser.parse(response.text)
            
            if feed.entries:
                return self._parse_arxiv_entry(feed.entries[0])
            else:
                logger.warning(f"No paper found for arXiv ID: {arxiv_id}")
                return {}
                
        except Exception as e:
            logger.error(f"Error fetching arXiv paper {arxiv_id}: {e}")
            return {}