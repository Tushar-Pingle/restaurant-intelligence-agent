"""
Menu Discovery Module

Dynamically discovers menu items and drinks from restaurant reviews.
Calculates sentiment per item and provides visualizations.

Key Features:
- Extracts food items AND drinks
- Maintains granularity (salmon sushi ≠ salmon roll)
- Lowercase normalization (avoids duplicates)
- Sentiment analysis per item (context-based)
- Visualizations (text + charts)
- Works with ANY cuisine type
"""

from typing import List, Dict, Any, Optional
from anthropic import Anthropic
import json
import os


class MenuDiscovery:
    """
    Discovers menu items and drinks from reviews using AI.
    Calculates sentiment and provides visualizations.
    """
    
    def __init__(self, client: Anthropic, model: str):
        """Initialize menu discovery."""
        self.client = client
        self.model = model
    
    def extract_menu_items(
        self,
        reviews: List[str],
        restaurant_name: str = "the restaurant",
        max_items: int = 50
    ) -> Dict[str, Any]:
        """
        Extract menu items and drinks from reviews with sentiment.
        
        Args:
            reviews: List of review texts
            restaurant_name: Restaurant name for context
            max_items: Maximum items to return
        
        Returns:
            Dictionary with food_items and drinks (with sentiment)
        """
        prompt = self._build_extraction_prompt(reviews, restaurant_name, max_items)
        
        try:
            response = self.client.messages.create(
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
    
    def visualize_items_text(
        self,
        items_data: Dict[str, Any],
        top_n: int = 10
    ) -> str:
        """
        D4-013, D4-014: Create text visualization with sentiment color coding.
        
        Args:
            items_data: Extracted items data
            top_n: Number of top items to show
        
        Returns:
            Formatted text visualization
        """
        food_items = items_data.get('food_items', [])
        drinks = items_data.get('drinks', [])
        
        # Sort by mention count
        food_sorted = sorted(food_items, key=lambda x: x.get('mention_count', 0), reverse=True)
        drinks_sorted = sorted(drinks, key=lambda x: x.get('mention_count', 0), reverse=True)
        
        output = []
        output.append("=" * 70)
        output.append("TOP MENU ITEMS (with sentiment)")
        output.append("=" * 70)
        
        # Food items
        output.append(f"\n🍽️  FOOD ITEMS (Top {min(top_n, len(food_sorted))}):")
        output.append("-" * 70)
        
        for item in food_sorted[:top_n]:
            name = item.get('name', 'unknown')
            sentiment = item.get('sentiment', 0)
            mentions = item.get('mention_count', 0)
            
            # D4-014: Sentiment color coding
            if sentiment >= 0.7:
                emoji = "��"  # Green - very positive
                sentiment_text = "POSITIVE"
            elif sentiment >= 0.3:
                emoji = "🟡"  # Yellow - neutral/mixed
                sentiment_text = "MIXED"
            elif sentiment >= 0:
                emoji = "🟠"  # Orange - slightly negative
                sentiment_text = "NEUTRAL"
            else:
                emoji = "🔴"  # Red - negative
                sentiment_text = "NEGATIVE"
            
            # Create bar visualization
            bar_length = int((mentions / max([i.get('mention_count', 1) for i in food_sorted[:top_n]])) * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            output.append(f"{emoji} {name:25} [{sentiment:+.2f}] {sentiment_text:8} {bar} {mentions} mentions")
        
        # Drinks
        if drinks_sorted:
            output.append(f"\n🍹 DRINKS (Top {min(top_n, len(drinks_sorted))}):")
            output.append("-" * 70)
            
            for drink in drinks_sorted[:top_n]:
                name = drink.get('name', 'unknown')
                sentiment = drink.get('sentiment', 0)
                mentions = drink.get('mention_count', 0)
                
                if sentiment >= 0.7:
                    emoji = "🟢"
                    sentiment_text = "POSITIVE"
                elif sentiment >= 0.3:
                    emoji = "🟡"
                    sentiment_text = "MIXED"
                elif sentiment >= 0:
                    emoji = "🟠"
                    sentiment_text = "NEUTRAL"
                else:
                    emoji = "🔴"
                    sentiment_text = "NEGATIVE"
                
                if drinks_sorted[:top_n]:
                    max_mentions = max([d.get('mention_count', 1) for d in drinks_sorted[:top_n]])
                    bar_length = int((mentions / max_mentions) * 20)
                else:
                    bar_length = 0
                bar = "█" * bar_length + "░" * (20 - bar_length)
                
                output.append(f"{emoji} {name:25} [{sentiment:+.2f}] {sentiment_text:8} {bar} {mentions} mentions")
        
        output.append("=" * 70)
        
        return "\n".join(output)
    
    def visualize_items_chart(
        self,
        items_data: Dict[str, Any],
        output_path: str = "menu_analysis.png",
        top_n: int = 10
    ) -> str:
        """
        D4-013, D4-014: Create chart visualization with sentiment colors.
        
        NOTE: Charts will be displayed in Gradio UI (Day 15-16).
        For now, saves to file for testing.
        
        Args:
            items_data: Extracted items data
            output_path: Path to save chart
            top_n: Number of items to show
        
        Returns:
            Path to saved chart
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            
            food_items = items_data.get('food_items', [])
            food_sorted = sorted(food_items, key=lambda x: x.get('mention_count', 0), reverse=True)[:top_n]
            
            if not food_sorted:
                return None
            
            # Prepare data
            names = [item.get('name', 'unknown')[:20] for item in food_sorted]
            mentions = [item.get('mention_count', 0) for item in food_sorted]
            sentiments = [item.get('sentiment', 0) for item in food_sorted]
            
            # D4-014: Color coding by sentiment
            colors = []
            for sentiment in sentiments:
                if sentiment >= 0.7:
                    colors.append('#4CAF50')  # Green - positive
                elif sentiment >= 0.3:
                    colors.append('#FFC107')  # Yellow - mixed
                elif sentiment >= 0:
                    colors.append('#FF9800')  # Orange - neutral
                else:
                    colors.append('#F44336')  # Red - negative
            
            # Create chart
            fig, ax = plt.subplots(figsize=(12, 8))
            bars = ax.barh(names, mentions, color=colors)
            
            ax.set_xlabel('Number of Mentions', fontsize=12)
            ax.set_ylabel('Menu Items', fontsize=12)
            ax.set_title('Top Menu Items by Mentions (Color = Sentiment)', fontsize=14, fontweight='bold')
            
            # Add sentiment scores as text
            for i, (bar, sentiment) in enumerate(zip(bars, sentiments)):
                width = bar.get_width()
                ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
                       f'{sentiment:+.2f}',
                       ha='left', va='center', fontsize=10)
            
            # Legend
            green_patch = mpatches.Patch(color='#4CAF50', label='Positive (≥0.7)')
            yellow_patch = mpatches.Patch(color='#FFC107', label='Mixed (0.3-0.7)')
            orange_patch = mpatches.Patch(color='#FF9800', label='Neutral (0-0.3)')
            red_patch = mpatches.Patch(color='#F44336', label='Negative (<0)')
            ax.legend(handles=[green_patch, yellow_patch, orange_patch, red_patch], 
                     loc='lower right')
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return output_path
            
        except ImportError:
            print("⚠️  matplotlib not installed - skipping chart generation")
            print("   Install with: pip install matplotlib")
            return None
        except Exception as e:
            print(f"❌ Error creating chart: {e}")
            return None
    
    def save_results(
        self,
        items_data: Dict[str, Any],
        output_path: str = "menu_analysis.json"
    ) -> str:
        """
        D4-015: Save menu analysis results to JSON.
        
        Args:
            items_data: Extracted items data
            output_path: Path to save JSON
        
        Returns:
            Path to saved file
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(items_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Menu analysis saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return None
    
    def _build_extraction_prompt(
        self,
        reviews: List[str],
        restaurant_name: str,
        max_items: int
    ) -> str:
        """Build menu extraction prompt with sentiment analysis."""
        review_sample = reviews[:100] if len(reviews) > 100 else reviews
        reviews_text = "\n\n---\n\n".join(review_sample)
        
        prompt = f"""You are analyzing customer reviews for {restaurant_name} to discover SPECIFIC menu items and drinks WITH SENTIMENT.

REVIEWS:
{reviews_text}

YOUR TASK:
Extract SPECIFIC food items and drinks mentioned in reviews AND calculate sentiment for each.

CRITICAL RULES:

1. GRANULARITY:
   - Keep items SEPARATE and SPECIFIC
   - "salmon sushi" ≠ "salmon roll" ≠ "salmon nigiri" (all different!)
   - Extract the EXACT item name customers use
   - Use LOWERCASE for all item names

2. SENTIMENT ANALYSIS:
   - For EACH item, analyze sentiment from the CONTEXT where it's mentioned
   - Look at the sentence/phrase around the item mention
   - Score: -1.0 (very negative) to +1.0 (very positive)
   
   Examples:
   - "The salmon sushi was amazing" → +0.9
   - "Salmon sushi was okay" → +0.3
   - "Disappointed with the salmon sushi" → -0.6

3. FOOD vs DRINKS:
   - Separate food from drinks
   - Differentiate: cocktails ≠ wine ≠ beer ≠ coffee

4. FILTER NOISE:
   - ❌ Skip: "food", "meal", "dish", "delicious" (generic terms)
   - ✅ Only: SPECIFIC menu items

OUTPUT FORMAT (JSON):
{{
  "food_items": [
    {{
      "name": "item name in lowercase",
      "mention_count": number,
      "sentiment": float (-1.0 to 1.0),
      "category": "appetizer/entree/dessert/etc",
      "example_context": "quote showing sentiment"
    }}
  ],
  "drinks": [
    {{
      "name": "drink name in lowercase",
      "mention_count": number,
      "sentiment": float (-1.0 to 1.0),
      "type": "cocktail/wine/beer/coffee/etc",
      "example_context": "quote showing sentiment"
    }}
  ],
  "total_extracted": total_count
}}

Extract ALL items with sentiment (up to {max_items} items):"""
        
        return prompt


if __name__ == "__main__":
    print("Testing menu discovery with visualization...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    discovery = MenuDiscovery(client=client, model="claude-sonnet-4-20250514")
    
    # Quick test
    sample_reviews = [
        "The salmon sushi was incredible! Best I've ever had.",
        "Miso soup was authentic and warming. Perfect.",
        "Tempura was disappointing - too oily.",
    ]
    
    result = discovery.extract_menu_items(sample_reviews, "Test Restaurant")
    
    # Test visualizations
    print(discovery.visualize_items_text(result, top_n=5))
    
    chart_path = discovery.visualize_items_chart(result, "test_menu.png", top_n=5)
    if chart_path:
        print(f"\n📊 Chart saved to: {chart_path}")
    
    json_path = discovery.save_results(result, "test_menu.json")
    print(f"💾 JSON saved to: {json_path}")
