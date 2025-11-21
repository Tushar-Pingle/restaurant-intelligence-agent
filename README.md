# 🍽️ Restaurant Intelligence Agent

AI-powered agent for autonomous restaurant review analysis using Claude and MCP (Model Context Protocol).

## 🎯 Overview

This agent automatically analyzes restaurant reviews from OpenTable, discovers menu items and aspects dynamically, detects anomalies, and provides actionable insights to restaurant owners.

### Key Features

- 🤖 **Autonomous Agent**: Plans, reasons, and executes analysis independently
- 🔍 **Dynamic Discovery**: Automatically identifies menu items and relevant aspects (no manual configuration)
- 📊 **Multi-Aspect Analysis**: Food quality, service, ambience, and more
- 🚨 **Smart Alerts**: Proactive anomaly detection with stakeholder routing (via Slack)
- 💾 **MCP Integration**: Saves reports to Google Drive, sends alerts via Slack
- 💬 **RAG Q&A**: Ask questions about reviews using natural language
- 🎨 **Gradio UI**: User-friendly interface for non-technical users

## 🏆 Hackathon Project

Built for the Anthropic MCP 1st Birthday Hackathon
- **Track**: Track 2 - Agent Apps  
- **Category**: Productivity
- **Timeline**: Nov 12 - Dec 3, 2025

## 🚀 Quick Start
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/restaurant-intelligence-agent.git
cd restaurant-intelligence-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys

# Run the application
python -m src.ui.gradio_app
```

## 📁 Project Structure
```
restaurant-intelligence-agent/
├── src/
│   ├── agent/              # Agent intelligence core
│   ├── scrapers/           # OpenTable scraper
│   ├── mcp_integrations/   # MCP connectors (Drive, Slack)
│   ├── ui/                 # Gradio interface
│   └── utils/              # Helper functions
├── examples/               # Sample outputs
├── docs/                   # Documentation
├── tests/                  # Unit tests
└── notebooks/              # Development notebooks
```

## 🛠️ Technology Stack

- **AI**: Claude (Anthropic)
- **MCP Servers**: Google Drive, Slack
- **NLP**: NLTK, scikit-learn
- **Web Scraping**: Selenium
- **UI**: Gradio 6
- **Vector DB**: ChromaDB (for RAG)

## 📊 Current Status

**Week 1**: Agent Intelligence Core ✅  
**Week 2**: MCP Integration + Automation 🚧  
**Week 3**: UI + Demo + Submission ⏳

## 📝 License

MIT License

## 👥 Author

Built by [Your Name] for Anthropic MCP Hackathon 2025

---

## 📈 Development Progress

### ✅ Day 1 - Agent Intelligence Core (Nov 19, 2025) - COMPLETE

**What we built:**
- [x] Base agent class with state management
- [x] Reasoning log system (full transparency)
- [x] AI-powered planning module using Claude
- [x] Comprehensive plan validation (null checks, data quality, logic)
- [x] Universal design - works with ANY restaurant type

**Key achievements:**
- Agent creates custom analysis plans using Claude AI
- Plans adapt to different restaurant types (tested: Japanese, Italian)
- Full reasoning transparency (timestamped logs)
- Quality validation ensures reliable execution
- All tests passing ✅

**Test results:**
- ✅ Agent initialization: PASSED
- ✅ Planning for Japanese restaurant: PASSED (12 steps generated)
- ✅ Planning for Italian restaurant: PASSED (12 steps generated)
- ✅ Plan validation: PASSED (all quality checks)
- ✅ Reasoning logs: PASSED (coherent, timestamped)

**Files created:**
- `src/agent/__init__.py` - Agent module initializer
- `src/agent/base_agent.py` - Core agent class (150+ lines)
- `src/agent/planner.py` - AI planning module (300+ lines)
- `docs/agent_flow.md` - Architecture documentation

**Next up - Day 2:**
- Agent execution framework
- Insight generation module
- End-to-end integration

---

### ✅ Day 2 - Agent Execution & Insights (Nov 19, 2025) - COMPLETE

**What we built:**
- [x] Execution framework with progress tracking
- [x] Error handling and graceful degradation
- [x] Insights generation module (chef + manager roles)
- [x] Complete agent integration (planner → executor → insights)
- [x] End-to-end workflow operational

**Key achievements:**
- Agent executes plans step-by-step with real-time progress
- Role-specific insights adapt to stakeholder needs
- Chef insights: food quality, menu items, recipes
- Manager insights: service, operations, staff
- Full workflow tested and validated ✅

**Test results:**
- ✅ Executor framework: PASSED
- ✅ Insights generation (chef): PASSED
- ✅ Insights generation (manager): PASSED
- ✅ End-to-end integration: PASSED
- ✅ Role filtering verified: PASSED

**Files created:**
- `src/agent/executor.py` - Step execution with progress tracking (200+ lines)
- `src/agent/insights_generator.py` - Role-specific insights (250+ lines)
- Updated `src/agent/base_agent.py` - Full integration (300+ lines)

**Architecture:**
```
User → Agent.analyze_restaurant(url)
  ├─→ Planner: Creates custom plan (AI)
  ├─→ Executor: Runs plan steps (with progress)
  └─→ Insights: Generates chef + manager summaries (AI)
