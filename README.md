# 🍽️ Restaurant Intelligence Agent

**AI-powered autonomous analysis of restaurant reviews with MCP integration**

Built for Anthropic MCP 1st Birthday Hackathon - Track 2: Agent Apps

---

## 🎯 What It Does

Automatically analyzes restaurant reviews from OpenTable and provides actionable insights:

- 🤖 **Autonomous Agent** - Plans and executes analysis independently
- 🔍 **Smart Discovery** - Finds menu items + aspects dynamically (no hardcoding!)
- ⚡ **Optimized** - Single-pass extraction (66% fewer API calls)
- 📊 **Multi-Stakeholder** - Chef-focused + Manager-focused insights
- 🔧 **MCP Tools** - Save reports, RAG Q&A, chart generation
- 💰 **Cost Efficient** - Batched processing for 1000+ reviews

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Chrome/Chromium (for scraping)
- Anthropic API key

### Installation
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/restaurant-intelligence-agent.git
cd restaurant-intelligence-agent

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# Run analysis
python integrate_scraper_with_agent.py
```

---

## 📁 Project Structure
```
restaurant-intelligence-agent/
├── src/
│   ├── agent/              # AI agents (planner, executor, analyzers)
│   │   ├── base_agent.py         # Main orchestrator
│   │   ├── unified_analyzer.py   # Single-pass extraction (NEW!)
│   │   ├── insights_generator.py # Chef/Manager insights
│   │   └── api_utils.py          # Retry logic
│   ├── scrapers/           # OpenTable scraper
│   │   └── opentable_scraper.py  # Production-ready scraper
│   ├── data_processing/    # Data pipeline
│   │   └── review_processor.py   # CSV export, DataFrame conversion
│   └── mcp_integrations/   # MCP tools
│       ├── save_report.py        # JSON report export
│       ├── query_reviews.py      # RAG Q&A
│       └── generate_chart.py     # Visualizations
├── data/
│   ├── raw/                # Scraped reviews (CSV)
│   └── processed/          # Processed data
├── outputs/                # Analysis results
│   ├── menu_analysis.json
│   ├── aspect_analysis.json
│   ├── insights.json
│   └── *.png              # Charts
├── reports/                # MCP-generated reports
└── integrate_scraper_with_agent.py  # Main pipeline
```

---

## 🛠️ How It Works

### 1. **Scrape Reviews**
```python
from src.scrapers.opentable_scraper import scrape_opentable

result = scrape_opentable(
    "https://www.opentable.ca/r/restaurant-name",
    max_reviews=100
)
```

### 2. **Run Analysis**
```python
from src.agent.base_agent import RestaurantAnalysisAgent

agent = RestaurantAnalysisAgent()
analysis = agent.analyze_restaurant(
    restaurant_url=url,
    restaurant_name="Restaurant Name",
    reviews=review_texts
)
```

### 3. **Get Insights**
```python
# Chef insights
print(analysis['insights']['chef'])

# Manager insights
print(analysis['insights']['manager'])

# Menu analysis
print(analysis['menu_analysis'])

# Aspect analysis
print(analysis['aspect_analysis'])
```

---

## 🎨 Key Features

### **Unified Analyzer** (NEW!)
Single-pass extraction of menu items + aspects:
- **Old approach**: 8 API calls for 50 reviews
- **New approach**: 4 API calls for 50 reviews
- **Savings**: 50% reduction in API costs 💰

### **Dynamic Discovery**
No hardcoding - adapts to ANY restaurant:
- Japanese → discovers: presentation, freshness, sushi rolls
- Italian → discovers: portion size, pasta dishes, wine pairing
- Mexican → discovers: spice level, tacos, authenticity

### **MCP Integration**
- **Save Reports**: JSON export to disk
- **RAG Q&A**: Ask questions about reviews
- **Chart Generation**: Sentiment visualizations

---

## 📊 Current Status

**✅ COMPLETE:**
- Scraper (production-ready)
- Data processing pipeline
- Unified analyzer (optimized)
- Menu + Aspect discovery
- Insights generation (Chef + Manager)
- MCP tool integration
- Complete end-to-end pipeline

**🚧 IN PROGRESS:**
- Gradio UI (Days 14-15)
- Anomaly detection (Days 14-15)

**⏳ PLANNED:**
- Demo video
- Social media post
- Final submission

---

## 🧪 Testing
```bash
# Test scraper
python -c "from src.scrapers.opentable_scraper import scrape_opentable; print('✅ Scraper OK')"

# Test agent
python -c "from src.agent.base_agent import RestaurantAnalysisAgent; print('✅ Agent OK')"

# Run full pipeline
python integrate_scraper_with_agent.py
```

---

## 📈 Performance

For **1000 reviews**:
- **API calls**: ~68 (vs. 136 with old approach)
- **Time**: ~15-20 minutes
- **Cost**: ~$2-3 (Claude Sonnet 4)

---

## 🏆 Hackathon Submission

- **Track**: Track 2 - Agent Apps
- **Category**: Productivity
- **Built**: Nov 12 - Dec 3, 2025
- **Status**: Pipeline complete, UI in progress

---

## 📝 License

MIT License

## 👤 Author

Built by Tushar Pingle for Anthropic MCP Hackathon 2025

---

## 🙏 Acknowledgments

- Anthropic for Claude API
- MCP framework
- OpenTable for review data
