"""
Modal Backend for Restaurant Intelligence Agent - PARALLEL OPTIMIZED
Version 3.0 - Uses Modal's parallel processing for 5x speed improvement

KEY OPTIMIZATIONS:
1. Parallel batch processing with .map() - Process all batches simultaneously
2. Parallel insights generation - Chef + Manager at same time
3. Larger batch sizes (30 reviews instead of 20)
4. Reduced timeout since parallel is faster

TARGET: 1000 reviews in ~5 minutes (down from 15+ minutes)
"""

import modal
from typing import Dict, Any, List
import os
import json

# Create Modal app
app = modal.App("restaurant-intelligence")

# Base image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
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
    """Simple sentiment calculation from review text."""
    if not text:
        return 0.0
    text = str(text).lower()
    
    positive = ['amazing', 'excellent', 'fantastic', 'great', 'awesome', 'delicious', 
                'perfect', 'outstanding', 'loved', 'beautiful', 'fresh', 'friendly', 
                'best', 'wonderful', 'incredible', 'superb', 'exceptional']
    negative = ['terrible', 'horrible', 'awful', 'bad', 'worst', 'disappointing', 
                'poor', 'overpriced', 'slow', 'rude', 'cold', 'bland', 'mediocre',
                'disgusting', 'inedible', 'undercooked', 'overcooked']
    
    pos = sum(1 for w in positive if w in text)
    neg = sum(1 for w in negative if w in text)
    
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / max(pos + neg, 1)


