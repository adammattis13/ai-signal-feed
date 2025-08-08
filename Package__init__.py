# src/__init__.py
"""AI Signal Feed - Core package"""

# src/scrapers/__init__.py
"""Web scrapers for different sources"""

from .arxiv_scraper import ArxivScraper

__all__ = ['ArxivScraper']

# src/classifier/__init__.py  
"""Signal classification system"""

from .signal_classifier import SignalClassifier

__all__ = ['SignalClassifier']

# src/database/__init__.py
"""Database models and operations"""

from .models import FeedItem, ScrapingLog
from .database import DatabaseManager, init_db, db_manager

__all__ = ['FeedItem', 'ScrapingLog', 'DatabaseManager', 'init_db', 'db_manager']

# src/scheduler/__init__.py
"""Scheduling system for automated scraping"""

__all__ = []

# src/utils/__init__.py
"""Utility functions"""

__all__ = []

# tests/__init__.py
"""Test suite"""