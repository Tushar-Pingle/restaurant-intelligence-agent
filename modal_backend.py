# ============================================================
# CHANGELOG - modal_backend.py
# ============================================================
# Issue ID | Change Description                              | Lines Affected
# ------------------------------------------------------------
# INIT-02  | SKIPPED - version pinning causes availability issues, kept original
# INIT-04  | Added memory config to Modal functions          | Lines ~75, ~95, ~140, ~180
# FMT-01   | Simplified format detection (both NESTED now)   | Lines ~250-290
# PROC-01  | Unified nested format handling                  | Lines ~250-290
# PROC-05  | Added logging when rating estimated from sentiment | Lines ~330-335
# API-01   | Added API key check with clear error message    | Lines ~200-210
# API-06   | Increased timeouts (600→900 for main, 900→1200 for API) | Lines ~140, ~180, ~420
# INS-02   | Centralized SENTIMENT_THRESHOLD constant (0.6)  | Lines ~45-50, used throughout
# INS-03   | Better name matching for summaries (strip, lower, title) | Lines ~380-410
# INS-04   | Increased summary items (15→20 food, 10→15 drinks, 15→20 aspects) | Lines ~350-360
# INS-05   | Append related_reviews during merge (not overwrite) | Lines ~300-320
# ============================================================
# MULTI-KEY VERSION: Uses 5 different API keys to avoid rate limits
# - anthropic-batch1: Odd batch processing (1, 3, 5, ...)
# - anthropic-batch2: Even batch processing (2, 4, 6, ...)
# - anthropic-chef: Chef insights generation
# - anthropic-manager: Manager insights generation
# - anthropic-summaries: Summary generation
# ============================================================

"""
New Modal Backend for Restaurant Intelligence Agent - PARALLEL OPTIMIZED
Version 3.1-MULTIKEY - With fixes from issue registry + Multi-API key support

KEY OPTIMIZATIONS:
1. Parallel batch processing with .map() - Process all batches simultaneously
2. Parallel insights generation - Chef + Manager at same time
3. Larger batch sizes (30 reviews instead of 20)
4. Reduced timeout since parallel is faster
5. MULTI-KEY: Different API keys for different tasks to avoid rate limits

TARGET: 1000 reviews in ~5 minutes (down from 15+ minutes)

FIXED: 
- Proper handling of both OpenTable and Google Maps scraper response formats
- Both scrapers now return NESTED format for consistency
"""

import modal
from typing import Dict, Any, List
import os
import json
import re

# Create Modal app
app = modal.App("restaurant-intelligence")

# ============================================================================
# [INS-02] CENTRALIZED CONSTANTS
# ============================================================================
SENTIMENT_THRESHOLD_POSITIVE = 0.6  # >= 0.6 is positive
SENTIMENT_THRESHOLD_NEGATIVE = 0.0  # < 0 is negative, 0-0.59 is neutral

# [INS-04] Increased summary counts
SUMMARY_FOOD_COUNT = 20      # Was 15
SUMMARY_DRINKS_COUNT = 15    # Was 10
SUMMARY_ASPECTS_COUNT = 20   # Was 15

