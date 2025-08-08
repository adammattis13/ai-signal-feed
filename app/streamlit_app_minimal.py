import streamlit as st
import requests
import feedparser
from datetime import datetime, timedelta
import re

# Page config
st.set_page_config(
    page_title="🧪 AI Signal Feed",
    page_icon="🧪", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def classify_signal(title, description="", score=0):
    """Simple signal classification"""
    text = f"{title} {description}".lower()
    
    # High impact keywords
    high_impact = ["state-of-the-art", "sota", "breakthrough", "introduce", "new model", 
                   "open source", "dataset", "benchmark", "outperform", "record"]
    
    # Curious keywords  
    curious = ["experiment", "explore", "try", "attempt", "hack", "tool", "library",
               "implementation", "clone", "recreation"]
    
    high_score = sum(1 for keyword in high_impact if keyword in text)
    curious_score = sum(1 for keyword in curious if keyword in text)
    
    if high_score >= 2 or score > 100:
        return "🔴", "red"
    elif high_score >= 1 or curious_score >= 2 or score > 20:
        return "🟡", "yellow"
    else:
        return "🟢", "green"

def scrape_arxiv():
    """Scrape arXiv papers"""
    try:
        url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': 'cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV',
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
            
            # Signal classification
            signal_emoji, signal_type = classify_signal(entry.title, entry.summary if hasattr(entry, 'summary') else "")
            
            items.append({
                'title': entry.title,
                'description': entry.summary[:300] + "..." if hasattr(entry, 'summary') and len(entry.summary) > 300 else entry.summary if hasattr(entry, 'summary') else "",
                'url': f"https://arxiv.org/abs/{arxiv_id}",
                'author': ", ".join(authors),
                'published_date': published_date,
                'source': 'arXiv',
                'signal_emoji': signal_emoji,
                'signal_type': signal_type,
                'score': 0
            })
        
        return items
        
    except Exception as e:
        st.error(f"arXiv scraping failed: {e}")
        return []

def scrape_github():
    """Scrape GitHub trending repos"""
    try:
        # Use GitHub's search API
        url = "https://api.github.com/search/repositories"
        params = {
            'q': 'AI OR "machine learning" OR "deep learning" language:python stars:>10',
            'sort': 'updated',
            'order': 'desc',
            'per_page': 20
        }
        
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if 'items' not in data:
            return []
        
        items = []
        for repo in data['items']:
            signal_emoji, signal_type = classify_signal(repo['name'], repo.get('description', ''), repo['stargazers_count'])
            
            items.append({
                'title': f"{repo['full_name']} - {repo.get('description', 'No description')[:100]}",
                'description': repo.get('description', ''),
                'url': repo['html_url'],
                'author': repo['owner']['login'],
                'published_date': datetime.fromisoformat(repo['created_at'].replace('Z', '+00:00')) if repo.get('created_at') else None,
                'source': 'GitHub',
                'signal_emoji': signal_emoji,
                'signal_type': signal_type,
                'score': repo['stargazers_count']
            })
        
        return items
        
    except Exception as e:
        st.error(f"GitHub scraping failed: {e}")
        return []

def render_feed_item(item):
    """Render a single feed item"""
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
            meta_parts.append(f"📅 {item['published_date'].strftime('%Y-%m-%d')}")
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
    """Main Streamlit app"""
    
    # Header
    st.markdown("# 🧪 AI Signal Feed")
    st.markdown("*Low-noise, high-signal AI discoveries (Minimal Version)*")
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 🎛️ Controls")
        
        # Manual scrape
        if st.button("🔄 Scrape Latest", use_container_width=True):
            with st.spinner("🔍 Scraping arXiv and GitHub..."):
                # Use session state to store results
                arxiv_items = scrape_arxiv()
                github_items = scrape_github()
                
                st.session_state.items = arxiv_items + github_items
                st.session_state.last_update = datetime.now()
                
                st.success(f"✅ Found {len(arxiv_items)} arXiv papers and {len(github_items)} GitHub repos!")
        
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
    
    # Main content
    if 'items' not in st.session_state:
        # Welcome message
        st.info("👋 Welcome! Click **'🔄 Scrape Latest'** in the sidebar to fetch the latest AI discoveries.")
        
        with st.expander("🚀 About AI Signal Feed", expanded=True):
            st.markdown("""
            This feed automatically discovers and classifies AI/ML content from:
            - 📄 **arXiv**: Latest research papers
            - 💾 **GitHub**: Trending AI repositories
            
            **Signal Classification:**
            - 🔴 **Red**: High-impact breakthroughs, SOTA models
            - 🟡 **Yellow**: Interesting experiments, useful tools
            - 🟢 **Green**: Educational content, insights
            
            *This is a minimal version that works without complex dependencies.*
            """)
        return
    
    # Apply filters
    items = st.session_state.items
    
    if signal_filter:
        items = [item for item in items if item['signal_type'] == signal_filter]
    if source_filter:
        items = [item for item in items if item['source'] == source_filter]
    
    # Display feed
    if not items:
        st.warning("🤔 No items match your filters. Try adjusting the filters or scraping fresh data.")
        return
    
    st.markdown(f"## 📰 Feed ({len(items)} items)")
    
    # Sort by signal priority (red first)
    signal_priority = {'red': 0, 'yellow': 1, 'green': 2}
    items.sort(key=lambda x: (signal_priority.get(x['signal_type'], 3), -x['score']))
    
    for item in items:
        render_feed_item(item)

if __name__ == "__main__":
    main()