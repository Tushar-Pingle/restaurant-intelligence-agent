# Gradio 6 Implementation Guide
## Restaurant Intelligence Agent UI

**Date:** November 24, 2025 (Day 15)  
**Hackathon:** Anthropic MCP 1st Birthday - Track 2 (Productivity)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Architecture](#architecture)
4. [Implementation Steps](#implementation-steps)
5. [Key Components](#key-components)
6. [Challenges & Solutions](#challenges--solutions)
7. [Testing](#testing)
8. [Next Steps](#next-steps)

---

## 🎯 Overview

Built a production-ready Gradio 6 web interface for the Restaurant Intelligence Agent that:
- Accepts OpenTable URLs for analysis
- Displays role-based insights (Chef vs Manager)
- Enables Q&A over customer reviews
- Provides interactive drill-down functionality

**Technology Stack:**
- **Framework:** Gradio 6.0.0
- **Backend:** Python 3.12
- **AI:** Claude Sonnet 4 (via Anthropic API)
- **Scraper:** Selenium + BeautifulSoup
- **Analysis:** Custom NLP pipeline

---

## 📦 Installation

### **Step 1: Install Gradio 6**

```bash
pip install gradio==6.0.0
```

### **Step 2: Verify Installation**

```python
import gradio as gr
print(gr.__version__)  # Should show 6.0.0
```

### **Step 3: Install Project Dependencies**

```bash
pip install anthropic selenium beautifulsoup4 pandas python-dotenv fastmcp
```

---

## 🏗️ Architecture

### **File Structure**

```
src/
├── ui/
│   ├── __init__.py
│   └── gradio_app.py          # Main Gradio interface
├── scrapers/
│   └── opentable_scraper.py   # Web scraping
├── data_processing/
│   └── review_cleaner.py      # Text preprocessing
├── agent/
│   ├── base_agent.py          # Core analysis agent
│   ├── unified_analyzer.py    # Menu/aspect analysis
│   └── insights_generator.py  # Chef/Manager insights
└── mcp_integrations/
    ├── generate_chart.py      # Visualizations
    └── query_reviews.py       # Q&A system (RAG)
```

### **Data Flow**

```
User Input (URL + Review Count)
        ↓
[Gradio Interface]
        ↓
[OpenTable Scraper] → Raw HTML
        ↓
[Review Processor] → Cleaned Text
        ↓
[AI Agent] → Unified Analysis
        ↓
[Insights Generator] → Chef + Manager Insights
        ↓
[Visualization Generator] → Charts
        ↓
[Gradio Display] → Interactive Results
        ↓
[Q&A System] ← User Questions
```

---

## 🛠️ Implementation Steps

### **Step 1: Create UI Directory Structure**

```bash
mkdir -p src/ui
touch src/ui/__init__.py
touch src/ui/gradio_app.py
```

### **Step 2: Build Basic Gradio Interface**

**Key Gradio 6 Change:** Theme moved from `Blocks()` to `.launch()`

```python
import gradio as gr

# ❌ OLD (Gradio 5)
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    pass

# ✅ NEW (Gradio 6)
with gr.Blocks() as demo:
    pass

demo.launch(theme=gr.themes.Soft())
```

### **Step 3: Design Layout**

**Three-Tab Design:**
1. **Chef Insights** - Menu performance, food quality
2. **Manager Insights** - Service, operations, ambience
3. **Ask Questions** - RAG-powered Q&A

**Components Used:**
- `gr.Textbox()` - URL input, progress display
- `gr.Dropdown()` - Review count selection, drill-down menus
- `gr.Button()` - Analyze, Ask buttons
- `gr.Image()` - Charts display
- `gr.Markdown()` - Formatted insights
- `gr.State()` - Context persistence (critical!)
- `gr.Tabs()` + `gr.Tab()` - Tabbed navigation

### **Step 4: Implement Progress Tracking**

Used `gr.Progress()` with `yield` for real-time updates:

```python
def analyze_restaurant_interface(url, review_count, progress=gr.Progress()):
    # Phase 1: Scraping
    progress(0.1, desc="📥 Scraping reviews...")
    yield (..., "📥 Scraping reviews...", ...)
    
    # Phase 2: Processing
    progress(0.3, desc="⚙️ Processing data...")
    yield (..., "⚙️ Processing data...", ...)
    
    # Phase 3: Analysis
    progress(0.8, desc="🤖 Running AI analysis...")
    yield (..., "🤖 Running AI analysis...", ...)
    
    # Final
    progress(1.0, desc="✅ Complete!")
    yield (..., "✅ Complete!", ...)
```

### **Step 5: Connect Backend**

**Imports:**
```python
from src.scrapers.opentable_scraper import scrape_opentable
from src.data_processing import process_reviews, clean_reviews_for_ai
from src.agent.base_agent import RestaurantAnalysisAgent
from src.mcp_integrations.query_reviews import query_reviews_direct
```

**Integration:**
```python
# Scrape
result = scrape_opentable(url=url, max_reviews=review_count, headless=True)

# Process
df = process_reviews(result)
reviews = clean_reviews_for_ai(df['review_text'].tolist())

# Analyze
agent = RestaurantAnalysisAgent()
analysis = agent.analyze_restaurant(url, restaurant_name, reviews)

# Display
chef_insights = analysis['insights']['chef']
manager_insights = analysis['insights']['manager']
```

### **Step 6: Implement Drill-Down Functionality**

**Dynamic Dropdowns:**
```python
# Populate dropdowns after analysis
chef_dropdown_choices = [item['name'] for item in menu_items]
manager_dropdown_choices = [aspect['name'] for aspect in aspects]

# Connect change events
chef_dropdown.change(
    fn=get_menu_item_summary,
    inputs=chef_dropdown,
    outputs=chef_summary
)
```

**Detail Functions:**
```python
def get_menu_item_summary(item_name: str) -> str:
    # Load menu_analysis.json
    # Find selected item
    # Return formatted summary with sentiment, mentions, reviews
    pass
```

### **Step 7: Build Q&A System**

**Architecture:**
1. Index reviews after analysis
2. Store in memory dictionary (keyed by restaurant name)
3. Use keyword search to find relevant reviews
4. Send top 50 to Claude for answer

**Key Code:**
```python
# In query_reviews.py
def find_relevant_reviews(reviews, question, max_reviews=50):
    # Extract keywords from question
    keywords = [k for k in question.lower().split() if k not in stop_words]
    
    # Score reviews by keyword matches
    scored = [(sum(1 for k in keywords if k in r.lower()), r) for r in reviews]
    scored.sort(reverse=True)
    
    # Return top matches
    return [r for score, r in scored[:max_reviews]]
```

**Context Persistence (Critical!):**
```python
# ❌ WRONG - Context lost between interactions
restaurant_context = gr.Textbox(visible=False)

# ✅ CORRECT - Context persists
restaurant_context = gr.State("")
```

---

## 🔑 Key Components

### **1. Main Interface (`create_interface()`)**

**Features:**
- Clean, professional design
- Mobile-responsive layout
- Real-time progress updates
- Error handling

**Code Structure:**
```python
def create_interface():
    with gr.Blocks(title="Restaurant Intelligence Agent") as demo:
        # Header
        gr.Markdown("# 🍽️ Restaurant Intelligence Agent")
        
        # Input Section
        with gr.Row():
            url_input = gr.Textbox(...)
            review_count = gr.Dropdown(...)
            analyze_btn = gr.Button(...)
        
        # Progress
        progress_box = gr.Textbox(...)
        
        # Hidden state
        restaurant_context = gr.State("")
        
        # Results Tabs
        with gr.Tabs():
            with gr.Tab("🍳 Chef Insights"):
                ...
            with gr.Tab("👔 Manager Insights"):
                ...
            with gr.Tab("💬 Ask Questions"):
                ...
        
        # Event handlers
        analyze_btn.click(fn=analyze_restaurant_interface, ...)
        
    return demo
```

### **2. Analysis Function (`analyze_restaurant_interface()`)**

**Generator Pattern for Progress:**
```python
def analyze_restaurant_interface(url, review_count, progress=gr.Progress()):
    try:
        # Validate input
        if not url or "opentable" not in url.lower():
            return error_output
        
        # Phase 1: Scrape
        progress(0.1, desc="Scraping...")
        yield intermediate_output
        result = scrape_opentable(...)
        
        # Phase 2: Process
        progress(0.3, desc="Processing...")
        yield intermediate_output
        reviews = process_reviews(result)
        
        # Phase 3: Analyze
        progress(0.5, desc="Analyzing...")
        yield intermediate_output
        analysis = agent.analyze_restaurant(...)
        
        # Phase 4: Format & Display
        progress(1.0, desc="Complete!")
        yield final_output
        
    except Exception as e:
        yield error_output
```

### **3. Insight Formatting (`clean_insight_text()`)**

**Problem:** Claude returns insights in various formats:
- Plain text
- Lists: `["item1", "item2"]`
- Dicts: `[{"priority": "high", "action": "..."}]`
- Mixed with quotes and brackets

**Solution:** Universal text cleaner

```python
def clean_insight_text(text):
    if isinstance(text, list):
        # Handle list of dicts (recommendations)
        if text and isinstance(text[0], dict):
            return '\n\n'.join(f"• {item['action']}" for item in text)
        # Handle simple list
        return '\n\n'.join(f"• {item}" for item in text)
    
    elif isinstance(text, str):
        # Parse string representations
        if text.startswith('[{'):
            parsed = ast.literal_eval(text)
            return format_list(parsed)
        
        if text.startswith('['):
            parsed = ast.literal_eval(text)
            return '\n\n'.join(f"• {item}" for item in parsed)
        
        # Clean quotes
        return text.strip('"\'[]')
    
    return str(text)
```

### **4. Q&A System (`query_reviews.py`)**

**Features:**
- Keyword-based relevance scoring
- Searches all indexed reviews
- Returns top 50 most relevant
- Context-aware answers

**Key Functions:**

```python
# Index reviews after analysis
def index_reviews_direct(restaurant_name, reviews):
    REVIEW_INDEX[restaurant_name.lower()] = reviews
    return f"Indexed {len(reviews)} reviews"

# Find relevant reviews
def find_relevant_reviews(reviews, question, max_reviews=50):
    keywords = extract_keywords(question)
    scored = score_by_keywords(reviews, keywords)
    return top_n(scored, max_reviews)

# Answer question
def query_reviews_direct(restaurant_name, question):
    reviews = REVIEW_INDEX.get(restaurant_name.lower())
    relevant = find_relevant_reviews(reviews, question)
    return ask_claude(relevant, question)
```

---

## 🐛 Challenges & Solutions

### **Challenge 1: Gradio 6 Breaking Changes**

**Problem:** `theme=` parameter in `Blocks()` causes error
```
TypeError: BlockContext.__init__() got an unexpected keyword argument 'theme'
```

**Solution:** Move theme to `.launch()`
```python
# Before
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    pass
demo.launch()

# After
with gr.Blocks() as demo:
    pass
demo.launch(theme=gr.themes.Soft())
```

### **Challenge 2: Insights Formatting Issues**

**Problem:** Raw JSON in display
```
["Strength 1", "Strength 2"]
[{'priority': 'high', 'action': '...'}]
```

**Solution:** Created `clean_insight_text()` function
- Handles lists, dicts, strings
- Extracts 'action' from recommendation dicts
- Converts to bullet points
- Removes brackets/quotes

### **Challenge 3: Manager Insights Rate Limit**

**Problem:** API rate limit (30K tokens/min) hit when generating insights
```
Error 429: rate_limit_error
```

**Solution:** Added 15s delay between chef and manager insights
```python
# In base_agent.py
chef_insights = generate_insights(role='chef')
time.sleep(15)  # Wait to avoid rate limit
manager_insights = generate_insights(role='manager')
```

### **Challenge 4: Q&A Context Not Persisting**

**Problem:** Restaurant context arrives as empty string `''`
```python
DEBUG: restaurant_context = ''
```

**Solution:** Use `gr.State()` instead of hidden `gr.Textbox()`
```python
# Before
restaurant_context = gr.Textbox(visible=False)

# After
restaurant_context = gr.State("")
```

**Why:** `gr.State()` is designed for persisting values between interactions, while hidden textboxes can lose state.

### **Challenge 5: Poor Q&A Quality**

**Problem:** Q&A using only first 10 reviews, missing relevant content
```
"Reviews don't mention Brussels sprouts" (but they do!)
```

**Solution:** 
1. Increased to 50 reviews
2. Added keyword-based filtering
3. Improved Claude prompt

**Result:** Now finds relevant reviews from entire dataset

---

## 🧪 Testing

### **Test 1: Basic Functionality (20 reviews)**
- ✅ Scraping works
- ✅ Analysis completes
- ✅ Insights display
- ✅ Charts generate
- ✅ Q&A works

### **Test 2: Rate Limits (100 reviews)**
- ✅ Manager insights generate (with 15s delay)
- ✅ No rate limit errors
- ⏱️ Total time: ~5-6 minutes

### **Test 3: Q&A Quality**
- ✅ Keyword search finds relevant reviews
- ✅ Answers cite specific review numbers
- ✅ Handles topics not in reviews gracefully

### **Test 4: Edge Cases**
- ✅ Invalid URL → Clear error message
- ✅ Empty reviews → Fallback message
- ✅ No context → "Analyze restaurant first" message

---

## 📊 Performance Metrics

| Reviews | Scraping | Analysis | Insights | Total | Cost |
|---------|----------|----------|----------|-------|------|
| 20      | 30s      | 1m       | 30s      | 2m    | $0.20 |
| 100     | 2m       | 3m       | 1m       | 6m    | $1.20 |
| 500     | 8m       | 12m      | 2m       | 22m*  | $5.00* |

*Estimated based on scaling

---

## 🎨 UI/UX Design Decisions

### **1. Three-Tab Layout**
**Why:** Separates concerns by user role
- Chef tab → Food/menu focused
- Manager tab → Operations focused
- Q&A tab → Ad-hoc questions

### **2. Drill-Down Dropdowns**
**Why:** Reduces cognitive load
- Overview first (charts + summaries)
- Details on demand (select item)

### **3. Progress Indicators**
**Why:** Long-running operations (5-20 minutes)
- Real-time updates every 30 seconds
- Phase descriptions (Scraping → Processing → Analyzing)
- Prevents user from thinking app is frozen

### **4. Error Handling**
**Why:** Graceful degradation
- Clear error messages
- Fallback insights if generation fails
- Validation before expensive operations

---

## 🚀 Next Steps

### **Immediate (Day 16)**
1. Deploy backend to Modal
2. Create Modal API endpoints
3. Update Gradio to call Modal instead of local functions

### **Day 17**
1. Create HuggingFace Space
2. Deploy Gradio UI to HF Space
3. Connect UI to Modal backend
4. Add API key as HF Secret

### **Day 18-19**
1. Create demo video (1-5 mins)
2. Polish README
3. Social media post
4. Final testing
5. Submit before Nov 30, 11:59 PM UTC

---

## 📝 Code Summary

### **Files Created/Modified (Day 15)**

1. **src/ui/gradio_app.py** (NEW - 620 lines)
   - Main Gradio interface
   - Progress tracking
   - Event handlers
   - Insight formatting

2. **src/mcp_integrations/query_reviews.py** (UPDATED)
   - Added keyword-based search
   - Increased max_reviews to 50
   - Better prompts for Claude

3. **src/agent/base_agent.py** (UPDATED)
   - Added 15s delay between insights
   - Fixed state clearing

4. **src/agent/insights_generator.py** (UPDATED)
   - Better error handling
   - Improved prompts

5. **src/data_processing/review_cleaner.py** (CREATED)
   - Text sanitization
   - Token reduction

---

## 🎓 Key Learnings

### **Gradio 6 Best Practices**

1. **Use `gr.State()` for persistence**, not hidden textboxes
2. **Move theme to `.launch()`**, not `Blocks()`
3. **Use generators with `yield`** for progress updates
4. **Wrap long operations** in try-except with user-friendly errors
5. **Test with `share=False`** locally before deploying

### **AI Agent Integration**

1. **Add delays between API calls** to avoid rate limits
2. **Handle variable response formats** from LLMs
3. **Provide fallback responses** when generation fails
4. **Log extensively** for debugging
5. **Validate responses** before displaying

### **Q&A System Design**

1. **Simple keyword search** often beats complex embeddings for small datasets
2. **Normalize inputs** (lowercase, strip) to avoid mismatches
3. **Show what's available** when context missing
4. **Cite sources** in answers for credibility
5. **Filter first, then send to LLM** to reduce tokens

---

## 📚 References

- [Gradio 6 Documentation](https://www.gradio.app/docs)
- [Gradio 6 Migration Guide](https://www.gradio.app/main/guides/gradio-6-migration-guide)
- [Anthropic API Docs](https://docs.anthropic.com/)
- [MCP 1st Birthday Hackathon](https://huggingface.co/MCP-1st-Birthday)

---

## ✅ Day 15 Completion Checklist

- [x] Install Gradio 6
- [x] Create UI directory structure
- [x] Build basic interface
- [x] Implement progress tracking
- [x] Connect backend (scraper, agent, insights)
- [x] Add drill-down functionality
- [x] Build Q&A system with RAG
- [x] Fix insights formatting
- [x] Fix rate limit issues
- [x] Fix Q&A context persistence
- [x] Improve Q&A quality (keyword search)
- [x] Test with 20 reviews ✅
- [x] Test with 100 reviews ✅
- [x] Document implementation ✅

---

**Status:** ✅ Day 15 Complete!  
**Next:** Day 16 - Modal Backend Deployment

---

*Generated: November 24, 2025*  
*Project: Restaurant Intelligence Agent*  
*Hackathon: Anthropic MCP 1st Birthday - Track 2*