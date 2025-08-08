import streamlit as st
import requests
import feedparser
from datetime import datetime, timedelta
import re
import json

# Try to import database functionality
try:
    from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import IntegrityError
    
    DATABASE_AVAILABLE = True
    
    # Simple database models
    Base = declarative_base()
    
    class FeedItem(Base):
        __tablename__ = "feed_items"
        
        id = Column(Integer, primary_key=True, index=True)
        source = Column(String(50), nullable=False, index=True)
        source_id = Column(String(200), nullable=False, index=True)
        url = Column(Text, nullable=False)
        title = Column(Text, nullable=False)
        description = Column(Text)
        author = Column(String(200))
        published_date = Column(DateTime, index=True)
        scraped_date = Column(DateTime, default=datetime.utcnow, index=True)
        score = Column(Integer, default=0)
        signal_type = Column(String(10), nullable=False, index=True)
        confidence_score = Column(Float, default=0.0)
        
except ImportError:
    DATABASE_AVAILABLE = False
    st.sidebar.warning("⚠️ Database not available - using session storage")

# Page config
st.set_page_config(
    page_title="🧪 AI Signal Feed",
    page_icon="🧪", 
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_database():
    """Initialize database if available"""
    if not DATABASE_AVAILABLE:
        return None
    
    try:
        # Use file-based SQLite
        engine = create_engine("sqlite:///ai_signal_feed.db", echo=False)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal
    except Exception as e:
        st.sidebar.error(f"Database init failed: {e}")
        return None

def save_to_database(items, SessionLocal):
    """Save items to database"""
    if not SessionLocal:
        return 0
    
    saved_count = 0
    db = SessionLocal()
    
    try:
        for item in items:
            # Check for duplicates
            existing = db.query(FeedItem).filter(
                FeedItem.source == item['source'],
                FeedItem.title == item['title']
            ).first()
            
            if existing:
                continue
            
            # Create new item
            feed_item = FeedItem(
                source=item['source'],
                source_id=item.get('source_id', f"{item['source']}_{hash(item['title'])}"),
                url=item['url'],
                title=item['title'],
                description=item['description'],
                author=item['author'],
                published_date=item['published_date'],
                score=item['score'],
                signal_type=item['signal_type'],
                confidence_score=item.get('confidence_score', 0.5)
            )
            
            db.add(feed_item)
            saved_count += 1
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        st.error(f"Database save error: {e}")
    finally:
        db.close()
    
    return saved_count

def load_from_database(SessionLocal, limit=100):
    """Load items from database"""
    if not SessionLocal:
        return []
    
    db = SessionLocal()
    try:
        items = db.query(FeedItem).order_by(FeedItem.scraped_date.desc()).limit(limit).all()
        
        result = []
        for item in items:
            result.append({
                'title': item.title,
                'description': item.description,
                'url': item.url,
                'author': item.author,
                'published_date': item.published_date,
                'source': item.source,
                'signal_emoji': "🔴" if item.signal_type == "red" else "🟡" if item.signal_type == "yellow" else "🟢",
                'signal_type': item.signal_type,
                'score': item.score,
                'scraped_date': item.scraped_date
            })
        
        return result
        
    except Exception as e:
        st.error(f"Database load error: {e}")
        return []
    finally:
        db.close()

def classify_signal(title, description="", score=0):
    """Enhanced signal classification"""
    text = f"{title} {description}".lower()
    
    # High impact keywords
    high_impact = ["state-of-the-art", "sota", "breakthrough", "introduce", "new model", 
                   "open source", "dataset", "benchmark", "outperform", "record", "new method",
                   "novel", "first", "achieve", "surpass", "beats", "better than"]
    
    # Curious keywords  
    curious = ["experiment", "explore", "try", "attempt", "hack", "tool", "library",
               "implementation", "clone", "recreation", "interesting", "cool", "simple"]
    
    # Insight keywords
    insight = ["explain", "understand", "analysis", "review", "comparison", "survey",
               "guide", "tutorial", "thoughts", "opinion", "commentary", "why", "how"]
    
    high_score = sum(1 for keyword in high_impact if keyword in text)
    curious_score = sum(1 for keyword in curious if keyword in text)
    insight_score = sum(1 for keyword in insight if keyword in text)
    
    # Score-based classification
    if high_score >= 2 or score > 100:
        return "🔴", "red", 0.8
    elif high_score >= 1 or curious_score >= 2 or score > 20:
        return "🟡", "yellow", 0.6
    elif insight_score >= 2:
        return "🟢", "green", 0.7
    else:
        return "🟢", "green", 0.4

def scrape_arxiv():
    """Enhanced arXiv scraper"""
    try:
        url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': 'cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV OR cat:stat.ML',
            'start': 0,
            'max_results': 50,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        
        response = requests.get(url, params=params, timeout=30)
        feed = feedparser.parse(response.text)
        
        items = []
        for entry in feed.entries:
            # Extract arXiv ID
            arxiv_id = entry.id.split("/")[-1]
            arxiv_id = re.sub(r'v\d+$', '', arxiv_id)
            
            # Authors
            authors = [author.name for author in entry.authors] if hasattr(entry, 'authors') else ['Unknown']
            
            # Published date
            published_date = None
            if hasattr(entry, 'published_parsed'):
                published_date = datetime(*entry.published_parsed[:6])
            
            # Enhanced signal classification
            signal_emoji, signal_type, confidence = classify_signal(
                entry.title, 
                entry.summary if hasattr(entry, 'summary') else ""
            )
            
            items.append({
                'title': entry.title,
                'description': entry.summary[:500] + "..." if hasattr(entry, 'summary') and len(entry.summary) > 500 else entry.summary if hasattr(entry, 'summary') else "",
                'url': f"https://arxiv.org/abs/{arxiv_id}",
                'author': ", ".join(authors[:3]) + ("..." if len(authors) > 3 else ""),  # Limit authors
                'published_date': published_date,
                'source': 'arXiv',
                'signal_emoji': signal_emoji,
                'signal_type': signal_type,
                'score': 0,
                'confidence_score': confidence,
                'source_id': f"arxiv_{arxiv_id}"
            })
        
        return items
        
    except Exception as e:
        st.error(f"arXiv scraping failed: {e}")
        return []

def scrape_github():
    """Enhanced GitHub scraper"""
    try:
        # Use GitHub's search API
        url = "https://api.github.com/search/repositories"
        
        # Search for recent AI repos
        cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        params = {
            'q': f'AI OR "machine learning" OR "deep learning" OR "neural network" language:python stars:>10 pushed:>{cutoff_date}',
            'sort': 'updated',
            'order': 'desc',
            'per_page': 30
        }
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if 'items' not in data:
            if 'message' in data:
                st.warning(f"GitHub API: {data['message']}")
            return []
        
        items = []
        for repo in data['items']:
            signal_emoji, signal_type, confidence = classify_signal(
                repo['name'], 
                repo.get('description', ''), 
                repo['stargazers_count']
            )
            
            # Clean description
            desc = repo.get('description', 'No description')
            if len(desc) > 200:
                desc = desc[:200] + "..."
            
            items.append({
                'title': f"{repo['full_name']} - {desc}",
                'description': repo.get('description', ''),
                'url': repo['html_url'],
                'author': repo['owner']['login'],
                'published_date': datetime.fromisoformat(repo['created_at'].replace('Z', '+00:00')) if repo.get('created_at') else None,
                'source': 'GitHub',
                'signal_emoji': signal_emoji,
                'signal_type': signal_type,
                'score': repo['stargazers_count'],
                'confidence_score': confidence,
                'source_id': f"github_{repo['id']}"
            })
        
        return items
        
    except Exception as e:
        st.error(f"GitHub scraping failed: {e}")
        return []

def render_feed_item(item):
    """Enhanced feed item rendering"""
    col1, col2 = st.columns([1, 20])
    
    with col1:
        st.markdown(f"## {item['signal_emoji']}")
        
    with col2:
        # Title and source
        st.markdown(f"**[{item['title']}]({item['url']})**")
        
        # Metadata
        meta_parts = []
        if item['author']:
            meta_parts.append(f"👤 {item['author']}")
        if item['published_date']:
            time_ago = datetime.now() - item['published_date'].replace(tzinfo=None) if item['published_date'].tzinfo else datetime.now() - item['published_date']
            if time_ago.days > 0:
                meta_parts.append(f"📅 {time_ago.days}d ago")
            else:
                hours = time_ago.seconds // 3600
                meta_parts.append(f"📅 {hours}h ago")
        meta_parts.append(f"🔗 {item['source']}")
        if item['score'] > 0:
            score_emoji = "⭐" if item['source'] == "GitHub" else "📊"
            meta_parts.append(f"{score_emoji} {item['score']}")
            
        st.caption(" | ".join(meta_parts))
        
        # Description
        if item['description']:
            with st.expander("📄 Description", expanded=False):
                st.write(item['description'])
        
        st.divider()

def main():
    """Enhanced main app"""
    
    # Initialize database
    SessionLocal = init_database()
    
    # Header
    st.markdown("# 🧪 AI Signal Feed")
    db_status = "🗄️ Database" if DATABASE_AVAILABLE else "💾 Session"
    st.markdown(f"*Low-noise, high-signal AI discoveries* ({db_status} storage)")
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Controls")
        
        # Manual scrape
        if st.button("🔄 Scrape Latest", use_container_width=True):
            with st.spinner("🔍 Scraping arXiv and GitHub..."):
                # Scrape data
                arxiv_items = scrape_arxiv()
                github_items = scrape_github()
                all_items = arxiv_items + github_items
                
                if DATABASE_AVAILABLE and SessionLocal:
                    # Save to database
                    saved_count = save_to_database(all_items, SessionLocal)
                    st.success(f"✅ Found {len(arxiv_items)} arXiv papers and {len(github_items)} GitHub repos!")
                    st.success(f"💾 Saved {saved_count} new items to database")
                    
                    # Load from database for display
                    st.session_state.items = load_from_database(SessionLocal)
                else:
                    # Use session state
                    st.session_state.items = all_items
                    st.success(f"✅ Found {len(arxiv_items)} arXiv papers and {len(github_items)} GitHub repos!")
                
                st.session_state.last_update = datetime.now()
        
        # Load from database button
        if DATABASE_AVAILABLE and SessionLocal:
            if st.button("📚 Load from Database", use_container_width=True):
                st.session_state.items = load_from_database(SessionLocal)
                st.success(f"Loaded {len(st.session_state.items)} items from database")
        
        # Filters
        signal_filter = st.selectbox(
            "🚦 Signal Type",
            options=[None, "red", "yellow", "green"],
            format_func=lambda x: "All Signals" if x is None else f"{'🔴' if x=='red' else '🟡' if x=='yellow' else '🟢'} {x.title()}",
            index=0
        )
        
        source_filter = st.selectbox(
            "📡 Source", 
            options=[None, "arXiv", "GitHub"],
            format_func=lambda x: "All Sources" if x is None else x,
            index=0
        )
        
        # Time filter
        hours_filter = st.selectbox(
            "⏰ Time Range",
            options=[None, 24, 72, 168],
            format_func=lambda x: "All Time" if x is None else f"Last {x}h",
            index=0
        )
        
        # Stats
        if 'items' in st.session_state:
            st.markdown("## 📊 Stats")
            items = st.session_state.items
            red_count = len([item for item in items if item['signal_type'] == 'red'])
            yellow_count = len([item for item in items if item['signal_type'] == 'yellow'])
            green_count = len([item for item in items if item['signal_type'] == 'green'])
            
            st.metric("Total Items", len(items))
            st.metric("🔴 Red", red_count)
            st.metric("🟡 Yellow", yellow_count) 
            st.metric("🟢 Green", green_count)
            
            if 'last_update' in st.session_state:
                st.caption(f"Last updated: {st.session_state.last_update.strftime('%H:%M:%S')}")
        
        # Database info
        if DATABASE_AVAILABLE:
            st.markdown("---")
            st.markdown("**💾 Storage:** Database")
            st.caption("Items persist between sessions")
        else:
            st.markdown("---")
            st.markdown("**💾 Storage:** Session")
            st.caption("Items reset on page reload")
    
    # Main content
    if 'items' not in st.session_state:
        # Try to load from database first
        if DATABASE_AVAILABLE and SessionLocal:
            existing_items = load_from_database(SessionLocal, limit=50)
            if existing_items:
                st.session_state.items = existing_items
                st.info(f"📚 Loaded {len(existing_items)} items from database")
        
        if 'items' not in st.session_state:
            # Welcome message
            st.info("👋 Welcome! Click **'🔄 Scrape Latest'** in the sidebar to fetch the latest AI discoveries.")
            
            with st.expander("🚀 About AI Signal Feed", expanded=True):
                st.markdown(f"""
                This feed automatically discovers and classifies AI/ML content from:
                - 📄 **arXiv**: Latest research papers (cs.AI, cs.LG, cs.CL, cs.CV, stat.ML)
                - 💾 **GitHub**: Trending AI repositories (updated in last week)
                
                **Signal Classification:**
                - 🔴 **Red**: High-impact breakthroughs, SOTA models, major releases
                - 🟡 **Yellow**: Interesting experiments, useful tools, novel approaches
                - 🟢 **Green**: Educational content, insights, analysis, reviews
                
                **Storage:** {db_status} - {"Persistent across sessions" if DATABASE_AVAILABLE else "Resets on page reload"}
                """)
            return
    
    # Apply filters
    items = st.session_state.items
    
    if signal_filter:
        items = [item for item in items if item['signal_type'] == signal_filter]
    if source_filter:
        items = [item for item in items if item['source'] == source_filter]
    if hours_filter:
        cutoff = datetime.now() - timedelta(hours=hours_filter)
        items = [item for item in items if item.get('published_date') and item['published_date'].replace(tzinfo=None) > cutoff]
    
    # Display feed
    if not items:
        st.warning("🤔 No items match your filters. Try adjusting the filters or scraping fresh data.")
        return
    
    st.markdown(f"## 📰 Feed ({len(items)} items)")
    
    # Sort by signal priority (red first), then by score/date
    signal_priority = {'red': 0, 'yellow': 1, 'green': 2}
    items.sort(key=lambda x: (
        signal_priority.get(x['signal_type'], 3), 
        -x['score'],
        -(x['published_date'].timestamp() if x['published_date'] else 0)
    ))
    
    for item in items:
        render_feed_item(item)

if __name__ == "__main__":
    main()