# ============================================================================
# PARALLEL BATCH PROCESSOR - The key optimization!
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=120,  # 2 min per batch is plenty
    retries=2,
)
def process_batch(batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single batch of reviews - runs in PARALLEL across containers!
    
    This function is called via .map() to process all batches simultaneously.
    Modal will spin up multiple containers to handle batches in parallel.
    """
    from anthropic import Anthropic
    import os
    
    reviews = batch_data["reviews"]
    restaurant_name = batch_data["restaurant_name"]
    batch_index = batch_data["batch_index"]
    start_index = batch_data["start_index"]
    
    print(f"🔄 Processing batch {batch_index} ({len(reviews)} reviews)...")
    
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    # Build extraction prompt
    numbered_reviews = []
    for i, review in enumerate(reviews):
        numbered_reviews.append(f"[Review {i}]: {review}")
    reviews_text = "\n\n".join(numbered_reviews)
    
    prompt = f"""You are analyzing customer reviews for {restaurant_name}. Extract BOTH menu items AND aspects in ONE PASS.

REVIEWS:
{reviews_text}

YOUR TASK - Extract THREE things simultaneously:
1. **MENU ITEMS** (food & drinks mentioned)
2. **ASPECTS** (what customers care about: service, ambience, etc.)
3. **SENTIMENT** for each

SENTIMENT SCALE (IMPORTANT):
- **Positive (0.6 to 1.0):** Customer clearly enjoyed/praised this item or aspect
- **Neutral (0.0 to 0.59):** Mixed feelings, okay but not exceptional, or simply mentioned without strong opinion
- **Negative (-1.0 to -0.01):** Customer complained, criticized, or expressed disappointment

RULES:
- Specific items only: "salmon sushi", "miso soup", "sake"
- Separate food from drinks
- Lowercase names
- For EACH item/aspect, list which review NUMBERS mention it (just indices, not text)

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

CRITICAL: Output ONLY valid JSON, no other text. Use sentiment scale: >= 0.6 positive, 0-0.59 neutral, < 0 negative

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
                item['name'] = item['name'].lower()
        
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
                item['name'] = item['name'].lower()
        
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
                aspect['name'] = aspect['name'].lower()
        
        print(f"✅ Batch {batch_index} complete: {len(data.get('food_items', []))} food, {len(data.get('drinks', []))} drinks, {len(data.get('aspects', []))} aspects")
        return {"success": True, "batch_index": batch_index, "data": data}
        
    except json.JSONDecodeError as e:
        print(f"⚠️ Batch {batch_index} JSON error: {e}")
        return {"success": False, "batch_index": batch_index, "data": {"food_items": [], "drinks": [], "aspects": []}}
    except Exception as e:
        print(f"❌ Batch {batch_index} error: {e}")
        return {"success": False, "batch_index": batch_index, "data": {"food_items": [], "drinks": [], "aspects": []}}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=180,  # 3 min for insights
)
def generate_insights_parallel(analysis_data: Dict[str, Any], restaurant_name: str, role: str) -> Dict[str, Any]:
    """Generate insights for a single role - runs in parallel with other insights."""
    from anthropic import Anthropic
    import os
    import re
    
    print(f"🧠 Generating {role} insights...")
    
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    # Build prompt based on role
    menu_items = analysis_data.get('menu_analysis', {}).get('food_items', [])[:20]
    drinks = analysis_data.get('menu_analysis', {}).get('drinks', [])[:10]
    aspects = analysis_data.get('aspect_analysis', {}).get('aspects', [])[:20]
    
    # Format menu summary
    menu_lines = ["TOP MENU ITEMS:"]
    for item in menu_items:
        s = item.get('sentiment', 0)
        emoji = "🟢" if s >= 0.6 else "🟡" if s >= 0 else "🔴"
        menu_lines.append(f"  {emoji} {item.get('name', '?')}: sentiment {s:+.2f}, {item.get('mention_count', 0)} mentions")
    menu_summary = "\n".join(menu_lines)
    
    # Format aspect summary
    aspect_lines = ["TOP ASPECTS:"]
    for a in aspects:
        s = a.get('sentiment', 0)
        emoji = "🟢" if s >= 0.6 else "🟡" if s >= 0 else "🔴"
        aspect_lines.append(f"  {emoji} {a.get('name', '?')}: sentiment {s:+.2f}, {a.get('mention_count', 0)} mentions")
    aspect_summary = "\n".join(aspect_lines)
    
    if role == 'chef':
        focus = "Focus on: Food quality, menu items, ingredients, presentation, portions, consistency"
        topic_filter = "ONLY on food/kitchen topics"
    else:
        focus = "Focus on: Service, staff, wait times, ambience, value, cleanliness"
        topic_filter = "ONLY on operations/service topics"
    
    prompt = f"""You are an expert restaurant consultant analyzing feedback for {restaurant_name}.

{menu_summary}

{aspect_summary}

SENTIMENT SCALE:
- 🟢 POSITIVE (>= 0.6): Highlight as STRENGTH
- 🟡 NEUTRAL (0 to 0.59): Room for improvement
- 🔴 NEGATIVE (< 0): Flag as CONCERN

YOUR TASK: Generate insights for the {"HEAD CHEF" if role == "chef" else "RESTAURANT MANAGER"}.
{focus}

RULES:
1. Focus {topic_filter}
2. STRENGTHS from items with sentiment >= 0.6
3. CONCERNS from items with sentiment < 0
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

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = response.content[0].text.strip()
        result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        # Find JSON in response
        match = re.search(r'\{[\s\S]*\}', result_text)
        if match:
            insights = json.loads(match.group())
            print(f"✅ {role.title()} insights generated")
            return {"role": role, "insights": insights}
        else:
            print(f"⚠️ No JSON found in {role} response")
            return {"role": role, "insights": _fallback_insights(role)}
            
    except Exception as e:
        print(f"❌ Error generating {role} insights: {e}")
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
# SUMMARY GENERATION - Single API call for ALL summaries (like original)
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=120,
)
def generate_all_summaries(
    food_items: List[Dict[str, Any]],
    drinks: List[Dict[str, Any]],
    aspects: List[Dict[str, Any]],
    restaurant_name: str
) -> Dict[str, Dict[str, str]]:
    """
    Generate ALL summaries in a SINGLE API call.
    
    This matches the original batch_generate_summaries() approach:
    - 1 API call for everything (not 4-5 separate calls)
    - Same cost as before
    - Same quality summaries
    
    Returns:
        {"food": {"item_name": "summary"}, "drinks": {...}, "aspects": {...}}
    """
    from anthropic import Anthropic
    import os
    import re
    
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    # Build compact data for prompt (top items only)
    food_data = []
    for f in food_items[:15]:
        reviews_sample = []
        for r in f.get('related_reviews', [])[:2]:
            if isinstance(r, dict):
                text = r.get('review_text', '')[:150]
            else:
                text = str(r)[:150]
            if text:
                reviews_sample.append(text)
        food_data.append({
            'name': f.get('name', 'unknown'),
            'sentiment': f.get('sentiment', 0),
            'mentions': f.get('mention_count', 0),
            'reviews': reviews_sample
        })
    
    drink_data = []
    for d in drinks[:10]:
        reviews_sample = []
        for r in d.get('related_reviews', [])[:2]:
            if isinstance(r, dict):
                text = r.get('review_text', '')[:150]
            else:
                text = str(r)[:150]
            if text:
                reviews_sample.append(text)
        drink_data.append({
            'name': d.get('name', 'unknown'),
            'sentiment': d.get('sentiment', 0),
            'mentions': d.get('mention_count', 0),
            'reviews': reviews_sample
        })
    
    aspect_data = []
    for a in aspects[:15]:
        reviews_sample = []
        for r in a.get('related_reviews', [])[:2]:
            if isinstance(r, dict):
                text = r.get('review_text', '')[:150]
            else:
                text = str(r)[:150]
            if text:
                reviews_sample.append(text)
        aspect_data.append({
            'name': a.get('name', 'unknown'),
            'sentiment': a.get('sentiment', 0),
            'mentions': a.get('mention_count', 0),
            'reviews': reviews_sample
        })
    
    prompt = f"""You are a restaurant review analyst for {restaurant_name}. Generate brief, specific summaries for each item.

