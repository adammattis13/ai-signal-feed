# 🧪 AI Signal Feed

A **low-noise, high-signal feed** of cutting-edge AI discoveries from research, dev, and open-source communities. Automatically scrapes, classifies, and presents the most interesting AI/ML content with color-coded signal strength.

## ✨ Features

- 🔍 **Multi-source scraping**: arXiv papers, GitHub repos, Reddit discussions, Hacker News
- 🧠 **Smart classification**: Automatically tags content as:
  - 🔴 **Red** (High Impact): SOTA models, breakthroughs, major releases  
  - 🟡 **Yellow** (Curious): Interesting tools, experiments, niche discoveries
  - 🟢 **Green** (Insight): Analysis, explanations, commentary
- 📊 **Clean feed UI**: Streamlit-based interface with filtering
- 🕓 **Automated updates**: Scheduled scraping every 6-12 hours
- 💾 **SQLite storage**: Simple, fast, file-based database

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone and navigate to project
git clone <your-repo-url>
cd ai-signal-feed

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template (optional)
cp .env.example .env
# Edit .env with your API keys if you have them
```

### 2. Test the System

```bash
# Run the test script to verify everything works
python test_scraper.py
```

This will:
- Scrape recent papers from arXiv
- Classify them with signal types
- Save to database
- Show summary statistics

### 3. Run the Feed UI

```bash
streamlit run app/streamlit_app.py
```

## 📁 Project Structure

```
ai-signal-feed/
├── src/
│   ├── scrapers/          # Web scrapers for each source
│   ├── classifier/        # Signal classification logic
│   ├── database/          # SQLite database models
│   ├── scheduler/         # Automated job scheduling
│   └── utils/             # Helper functions
├── app/
│   └── streamlit_app.py   # Web UI
├── config/
│   └── settings.py        # Configuration
├── data/                  # SQLite database storage
└── tests/                 # Test suite
```

## 🔧 Configuration

Edit `config/settings.py` to customize:

- **arXiv categories**: Which research areas to follow
- **GitHub keywords**: What repos to track
- **Reddit subreddits**: Which communities to monitor
- **Classification weights**: How to score different signals
- **Update frequency**: How often to scrape

## 🏷️ Signal Classification

The system automatically classifies items using:

- **Keywords analysis**: Looks for terms like "state-of-the-art", "introduce", "breakthrough"
- **Engagement metrics**: GitHub stars, Reddit upvotes, HN points
- **Source authority**: Known researchers, authoritative domains
- **Recency**: Newer content gets higher priority

## 🛠️ Development

### Add New Scrapers

1. Create new scraper in `src/scrapers/` inheriting from `BaseScraper`
2. Implement the `scrape()` method
3. Add to scheduler configuration
4. Update imports in `__init__.py`

### Customize Classification

Edit `src/classifier/signal_classifier.py` to:
- Add new keyword categories
- Adjust scoring weights  
- Add source-specific rules
- Improve authority detection

### Environment Variables

Optional API keys for higher rate limits:

```bash
# GitHub (recommended)
GITHUB_TOKEN=your_personal_access_token

# Reddit (for Reddit scraping)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
```

## 📊 Current Status

**✅ MVP Complete:**
- [x] arXiv scraper with classification
- [x] Signal classifier (red/yellow/green)
- [x] SQLite database with models
- [x] Test script verification
- [ ] Streamlit UI (next step!)
- [ ] GitHub scraper  
- [ ] Reddit scraper
- [ ] Hacker News scraper
- [ ] Automated scheduling

## 🔮 Next Steps

1. **Build Streamlit UI** - Feed interface with filtering
2. **Add remaining scrapers** - GitHub, Reddit, HN
3. **Implement scheduling** - Automated daily updates  
4. **Deploy** - Docker + cloud deployment
5. **Enhance classification** - More sophisticated ML models

## 🤝 Contributing

This is an MVP! Contributions welcome:

- Add new data sources
- Improve classification accuracy
- Enhance UI/UX
- Add tests
- Optimize performance

## 📄 License

MIT License - See LICENSE file for details

---

**Built with ❤️ for the AI research community**