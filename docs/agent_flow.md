# Restaurant Intelligence Agent - Planning Flow

## 🌍 UNIVERSAL SYSTEM - Works with ANY Restaurant

**CRITICAL**: This agent is designed to work with **ANY OpenTable restaurant URL** without modification.
- ❌ NOT hardcoded for specific restaurants
- ✅ Discovers menu items dynamically from reviews
- ✅ Discovers relevant aspects dynamically  
- ✅ Adapts to restaurant type automatically (fine dining, casual, fast food, etc.)

**Examples of restaurants this works with:**
- Japanese (Miku) ✅
- Italian (any pasta place) ✅
- American (burgers, steaks) ✅
- Fast food (McDonald's competitor) ✅
- Coffee shops ✅
- ANY restaurant on OpenTable ✅

---

## 🎯 High-Level Overview

This shows how the agent works from start to finish **for ANY restaurant**:
```
┌─────────────────────────────────────────────────────────────┐
│                     USER INPUT                              │
│  Paste ANY OpenTable URL:                                   │
│  • https://opentable.ca/r/ANY-RESTAURANT                    │
│  • Agent doesn't need to know restaurant in advance         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              AGENT PLANNING PHASE                           │
│  • Agent receives the URL (any restaurant)                  │
│  • Agent thinks about what needs to be done                 │
│  • Agent creates a UNIVERSAL step-by-step plan              │
│                                                             │
│  Universal Plan (works for ALL restaurants):                │
│    Step 1: Scrape reviews from URL                         │
│    Step 2: Discover menu items (extracts from reviews)     │
│    Step 3: Discover aspects (learns what matters here)     │
│    Step 4: Analyze sentiment                               │
│    Step 5: Detect any problems                             │
│    Step 6: Generate insights                               │
│    Step 7: Save report to Google Drive                     │
│    Step 8: Send alerts if problems found                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              AGENT EXECUTION PHASE                          │
│  • Agent executes each step                                 │
│  • ADAPTS to whatever it discovers                          │
│  • No assumptions about restaurant type                     │
│                                                             │
│  Example 1 - Japanese Restaurant:                           │
│    ✓ Discovered: sushi, sashimi, tempura                   │
│    ✓ Aspects: presentation, freshness, authenticity        │
│                                                             │
│  Example 2 - Italian Restaurant:                            │
│    ✓ Discovered: pasta, pizza, risotto                     │
│    ✓ Aspects: sauce quality, portion size, authenticity    │
│                                                             │
│  Example 3 - Fast Food:                                     │
│    ✓ Discovered: burgers, fries, shakes                    │
│    ✓ Aspects: speed, value, consistency                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   OUTPUTS (Custom per Restaurant)           │
│  • PDF Report (customized to that restaurant)               │
│  • Slack Alert (if issues detected)                         │
│  • Q&A Interface (ask questions about reviews)              │
│  • Visualizations (based on discovered items/aspects)       │
└─────────────────────────────────────────────────────────────┘
```

## 🧠 How the Agent "Thinks" (Works for ANY Restaurant)

### Step 1: Analyze the Input (Universal)

**Example 1: User provides Japanese restaurant URL**
```
Agent's thoughts:
"I received: https://opentable.ca/r/some-sushi-place
 
 What I know:
 - This is an OpenTable URL
 - I need to analyze customer reviews
 
 What I DON'T know (will discover):
 - Restaurant type (Japanese? Italian? American?)
 - Menu items (sushi? pasta? burgers?)
 - What customers care about (presentation? speed? value?)
 
 My approach:
 1. Get the data first
 2. Let the REVIEWS tell me what matters
 3. Don't assume anything"
```

**Example 2: User provides Italian restaurant URL**
```
Agent's thoughts:
"I received: https://opentable.ca/r/some-italian-place
 
 Same approach - I don't assume:
 - Menu could be pizza, pasta, seafood, or all
 - Customers might care about: sauce, portions, wine, authenticity
 - I'll discover everything from the reviews"
```

**Example 3: User provides fast food URL**
```
Agent's thoughts:
"I received: https://opentable.ca/r/some-burger-chain
 
 Different restaurant type, same approach:
 - Menu likely: burgers, fries, drinks
 - Customers probably care about: speed, value, consistency
 - But I won't assume - I'll discover from reviews"
```

### Step 2: Create Universal Plan

The agent creates THE SAME PLAN for every restaurant:
```python
# This plan works for Japanese, Italian, Mexican, Fast Food, ANY type:

plan = [
    {
        "step": 1,
        "action": "scrape_reviews",
        "params": {"url": user_provided_url},  # ANY URL works
        "reason": "I need review data before I can analyze anything"
    },
    {
        "step": 2,
        "action": "discover_menu_items",
        "params": {"reviews": "scraped_data"},
        "reason": "I don't know what's on the menu - customers will tell me in reviews"
        # Will find: sushi OR pasta OR burgers (whatever is mentioned)
    },
    {
        "step": 3,
        "action": "discover_aspects",
        "params": {"reviews": "scraped_data"},
        "reason": "I need to learn what matters to THIS restaurant's customers"
        # Might find: "presentation" OR "portion size" OR "speed" (depends on restaurant)
    },
    {
        "step": 4,
        "action": "analyze_sentiment",
        "params": {"reviews": "scraped_data"},
        "reason": "Universal - every restaurant needs sentiment analysis"
    },
    # ... remaining steps are also universal
]
```

## 📝 Example: Agent Handles Different Restaurant Types

### Scenario A: Japanese Fine Dining
```
[10:00:00] Received URL: https://opentable.ca/r/sushi-restaurant
[10:00:01] Creating universal analysis plan (8 steps)
[10:00:06] STEP 2 COMPLETE: Discovered menu items
            Found: salmon sushi (89 mentions), miso soup (67 mentions), tempura (45 mentions)
[10:00:50] STEP 3 COMPLETE: Discovered aspects customers care about
            Aspects: presentation, freshness, authenticity, service attentiveness
[10:01:30] Agent adapted to: Fine dining Japanese restaurant
```

### Scenario B: Italian Casual Dining
```
[10:00:00] Received URL: https://opentable.ca/r/italian-bistro
[10:00:01] Creating universal analysis plan (8 steps)
[10:00:06] STEP 2 COMPLETE: Discovered menu items
            Found: carbonara (112 mentions), margherita pizza (89 mentions), tiramisu (56 mentions)
[10:00:50] STEP 3 COMPLETE: Discovered aspects customers care about
            Aspects: sauce quality, portion size, value for money, wine selection
[10:01:30] Agent adapted to: Casual Italian restaurant
```

### Scenario C: Fast Casual (Burgers)
```
[10:00:00] Received URL: https://opentable.ca/r/burger-joint
[10:00:01] Creating universal analysis plan (8 steps)
[10:00:06] STEP 2 COMPLETE: Discovered menu items
            Found: cheeseburger (156 mentions), fries (134 mentions), milkshake (67 mentions)
[10:00:50] STEP 3 COMPLETE: Discovered aspects customers care about
            Aspects: speed of service, value, consistency, cleanliness
[10:01:30] Agent adapted to: Fast casual burger restaurant
```

## 🔄 Why This Is TRULY Universal

### ❌ Bad Approach (What we're NOT doing):
```python
# Hardcoded - only works for one restaurant
menu_items = ["salmon roll", "tuna sashimi", "miso soup"]  # Japanese only!
aspects = ["food quality", "service", "ambience"]  # Generic, misses specifics

# This breaks when you analyze an Italian or Mexican restaurant
```

### ✅ Our Approach (What we ARE doing):
```python
# Dynamic - works for ANY restaurant
menu_items = discover_from_reviews(reviews)  # Finds whatever customers mention
aspects = discover_from_reviews(reviews)     # Learns what matters HERE

# Examples of what it discovers:
# Japanese: menu_items = ["sushi", "sashimi"], aspects = ["freshness", "presentation"]
# Italian:  menu_items = ["pasta", "pizza"],   aspects = ["sauce", "portions"]
# Mexican:  menu_items = ["tacos", "burritos"], aspects = ["spice level", "authenticity"]
```

## 🎯 Key Principles (Universal Design)

1. **NEVER assume restaurant type** - Let reviews tell us
2. **NEVER hardcode menu items** - Discover from customer mentions
3. **NEVER use generic aspects** - Learn what THIS restaurant's customers care about
4. **ALWAYS adapt** - Japanese needs different analysis than fast food
5. **ONE codebase** - Same code handles ALL restaurant types