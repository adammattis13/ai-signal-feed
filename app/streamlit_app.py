import streamlit as st
from datetime import datetime, timedelta
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.database import DatabaseManager, init_db
from src.scrapers.arxiv_scraper import ArxivScraper
from src.scrapers.github_scraper import GitHubScraper
from src.scrapers.reddit_scraper import RedditScraper
from src.scrapers.hackernews_scraper import HackerNewsScraper
from src.classifier.signal_classifier import SignalClassifier
from config.settings import SIGNAL_COLORS, ITEMS_PER_PAGE

# Page config
st.set_page_config(
    page_title="🧪 AI Signal Feed",
    page_icon="🧪", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
@st.cache_resource
def init_database():
    """Initialize database connection"""
    init_db()
    return DatabaseManager()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_feed_data(source_filter, signal_filter, hours_back, limit, offset):
    """Get feed data with caching"""
    db_manager = init_database()
    return db_manager.get_feed_items(
        source=source_filter,
        signal_type=signal_filter, 
        hours_back=hours_back,
        limit=limit,
        offset=offset
    )

def format_time_ago(dt):
    """Format datetime as time ago string"""
    if not dt:
        return "Unknown"
        
    now = datetime.utcnow()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=None)
        now = now.replace(tzinfo=None)
    
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}h ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}m ago"
    else:
        return "Just now"

def render_feed_item(item):
    """Render a single feed item"""
    # Signal color
    signal_emoji = SIGNAL_COLORS.get(item.signal_type, "⚪")
    
    # Create columns for layout
    col1, col2 = st.columns([1, 20])
    
    with col1:
        st.markdown(f"## {signal_emoji}")
        
    with col2:
        # Title and source
        st.markdown(f"**[{item.title}]({item.url})**")
        
        # Metadata row
        meta_parts = []
        if item.author:
            meta_parts.append(f"👤 {item.author}")
        meta_parts.append(f"📅 {format_time_ago(item.published_date)}")
        meta_parts.append(f"🔗 {item.source.title()}")
        if item.score > 0:
            score_emoji = "⭐" if item.source == "github" else "⬆️"
            meta_parts.append(f"{score_emoji} {item.score}")
            
        st.caption(" | ".join(meta_parts))
        
        # Description
        if item.description:
            with st.expander("📄 Abstract / Description", expanded=False):
                st.write(item.description)
                
        # Tags
        if item.tags:
            try:
                import json
                tags = json.loads(item.tags) if isinstance(item.tags, str) else item.tags
                if tags:
                    tag_html = " ".join([f"`{tag}`" for tag in tags[:5]])  # Limit tags
                    st.markdown(f"🏷️ {tag_html}")
            except:
                pass
        
        st.divider()

def run_manual_scrape():
    """Run manual scraping"""
    st.write("### 🔍 Scraping all sources...")
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Create a log container
    log_container = st.expander("📝 Detailed Logs", expanded=True)
    log_text = log_container.empty()
    
    # Capture logs in a list
    import io
    import logging
    
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to scrapers
    scrapers_logger = logging.getLogger('src.scrapers')
    scrapers_logger.addHandler(handler)
    scrapers_logger.setLevel(logging.INFO)
    
    try:
        classifier = SignalClassifier()
        db_manager = init_database()
        
        # Define scrapers
        scrapers = [
            ("arXiv Papers", ArxivScraper()),
            ("GitHub Repos", GitHubScraper()),
            ("Reddit Posts", RedditScraper()),
            ("Hacker News", HackerNewsScraper())
        ]
        
        all_items = []
        total_scrapers = len(scrapers)
        
        for i, (name, scraper) in enumerate(scrapers):
            status_text.text(f"🔍 Scraping {name}...")
            progress_bar.progress((i) / total_scrapers)
            
            # Update log display
            current_logs = log_capture.getvalue()
            if current_logs:
                log_text.text_area("Logs:", current_logs, height=200)
            
            try:
                # Scrape items
                st.write(f"🔍 **Starting {name} scraper...**")
                items = scraper.scrape()
                
                # Update logs after each scraper
                current_logs = log_capture.getvalue()
                if current_logs:
                    log_text.text_area("Logs:", current_logs, height=200)
                
                if items:
                    st.success(f"✅ {name}: Found {len(items)} items")
                    all_items.extend(items)
                else:
                    st.warning(f"⚠️ {name}: No items found")
                    
            except Exception as e:
                st.error(f"❌ {name}: {str(e)}")
                # Still show logs even if error
                current_logs = log_capture.getvalue()
                if current_logs:
                    log_text.text_area("Logs:", current_logs, height=200)
                continue
        
        # Classification and saving
        status_text.text("🧠 Classifying and saving items...")
        progress_bar.progress(0.8)
        
        if all_items:
            st.write("🧠 **Classifying items...**")
            saved_count = 0
            for item in all_items:
                # Classify
                signal_type, confidence = classifier.classify(item)
                item['signal_type'] = signal_type
                item['confidence_score'] = confidence
                
                # Save to database
                if db_manager.add_feed_item(item):
                    saved_count += 1
            
            progress_bar.progress(1.0)
            status_text.text("✅ Scraping completed!")
            
            st.success(f"🎉 Successfully scraped {len(all_items)} total items and saved {saved_count} new ones!")
            
            # Show breakdown by source
            from collections import Counter
            source_counts = Counter(item['source'] for item in all_items)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("arXiv", source_counts.get('arxiv', 0))
            with col2:
                st.metric("GitHub", source_counts.get('github', 0))
            with col3:
                st.metric("Reddit", source_counts.get('reddit', 0))
            with col4:
                st.metric("Hacker News", source_counts.get('hackernews', 0))
            
            # Final log update
            final_logs = log_capture.getvalue()
            if final_logs:
                log_text.text_area("Final Logs:", final_logs, height=300)
            
            # Clear cache to show new data
            st.cache_data.clear()
            time.sleep(2)  # Brief pause before rerun
            st.rerun()
        else:
            st.error("❌ No items found from any source")
            
    except Exception as e:
        st.error(f"❌ Scraping failed: {str(e)}")
        progress_bar.progress(0)
        status_text.text("❌ Scraping failed")
    
    finally:
        # Clean up logging handler
        scrapers_logger.removeHandler(handler)

