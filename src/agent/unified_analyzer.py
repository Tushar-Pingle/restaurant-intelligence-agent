"""
Unified Review Analyzer - Single-pass extraction
Extracts menu items, aspects, and sentiment in ONE API call per batch
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
    
    Reduces API calls by 3x!
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
                "menu_items": {...},
                "aspects": {...},
                "overall_stats": {...}
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
                batch_result = self._analyze_batch(batch, restaurant_name)
                
                # Merge menu items
                for item in batch_result.get('food_items', []):
                    name = item['name']
                    if name in all_food_items:
                        all_food_items[name]['mention_count'] += item['mention_count']
                        all_food_items[name]['related_reviews'].extend(item.get('related_reviews', []))
                        old_sent = all_food_items[name]['sentiment']
                        new_sent = item['sentiment']
                        all_food_items[name]['sentiment'] = (old_sent + new_sent) / 2
                    else:
                        all_food_items[name] = item
                
                # Merge drinks
                for drink in batch_result.get('drinks', []):
                    name = drink['name']
                    if name in all_drinks:
                        all_drinks[name]['mention_count'] += drink['mention_count']
                        all_drinks[name]['related_reviews'].extend(drink.get('related_reviews', []))
                        old_sent = all_drinks[name]['sentiment']
                        new_sent = drink['sentiment']
                        all_drinks[name]['sentiment'] = (old_sent + new_sent) / 2
                    else:
                        all_drinks[name] = drink
                
                # Merge aspects
                for aspect in batch_result.get('aspects', []):
                    name = aspect['name']
                    if name in all_aspects:
                        all_aspects[name]['mention_count'] += aspect['mention_count']
                        all_aspects[name]['related_reviews'].extend(aspect.get('related_reviews', []))
                        old_sent = all_aspects[name]['sentiment']
                        new_sent = aspect['sentiment']
                        all_aspects[name]['sentiment'] = (old_sent + new_sent) / 2
                    else:
                        all_aspects[name] = aspect
                
            except Exception as e:
                print(f"   ⚠️  Batch {batch_num} failed: {e}")
                continue
        
        # Convert to lists and sort
        food_items_list = sorted(list(all_food_items.values()), 
                                key=lambda x: x['mention_count'], reverse=True)
        drinks_list = sorted(list(all_drinks.values()), 
                            key=lambda x: x['mention_count'], reverse=True)
        aspects_list = sorted(list(all_aspects.values()), 
                             key=lambda x: x['mention_count'], reverse=True)
        
        print(f"✅ Discovered: {len(food_items_list)} food + {len(drinks_list)} drinks + {len(aspects_list)} aspects")
        
        return {
            "menu_analysis": {
                "food_items": food_items_list,
                "drinks": drinks_list,
                "total_extracted": len(food_items_list) + len(drinks_list)
            },
            "aspect_analysis": {
                "aspects": aspects_list,
                "total_aspects": len(aspects_list)
            }
        }
    
    def _analyze_batch(
        self,
        reviews: List[str],
        restaurant_name: str
    ) -> Dict[str, Any]:
        """Analyze a single batch - extract EVERYTHING in one call."""
        prompt = self._build_unified_prompt(reviews, restaurant_name)
        
        try:
            response = call_claude_with_retry(
                client=self.client,
                model=self.model,
                max_tokens=6000,  # Larger since we're getting more data
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            data = json.loads(result_text)
            data = self._normalize_data(data)
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            return {"food_items": [], "drinks": [], "aspects": []}
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            return {"food_items": [], "drinks": [], "aspects": []}
    
    def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize all names to lowercase."""
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
    
    def _build_unified_prompt(
        self,
        reviews: List[str],
        restaurant_name: str
    ) -> str:
        """Build unified extraction prompt."""
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

RULES:

**MENU ITEMS:**
- Specific items only: "salmon sushi", "miso soup", "sake"
- Separate food from drinks
- Lowercase names
- Calculate sentiment per item

**ASPECTS:**
- What customers discuss: "service speed", "food quality", "ambience", "value"
- Be specific: "service speed" not just "service"
- Cuisine-specific welcome: "freshness", "authenticity", "presentation"
- Lowercase names
- Calculate sentiment per aspect

**REVIEW LINKING:**
- For EACH item/aspect, list which reviews mention it
- Use review numbers: [Review 0], [Review 1]
- Include full review text

OUTPUT (JSON):
{{
  "food_items": [
    {{
      "name": "salmon aburi sushi",
      "mention_count": 2,
      "sentiment": 0.9,
      "category": "sushi",
      "related_reviews": [
        {{
          "review_index": 0,
          "review_text": "full text",
          "sentiment_context": "quote"
        }}
      ]
    }}
  ],
  "drinks": [...same structure...],
  "aspects": [
    {{
      "name": "service speed",
      "mention_count": 3,
      "sentiment": 0.6,
      "description": "brief desc",
      "related_reviews": [...]
    }}
  ]
}}

Extract everything:"""
        
        return prompt