# ============================================================================
# Base image with all dependencies
# ============================================================================
image = (
    modal.Image.debian_slim(python_version="3.12")
    # Keep original - don't pin versions (causes availability issues)
    .apt_install("chromium", "chromium-driver")
    .run_commands("ln -sf /usr/bin/chromedriver /usr/local/bin/chromedriver")
    .run_commands("ln -sf /usr/bin/chromium /usr/local/bin/chromium")
    .pip_install(
        "anthropic",
        "selenium", 
        "beautifulsoup4",
        "pandas",
        "python-dotenv",
        "matplotlib",
        "fastapi[standard]",
        "httpx",
        "fastmcp",
    )
    .add_local_python_source("src")
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_sentiment(text: str) -> float:
    """
    Simple sentiment calculation from review text.
    Returns value from -1 (very negative) to +1 (very positive).
    """
    if not text:
        return 0.0
    text = str(text).lower()
    
    positive = ['amazing', 'excellent', 'fantastic', 'great', 'awesome', 'delicious', 
                'perfect', 'outstanding', 'loved', 'beautiful', 'fresh', 'friendly', 
                'best', 'wonderful', 'incredible', 'superb', 'exceptional', 'good',
                'nice', 'tasty', 'recommend', 'enjoy', 'impressed', 'favorite']
    negative = ['terrible', 'horrible', 'awful', 'bad', 'worst', 'disappointing', 
                'poor', 'overpriced', 'slow', 'rude', 'cold', 'bland', 'mediocre',
                'disgusting', 'inedible', 'undercooked', 'overcooked']
    
    pos = sum(1 for w in positive if w in text)
    neg = sum(1 for w in negative if w in text)
    
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / max(pos + neg, 1)


# ============================================================================
# BATCH PROCESSOR - ODD BATCHES (uses anthropic-batch1 key)
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-batch1")],
    timeout=210,
    retries=3,
    memory=512,  # [INIT-04] Added memory config
)
def process_batch_odd(batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process ODD-numbered batches (1, 3, 5, ...) - uses anthropic-batch1 key.
    Runs in PARALLEL across containers!
    """
    from anthropic import Anthropic
    import os
    
    # [API-01] Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment!")
        return {"success": False, "batch_index": batch_data.get("batch_index", 0), 
                "error": "API key not configured", "data": {"food_items": [], "drinks": [], "aspects": []}}
    
    reviews = batch_data["reviews"]
    restaurant_name = batch_data["restaurant_name"]
    batch_index = batch_data["batch_index"]
    start_index = batch_data["start_index"]
    
    print(f"🔄 [BATCH1-KEY] Processing batch {batch_index} ({len(reviews)} reviews)...")
    
    client = Anthropic(api_key=api_key)
    
    # Build extraction prompt
    numbered_reviews = []
    for i, review in enumerate(reviews):
        numbered_reviews.append(f"[Review {i}]: {review}")
    reviews_text = "\n\n".join(numbered_reviews)
    
    # [INS-02] Use centralized threshold in prompt
    prompt = f"""You are analyzing customer reviews for {restaurant_name}. Extract BOTH menu items AND aspects in ONE PASS.

REVIEWS:
{reviews_text}

YOUR TASK - Extract THREE things simultaneously:
1. **MENU ITEMS** (food & drinks mentioned)
2. **ASPECTS** (what customers care about: service, ambience, etc.)
3. **SENTIMENT** for each

SENTIMENT SCALE (IMPORTANT):
- **Positive ({SENTIMENT_THRESHOLD_POSITIVE} to 1.0):** Customer clearly enjoyed/praised this item or aspect
- **Neutral ({SENTIMENT_THRESHOLD_NEGATIVE} to {SENTIMENT_THRESHOLD_POSITIVE - 0.01}):** Mixed feelings, okay but not exceptional
- **Negative (-1.0 to {SENTIMENT_THRESHOLD_NEGATIVE - 0.01}):** Customer complained, criticized, or expressed disappointment

RULES:
- Specific items only: "salmon sushi", "miso soup", "sake"
- Separate food from drinks
- Lowercase names
- For EACH item/aspect, list which review NUMBERS mention it

OUTPUT (JSON):
{{
  "food_items": [
    {{"name": "item name", "mention_count": 2, "sentiment": 0.85, "category": "type", "related_reviews": [0, 5]}}
  ],
  "drinks": [
    {{"name": "drink name", "mention_count": 1, "sentiment": 0.7, "category": "alcohol", "related_reviews": [3]}}
  ],
  "aspects": [
    {{"name": "service speed", "mention_count": 3, "sentiment": 0.65, "description": "brief desc", "related_reviews": [1, 2, 7]}}
  ]
}}

CRITICAL: Output ONLY valid JSON, no other text.
Use sentiment scale: >= {SENTIMENT_THRESHOLD_POSITIVE} positive, {SENTIMENT_THRESHOLD_NEGATIVE}-{SENTIMENT_THRESHOLD_POSITIVE - 0.01} neutral, < {SENTIMENT_THRESHOLD_NEGATIVE} negative

Extract everything:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        data = json.loads(result_text)
        
        # Map review indices back to full text
        for item in data.get('food_items', []):
            indices = item.get('related_reviews', [])
            item['related_reviews'] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(reviews):
                    item['related_reviews'].append({
                        'review_index': start_index + idx,
                        'review_text': reviews[idx]
                    })
            if 'name' in item:
                item['name'] = item['name'].lower().strip()  # [INS-03] Added strip()
        
        for item in data.get('drinks', []):
            indices = item.get('related_reviews', [])
            item['related_reviews'] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(reviews):
                    item['related_reviews'].append({
                        'review_index': start_index + idx,
                        'review_text': reviews[idx]
                    })
            if 'name' in item:
                item['name'] = item['name'].lower().strip()  # [INS-03] Added strip()
        
        for aspect in data.get('aspects', []):
            indices = aspect.get('related_reviews', [])
            aspect['related_reviews'] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(reviews):
                    aspect['related_reviews'].append({
                        'review_index': start_index + idx,
                        'review_text': reviews[idx]
                    })
            if 'name' in aspect:
                aspect['name'] = aspect['name'].lower().strip()  # [INS-03] Added strip()
        
        print(f"✅ Batch {batch_index} complete: {len(data.get('food_items', []))} food, {len(data.get('drinks', []))} drinks, {len(data.get('aspects', []))} aspects")
        return {"success": True, "batch_index": batch_index, "data": data}
        
    except json.JSONDecodeError as e:
        print(f"⚠️ Batch {batch_index} JSON error: {e}")
        return {"success": False, "batch_index": batch_index, "data": {"food_items": [], "drinks": [], "aspects": []}}
    except Exception as e:
        print(f"❌ Batch {batch_index} error: {e}")
        return {"success": False, "batch_index": batch_index, "data": {"food_items": [], "drinks": [], "aspects": []}}


# ============================================================================
# BATCH PROCESSOR - EVEN BATCHES (uses anthropic-batch2 key)
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-batch2")],
    timeout=210,
    retries=3,
    memory=512,  # [INIT-04] Added memory config
)
def process_batch_even(batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process EVEN-numbered batches (2, 4, 6, ...) - uses anthropic-batch2 key.
    Runs in PARALLEL across containers!
    """
    from anthropic import Anthropic
    import os
    
    # [API-01] Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment!")
        return {"success": False, "batch_index": batch_data.get("batch_index", 0), 
                "error": "API key not configured", "data": {"food_items": [], "drinks": [], "aspects": []}}
    
    reviews = batch_data["reviews"]
    restaurant_name = batch_data["restaurant_name"]
    batch_index = batch_data["batch_index"]
    start_index = batch_data["start_index"]
    
    print(f"🔄 [BATCH2-KEY] Processing batch {batch_index} ({len(reviews)} reviews)...")
    
    client = Anthropic(api_key=api_key)
    
    # Build extraction prompt
    numbered_reviews = []
    for i, review in enumerate(reviews):
        numbered_reviews.append(f"[Review {i}]: {review}")
    reviews_text = "\n\n".join(numbered_reviews)
    
    # [INS-02] Use centralized threshold in prompt
    prompt = f"""You are analyzing customer reviews for {restaurant_name}. Extract BOTH menu items AND aspects in ONE PASS.

REVIEWS:
{reviews_text}

YOUR TASK - Extract THREE things simultaneously:
1. **MENU ITEMS** (food & drinks mentioned)
2. **ASPECTS** (what customers care about: service, ambience, etc.)
3. **SENTIMENT** for each

SENTIMENT SCALE (IMPORTANT):
- **Positive ({SENTIMENT_THRESHOLD_POSITIVE} to 1.0):** Customer clearly enjoyed/praised this item or aspect
- **Neutral ({SENTIMENT_THRESHOLD_NEGATIVE} to {SENTIMENT_THRESHOLD_POSITIVE - 0.01}):** Mixed feelings, okay but not exceptional
- **Negative (-1.0 to {SENTIMENT_THRESHOLD_NEGATIVE - 0.01}):** Customer complained, criticized, or expressed disappointment

RULES:
- Specific items only: "salmon sushi", "miso soup", "sake"
- Separate food from drinks
- Lowercase names
- For EACH item/aspect, list which review NUMBERS mention it

OUTPUT (JSON):
{{
  "food_items": [
    {{"name": "item name", "mention_count": 2, "sentiment": 0.85, "category": "type", "related_reviews": [0, 5]}}
  ],
  "drinks": [
    {{"name": "drink name", "mention_count": 1, "sentiment": 0.7, "category": "alcohol", "related_reviews": [3]}}
  ],
  "aspects": [
    {{"name": "service speed", "mention_count": 3, "sentiment": 0.65, "description": "brief desc", "related_reviews": [1, 2, 7]}}
  ]
}}

CRITICAL: Output ONLY valid JSON, no other text.
Use sentiment scale: >= {SENTIMENT_THRESHOLD_POSITIVE} positive, {SENTIMENT_THRESHOLD_NEGATIVE}-{SENTIMENT_THRESHOLD_POSITIVE - 0.01} neutral, < {SENTIMENT_THRESHOLD_NEGATIVE} negative

Extract everything:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        data = json.loads(result_text)
        
        # Map review indices back to full text
        for item in data.get('food_items', []):
            indices = item.get('related_reviews', [])
            item['related_reviews'] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(reviews):
                    item['related_reviews'].append({
                        'review_index': start_index + idx,
                        'review_text': reviews[idx]
                    })
            if 'name' in item:
                item['name'] = item['name'].lower().strip()  # [INS-03] Added strip()
        
        for item in data.get('drinks', []):
            indices = item.get('related_reviews', [])
            item['related_reviews'] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(reviews):
                    item['related_reviews'].append({
                        'review_index': start_index + idx,
                        'review_text': reviews[idx]
                    })
            if 'name' in item:
                item['name'] = item['name'].lower().strip()  # [INS-03] Added strip()
        
        for aspect in data.get('aspects', []):
            indices = aspect.get('related_reviews', [])
            aspect['related_reviews'] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(reviews):
                    aspect['related_reviews'].append({
                        'review_index': start_index + idx,
                        'review_text': reviews[idx]
                    })
            if 'name' in aspect:
                aspect['name'] = aspect['name'].lower().strip()  # [INS-03] Added strip()
        
        print(f"✅ Batch {batch_index} complete: {len(data.get('food_items', []))} food, {len(data.get('drinks', []))} drinks, {len(data.get('aspects', []))} aspects")
        return {"success": True, "batch_index": batch_index, "data": data}
        
    except json.JSONDecodeError as e:
        print(f"⚠️ Batch {batch_index} JSON error: {e}")
        return {"success": False, "batch_index": batch_index, "data": {"food_items": [], "drinks": [], "aspects": []}}
    except Exception as e:
        print(f"❌ Batch {batch_index} error: {e}")
        return {"success": False, "batch_index": batch_index, "data": {"food_items": [], "drinks": [], "aspects": []}}


# ============================================================================
# CHEF INSIGHTS (uses anthropic-chef key)
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-chef")],
    timeout=210,
    retries=3,
    memory=512,  # [INIT-04] Added memory config
)
def generate_chef_insights(analysis_data: Dict[str, Any], restaurant_name: str) -> Dict[str, Any]:
    """Generate CHEF insights - uses anthropic-chef key."""
    from anthropic import Anthropic
    import os
    import time as time_module
    
    role = "chef"
    print(f"🧠 [CHEF-KEY] Generating {role} insights...")
    
    # [API-01] Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"❌ ANTHROPIC_API_KEY not found for {role} insights!")
        return {"role": role, "insights": _fallback_insights(role)}
    
    client = Anthropic(api_key=api_key)
    
    menu_items = analysis_data.get('menu_analysis', {}).get('food_items', [])[:20]
    drinks = analysis_data.get('menu_analysis', {}).get('drinks', [])[:10]
    aspects = analysis_data.get('aspect_analysis', {}).get('aspects', [])[:20]
    
    # [INS-02] Use centralized threshold for formatting
    menu_lines = ["TOP MENU ITEMS:"]
    for item in menu_items:
        s = item.get('sentiment', 0)
        indicator = "[+]" if s >= SENTIMENT_THRESHOLD_POSITIVE else "[~]" if s >= SENTIMENT_THRESHOLD_NEGATIVE else "[-]"
        menu_lines.append(f"  {indicator} {item.get('name', '?')}: sentiment {s:+.2f}, {item.get('mention_count', 0)} mentions")
    menu_summary = "\n".join(menu_lines)
    
    aspect_lines = ["TOP ASPECTS:"]
    for a in aspects:
        s = a.get('sentiment', 0)
        indicator = "[+]" if s >= SENTIMENT_THRESHOLD_POSITIVE else "[~]" if s >= SENTIMENT_THRESHOLD_NEGATIVE else "[-]"
        aspect_lines.append(f"  {indicator} {a.get('name', '?')}: sentiment {s:+.2f}, {a.get('mention_count', 0)} mentions")
    aspect_summary = "\n".join(aspect_lines)
    
    focus = "Focus on: Food quality, menu items, ingredients, presentation, portions, consistency"
    topic_filter = "ONLY on food/kitchen topics"
    
    # [INS-02] Use centralized threshold in prompt
    prompt = f"""You are an expert restaurant consultant analyzing feedback for {restaurant_name}.

{menu_summary}

{aspect_summary}

SENTIMENT SCALE:
- POSITIVE (>= {SENTIMENT_THRESHOLD_POSITIVE}): Highlight as STRENGTH
- NEUTRAL ({SENTIMENT_THRESHOLD_NEGATIVE} to {SENTIMENT_THRESHOLD_POSITIVE - 0.01}): Room for improvement
- NEGATIVE (< {SENTIMENT_THRESHOLD_NEGATIVE}): Flag as CONCERN

YOUR TASK: Generate insights for the HEAD CHEF.
{focus}

RULES:
1. Focus {topic_filter}
2. STRENGTHS from items with sentiment >= {SENTIMENT_THRESHOLD_POSITIVE}
3. CONCERNS from items with sentiment < {SENTIMENT_THRESHOLD_NEGATIVE}
4. Output ONLY valid JSON

OUTPUT:
{{
  "summary": "2-3 sentence executive summary",
  "strengths": ["strength 1", "strength 2", "strength 3", "strength 4", "strength 5"],
  "concerns": ["concern 1", "concern 2", "concern 3"],
  "recommendations": [
    {{"priority": "high", "action": "action", "reason": "why", "evidence": "data"}},
    {{"priority": "medium", "action": "action", "reason": "why", "evidence": "data"}},
    {{"priority": "low", "action": "action", "reason": "why", "evidence": "data"}}
  ]
}}

Generate {role} insights:"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔄 Calling API for {role} insights (attempt {attempt + 1}/{max_retries})...")
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text.strip()
            print(f"📝 {role} raw response length: {len(result_text)} chars")
            
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            match = re.search(r'\{[\s\S]*\}', result_text)
            if match:
                try:
                    insights = json.loads(match.group())
                    if 'summary' in insights and 'strengths' in insights:
                        print(f"✅ {role.title()} insights generated successfully")
                        return {"role": role, "insights": insights}
                    else:
                        print(f"⚠️ {role} insights missing required fields")
                        return {"role": role, "insights": _fallback_insights(role)}
                except json.JSONDecodeError as je:
                    print(f"⚠️ {role} JSON parse error: {je}")
                    return {"role": role, "insights": _fallback_insights(role)}
            else:
                print(f"⚠️ No JSON found in {role} response")
                return {"role": role, "insights": _fallback_insights(role)}
                
        except Exception as e:
            error_str = str(e)
            if '529' in error_str or 'overloaded' in error_str.lower() or '429' in error_str or 'rate' in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"⚠️ API overloaded for {role}, waiting {wait_time}s before retry...")
                    time_module.sleep(wait_time)
                    continue
                else:
                    print(f"❌ API still overloaded after {max_retries} retries for {role}")
                    return {"role": role, "insights": _fallback_insights(role)}
            else:
                print(f"❌ Error generating {role} insights: {e}")
                return {"role": role, "insights": _fallback_insights(role)}
    
    return {"role": role, "insights": _fallback_insights(role)}


# ============================================================================
# MANAGER INSIGHTS (uses anthropic-manager key)
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-manager")],
    timeout=210,
    retries=3,
    memory=512,  # [INIT-04] Added memory config
)
def generate_manager_insights(analysis_data: Dict[str, Any], restaurant_name: str) -> Dict[str, Any]:
    """Generate MANAGER insights - uses anthropic-manager key."""
    from anthropic import Anthropic
    import os
    import time as time_module
    
    role = "manager"
    print(f"🧠 [MANAGER-KEY] Generating {role} insights...")
    
    # [API-01] Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"❌ ANTHROPIC_API_KEY not found for {role} insights!")
        return {"role": role, "insights": _fallback_insights(role)}
    
    client = Anthropic(api_key=api_key)
    
    menu_items = analysis_data.get('menu_analysis', {}).get('food_items', [])[:20]
    drinks = analysis_data.get('menu_analysis', {}).get('drinks', [])[:10]
    aspects = analysis_data.get('aspect_analysis', {}).get('aspects', [])[:20]
    
    # [INS-02] Use centralized threshold for formatting
    menu_lines = ["TOP MENU ITEMS:"]
    for item in menu_items:
        s = item.get('sentiment', 0)
        indicator = "[+]" if s >= SENTIMENT_THRESHOLD_POSITIVE else "[~]" if s >= SENTIMENT_THRESHOLD_NEGATIVE else "[-]"
        menu_lines.append(f"  {indicator} {item.get('name', '?')}: sentiment {s:+.2f}, {item.get('mention_count', 0)} mentions")
    menu_summary = "\n".join(menu_lines)
    
    aspect_lines = ["TOP ASPECTS:"]
    for a in aspects:
        s = a.get('sentiment', 0)
        indicator = "[+]" if s >= SENTIMENT_THRESHOLD_POSITIVE else "[~]" if s >= SENTIMENT_THRESHOLD_NEGATIVE else "[-]"
        aspect_lines.append(f"  {indicator} {a.get('name', '?')}: sentiment {s:+.2f}, {a.get('mention_count', 0)} mentions")
    aspect_summary = "\n".join(aspect_lines)
    
    focus = "Focus on: Service, staff, wait times, ambience, value, cleanliness"
    topic_filter = "ONLY on operations/service topics"
    
    # [INS-02] Use centralized threshold in prompt
    prompt = f"""You are an expert restaurant consultant analyzing feedback for {restaurant_name}.