def main():
    """Main Streamlit app"""
    
    # Header
    st.markdown("# 🧪 AI Signal Feed")
    st.markdown("*Low-noise, high-signal AI discoveries from research and dev communities*")
    
    # Sidebar filters
    with st.sidebar:
        st.markdown("## 🎛️ Filters")
        
        # Source filter
        source_filter = st.selectbox(
            "📡 Source",
            options=[None, "arxiv", "github", "reddit", "hackernews"],
            format_func=lambda x: "All Sources" if x is None else x.title(),
            index=0
        )
        
        # Signal filter  
        signal_filter = st.selectbox(
            "🚦 Signal Type",
            options=[None, "red", "yellow", "green"],
            format_func=lambda x: "All Signals" if x is None else f"{SIGNAL_COLORS.get(x, '')} {x.title()}",
            index=0
        )
        
        # Time filter
        time_filter = st.selectbox(
            "📅 Time Range", 
            options=[24, 72, 168, None],
            format_func=lambda x: f"Last {x}h" if x else "All Time",
            index=1
        )
        
        st.divider()
        
        # Manual scrape button
        if st.button("🔄 Scrape Now", use_container_width=True):
            run_manual_scrape()
            
        # Stats
        st.markdown("## 📊 Stats")
        db_manager = init_database()
        
        total_items = db_manager.get_item_count()
        red_items = db_manager.get_item_count(signal_type="red") 
        yellow_items = db_manager.get_item_count(signal_type="yellow")
        green_items = db_manager.get_item_count(signal_type="green")
        
        st.metric("Total Items", total_items)
        st.metric(f"{SIGNAL_COLORS['red']} Red", red_items)
        st.metric(f"{SIGNAL_COLORS['yellow']} Yellow", yellow_items)
        st.metric(f"{SIGNAL_COLORS['green']} Green", green_items)
    
    # Main content
    if st.button("🔄 Refresh Feed", use_container_width=False):
        st.cache_data.clear()
        st.rerun()
    
    # Get feed items
    items = get_feed_data(source_filter, signal_filter, time_filter, ITEMS_PER_PAGE, 0)
    
    if not items:
        st.info("🤔 No items found. Try adjusting filters or run a manual scrape.")
        
        # Show quick start if no data
        with st.expander("🚀 Quick Start", expanded=True):
            st.markdown("""
            **No data yet? Here's how to get started:**
            
            1. Click **"🔄 Scrape Now"** in the sidebar to fetch from all sources:
               - 📄 **arXiv**: Latest AI/ML research papers
               - 💾 **GitHub**: Trending AI repositories  
               - 💬 **Reddit**: r/MachineLearning, r/LocalLLaMA, r/artificial
               - 📰 **Hacker News**: AI/ML discussions and links
            2. Or run the test script: `python test_scraper.py`
            3. Refresh the page to see your feed!
            
            The system will automatically classify content as:
            - 🔴 **Red**: High-impact breakthroughs, SOTA models
            - 🟡 **Yellow**: Curious experiments, interesting tools  
            - 🟢 **Green**: Insights, analysis, commentary
            """)
        return
    
    # Display items
    st.markdown(f"## 📰 Feed ({len(items)} items)")
    
    for item in items:
        render_feed_item(item)
    
    # Pagination placeholder (for future)
    if len(items) == ITEMS_PER_PAGE:
        st.info("📄 Pagination coming soon! For now, adjust time filters to see more items.")

if __name__ == "__main__":
    main()