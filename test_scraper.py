#!/usr/bin/env python3
"""
Test script for AI Signal Feed scrapers
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.scrapers.arxiv_scraper import ArxivScraper
from src.classifier.signal_classifier import SignalClassifier
from src.database.database import DatabaseManager, init_db
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_arxiv_scraper():
    """Test the arXiv scraper"""
    logger.info("🧪 Testing arXiv scraper...")
    
    try:
        scraper = ArxivScraper()
        items = scraper.scrape()
        
        logger.info(f"✅ arXiv scraper found {len(items)} items")
        
        # Show first few items
        for i, item in enumerate(items[:3]):
            logger.info(f"📄 Item {i+1}: {item['title'][:60]}...")
            logger.info(f"   📅 Published: {item.get('published_date', 'Unknown')}")
            logger.info(f"   👤 Author: {item.get('author', 'Unknown')}")
            logger.info(f"   🏷️  Tags: {item.get('tags', [])}")
            logger.info(f"   🔗 URL: {item['url']}")
            print()
            
        return items
        
    except Exception as e:
        logger.error(f"❌ arXiv scraper test failed: {e}")
        return []

def test_classifier(items):
    """Test the signal classifier"""
    logger.info("🧪 Testing signal classifier...")
    
    if not items:
        logger.warning("⚠️  No items to classify")
        return
        
    try:
        classifier = SignalClassifier()
        
        classified_items = []
        for item in items:
            signal_type, confidence = classifier.classify(item)
            item['signal_type'] = signal_type
            item['confidence_score'] = confidence
            classified_items.append(item)
            
        # Show classification results
        summary = classifier.get_classification_summary(items)
        logger.info(f"✅ Classification complete!")
        logger.info(f"   🔴 Red (High Impact): {summary['red']} ({summary['red_pct']}%)")
        logger.info(f"   🟡 Yellow (Curious): {summary['yellow']} ({summary['yellow_pct']}%)")
        logger.info(f"   🟢 Green (Insight): {summary['green']} ({summary['green_pct']}%)")
        print()
        
        # Show examples by category
        for signal_type in ['red', 'yellow', 'green']:
            examples = [item for item in classified_items if item['signal_type'] == signal_type]
            if examples:
                emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢"}[signal_type]
                logger.info(f"{emoji} {signal_type.upper()} example:")
                example = examples[0]
                logger.info(f"   📄 {example['title']}")
                logger.info(f"   🎯 Confidence: {example['confidence_score']:.2f}")
                print()
                
        return classified_items
        
    except Exception as e:
        logger.error(f"❌ Classifier test failed: {e}")
        return []

def test_database(items):
    """Test database operations"""
    logger.info("🧪 Testing database...")
    
    if not items:
        logger.warning("⚠️  No items to save to database")
        return
        
    try:
        # Initialize database
        init_db()
        db_manager = DatabaseManager()
        
        # Save items to database
        saved_count = 0
        for item in items:
            result = db_manager.add_feed_item(item)
            if result:
                saved_count += 1
                
        logger.info(f"✅ Saved {saved_count}/{len(items)} items to database")
        
        # Test retrieval
        retrieved_items = db_manager.get_feed_items(limit=5)
        logger.info(f"✅ Retrieved {len(retrieved_items)} items from database")
        
        # Show count by signal type
        for signal_type in ['red', 'yellow', 'green']:
            count = db_manager.get_item_count(signal_type=signal_type)
            emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢"}[signal_type]
            logger.info(f"   {emoji} {signal_type}: {count} items")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting AI Signal Feed tests...\n")
    
    # Test arXiv scraper
    items = test_arxiv_scraper()
    print("-" * 50)
    
    # Test classifier
    classified_items = test_classifier(items)
    print("-" * 50)
    
    # Test database
    db_success = test_database(classified_items)
    print("-" * 50)
    
    # Summary
    if items and classified_items and db_success:
        logger.info("🎉 All tests passed! The system is working.")
        logger.info(f"📊 Summary: Scraped {len(items)} items, classified them, and saved to database.")
    else:
        logger.error("❌ Some tests failed. Check the logs above.")
        
    logger.info("\n🔥 Ready to build the Streamlit UI!")

if __name__ == "__main__":
    main()