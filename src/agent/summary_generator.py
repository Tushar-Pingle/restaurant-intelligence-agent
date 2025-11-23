"""
Summary Generator for Menu Items and Aspects

Generates coherent AI summaries for each menu item and aspect
by synthesizing all related review mentions.
"""

from typing import Dict, List, Any
from anthropic import Anthropic
import json


class SummaryGenerator:
    """
    Generates AI-powered summaries for menu items and aspects.
    """
    
    def __init__(self, client: Anthropic, model: str = "claude-sonnet-4-20250514"):
        self.client = client
        self.model = model
    
    def generate_menu_summaries(
        self,
        menu_data: Dict[str, Any],
        restaurant_name: str = "the restaurant"
    ) -> Dict[str, Any]:
        """
        Add AI-generated summaries to menu items.
        
        Args:
            menu_data: Menu analysis with food_items and drinks
            restaurant_name: Name of restaurant for context
            
        Returns:
            Updated menu_data with summary field added to each item
        """
        # Process food items
        if 'food_items' in menu_data:
            menu_data['food_items'] = self._add_summaries_to_items(
                menu_data['food_items'],
                restaurant_name,
                item_type="menu item"
            )
        
        # Process drinks
        if 'drinks' in menu_data:
            menu_data['drinks'] = self._add_summaries_to_items(
                menu_data['drinks'],
                restaurant_name,
                item_type="drink"
            )
        
        return menu_data
    
    def generate_aspect_summaries(
        self,
        aspect_data: Dict[str, Any],
        restaurant_name: str = "the restaurant"
    ) -> Dict[str, Any]:
        """
        Add AI-generated summaries to aspects.
        
        Args:
            aspect_data: Aspect analysis with aspects array
            restaurant_name: Name of restaurant for context
            
        Returns:
            Updated aspect_data with summary field added to each aspect
        """
        if 'aspects' in aspect_data:
            aspect_data['aspects'] = self._add_summaries_to_items(
                aspect_data['aspects'],
                restaurant_name,
                item_type="aspect"
            )
        
        return aspect_data
    
    def _add_summaries_to_items(
        self,
        items: List[Dict[str, Any]],
        restaurant_name: str,
        item_type: str
    ) -> List[Dict[str, Any]]:
        """
        Add summaries to a list of items (menu items or aspects).
        Processes in batches for efficiency.
        """
        if not items:
            return items
        
        # Process in batches of 10 items
        batch_size = 10
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            
            print(f"   Generating summaries for {len(batch)} {item_type}s...")
            
            # Generate summaries for this batch
            summaries = self._generate_batch_summaries(
                batch,
                restaurant_name,
                item_type
            )
            
            # Add summaries to items
            for j, item in enumerate(batch):
                item_name = item.get('name', 'unknown')
                if item_name in summaries:
                    item['summary'] = summaries[item_name]
                else:
                    # Fallback: Create simple summary from sentiment context
                    item['summary'] = self._create_fallback_summary(item, item_type)
        
        return items
    
    def _generate_batch_summaries(
        self,
        items: List[Dict[str, Any]],
        restaurant_name: str,
        item_type: str
    ) -> Dict[str, str]:
        """
        Generate summaries for a batch of items using Claude API.
        """
        prompt = self._build_summary_prompt(items, restaurant_name, item_type)
        
        try:
            import time
            time.sleep(2)  # Add 2 second delay between summary batches
    
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            summaries = json.loads(result_text)
            return summaries.get('summaries', {})
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️  Failed to parse summaries: {e}")
            return {}
        except Exception as e:
            print(f"   ⚠️  Error generating summaries: {e}")
            return {}
    
    def _build_summary_prompt(
        self,
        items: List[Dict[str, Any]],
        restaurant_name: str,
        item_type: str
    ) -> str:
        """Build prompt for batch summary generation."""
        
        # Prepare items data
        items_data = []
        for item in items:
            name = item.get('name', 'unknown')
            sentiment = item.get('sentiment', 0)
            mention_count = item.get('mention_count', 0)
            related_reviews = item.get('related_reviews', [])
            
            # Extract all sentiment contexts
            contexts = [r.get('sentiment_context', '') for r in related_reviews if r.get('sentiment_context')]
            
            items_data.append({
                'name': name,
                'sentiment': sentiment,
                'mention_count': mention_count,
                'contexts': contexts
            })
        
        items_json = json.dumps(items_data, indent=2)
        
        prompt = f"""You are summarizing customer feedback for {restaurant_name}.

For each {item_type} below, create a 2-3 sentence summary that:
1. Synthesizes what customers say across ALL mentions
2. Highlights the overall sentiment (positive/negative/mixed)
3. Mentions specific details customers care about
4. Is written for restaurant owners/managers to understand customer opinion

{item_type.upper()}S TO SUMMARIZE:
{items_json}

OUTPUT FORMAT (JSON):
{{
  "summaries": {{
    "{item_type} name 1": "Summary sentence 1. Summary sentence 2.",
    "{item_type} name 2": "Summary sentence 1. Summary sentence 2."
  }}
}}

Rules:
- Each summary must be 2-3 complete sentences
- Use specific details from the contexts provided
- Match the sentiment score (positive if >0.3, negative if <-0.3, mixed otherwise)
- Write in professional, actionable language
- Output ONLY valid JSON

Generate summaries:"""
        
        return prompt
    
    def _create_fallback_summary(
        self,
        item: Dict[str, Any],
        item_type: str
    ) -> str:
        """
        Create a simple fallback summary if AI generation fails.
        """
        name = item.get('name', 'this item')
        sentiment = item.get('sentiment', 0)
        mention_count = item.get('mention_count', 0)
        related_reviews = item.get('related_reviews', [])
        
        # Get first context as example
        first_context = ""
        if related_reviews and related_reviews[0].get('sentiment_context'):
            first_context = related_reviews[0]['sentiment_context']
        
        # Create simple summary based on sentiment
        if sentiment > 0.3:
            tone = "positively received"
        elif sentiment < -0.3:
            tone = "received negative feedback"
        else:
            tone = "received mixed feedback"
        
        summary = f"The {name} is {tone} by customers, mentioned in {mention_count} review(s)."
        
        if first_context:
            summary += f" Customers noted: '{first_context[:100]}...'"
        
        return summary