{menu_summary}

{aspect_summary}

SENTIMENT SCALE:
- POSITIVE (>= {SENTIMENT_THRESHOLD_POSITIVE}): Highlight as STRENGTH
- NEUTRAL ({SENTIMENT_THRESHOLD_NEGATIVE} to {SENTIMENT_THRESHOLD_POSITIVE - 0.01}): Room for improvement
- NEGATIVE (< {SENTIMENT_THRESHOLD_NEGATIVE}): Flag as CONCERN

YOUR TASK: Generate insights for the RESTAURANT MANAGER.
{focus}

RULES:
1. Focus {topic_filter}
2. STRENGTHS from items with sentiment >= {SENTIMENT_THRESHOLD_POSITIVE}
3. CONCERNS from items with sentiment < {SENTIMENT_THRESHOLD_NEGATIVE}
4. Output ONLY valid JSON

OUTPUT:
{{
  "summary": "2-3 sentence executive summary",
  "strengths": ["strength 1", "strength 2", "strength 3", "strength 4", "strength 5"],
  "concerns": ["concern 1", "concern 2", "concern 3"],
  "recommendations": [
    {{"priority": "high", "action": "action", "reason": "why", "evidence": "data"}},
    {{"priority": "medium", "action": "action", "reason": "why", "evidence": "data"}},
    {{"priority": "low", "action": "action", "reason": "why", "evidence": "data"}}
  ]
}}