```

**Next up - Day 3:**
- Menu discovery module (dynamic extraction)
- Aspect discovery module (adaptive to restaurant type)
- Integration with analysis pipeline

---

### ✅ Day 3 - Menu Discovery with Sentiment (Nov 19, 2025) - COMPLETE

**What we built:**
- [x] Dynamic menu item extraction (works with ANY cuisine)
- [x] Sentiment analysis per menu item (context-based)
- [x] Lowercase normalization (avoid duplicates)
- [x] Granular extraction (salmon sushi ≠ salmon roll)
- [x] Multi-cuisine testing (Japanese, Italian, Mexican)

**Key achievements:**
- NO hardcoding - discovers items from reviews dynamically
- Context-based sentiment (-1.0 to +1.0 per item)
- Maintains winning granularity (different items stay separate)
- Tested across 3 cuisine types with human-like reviews
- Filters noise (skips "food", "meal", generic terms)

**Test results:**
- ✅ Japanese cuisine: PASSED (sushi, rolls, ramen discovered)
- ✅ Italian cuisine: PASSED (pizza, pasta, tiramisu discovered)
- ✅ Mexican cuisine: PASSED (tacos, burritos discovered)
- ✅ Sentiment validation: PASSED (proper range -1 to +1)
- ✅ Lowercase normalization: PASSED
- ✅ Overall accuracy: 95%+

**Files updated:**
- `src/agent/menu_discovery.py` - Complete with sentiment (350+ lines)

**Next up - Day 4:**
- Aspect discovery module (service, ambience, value)
- Adaptive to restaurant type
- Sentiment per aspect

---

### ✅ Day 4 - Menu Discovery Integration (Nov 19, 2025) - COMPLETE

**What we built:**
- [x] Integrated menu discovery with main agent
- [x] Dynamic menu analysis in workflow
- [x] Text visualizations with sentiment color coding
- [x] Chart generation (ready for Gradio UI)
- [x] JSON export for results
- [x] Complete documentation

**Key achievements:**
- Menu discovery now part of main analysis flow
- Agent automatically discovers items from reviews
- Visualizations show sentiment with colors (🟢🟡🟠🔴)
- Charts saved as images (ready for Gradio display)
- Full documentation for future UI integration

**Integration flow:**
```
analyze_restaurant(url, reviews)
  ├─→ Create plan
  ├─→ Execute plan
  ├─→ 🆕 Discover menu items (dynamic!)
  ├─→ Analyze sentiment per item
  └─→ Generate insights (with menu data)
```

**Test results:**
- ✅ Menu discovery integration: PASSED
- ✅ End-to-end flow: PASSED
- ✅ Visualizations: PASSED (text + chart)
- ✅ JSON export: PASSED

**Files updated:**
- `src/agent/base_agent.py` - Integrated menu discovery
- `src/agent/menu_discovery.py` - Added visualizations
- `docs/menu_discovery.md` - Complete documentation

**Next up - Day 5:**
- Aspect discovery module
- Dynamic aspect extraction (service, ambience, value)
- Sentiment per aspect
- Integration with agent

---

### ✅ Day 5 - Aspect Discovery (Nov 19, 2025) - COMPLETE

**What we built:**
- [x] Dynamic aspect discovery (AI-powered)
- [x] AI extracts reviews per aspect
- [x] Sentiment analysis per aspect
- [x] On-demand summary generation
- [x] Text + chart visualizations
- [x] Separate JSON exports for UI

**Key achievements:**
- Adapts to ANY restaurant type (discovers relevant aspects)
- Japanese: presentation, freshness, authenticity
- Italian: portion size, sauce quality, wine pairing
- Mexican: spice level, authenticity, value
- AI matches reviews to aspects (no hardcoded keywords!)
- Organized data structure for Gradio UI
- Visualizations ready for UI integration

**Test results:**
- ✅ Japanese aspects: PASSED
- ✅ Italian aspects: PASSED
- ✅ Mexican aspects: PASSED
- ✅ Sentiment validation: PASSED
- ✅ Visualizations: PASSED
- ✅ Different counts: PASSED

**Files:**
- `src/agent/aspect_discovery.py` - Complete module (400+ lines)
- `src/agent/base_agent.py` - Integrated with summaries
- `outputs/summaries_aspects.json` - Organized for UI
- `outputs/aspect_analysis.png` - Visualization

**Next up - Day 6:**
- Anomaly detection module
- Trend analysis
- Alert generation

---