FOOD ITEMS:
{json.dumps(food_data, indent=2)}

DRINKS:
{json.dumps(drink_data, indent=2)}

ASPECTS:
{json.dumps(aspect_data, indent=2)}

For EACH item, write a 2-3 sentence summary that:
1. Synthesizes what customers say (use the sample reviews provided)
2. Reflects the sentiment score (positive if >= 0.6, negative if < 0, neutral otherwise)
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
        
        # Parse JSON
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
# MAIN ANALYSIS FUNCTION - PARALLEL OPTIMIZED
# ============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=600,  # 10 min max (down from 40 min)
)
def full_analysis_parallel(url: str, max_reviews: int = 100) -> Dict[str, Any]:
    """
    PARALLEL OPTIMIZED analysis pipeline.
    
    Speed improvements:
    1. Batches processed in PARALLEL via .map()
    2. Chef + Manager insights generated in PARALLEL
    3. Larger batch size (30 reviews)
    
    Target: 1000 reviews in ~5 minutes
    """
    import time
    start_time = time.time()
    
    print(f"🚀 Starting PARALLEL analysis for {url}")
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
    
    # Process reviews - FIXED: Handle both old and new scraper formats
    from src.data_processing import clean_reviews_for_ai
    import pandas as pd
    
    # The scraper returns data at top level, not nested under 'reviews'
    # Build DataFrame directly from scraper result
    if 'names' in result:
        # New format: data at top level
        df = pd.DataFrame({
            'name': result.get('names', []),
            'date': result.get('dates', []),
            'overall_rating': result.get('overall_ratings', []),
            'food_rating': result.get('food_ratings', []),
            'service_rating': result.get('service_ratings', []),
            'ambience_rating': result.get('ambience_ratings', []),
            'review_text': result.get('reviews', [])
        })
    else:
        # Fallback: try old format with process_reviews
        from src.data_processing import process_reviews
        df = process_reviews(result)
    
    # Convert ratings to numeric
    for col in ['overall_rating', 'food_rating', 'service_rating', 'ambience_rating']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Get clean review texts
    reviews = clean_reviews_for_ai(df["review_text"].dropna().tolist(), verbose=False)
    
    print(f"📊 Total reviews: {len(reviews)}")
    
    # Create trend data
    trend_data = []
    for _, row in df.iterrows():
        text = str(row.get("review_text", ""))
        trend_data.append({
            "date": str(row.get("date", "")),
            "rating": float(row.get("overall_rating", 0) or 0),
            "sentiment": calculate_sentiment(text)
        })
    
    # Extract restaurant name
    if platform == "opentable":
        restaurant_name = url.split("/")[-1].split("?")[0].replace("-", " ").title()
    else:
        if '/place/' in url:
            restaurant_name = url.split('/place/')[1].split('/')[0].replace('+', ' ').replace('%20', ' ')
        else:
            restaurant_name = "Restaurant"
    
    # Phase 2: PARALLEL batch extraction
    print("🔄 Phase 2: PARALLEL batch extraction...")
    extract_start = time.time()
    
    BATCH_SIZE = 30  # Larger batches = fewer API calls
    batches = []
    for i in range(0, len(reviews), BATCH_SIZE):
        batch_reviews = reviews[i:i+BATCH_SIZE]
        batches.append({
            "reviews": batch_reviews,
            "restaurant_name": restaurant_name,
            "batch_index": len(batches) + 1,
            "start_index": i
        })
    
    print(f"📦 Created {len(batches)} batches of ~{BATCH_SIZE} reviews each")
    print(f"🚀 Processing ALL batches in PARALLEL...")
    
    # THIS IS THE KEY: Process all batches in parallel!
    batch_results = list(process_batch.map(batches))
    
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
            name = item.get('name', '').lower()
            if not name:
                continue
            if name in all_food_items:
                all_food_items[name]['mention_count'] += item.get('mention_count', 1)
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
            name = item.get('name', '').lower()
            if not name:
                continue
            if name in all_drinks:
                all_drinks[name]['mention_count'] += item.get('mention_count', 1)
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
            name = aspect.get('name', '').lower()
            if not name:
                continue
            if name in all_aspects:
                all_aspects[name]['mention_count'] += aspect.get('mention_count', 1)
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
    
    # Phase 2.5: Generate ALL summaries in ONE API call (like original)
    print("📝 Phase 2.5: Generating summaries (single API call)...")
    summary_start = time.time()
    
    # Call the single summary function
    summaries = generate_all_summaries.remote(
        food_items=food_list[:15],
        drinks=drinks_list[:10],
        aspects=aspects_list[:15],
        restaurant_name=restaurant_name
    )
    
    # Apply summaries to items
    food_summaries = summaries.get('food', {})
    drink_summaries = summaries.get('drinks', {})
    aspect_summaries = summaries.get('aspects', {})
    
    for item in food_list:
        name = item.get('name', '').lower()
        if name in food_summaries:
            item['summary'] = food_summaries[name]
        elif name.title() in food_summaries:
            item['summary'] = food_summaries[name.title()]
    
    for item in drinks_list:
        name = item.get('name', '').lower()
        if name in drink_summaries:
            item['summary'] = drink_summaries[name]
        elif name.title() in drink_summaries:
            item['summary'] = drink_summaries[name.title()]
    
    for item in aspects_list:
        name = item.get('name', '').lower()
        if name in aspect_summaries:
            item['summary'] = aspect_summaries[name]
        elif name.title() in aspect_summaries:
            item['summary'] = aspect_summaries[name.title()]
    
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
    
    # Phase 3: PARALLEL insights generation
    print("🧠 Phase 3: PARALLEL insights generation...")
    insights_start = time.time()
    
    # Generate both insights in parallel!
    insight_inputs = [
        (analysis_data, restaurant_name, "chef"),
        (analysis_data, restaurant_name, "manager")
    ]
    
    insight_results = list(generate_insights_parallel.starmap(insight_inputs))
    
    insights = {}
    for result in insight_results:
        insights[result["role"]] = result["insights"]
    
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
            "processing_time_seconds": round(total_time, 1)
        }
    }
    
    # Log response size
    response_size = len(json.dumps(analysis))
    print(f"[MODAL] Response size: {response_size / 1024:.1f} KB")
    
    return analysis


# ============================================================================
# FASTAPI APP - Updated to use parallel function
# ============================================================================

@app.function(
    image=image, 
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=900,  # 15 min timeout for the API endpoint
)
@modal.asgi_app()
def fastapi_app():
    """Main API - uses parallel processing for speed."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    
    web_app = FastAPI(title="Restaurant Intelligence API - PARALLEL OPTIMIZED")
    
    class AnalyzeRequest(BaseModel):
        url: str
        max_reviews: int = 100
    
    @web_app.get("/")
    async def root():
        return {
            "name": "Restaurant Intelligence API",
            "version": "3.0-parallel",
            "optimizations": ["parallel_batches", "parallel_insights", "larger_batch_size"],
            "target": "1000 reviews in ~5 minutes"
        }
    
    @web_app.get("/health")
    async def health():
        return {"status": "healthy", "version": "parallel"}
    
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
    print("🧪 Testing PARALLEL Modal deployment...\n")
    
    print("1️⃣ API will be deployed at:")
    print("   https://tushar-pingle--restaurant-intelligence-fastapi-app.modal.run")
    
    print("\n✅ Deploy with: modal deploy modal_backend.py")