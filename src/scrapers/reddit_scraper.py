from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import time

from .base import BaseScraper
from config.settings import REDDIT_SUBREDDITS, REDDIT_POST_LIMIT, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

logger = logging.getLogger(__name__)

class RedditScraper(BaseScraper):
    """Scraper for Reddit AI/ML communities"""
    
    def __init__(self):
        super().__init__("reddit", rate_limit=2.0)  # Reddit has strict rate limits
        
        # Try to use PRAW if credentials available, otherwise use web scraping
        self.use_api = bool(REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET)
        
        if self.use_api:
            try:
                import praw
                self.reddit = praw.Reddit(
                    client_id=REDDIT_CLIENT_ID,
                    client_secret=REDDIT_CLIENT_SECRET,
                    user_agent=REDDIT_USER_AGENT
                )
                logger.info("Reddit scraper initialized with PRAW API")
            except ImportError:
                logger.warning("PRAW not installed, falling back to web scraping")
                self.use_api = False
            except Exception as e:
                logger.warning(f"PRAW initialization failed: {e}, falling back to web scraping")
                self.use_api = False
        else:
            logger.info("Reddit scraper initialized with web scraping (no API credentials)")
    
    def _parse_reddit_post_api(self, submission) -> Dict[str, Any]:
        """
        Parse a Reddit post from PRAW API
        
        Args:
            submission: PRAW submission object
            
        Returns:
            Parsed item dictionary
        """
        # Basic info
        post_id = submission.id
        title = self._clean_text(submission.title)
        author = str(submission.author) if submission.author else "[deleted]"
        
        # Description from selftext or URL
        description = ""
        if submission.selftext:
            description = self._clean_text(submission.selftext)
            if len(description) > 300:
                description = description[:300] + "..."
        elif submission.url and not submission.url.startswith('https://www.reddit.com'):
            description = f"Link: {submission.url}"
        
        # Metrics
        score = submission.score
        num_comments = submission.num_comments
        
        # Dates
        published_date = datetime.fromtimestamp(submission.created_utc)
        
        # URL - use permalink for discussions, direct URL for links
        url = f"https://www.reddit.com{submission.permalink}"
        
        # Tags
        tags = [f"r/{submission.subreddit.display_name}"]
        if hasattr(submission, 'link_flair_text') and submission.link_flair_text:
            tags.append(submission.link_flair_text)
        
        # Extra data
        extra_data = {
            'reddit_id': post_id,
            'subreddit': submission.subreddit.display_name,
            'post_type': 'self' if submission.is_self else 'link',
            'external_url': submission.url if not submission.is_self else None,
            'flair': submission.link_flair_text,
            'upvote_ratio': getattr(submission, 'upvote_ratio', None),
            'gilded': getattr(submission, 'gilded', 0),
            'over_18': submission.over_18
        }
        
        return self._create_item_dict(
            source_id=f"reddit_{post_id}",
            url=url,
            title=title,
            description=description,
            author=author,
            published_date=published_date,
            score=score,
            comment_count=num_comments,
            tags=tags,
            extra_data=extra_data
        )
    
    def _parse_reddit_post_web(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a Reddit post from JSON API (web scraping)
        
        Args:
            post_data: Post data from Reddit JSON API
            
        Returns:
            Parsed item dictionary
        """
        data = post_data.get('data', {})
        
        # Basic info
        post_id = data.get('id', '')
        title = self._clean_text(data.get('title', ''))
        author = data.get('author', '[deleted]')
        
        # Description
        description = ""
        selftext = data.get('selftext', '')
        if selftext:
            description = self._clean_text(selftext)
            if len(description) > 300:
                description = description[:300] + "..."
        elif data.get('url') and not data.get('url', '').startswith('https://www.reddit.com'):
            description = f"Link: {data.get('url')}"
        
        # Metrics
        score = data.get('score', 0)
        num_comments = data.get('num_comments', 0)
        
        # Dates
        published_date = None
        if data.get('created_utc'):
            published_date = datetime.fromtimestamp(data['created_utc'])
        
        # URL
        permalink = data.get('permalink', '')
        url = f"https://www.reddit.com{permalink}"
        
        # Tags
        tags = [f"r/{data.get('subreddit', '')}"]
        if data.get('link_flair_text'):
            tags.append(data['link_flair_text'])
        
        # Extra data
        extra_data = {
            'reddit_id': post_id,
            'subreddit': data.get('subreddit', ''),
            'post_type': 'self' if data.get('is_self') else 'link',
            'external_url': data.get('url') if not data.get('is_self') else None,
            'flair': data.get('link_flair_text'),
            'upvote_ratio': data.get('upvote_ratio'),
            'gilded': data.get('gilded', 0),
            'over_18': data.get('over_18', False)
        }
        
        return self._create_item_dict(
            source_id=f"reddit_{post_id}",
            url=url,
            title=title,
            description=description,
            author=author,
            published_date=published_date,
            score=score,
            comment_count=num_comments,
            tags=tags,
            extra_data=extra_data
        )
    
    def _scrape_subreddit_api(self, subreddit_name: str, limit: int) -> List[Dict[str, Any]]:
        """Scrape subreddit using PRAW API"""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            items = []
            
            # Get hot posts
            for submission in subreddit.hot(limit=limit):
                try:
                    item = self._parse_reddit_post_api(submission)
                    if self.validate_item(item):
                        items.append(item)
                except Exception as e:
                    logger.error(f"Error parsing Reddit post: {e}")
                    continue
            
            logger.info(f"Scraped {len(items)} posts from r/{subreddit_name} (API)")
            return items
            
        except Exception as e:
            logger.error(f"Error scraping r/{subreddit_name} with API: {e}")
            return []
    
    def _scrape_subreddit_web(self, subreddit_name: str, limit: int) -> List[Dict[str, Any]]:
        """Scrape subreddit using web JSON API"""
        try:
            url = f"https://www.reddit.com/r/{subreddit_name}/hot.json"
            params = {'limit': limit}
            
            response = self._make_request(url, params=params)
            data = response.json()
            
            items = []
            posts = data.get('data', {}).get('children', [])
            
            for post in posts:
                try:
                    item = self._parse_reddit_post_web(post)
                    if self.validate_item(item):
                        items.append(item)
                except Exception as e:
                    logger.error(f"Error parsing Reddit post: {e}")
                    continue
            
            logger.info(f"Scraped {len(items)} posts from r/{subreddit_name} (web)")
            return items
            
        except Exception as e:
            logger.error(f"Error scraping r/{subreddit_name} with web: {e}")
            return []
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape posts from Reddit AI/ML communities
        
        Returns:
            List of Reddit post items
        """
        logger.info(f"Starting Reddit scrape for subreddits: {REDDIT_SUBREDDITS}")
        
        all_items = []
        
        for subreddit_name in REDDIT_SUBREDDITS:
            try:
                if self.use_api:
                    items = self._scrape_subreddit_api(subreddit_name, REDDIT_POST_LIMIT)
                else:
                    items = self._scrape_subreddit_web(subreddit_name, REDDIT_POST_LIMIT)
                
                all_items.extend(items)
                
                # Rate limiting between subreddits
                time.sleep(self.rate_limit)
                
            except Exception as e:
                logger.error(f"Error scraping r/{subreddit_name}: {e}")
                continue
        
        # Remove duplicates (cross-posts)
        seen_ids = set()
        unique_items = []
        for item in all_items:
            reddit_id = item.get('extra_data', {}).get('reddit_id')
            if reddit_id and reddit_id not in seen_ids:
                seen_ids.add(reddit_id)
                unique_items.append(item)
        
        logger.info(f"Successfully scraped {len(unique_items)} unique items from Reddit")
        return unique_items
    
    def get_subreddit_trending(self, subreddit_name: str, time_period: str = "day") -> List[Dict[str, Any]]:
        """
        Get trending posts from a specific subreddit
        
        Args:
            subreddit_name: Name of subreddit
            time_period: "hour", "day", "week", "month", "year", "all"
            
        Returns:
            List of trending post items
        """
        try:
            if self.use_api:
                subreddit = self.reddit.subreddit(subreddit_name)
                submissions = subreddit.top(time_filter=time_period, limit=REDDIT_POST_LIMIT)
                
                items = []
                for submission in submissions:
                    item = self._parse_reddit_post_api(submission)
                    if self.validate_item(item):
                        items.append(item)
                
                return items
            else:
                url = f"https://www.reddit.com/r/{subreddit_name}/top.json"
                params = {'t': time_period, 'limit': REDDIT_POST_LIMIT}
                
                response = self._make_request(url, params=params)
                data = response.json()
                
                items = []
                for post in data.get('data', {}).get('children', []):
                    item = self._parse_reddit_post_web(post)
                    if self.validate_item(item):
                        items.append(item)
                
                return items
                
        except Exception as e:
            logger.error(f"Error getting trending posts from r/{subreddit_name}: {e}")
            return []