def add_summaries_to_analysis(
    menu_data: Dict[str, Any],
    aspect_data: Dict[str, Any],
    client: Anthropic,
    restaurant_name: str = "the restaurant",
    model: str = "claude-sonnet-4-20250514"
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Convenience function to add summaries to both menu and aspect data.
    
    Args:
        menu_data: Menu analysis dictionary
        aspect_data: Aspect analysis dictionary
        client: Anthropic API client
        restaurant_name: Name of restaurant
        model: Claude model to use
        
    Returns:
        Tuple of (updated_menu_data, updated_aspect_data)
    """
    print("\n🤖 Generating AI summaries for menu items and aspects...")
    
    generator = SummaryGenerator(client, model)
    
    # Generate menu summaries
    print("\n📋 Menu Item Summaries:")
    menu_data = generator.generate_menu_summaries(menu_data, restaurant_name)
    
    # Generate aspect summaries
    print("\n🔍 Aspect Summaries:")
    aspect_data = generator.generate_aspect_summaries(aspect_data, restaurant_name)
    
    print("✅ All summaries generated!\n")
    
    return menu_data, aspect_data


if __name__ == "__main__":
    # Test the summary generator
    from anthropic import Anthropic
    import os
    
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    # Sample menu data
    test_menu = {
        "food_items": [
            {
                "name": "salmon oshi sushi",
                "sentiment": 0.85,
                "mention_count": 5,
                "related_reviews": [
                    {"sentiment_context": "The salmon oshi sushi was incredible, so fresh and beautifully presented"},
                    {"sentiment_context": "Best salmon dish I've ever had, melts in your mouth"}
                ]
            }
        ]
    }
    
    # Test generation
    generator = SummaryGenerator(client)
    result = generator.generate_menu_summaries(test_menu, "Test Restaurant")
    
    print(json.dumps(result, indent=2))