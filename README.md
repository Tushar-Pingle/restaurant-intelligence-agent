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
