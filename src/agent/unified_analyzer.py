"""
Unified Review Analyzer - Single-pass extraction
Extracts menu items, aspects, and sentiment in ONE API call per batch

UPDATED: New sentiment scale
- Positive: >= 0.6
- Neutral: 0 to 0.59
- Negative: < 0
"""

from typing import List, Dict, Any
from anthropic import Anthropic
import json
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.agent.api_utils import call_claude_with_retry


class UnifiedReviewAnalyzer:
    """
    Analyzes reviews in a SINGLE PASS to extract:
    - Menu items (food + drinks)
    - Customer aspects (service, ambience, etc.)
    - Sentiment for each
    
    Reduces API calls by 3x compared to separate extraction!
    """
    
    def __init__(self, client: Anthropic, model: str):
        self.client = client
        self.model = model
    
    def analyze_reviews(
        self,
        reviews: List[str],
        restaurant_name: str = "the restaurant",
        batch_size: int = 20
    ) -> Dict[str, Any]:
        """
        Single-pass analysis of all reviews.
        
        Returns:
            {
                "menu_analysis": {
                    "food_items": [...],
                    "drinks": [...]
                },
                "aspect_analysis": {
                    "aspects": [...]
                }
            }
        """
        print(f"🚀 Unified analysis: {len(reviews)} reviews in batches of {batch_size}...")
        
        all_food_items = {}
        all_drinks = {}
        all_aspects = {}
        
        # Process in batches
        for i in range(0, len(reviews), batch_size):
            batch = reviews[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(reviews) + batch_size - 1) // batch_size
            
            print(f"   Batch {batch_num}/{total_batches}: {len(batch)} reviews...")
            
            try:
                batch_result = self._analyze_batch(batch, restaurant_name, start_index=i)
                
                # Merge food items
                for item in batch_result.get('food_items', []):
                    name = item.get('name', '').lower()
                    if not name:
                        continue
                    if name in all_food_items:
                        all_food_items[name]['mention_count'] += item.get('mention_count', 1)
                        all_food_items[name]['related_reviews'].extend(item.get('related_reviews', []))
                        # Average sentiment
                        old_sent = all_food_items[name]['sentiment']
                        new_sent = item.get('sentiment', 0)
                        old_count = all_food_items[name]['mention_count'] - item.get('mention_count', 1)
                        new_count = item.get('mention_count', 1)
                        all_food_items[name]['sentiment'] = (old_sent * old_count + new_sent * new_count) / (old_count + new_count)
                    else:
                        all_food_items[name] = item
                
                # Merge drinks
                for item in batch_result.get('drinks', []):
                    name = item.get('name', '').lower()
                    if not name:
                        continue
                    if name in all_drinks:
                        all_drinks[name]['mention_count'] += item.get('mention_count', 1)
                        all_drinks[name]['related_reviews'].extend(item.get('related_reviews', []))
                        old_sent = all_drinks[name]['sentiment']
                        new_sent = item.get('sentiment', 0)
                        old_count = all_drinks[name]['mention_count'] - item.get('mention_count', 1)
                        new_count = item.get('mention_count', 1)
                        all_drinks[name]['sentiment'] = (old_sent * old_count + new_sent * new_count) / (old_count + new_count)
                    else:
                        all_drinks[name] = item
                
                # Merge aspects
                for aspect in batch_result.get('aspects', []):
                    name = aspect.get('name', '').lower()
                    if not name:
                        continue
                    if name in all_aspects:
                        all_aspects[name]['mention_count'] += aspect.get('mention_count', 1)
                        all_aspects[name]['related_reviews'].extend(aspect.get('related_reviews', []))
                        old_sent = all_aspects[name]['sentiment']
                        new_sent = aspect.get('sentiment', 0)
                        old_count = all_aspects[name]['mention_count'] - aspect.get('mention_count', 1)
                        new_count = aspect.get('mention_count', 1)
                        all_aspects[name]['sentiment'] = (old_sent * old_count + new_sent * new_count) / (old_count + new_count)
                    else:
                        all_aspects[name] = aspect
                        
            except Exception as e:
                print(f"   ⚠️ Batch {batch_num} error: {e}")
                continue
        
        # Convert to lists and sort by mention count
        food_list = sorted(all_food_items.values(), key=lambda x: x.get('mention_count', 0), reverse=True)
        drinks_list = sorted(all_drinks.values(), key=lambda x: x.get('mention_count', 0), reverse=True)
        aspects_list = sorted(all_aspects.values(), key=lambda x: x.get('mention_count', 0), reverse=True)
        
        print(f"✅ Discovered: {len(food_list)} food + {len(drinks_list)} drinks + {len(aspects_list)} aspects")
        
        return {
            "menu_analysis": {
                "food_items": food_list,
                "drinks": drinks_list
            },
            "aspect_analysis": {
                "aspects": aspects_list
            }
        }
    
    def _analyze_batch(
        self,
        reviews: List[str],
        restaurant_name: str,
        start_index: int = 0
    ) -> Dict[str, Any]:
        """Analyze a single batch of reviews."""
        
        prompt = self._build_unified_prompt(reviews, restaurant_name, start_index)
        
        try:
            response = call_claude_with_retry(
                client=self.client,
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            try:
                data = json.loads(result_text)
            except json.JSONDecodeError as e:
                print(f"   ⚠️ JSON parse error: {e}")
                return {"food_items": [], "drinks": [], "aspects": []}
            
            # Post-process: Add full review text back using indices
            data = self._map_reviews_to_items(data, reviews, start_index)
            data = self._normalize_data(data)
            
            return data
            
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            return {"food_items": [], "drinks": [], "aspects": []}
    
    def _build_unified_prompt(
        self,
        reviews: List[str],
        restaurant_name: str,
        start_index: int
    ) -> str:
        """Build unified extraction prompt with NEW SENTIMENT SCALE."""
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

Examples:
- "The pasta was absolutely divine!" → 0.85 (Positive)
- "The pasta was decent, nothing special" → 0.3 (Neutral)
- "The pasta was undercooked and bland" → -0.6 (Negative)

RULES:

**MENU ITEMS:**
- Specific items only: "salmon sushi", "miso soup", "sake"
- Separate food from drinks
- Lowercase names
- Calculate sentiment per item using the scale above

**ASPECTS:**
- What customers discuss: "service speed", "food quality", "ambience", "value"
- Be specific: "service speed" not just "service"
- Cuisine-specific welcome: "freshness", "authenticity", "presentation"
- Lowercase names
- Calculate sentiment per aspect using the scale above

**REVIEW LINKING:**
- For EACH item/aspect, list which review NUMBERS mention it
- Use ONLY the review index numbers: 0, 1, 2, etc.
- DO NOT include review text in your response (saves tokens and prevents JSON errors)

OUTPUT (JSON) - IMPORTANT: Return ONLY review indices, NOT full text:
{{
  "food_items": [
    {{
      "name": "salmon aburi sushi",
      "mention_count": 2,
      "sentiment": 0.85,
      "category": "sushi",
      "related_reviews": [0, 5]
    }}
  ],
  "drinks": [
    {{
      "name": "sake",
      "mention_count": 1,
      "sentiment": 0.7,
      "category": "alcohol",
      "related_reviews": [3]
    }}
  ],
  "aspects": [
    {{
      "name": "service speed",
      "mention_count": 3,
      "sentiment": 0.65,
      "description": "How quickly food arrives",
      "related_reviews": [1, 2, 7]
    }}
  ]
}}

CRITICAL: 
- related_reviews should be an array of NUMBERS ONLY: [0, 1, 5]
- DO NOT include review text or quotes
- This prevents JSON parsing errors and saves tokens
- Output ONLY valid JSON, no other text
- Use the sentiment scale: >= 0.6 positive, 0-0.59 neutral, < 0 negative

Extract everything:"""
        
        return prompt
    
    def _map_reviews_to_items(
        self,
        data: Dict[str, Any],
        reviews: List[str],
        start_index: int
    ) -> Dict[str, Any]:
        """
        Map review indices back to full review text.
        
        Claude returns just indices to avoid JSON breaking.
        We add the full text back here.
        """
        for item in data.get('food_items', []):
            indices = item.get('related_reviews', [])
            item['related_reviews'] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(reviews):
                    item['related_reviews'].append({
                        'review_index': start_index + idx,
                        'review_text': reviews[idx]
                    })
        
        for item in data.get('drinks', []):
            indices = item.get('related_reviews', [])
            item['related_reviews'] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(reviews):
                    item['related_reviews'].append({
                        'review_index': start_index + idx,
                        'review_text': reviews[idx]
                    })
        
        for aspect in data.get('aspects', []):
            indices = aspect.get('related_reviews', [])
            aspect['related_reviews'] = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(reviews):
                    aspect['related_reviews'].append({
                        'review_index': start_index + idx,
                        'review_text': reviews[idx]
                    })
        
        return data
    
    def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize names to lowercase."""
        for item in data.get('food_items', []):
            if 'name' in item:
                item['name'] = item['name'].lower()
        
        for drink in data.get('drinks', []):
            if 'name' in drink:
                drink['name'] = drink['name'].lower()
        
        for aspect in data.get('aspects', []):
            if 'name' in aspect:
                aspect['name'] = aspect['name'].lower()
        
        return data