Generate {role} insights:"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🔄 Calling API for {role} insights (attempt {attempt + 1}/{max_retries})...")
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text.strip()
            print(f"📝 {role} raw response length: {len(result_text)} chars")
            
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            match = re.search(r'\{[\s\S]*\}', result_text)
            if match:
                try:
                    insights = json.loads(match.group())
                    if 'summary' in insights and 'strengths' in insights:
                        print(f"✅ {role.title()} insights generated successfully")
                        return {"role": role, "insights": insights}
                    else:
                        print(f"⚠️ {role} insights missing required fields")
                        return {"role": role, "insights": _fallback_insights(role)}
                except json.JSONDecodeError as je:
                    print(f"⚠️ {role} JSON parse error: {je}")
                    return {"role": role, "insights": _fallback_insights(role)}
            else:
                print(f"⚠️ No JSON found in {role} response")
                return {"role": role, "insights": _fallback_insights(role)}
                
        except Exception as e:
            error_str = str(e)
            if '529' in error_str or 'overloaded' in error_str.lower() or '429' in error_str or 'rate' in error_str.lower():
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    print(f"⚠️ API overloaded for {role}, waiting {wait_time}s before retry...")
                    time_module.sleep(wait_time)
                    continue
                else:
                    print(f"❌ API still overloaded after {max_retries} retries for {role}")
                    return {"role": role, "insights": _fallback_insights(role)}
            else:
                print(f"❌ Error generating {role} insights: {e}")
                return {"role": role, "insights": _fallback_insights(role)}
    
    return {"role": role, "insights": _fallback_insights(role)}


