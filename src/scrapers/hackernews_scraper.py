from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import re

from .base import BaseScraper
from config.settings import HN_AI_KEYWORDS, HN_MIN_SCORE

logger = logging.getLogger(__name__)

class HackerNewsScraper(BaseScraper):
    """Scraper for Hacker News AI/ML stories"""
    
    def __init__(self):
        super().__init__("hackernews", rate_limit=1.0)
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.hn_url = "https://news.ycombinator.com"
        
    def _get_story_details(self, story_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific HN story
        
        Args:
            story_id: Hacker News story ID
            
        Returns:
            Story details or None if failed
        """
        try:
            story_url = f"{self.base_url}/item/{story_id}.json"
            response = self._make_request(story_url)
            return response.json()
            
        except Exception as e:
            logger.debug(f"Error fetching HN story {story_id}: {e}")
            return None
    
    def _is_ai_related(self, title: str, url: str = "") -> bool:
        """
        Check if story is AI/ML related
        
        Args:
            title: Story title
            url: Story URL
            
        Returns:
            True if AI/ML related
        """
        text_to_check = f"{title} {url}".lower()
        
        for keyword in HN_AI_KEYWORDS:
            if keyword.lower() in text_to_check:
                return True
        
        return False
    
    def _parse_hn_story(self, story_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a Hacker News story
        
        Args:
            story_data: Story data from HN API
            
        Returns:
            Parsed item dictionary
        """
        # Basic info
        story_id = story_data.get('id', '')
        title = self._clean_text(story_data.get('title', ''))
        author = story_data.get('by', 'Unknown')
        
        # URLs
        external_url = story_data.get('url', '')
        hn_url = f"{self.hn_url}/item?id={story_id}"
        
        # Use external URL if available, otherwise HN discussion
        main_url = external_url if external_url else hn_url
        
        # Description
        description = ""
        if story_data.get('text'):
            description = self._clean_text(story_data['text'])
            if len(description) > 300:
                description = description[:300] + "..."
        elif external_url:
            description = f"External link: {external_url}"
        
        # Metrics
        score = story_data.get('score', 0)
        comment_count = len(story_data.get('kids', []))
        
        # Date
        published_date = None
        if story_data.get('time'):
            published_date = datetime.fromtimestamp(story_data['time'])
        
        # Tags - extract from URL domain
        tags = ['hackernews']
        if external_url:
            # Extract domain for tagging
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', external_url)
            if domain_match:
                domain = domain_match.group(1)
                tags.append(domain)
                
                # Special tagging for known AI/ML sites
                if 'arxiv.org' in domain:
                    tags.append('research')
                elif 'github.com' in domain:
                    tags.append('code')
                elif any(word in domain for word in ['ai', 'ml', 'deep', 'neural']):
                    tags.append('ai-ml')
        
        # Story type
        story_type = story_data.get('type', 'story')
        if story_type in ['job', 'poll']:
            tags.append(story_type)
        
        # Extra data
        extra_data = {
            'hn_id': story_id,
            'hn_discussion_url': hn_url,
            'external_url': external_url,
            'story_type': story_type,
            'descendants': story_data.get('descendants', 0),  # Total comment count including replies
            'domain': domain_match.group(1) if external_url and domain_match else None
        }
        
        return self._create_item_dict(
            source_id=f"hn_{story_id}",
            url=main_url,
            title=title,
            description=description,
            author=author,
            published_date=published_date,
            score=score,
            comment_count=comment_count,
            tags=tags,
            extra_data=extra_data
        )
    
    def _get_story_list(self, endpoint: str, limit: int = 100) -> List[int]:
        """
        Get list of story IDs from HN endpoint
        
        Args:
            endpoint: HN API endpoint (e.g., 'topstories', 'newstories')
            limit: Maximum number of stories to fetch
            
        Returns:
            List of story IDs
        """
        try:
            url = f"{self.base_url}/{endpoint}.json"
            response = self._make_request(url)
            story_ids = response.json()
            
            return story_ids[:limit] if story_ids else []
            
        except Exception as e:
            logger.error(f"Error fetching {endpoint} from HN: {e}")
            return []
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape AI/ML stories from Hacker News
        
        Returns:
            List of story items
        """
        logger.info("Starting Hacker News scrape for AI/ML stories")
        
        items = []
        
        try:
            # Get top stories first, then new stories
            endpoints = [
                ('topstories', 50),
                ('newstories', 30)
            ]
            
            processed_ids = set()
            
            for endpoint, limit in endpoints:
                logger.info(f"Fetching {endpoint} from Hacker News...")
                story_ids = self._get_story_list(endpoint, limit)
                
                ai_stories_found = 0
                
                for story_id in story_ids:
                    # Skip if already processed (story might appear in both top and new)
                    if story_id in processed_ids:
                        continue
                    
                    processed_ids.add(story_id)
                    
                    # Get story details
                    story_data = self._get_story_details(story_id)
                    if not story_data:
                        continue
                    
                    # Check if story meets criteria
                    title = story_data.get('title', '')
                    url = story_data.get('url', '')
                    score = story_data.get('score', 0)
                    
                    # Filter: AI/ML related + minimum score
                    if not self._is_ai_related(title, url):
                        continue
                        
                    if score < HN_MIN_SCORE:
                        continue
                    
                    # Skip jobs and polls unless explicitly AI/ML related
                    story_type = story_data.get('type', 'story')
                    if story_type in ['job', 'poll']:
                        # Only include if title strongly indicates AI/ML
                        if not any(keyword in title.lower() for keyword in ['ai', 'ml', 'machine learning', 'deep learning', 'neural']):
                            continue
                    
                    try:
                        item = self._parse_hn_story(story_data)
                        
                        if self.validate_item(item):
                            items.append(item)
                            ai_stories_found += 1
                            logger.debug(f"Found AI/ML story: {title[:50]}...")
                    
                    except Exception as e:
                        logger.error(f"Error parsing HN story {story_id}: {e}")
                        continue
                
                logger.info(f"Found {ai_stories_found} AI/ML stories in {endpoint}")
            
            logger.info(f"Successfully scraped {len(items)} items from Hacker News")
            
        except Exception as e:
            logger.error(f"Error scraping Hacker News: {e}")
            raise
        
        return items
    
    def get_story_comments(self, story_id: int, max_comments: int = 10) -> List[Dict[str, Any]]:
        """
        Get top comments for a story (useful for future enhancement)
        
        Args:
            story_id: HN story ID
            max_comments: Maximum comments to fetch
            
        Returns:
            List of comment data
        """
        try:
            story_data = self._get_story_details(story_id)
            if not story_data or not story_data.get('kids'):
                return []
            
            comments = []
            comment_ids = story_data['kids'][:max_comments]
            
            for comment_id in comment_ids:
                comment_data = self._get_story_details(comment_id)
                if comment_data and comment_data.get('text'):
                    comments.append({
                        'id': comment_id,
                        'author': comment_data.get('by', 'Unknown'),
                        'text': self._clean_text(comment_data['text']),
                        'time': datetime.fromtimestamp(comment_data['time']) if comment_data.get('time') else None
                    })
            
            return comments
            
        except Exception as e:
            logger.error(f"Error fetching comments for HN story {story_id}: {e}")
            return []
    
    def search_stories(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search HN stories (using Algolia HN Search API)
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of story items
        """
        try:
            # Use Algolia HN Search API
            search_url = "https://hn.algolia.com/api/v1/search"
            params = {
                'query': query,
                'tags': 'story',
                'hitsPerPage': max_results,
                'numericFilters': f'points>{HN_MIN_SCORE}'
            }
            
            response = self._make_request(search_url, params=params)
            data = response.json()
            
            items = []
            for hit in data.get('hits', []):
                # Convert Algolia format to HN API format
                story_data = {
                    'id': hit.get('objectID'),
                    'title': hit.get('title'),
                    'url': hit.get('url'),
                    'by': hit.get('author'),
                    'score': hit.get('points', 0),
                    'time': hit.get('created_at_i'),
                    'kids': [],  # Comments not included in search
                    'descendants': hit.get('num_comments', 0)
                }
                
                try:
                    item = self._parse_hn_story(story_data)
                    if self.validate_item(item):
                        items.append(item)
                except Exception as e:
                    logger.error(f"Error parsing search result: {e}")
                    continue
            
            logger.info(f"Found {len(items)} stories for query '{query}'")
            return items
            
        except Exception as e:
            logger.error(f"Error searching HN stories: {e}")
            return []