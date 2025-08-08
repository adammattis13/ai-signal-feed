from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import os

from .base import BaseScraper
from config.settings import GITHUB_KEYWORDS, GITHUB_MIN_STARS, GITHUB_TOKEN

logger = logging.getLogger(__name__)

class GitHubScraper(BaseScraper):
    """Scraper for trending GitHub repositories"""
    
    def __init__(self):
        super().__init__("github", rate_limit=1.0)
        self.base_url = "https://api.github.com"
        
        # Setup authentication if token available
        if GITHUB_TOKEN:
            self.session.headers.update({
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            })
            logger.info("GitHub scraper initialized with authentication")
        else:
            logger.warning("No GitHub token provided - rate limits will be lower")
    
    def _build_search_query(self, keywords: List[str], days_back: int = 7) -> str:
        """
        Build GitHub search query for AI/ML repositories
        
        Args:
            keywords: List of keywords to search for
            days_back: Number of days back to search for recent activity
            
        Returns:
            GitHub API search query
        """
        # Create keyword search (machine learning OR AI OR deep learning...)
        keyword_query = " OR ".join([f'"{keyword}"' for keyword in keywords[:5]])  # Limit to avoid URL length issues
        
        # Add date filter for recent activity  
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        # Build full query
        query = f"({keyword_query}) language:python pushed:>{cutoff_date} stars:>{GITHUB_MIN_STARS}"
        
        logger.info(f"GitHub search query: {query}")
        return query
    
    def _parse_repo(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a GitHub repository from API response
        
        Args:
            repo_data: Repository data from GitHub API
            
        Returns:
            Parsed item dictionary
        """
        # Extract basic info
        repo_id = str(repo_data.get('id', ''))
        name = repo_data.get('name', '')
        full_name = repo_data.get('full_name', '')
        description = repo_data.get('description', '') or "No description provided"
        
        # Clean description
        description = self._clean_text(description)
        
        # URLs
        url = repo_data.get('html_url', '')
        
        # Author/owner
        owner = repo_data.get('owner', {})
        author = owner.get('login', 'Unknown')
        
        # Metrics
        stars = repo_data.get('stargazers_count', 0)
        forks = repo_data.get('forks_count', 0)
        issues = repo_data.get('open_issues_count', 0)
        
        # Dates
        created_date = None
        updated_date = None
        try:
            if repo_data.get('created_at'):
                created_date = datetime.fromisoformat(repo_data['created_at'].replace('Z', '+00:00'))
            if repo_data.get('updated_at'):
                updated_date = datetime.fromisoformat(repo_data['updated_at'].replace('Z', '+00:00'))
        except ValueError as e:
            logger.debug(f"Error parsing dates for repo {full_name}: {e}")
        
        # Language and topics as tags
        tags = []
        if repo_data.get('language'):
            tags.append(repo_data['language'])
        if repo_data.get('topics'):
            tags.extend(repo_data['topics'][:5])  # Limit topics
        
        # Title with context
        title = f"{full_name}"
        if description:
            title = f"{full_name} - {description[:100]}{'...' if len(description) > 100 else ''}"
        
        # Extra data
        extra_data = {
            'github_id': repo_id,
            'full_name': full_name,
            'language': repo_data.get('language'),
            'topics': repo_data.get('topics', []),
            'forks': forks,
            'issues': issues,
            'license': repo_data.get('license', {}).get('name') if repo_data.get('license') else None,
            'is_fork': repo_data.get('fork', False),
            'default_branch': repo_data.get('default_branch', 'main')
        }
        
        return self._create_item_dict(
            source_id=f"github_{repo_id}",
            url=url,
            title=title,
            description=description,
            author=author,
            published_date=created_date,
            score=stars,
            comment_count=issues,  # Use issues as "comments"
            tags=tags,
            extra_data=extra_data
        )
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape trending GitHub repositories
        
        Returns:
            List of repository items
        """
        logger.info(f"Starting GitHub scrape for keywords: {GITHUB_KEYWORDS}")
        
        items = []
        
        try:
            # Build search query
            query = self._build_search_query(GITHUB_KEYWORDS, days_back=7)
            
            # Search repositories
            search_url = f"{self.base_url}/search/repositories"
            params = {
                'q': query,
                'sort': 'updated',  # Sort by recent activity
                'order': 'desc',
                'per_page': 50  # Max per page
            }
            
            logger.info("Searching GitHub repositories...")
            response = self._make_request(search_url, params=params)
            data = response.json()
            
            total_count = data.get('total_count', 0)
            repositories = data.get('items', [])
            
            logger.info(f"Found {total_count} total repositories, processing {len(repositories)}")
            
            # Process each repository
            for repo_data in repositories:
                try:
                    item = self._parse_repo(repo_data)
                    
                    if self.validate_item(item):
                        items.append(item)
                        logger.debug(f"Parsed GitHub repo: {item['title'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error parsing GitHub repo: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(items)} items from GitHub")
            
        except Exception as e:
            logger.error(f"Error scraping GitHub: {e}")
            raise
        
        return items
    
    def get_repo_details(self, full_name: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific repository
        
        Args:
            full_name: Repository full name (e.g., "user/repo")
            
        Returns:
            Detailed repository information
        """
        try:
            repo_url = f"{self.base_url}/repos/{full_name}"
            response = self._make_request(repo_url)
            repo_data = response.json()
            
            return self._parse_repo(repo_data)
                
        except Exception as e:
            logger.error(f"Error fetching GitHub repo {full_name}: {e}")
            return {}
    
    def get_trending_by_topic(self, topic: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get trending repositories for a specific topic
        
        Args:
            topic: GitHub topic (e.g., "machine-learning", "artificial-intelligence")
            days_back: Number of days to look back
            
        Returns:
            List of repository items
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            query = f"topic:{topic} pushed:>{cutoff_date} stars:>{GITHUB_MIN_STARS}"
            
            search_url = f"{self.base_url}/search/repositories"
            params = {
                'q': query,
                'sort': 'stars',
                'order': 'desc',
                'per_page': 20
            }
            
            response = self._make_request(search_url, params=params)
            data = response.json()
            
            items = []
            for repo_data in data.get('items', []):
                item = self._parse_repo(repo_data)
                if self.validate_item(item):
                    items.append(item)
            
            logger.info(f"Found {len(items)} trending repos for topic '{topic}'")
            return items
            
        except Exception as e:
            logger.error(f"Error fetching trending repos for topic {topic}: {e}")
            return []