def _fallback_insights(role: str) -> Dict[str, Any]:
    """Fallback insights if generation fails."""
    return {
        "summary": f"Analysis complete. See data for {role} insights.",
        "strengths": ["Data available in charts"],
        "concerns": ["Review individual items for details"],
        "recommendations": [{"priority": "medium", "action": "Review data", "reason": "Auto-generated", "evidence": "N/A"}]
    }


# ============================================================================
# SUMMARY GENERATION (uses anthropic-summaries key)
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-summaries")],
    timeout=210,
    memory=512,  # [INIT-04] Added memory config
)
def generate_all_summaries(
    food_items: List[Dict[str, Any]],
    drinks: List[Dict[str, Any]],
    aspects: List[Dict[str, Any]],
    restaurant_name: str
) -> Dict[str, Dict[str, str]]:
    """Generate ALL summaries in a SINGLE API call - uses anthropic-summaries key."""
    from anthropic import Anthropic
    import os
    
    print(f"📝 [SUMMARIES-KEY] Generating all summaries...")
    
    # [API-01] Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found for summary generation!")
        return {"food": {}, "drinks": {}, "aspects": {}}
    
    client = Anthropic(api_key=api_key)
    
    # Build prompt
    food_list_str = "\n".join([f"- {f.get('name', '?')} (sentiment: {f.get('sentiment', 0):.2f}, mentions: {f.get('mention_count', 0)})" for f in food_items])
    drinks_list_str = "\n".join([f"- {d.get('name', '?')} (sentiment: {d.get('sentiment', 0):.2f}, mentions: {d.get('mention_count', 0)})" for d in drinks])
    aspects_list_str = "\n".join([f"- {a.get('name', '?')} (sentiment: {a.get('sentiment', 0):.2f}, mentions: {a.get('mention_count', 0)})" for a in aspects])
    
    # [INS-02] Use centralized threshold in prompt
    prompt = f"""Generate brief 2-3 sentence summaries for each item at {restaurant_name}.

FOOD ITEMS:
{food_list_str}

DRINKS:
{drinks_list_str}

ASPECTS:
{aspects_list_str}

For each summary:
1. Synthesizes what customers say
2. Reflects the sentiment score (positive if >= {SENTIMENT_THRESHOLD_POSITIVE}, negative if < {SENTIMENT_THRESHOLD_NEGATIVE}, neutral otherwise)
3. Gives actionable insight for restaurant staff

OUTPUT FORMAT (JSON):
{{
  "food": {{
    "item name": "2-3 sentence summary based on reviews...",
    "another item": "summary..."
  }},
  "drinks": {{
    "drink name": "summary..."
  }},
  "aspects": {{
    "aspect name": "summary..."
  }}
}}

CRITICAL: Output ONLY valid JSON. Generate summaries for ALL items listed above."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text.strip()
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        match = re.search(r'\{[\s\S]*\}', result_text)
        if match:
            summaries = json.loads(match.group())
            print(f"✅ Generated summaries: {len(summaries.get('food', {}))} food, {len(summaries.get('drinks', {}))} drinks, {len(summaries.get('aspects', {}))} aspects")
            return summaries
        else:
            print("⚠️ No JSON found in summary response")
            return {"food": {}, "drinks": {}, "aspects": {}}
            
    except Exception as e:
        print(f"⚠️ Summary generation error: {e}")
        return {"food": {}, "drinks": {}, "aspects": {}}


# ============================================================================
# MAIN ANALYSIS FUNCTION - PARALLEL OPTIMIZED WITH MULTI-KEY
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-batch1")],  # Fallback for scraper
    timeout=2100,  # [API-06] Increased timeout
    memory=1024,  # [INIT-04] Added memory config for main function
)
def full_analysis_parallel(url: str, max_reviews: int = 100) -> Dict[str, Any]:
    """
    PARALLEL OPTIMIZED analysis pipeline with MULTI-KEY support.
    
    Uses different API keys for different tasks:
    - Odd batches: anthropic-batch1
    - Even batches: anthropic-batch2
    - Chef insights: anthropic-chef
    - Manager insights: anthropic-manager
    - Summaries: anthropic-summaries
    """
    import time
    import pandas as pd
    start_time = time.time()
    
    print(f"🚀 Starting MULTI-KEY PARALLEL analysis for {url}")
    print(f"📊 Max reviews: {max_reviews}")
    
    # Detect platform
    url_lower = url.lower()
    platform = "opentable" if 'opentable' in url_lower else "google_maps" if any(x in url_lower for x in ['google.com/maps', 'goo.gl/maps', 'maps.google', 'maps.app.goo.gl']) else "unknown"
    
    if platform == "unknown":
        return {"success": False, "error": "Unsupported platform. Use OpenTable or Google Maps."}
    
    # Phase 1: Scrape reviews
    print("📥 Phase 1: Scraping reviews...")
    scrape_start = time.time()
    
    if platform == "opentable":
        from src.scrapers.opentable_scraper import scrape_opentable
        result = scrape_opentable(url=url, max_reviews=max_reviews, headless=True)
    else:
        from src.scrapers.google_maps_scraper import scrape_google_maps
        result = scrape_google_maps(url=url, max_reviews=max_reviews, headless=True)
    
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Scraping failed")}
    
    print(f"✅ Scraping complete in {time.time() - scrape_start:.1f}s")
    print(f"📦 Raw result keys: {list(result.keys())}")
    
    # =========================================================================
    # [FMT-01][PROC-01] SIMPLIFIED: Both scrapers now return NESTED format
    # =========================================================================
    from src.data_processing import clean_reviews_for_ai
    
    reviews_data = result.get('reviews', {})
    print(f"📦 reviews_data type: {type(reviews_data)}")
    
    # Both OpenTable and Google Maps now return nested format:
    # {'reviews': {'names': [...], 'dates': [...], 'review_texts': [...], ...}}
    if isinstance(reviews_data, dict) and 'review_texts' in reviews_data:
        print(f"📋 Detected NESTED format (source: {platform})")
        review_texts = reviews_data.get('review_texts', [])
        n = len(review_texts)
        
        if n == 0:
            return {"success": False, "error": "No reviews found in response."}
        
        df = pd.DataFrame({
            'name': (reviews_data.get('names', []) + [''] * n)[:n],
            'date': (reviews_data.get('dates', []) + [''] * n)[:n],
            'overall_rating': (reviews_data.get('overall_ratings', []) + [0.0] * n)[:n],
            'food_rating': reviews_data.get('food_ratings', [0.0] * n)[:n],
            'service_rating': reviews_data.get('service_ratings', [0.0] * n)[:n],
            'ambience_rating': reviews_data.get('ambience_ratings', [0.0] * n)[:n],
            'review_text': review_texts
        })
        print(f"✅ Built DataFrame: {len(df)} reviews")
    
    # Fallback for legacy flat format (shouldn't happen with updated scrapers)
    elif 'names' in result and isinstance(result.get('names'), list):
        print("📋 Detected LEGACY flat format - using fallback")
        review_texts = result.get('reviews', result.get('review_texts', []))
        n = len(review_texts) if isinstance(review_texts, list) else 0
        
        if n == 0:
            return {"success": False, "error": "No reviews found in legacy format response."}
        
        df = pd.DataFrame({
            'name': (result.get('names', []) + [''] * n)[:n],
            'date': (result.get('dates', []) + [''] * n)[:n],
            'overall_rating': (result.get('overall_ratings', []) + [0.0] * n)[:n],
            'food_rating': (result.get('food_ratings', []) + [0.0] * n)[:n],
            'service_rating': (result.get('service_ratings', []) + [0.0] * n)[:n],
            'ambience_rating': (result.get('ambience_ratings', []) + [0.0] * n)[:n],
            'review_text': review_texts
        })
        print(f"✅ Built DataFrame from legacy format: {len(df)} reviews")
    
    else:
        return {"success": False, "error": "Could not parse reviews - unexpected format."}
    
    # Validate we got something
    if df is None or len(df) == 0:
        return {"success": False, "error": "No reviews found. The restaurant may have no reviews or the scraper couldn't access them."}
    
    # =========================================================================
    # Convert ratings to numeric
    # =========================================================================
    def parse_rating(val):
        """Convert rating to numeric."""
        if pd.isna(val) or val == '' or val is None:
            return 0.0
        
        try:
            num = float(val)
            if 0 <= num <= 5:
                return num
        except (ValueError, TypeError):
            pass
        
        text_map = {
            'excellent': 5.0, 'very good': 4.5, 'good': 4.0,
            'average': 3.0, 'below average': 2.0, 'poor': 1.0, 'terrible': 1.0,
            '5': 5.0, '4': 4.0, '3': 3.0, '2': 2.0, '1': 1.0,
        }
        
        val_str = str(val).lower().strip()
        for key, num in text_map.items():
            if key in val_str:
                return num
        
        return 0.0
    
    for col in ['overall_rating', 'food_rating', 'service_rating', 'ambience_rating']:
        if col in df.columns:
            df[col] = df[col].apply(parse_rating)
    
    # Get clean review texts
    reviews = clean_reviews_for_ai(df["review_text"].dropna().tolist(), verbose=False)
    
    print(f"📊 Total clean reviews: {len(reviews)}")
    
    # Debug ratings
    valid_ratings = df['overall_rating'][df['overall_rating'] > 0]
    print(f"📊 Valid ratings: {len(valid_ratings)} out of {len(df)} reviews")
    if len(valid_ratings) > 0:
        print(f"📊 Rating range: {valid_ratings.min():.1f} to {valid_ratings.max():.1f}, avg: {valid_ratings.mean():.2f}")
    
    # =========================================================================
    # Create trend_data with proper date handling
    # =========================================================================
    trend_data = []
    estimated_rating_count = 0  # [PROC-05] Track estimated ratings
    
    for _, row in df.iterrows():
        text = str(row.get("review_text", ""))
        rating = float(row.get("overall_rating", 0) or 0)
        sentiment = calculate_sentiment(text)
        
        # [PROC-05] If no rating extracted, estimate from sentiment and LOG IT
        if rating == 0 and sentiment != 0:
            rating = round((sentiment + 1) * 2 + 1, 1)  # -1→1, 0→3, 1→5
            estimated_rating_count += 1
        
        date_val = row.get("date", "")
        if pd.isna(date_val):
            date_val = ""
        else:
            date_val = str(date_val).strip()
        
        trend_data.append({
            "date": date_val,
            "rating": rating,
            "sentiment": sentiment
        })
    
    # [PROC-05] Log estimated ratings
    if estimated_rating_count > 0:
        print(f"📊 Estimated {estimated_rating_count} ratings from sentiment (no rating extracted from page)")
    
    print(f"📊 Trend data points: {len(trend_data)}")
    if trend_data:
        sample_dates = [t['date'] for t in trend_data[:5]]
        print(f"📊 Sample dates: {sample_dates}")
    
    # Extract restaurant name
    if platform == "opentable":
        restaurant_name = url.split("/")[-1].split("?")[0].replace("-", " ").title()
    else:
        if '/place/' in url:
            restaurant_name = url.split('/place/')[1].split('/')[0].replace('+', ' ').replace('%20', ' ')
        else:
            restaurant_name = "Restaurant"
    
    # Phase 2: PARALLEL batch extraction with MULTI-KEY
    print("🔄 Phase 2: PARALLEL batch extraction (MULTI-KEY)...")
    extract_start = time.time()
    
    BATCH_SIZE = 30
    odd_batches = []
    even_batches = []
    
    batch_num = 1
    for i in range(0, len(reviews), BATCH_SIZE):
        batch_reviews = reviews[i:i+BATCH_SIZE]
        batch_data = {
            "reviews": batch_reviews,
            "restaurant_name": restaurant_name,
            "batch_index": batch_num,
            "start_index": i
        }
        
        # Split odd/even for different API keys
        if batch_num % 2 == 1:
            odd_batches.append(batch_data)
        else:
            even_batches.append(batch_data)
        batch_num += 1
    
    print(f"📦 Created {len(odd_batches)} odd batches (batch1 key) + {len(even_batches)} even batches (batch2 key)")
    print(f"🚀 Processing ALL batches in PARALLEL across 2 API keys...")
    
    # Process odd and even batches in parallel (each uses different key!)
    odd_results = list(process_batch_odd.map(odd_batches)) if odd_batches else []
    even_results = list(process_batch_even.map(even_batches)) if even_batches else []
    
    # Combine results
    batch_results = odd_results + even_results
    
    print(f"✅ All batches complete in {time.time() - extract_start:.1f}s")
    
    # Merge results from all batches
    all_food_items = {}
    all_drinks = {}
    all_aspects = {}
    
    for batch_result in batch_results:
        if not batch_result.get("success"):
            continue
        
        data = batch_result.get("data", {})
        
        # Merge food items
        for item in data.get('food_items', []):
            name = item.get('name', '').lower().strip()  # [INS-03] Added strip()
            if not name:
                continue
            if name in all_food_items:
                all_food_items[name]['mention_count'] += item.get('mention_count', 1)
                # [INS-05] APPEND related_reviews instead of overwrite
                all_food_items[name]['related_reviews'].extend(item.get('related_reviews', []))
                # Weighted average sentiment
                old_count = all_food_items[name]['mention_count'] - item.get('mention_count', 1)
                new_count = item.get('mention_count', 1)
                if old_count + new_count > 0:
                    old_sent = all_food_items[name]['sentiment']
                    new_sent = item.get('sentiment', 0)
                    all_food_items[name]['sentiment'] = (old_sent * old_count + new_sent * new_count) / (old_count + new_count)
            else:
                all_food_items[name] = item
        
        # Merge drinks
        for item in data.get('drinks', []):
            name = item.get('name', '').lower().strip()  # [INS-03] Added strip()
            if not name:
                continue
            if name in all_drinks:
                all_drinks[name]['mention_count'] += item.get('mention_count', 1)
                # [INS-05] APPEND related_reviews instead of overwrite
                all_drinks[name]['related_reviews'].extend(item.get('related_reviews', []))
                old_count = all_drinks[name]['mention_count'] - item.get('mention_count', 1)
                new_count = item.get('mention_count', 1)
                if old_count + new_count > 0:
                    old_sent = all_drinks[name]['sentiment']
                    new_sent = item.get('sentiment', 0)
                    all_drinks[name]['sentiment'] = (old_sent * old_count + new_sent * new_count) / (old_count + new_count)
            else:
                all_drinks[name] = item
        
        # Merge aspects
        for aspect in data.get('aspects', []):
            name = aspect.get('name', '').lower().strip()  # [INS-03] Added strip()
            if not name:
                continue
            if name in all_aspects:
                all_aspects[name]['mention_count'] += aspect.get('mention_count', 1)
                # [INS-05] APPEND related_reviews instead of overwrite
                all_aspects[name]['related_reviews'].extend(aspect.get('related_reviews', []))
                old_count = all_aspects[name]['mention_count'] - aspect.get('mention_count', 1)
                new_count = aspect.get('mention_count', 1)
                if old_count + new_count > 0:
                    old_sent = all_aspects[name]['sentiment']
                    new_sent = aspect.get('sentiment', 0)
                    all_aspects[name]['sentiment'] = (old_sent * old_count + new_sent * new_count) / (old_count + new_count)
            else:
                all_aspects[name] = aspect
    
    # Sort by mention count
    food_list = sorted(all_food_items.values(), key=lambda x: x.get('mention_count', 0), reverse=True)
    drinks_list = sorted(all_drinks.values(), key=lambda x: x.get('mention_count', 0), reverse=True)
    aspects_list = sorted(all_aspects.values(), key=lambda x: x.get('mention_count', 0), reverse=True)
    
    print(f"📊 Discovered: {len(food_list)} food + {len(drinks_list)} drinks + {len(aspects_list)} aspects")
    
    # Phase 2.5: Generate ALL summaries in ONE API call (uses anthropic-summaries key)
    print("📝 Phase 2.5: Generating summaries (SUMMARIES-KEY)...")
    summary_start = time.time()
    
    # [INS-04] Use increased summary counts
    summaries = generate_all_summaries.remote(
        food_items=food_list[:SUMMARY_FOOD_COUNT],
        drinks=drinks_list[:SUMMARY_DRINKS_COUNT],
        aspects=aspects_list[:SUMMARY_ASPECTS_COUNT],
        restaurant_name=restaurant_name
    )
    
    # [INS-03] Apply summaries with better name matching
    food_summaries = summaries.get('food', {})
    drink_summaries = summaries.get('drinks', {})
    aspect_summaries = summaries.get('aspects', {})
    
    # [INS-03] Helper function for flexible name matching
    def find_summary(name: str, summary_dict: Dict[str, str]) -> str:
        """Find summary with flexible matching (lowercase, title, strip)."""
        name_clean = name.lower().strip()
        name_title = name_clean.title()
        
        # Try exact lowercase match
        if name_clean in summary_dict:
            return summary_dict[name_clean]
        # Try title case match
        if name_title in summary_dict:
            return summary_dict[name_title]
        # Try matching any key that starts with same word
        for key, val in summary_dict.items():
            if key.lower().strip() == name_clean:
                return val
        return ""
    
    for item in food_list:
        name = item.get('name', '')
        summary = find_summary(name, food_summaries)
        if summary:
            item['summary'] = summary
    
    for item in drinks_list:
        name = item.get('name', '')
        summary = find_summary(name, drink_summaries)
        if summary:
            item['summary'] = summary
    
    for item in aspects_list:
        name = item.get('name', '')
        summary = find_summary(name, aspect_summaries)
        if summary:
            item['summary'] = summary
    
    print(f"✅ Summaries complete in {time.time() - summary_start:.1f}s")
    
    # Build analysis data
    analysis_data = {
        "menu_analysis": {
            "food_items": food_list,
            "drinks": drinks_list
        },
        "aspect_analysis": {
            "aspects": aspects_list
        }
    }
    
    # Phase 3: PARALLEL insights generation (MULTI-KEY: chef + manager simultaneously!)
    print("🧠 Phase 3: PARALLEL insights (CHEF-KEY + MANAGER-KEY simultaneously)...")
    insights_start = time.time()
    
    # Spawn both in parallel - each uses its own API key!
    chef_future = generate_chef_insights.spawn(analysis_data, restaurant_name)
    manager_future = generate_manager_insights.spawn(analysis_data, restaurant_name)
    
    # Wait for both to complete
    chef_result = chef_future.get()
    manager_result = manager_future.get()
    
    insights = {
        "chef": chef_result.get("insights", {}),
        "manager": manager_result.get("insights", {})
    }
    
    print(f"📊 Chef insights: {len(insights['chef'].get('strengths', []))} strengths, {len(insights['chef'].get('concerns', []))} concerns")
    print(f"📊 Manager insights: {len(insights['manager'].get('strengths', []))} strengths, {len(insights['manager'].get('concerns', []))} concerns")
    
    print(f"✅ Insights complete in {time.time() - insights_start:.1f}s")
    
    # Build final response
    total_time = time.time() - start_time
    print(f"🎉 TOTAL TIME: {total_time:.1f}s ({total_time/60:.1f} min)")
    
    analysis = {
        "success": True,
        "restaurant_name": restaurant_name,
        "menu_analysis": analysis_data["menu_analysis"],
        "aspect_analysis": analysis_data["aspect_analysis"],
        "insights": insights,
        "trend_data": trend_data,
        "source": platform,
        "stats": {
            "total_reviews": len(reviews),
            "food_items": len(food_list),
            "drinks": len(drinks_list),
            "aspects": len(aspects_list),
            "processing_time_seconds": round(total_time, 1),
            "estimated_ratings": estimated_rating_count  # [PROC-05] Include in stats
        }
    }
    
    response_size = len(json.dumps(analysis))
    print(f"[MODAL] Response size: {response_size / 1024:.1f} KB")
    
    return analysis


# ============================================================================
# FASTAPI APP
# ============================================================================

@app.function(
    image=image, 
    secrets=[modal.Secret.from_name("anthropic-batch1")],  # Fallback key
    timeout=2100,  # [API-06] Increased timeout
    memory=1024,   # [INIT-04] Added memory config
)
@modal.asgi_app()
def fastapi_app():
    """Main API - uses parallel processing with multi-key for speed."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    
    web_app = FastAPI(title="Restaurant Intelligence API - MULTI-KEY PARALLEL")
    
    class AnalyzeRequest(BaseModel):
        url: str
        max_reviews: int = 100
    
    @web_app.get("/")
    async def root():
        return {
            "name": "Restaurant Intelligence API",
            "version": "3.1-multikey",
            "optimizations": ["parallel_batches", "parallel_insights", "multi_api_keys"],
            "keys_used": ["batch1", "batch2", "chef", "manager", "summaries"],
            "target": "1000 reviews in ~5 minutes",
            "sentiment_threshold": SENTIMENT_THRESHOLD_POSITIVE
        }
    
    @web_app.get("/health")
    async def health():
        return {"status": "healthy", "version": "3.1-multikey"}
    
    @web_app.post("/analyze")
    async def analyze(request: AnalyzeRequest):
        try:
            result = full_analysis_parallel.remote(url=request.url, max_reviews=request.max_reviews)
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    
    return web_app


# ============================================================================
# LOCAL ENTRYPOINT FOR TESTING
# ============================================================================

@app.local_entrypoint()
def main():
    print("🧪 Testing MULTI-KEY PARALLEL Modal deployment...\n")
    
    print("📋 Required secrets (create all 5 in Modal dashboard):")
    print("   - anthropic-batch1   (for odd batch processing)")
    print("   - anthropic-batch2   (for even batch processing)")
    print("   - anthropic-chef     (for chef insights)")
    print("   - anthropic-manager  (for manager insights)")
    print("   - anthropic-summaries (for summary generation)")
    
    print(f"\n📊 Configuration:")
    print(f"   Sentiment threshold (positive): >= {SENTIMENT_THRESHOLD_POSITIVE}")
    print(f"   Summary counts: {SUMMARY_FOOD_COUNT} food, {SUMMARY_DRINKS_COUNT} drinks, {SUMMARY_ASPECTS_COUNT} aspects")
    
    print("\n1️⃣ API will be deployed at:")
    print("   https://tushar-pingle--restaurant-intelligence-fastapi-app.modal.run")
    
    print("\n✅ Deploy with: modal deploy modal_backend.py")