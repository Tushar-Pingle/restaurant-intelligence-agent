"""
Menu Discovery Module - FIXED for large review sets
Processes reviews in batches with retry logic
"""

from typing import List, Dict, Any, Optional
from anthropic import Anthropic
import json
import os
import sys

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.agent.api_utils import call_claude_with_retry


class MenuDiscovery:
    """
    Discovers menu items and drinks from reviews using AI.
    Handles large review sets by batching.
    """
    
    def __init__(self, client: Anthropic, model: str):
        """Initialize menu discovery."""
        self.client = client
        self.model = model
    
    def extract_menu_items(
        self,
        reviews: List[str],
        restaurant_name: str = "the restaurant",
        max_items: int = 50,
        batch_size: int = 15
    ) -> Dict[str, Any]:
        """Extract menu items in batches to handle large review sets."""
        print(f"🔍 Processing {len(reviews)} reviews in batches of {batch_size}...")
        
        all_food_items = {}
        all_drinks = {}
        
        # Process in batches
        for i in range(0, len(reviews), batch_size):
            batch = reviews[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(reviews) + batch_size - 1) // batch_size
            
            print(f"   Batch {batch_num}/{total_batches}: {len(batch)} reviews...")
            
            try:
                batch_result = self._extract_batch(batch, restaurant_name, max_items)
                
                # Merge results
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
                
            except Exception as e:
                print(f"   ⚠️  Batch {batch_num} failed: {e}")
                continue
        
        # Convert back to lists
        food_items_list = list(all_food_items.values())
        drinks_list = list(all_drinks.values())
        
        # Sort by mention count
        food_items_list.sort(key=lambda x: x['mention_count'], reverse=True)
        drinks_list.sort(key=lambda x: x['mention_count'], reverse=True)
        
        # Limit results
        food_items_list = food_items_list[:max_items]
        drinks_list = drinks_list[:max_items]
        
        print(f"✅ Discovered {len(food_items_list)} food items + {len(drinks_list)} drinks")
        
        return {
            "food_items": food_items_list,
            "drinks": drinks_list,
            "total_extracted": len(food_items_list) + len(drinks_list)
        }
    
    def _extract_batch(
        self,
        reviews: List[str],
        restaurant_name: str,
        max_items: int
    ) -> Dict[str, Any]:
        """Extract from a single batch with retry logic."""
        prompt = self._build_extraction_prompt(reviews, restaurant_name, max_items)
        
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
            
            extracted_data = json.loads(result_text)
            extracted_data = self._normalize_items(extracted_data)
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse menu items: {e}")
            return {"food_items": [], "drinks": [], "total_extracted": 0}
        except Exception as e:
            print(f"❌ Error extracting menu items: {e}")
            return {"food_items": [], "drinks": [], "total_extracted": 0}
    
    def _normalize_items(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize item names to lowercase."""
        for item in data.get('food_items', []):
            if 'name' in item:
                item['name'] = item['name'].lower()
        
        for drink in data.get('drinks', []):
            if 'name' in drink:
                drink['name'] = drink['name'].lower()
        
        return data
    
    def generate_item_summary(
        self,
        item: Dict[str, Any],
        restaurant_name: str = "the restaurant"
    ) -> str:
        """Generate 2-3 sentence summary for a menu item."""
        item_name = item.get('name', 'unknown')
        sentiment = item.get('sentiment', 0)
        related_reviews = item.get('related_reviews', [])
        
        if not related_reviews:
            return f"No specific feedback found for {item_name}."
        
        review_texts = [r.get('review_text', '') for r in related_reviews[:10]]
        reviews_combined = "\n\n".join(review_texts)
        
        prompt = f"""Summarize customer feedback about "{item_name}" at {restaurant_name}.

REVIEWS MENTIONING THIS ITEM:
{reviews_combined}

TASK:
Create a 2-3 sentence summary of what customers say about {item_name}.

- Overall sentiment: {sentiment:+.2f} ({self._sentiment_label(sentiment)})
- Be specific and evidence-based
- Mention common praise points
- Mention concerns if any
- Keep it concise (2-3 sentences max)

Summary:"""
        
        try:
            response = call_claude_with_retry(
                client=self.client,
                model=self.model,
                max_tokens=200,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            return f"Unable to generate summary for {item_name}."
    
    def _sentiment_label(self, sentiment: float) -> str:
        """Convert sentiment score to label."""
        if sentiment >= 0.7:
            return "Very Positive"
        elif sentiment >= 0.3:
            return "Positive"
        elif sentiment >= 0:
            return "Mixed"
        elif sentiment >= -0.3:
            return "Negative"
        else:
            return "Very Negative"
    
    def _build_extraction_prompt(
        self,
        reviews: List[str],
        restaurant_name: str,
        max_items: int
    ) -> str:
        """Build menu extraction prompt."""
        numbered_reviews = []
        for i, review in enumerate(reviews):
            numbered_reviews.append(f"[Review {i}]: {review}")
        
        reviews_text = "\n\n".join(numbered_reviews)
        
        prompt = f"""You are analyzing customer reviews for {restaurant_name} to discover SPECIFIC menu items and drinks WITH SENTIMENT.

REVIEWS (numbered for reference):
{reviews_text}

YOUR TASK:
1. Extract SPECIFIC food items and drinks
2. Calculate sentiment for each
3. IDENTIFY WHICH REVIEWS mention each item (use review numbers!)

CRITICAL RULES:

1. GRANULARITY:
   - Keep items SEPARATE: "salmon sushi" ≠ "salmon roll" ≠ "salmon nigiri"
   - Use LOWERCASE for all item names

2. SENTIMENT ANALYSIS:
   - Calculate sentiment from context where item is mentioned
   - Score: -1.0 (very negative) to +1.0 (very positive)

3. FOOD vs DRINKS:
   - Separate food from drinks

4. REVIEW EXTRACTION:
   - For EACH item, identify which reviews mention it
   - Use review numbers
   - Include full review text

5. FILTER NOISE:
   - ❌ Skip: "food", "meal"
   - ✅ Only: SPECIFIC menu items

OUTPUT FORMAT (JSON):
{{
  "food_items": [
    {{
      "name": "item name in lowercase",
      "mention_count": number,
      "sentiment": float,
      "category": "appetizer/entree/dessert/etc",
      "related_reviews": [
        {{
          "review_index": 0,
          "review_text": "full review text",
          "sentiment_context": "quote"
        }}
      ]
    }}
  ],
  "drinks": [...same structure...],
  "total_extracted": total_count
}}

Extract ALL items (up to {max_items}):"""
        
        return prompt
