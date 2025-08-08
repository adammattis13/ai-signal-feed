#!/usr/bin/env python3
"""
Test individual scrapers one at a time
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.scrapers.arxiv_scraper import ArxivScraper
from src.scrapers.github_scraper import GitHubScraper
from src.scrapers.reddit_scraper import RedditScraper
from src.scrapers.hackernews_scraper import HackerNewsScraper
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_arxiv():
    """Test arXiv scraper"""
    print("🧪 Testing arXiv scraper...")
    scraper = ArxivScraper()
    items = scraper.scrape()
    print(f"✅ Found {len(items)} arXiv papers")
    if items:
        example = items[0]
        print(f"📄 Example: {example['title'][:60]}...")
    return items

def test_github():
    """Test GitHub scraper"""
    print("\n🧪 Testing GitHub scraper...")
    scraper = GitHubScraper()
    items = scraper.scrape()
    print(f"✅ Found {len(items)} GitHub repos")
    if items:
        example = items[0]
        print(f"💾 Example: {example['title'][:60]}...")
        print(f"   ⭐ Stars: {example.get('score', 0)}")
    return items

def test_reddit():
    """Test Reddit scraper"""
    print("\n🧪 Testing Reddit scraper...")
    scraper = RedditScraper()
    items = scraper.scrape()
    print(f"✅ Found {len(items)} Reddit posts")
    if items:
        example = items[0]
        print(f"💬 Example: {example['title'][:60]}...")
        print(f"   ⬆️ Score: {example.get('score', 0)}")
    return items

def test_hackernews():
    """Test Hacker News scraper"""
    print("\n🧪 Testing Hacker News scraper...")
    scraper = HackerNewsScraper()
    items = scraper.scrape()
    print(f"✅ Found {len(items)} HN stories")
    if items:
        example = items[0]
        print(f"📰 Example: {example['title'][:60]}...")
        print(f"   📊 Score: {example.get('score', 0)}")
    return items

def main():
    """Test individual scrapers"""
    print("🚀 Testing individual scrapers...\n")
    
    # Choose which to test
    print("Which scraper would you like to test?")
    print("1. arXiv (research papers)")
    print("2. GitHub (repositories)")  
    print("3. Reddit (discussions)")
    print("4. Hacker News (stories)")
    print("5. All scrapers")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        test_arxiv()
    elif choice == "2":
        test_github()
    elif choice == "3":
        test_reddit()
    elif choice == "4":
        test_hackernews()
    elif choice == "5":
        test_arxiv()
        test_github()
        test_reddit()
        test_hackernews()
    else:
        print("Invalid choice. Testing arXiv by default...")
        test_arxiv()
    
    print("\n🎉 Testing complete!")

if __name__ == "__main__":
    main()