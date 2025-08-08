import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/ai_signal_feed.db")

# API Keys
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "ai-signal-feed/1.0")

# arXiv Settings
ARXIV_CATEGORIES = [
    "cs.AI",      # Artificial Intelligence
    "cs.LG",      # Machine Learning  
    "cs.CL",      # Computation and Language
    "cs.CV",      # Computer Vision
    "stat.ML",    # Machine Learning (stats)
]
ARXIV_MAX_RESULTS = 50  # per category per day

# GitHub Settings
GITHUB_KEYWORDS = [
    "AI", "artificial-intelligence", "machine-learning", "ML", 
    "deep-learning", "neural-network", "NLP", "computer-vision",
    "generative-ai", "LLM", "large-language-model", "transformer"
]
GITHUB_MIN_STARS = 10  # minimum stars for trending repos

# Reddit Settings  
REDDIT_SUBREDDITS = [
    "MachineLearning",
    "LocalLLaMA", 
    "artificial"
]
REDDIT_POST_LIMIT = 25  # per subreddit

# Hacker News Settings
HN_AI_KEYWORDS = [
    "AI", "ML", "machine learning", "deep learning", "neural network",
    "LLM", "GPT", "transformer", "generative", "artificial intelligence",
    "computer vision", "NLP", "natural language", "PyTorch", "TensorFlow"
]
HN_MIN_SCORE = 20  # minimum HN score

# Signal Classification Weights
SIGNAL_WEIGHTS = {
    "high_impact_keywords": [
        "state-of-the-art", "SOTA", "breakthrough", "introduce", "new model",
        "open source", "dataset", "benchmark", "outperform", "record"
    ],
    "curious_keywords": [
        "experiment", "explore", "try", "attempt", "hack", "tool", "library",
        "implementation", "clone", "recreation"
    ],
    "insight_keywords": [
        "explain", "understand", "analysis", "review", "comparison", "survey",
        "trend", "thoughts", "opinion", "commentary"
    ]
}

# Scheduling
SCRAPE_INTERVAL_HOURS = 6
MAX_RETRIES = 3

# UI Settings
ITEMS_PER_PAGE = 50
SIGNAL_COLORS = {
    "red": "🔴",
    "yellow": "🟡", 
    "green": "🟢"
}