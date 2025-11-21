"""
Menu Discovery Module

Dynamically discovers menu items and drinks from restaurant reviews.
NO hardcoding - works with ANY restaurant type!

Key Features:
- Extracts food items AND drinks
- Maintains granularity (salmon sushi ≠ salmon roll)
- Reads full review context for validation
- Filters generic noise
- Differentiates drink types (cocktails, wine, beer, coffee)

UNIVERSAL DESIGN:
- Japanese: discovers sushi, sashimi, tempura variants
- Italian: discovers pizza types, pasta dishes, wines
- Mexican: discovers taco variants, margaritas, tequilas
- Burger shop: discovers different burger types separately
"""

from typing import List, Dict, Any, Optional
from anthropic import Anthropic
import json


class MenuDiscovery:
    """
    Discovers menu items and drinks from reviews using AI.
    
    Example:
        discovery = MenuDiscovery(client, model)
        
        # Extract items from reviews
        items = discovery.extract_menu_items(reviews)
        
        # Returns granular items:
        # ["salmon sushi", "tuna sashimi", "spicy tuna roll", 
        #  "sake (hot)", "plum wine", "green tea"]
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
        D3-004: Extract menu items and drinks from reviews.
        
        Args:
            reviews: List of review texts
            restaurant_name: Restaurant name for context
            max_items: Maximum items to return (default 50)
        
        Returns:
            Dictionary with:
                - food_items: List of food items with details
                - drinks: List of drinks with details
                - total_extracted: Total count
        """
        # D3-003: Build the extraction prompt
        prompt = self._build_extraction_prompt(reviews, restaurant_name, max_items)
        
        try:
            # Call Claude to extract items
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.3,  # Lower temp for consistent extraction
                messages=[{"role": "user", "content": prompt}]
            )
            
            # D3-005: Parse JSON response
            result_text = response.content[0].text
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            extracted_data = json.loads(result_text)
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse menu items: {e}")
            return {"food_items": [], "drinks": [], "total_extracted": 0}
        except Exception as e:
            print(f"❌ Error extracting menu items: {e}")
            return {"food_items": [], "drinks": [], "total_extracted": 0}
    
    def _build_extraction_prompt(
        self,
        reviews: List[str],
        restaurant_name: str,
        max_items: int
    ) -> str:
        """
        D3-003: Build the menu extraction prompt.
        D3-008: Refined to reduce noise.
        
        Args:
            reviews: Review texts
            restaurant_name: Restaurant name
            max_items: Max items to extract
        
        Returns:
            Formatted prompt
        """
        # Sample reviews if too many
        review_sample = reviews[:100] if len(reviews) > 100 else reviews
        reviews_text = "\n\n---\n\n".join(review_sample)
        
        prompt = f"""You are analyzing customer reviews for {restaurant_name} to discover SPECIFIC menu items and drinks.

REVIEWS:
{reviews_text}

YOUR TASK:
Extract SPECIFIC food items and drinks mentioned in these reviews.

CRITICAL RULES:

1. GRANULARITY (Most Important):
   - Keep items SEPARATE and SPECIFIC
   - "salmon sushi" ≠ "salmon roll" ≠ "salmon nigiri" (all different!)
   - "margherita pizza" ≠ "pepperoni pizza" (different items!)
   - "beef burger" ≠ "chicken burger" ≠ "veggie burger" (all separate!)
   - Extract the EXACT item name customers use

2. FOOD vs DRINKS:
   - Separate food items from drinks
   - Differentiate drink types: cocktails ≠ wine ≠ beer ≠ coffee ≠ tea
   - "margarita" ≠ "red wine" ≠ "latte" (all different categories!)

3. CONTEXT VALIDATION:
   - READ THE FULL REVIEW to confirm it's actually a menu item
   - "Miku special" is OK if review confirms it's a dish
   - Include specialty/signature items if context confirms they exist

4. FILTER NOISE (Critical):
   - ❌ Skip generic terms: "food", "meal", "dish", "entree", "appetizer"
   - ❌ Skip adjectives alone: "delicious", "amazing", "fresh"
   - ❌ Skip non-items: "service", "atmosphere", "experience"
   - ✅ Only extract SPECIFIC menu items that customers ordered

5. MENTION TRACKING:
   - Count how many reviews mention each item
   - Even items mentioned ONCE should be included
   - We want comprehensive coverage (up to {max_items} items)

OUTPUT FORMAT (JSON):
{{
  "food_items": [
    {{
      "name": "exact item name from reviews",
      "mention_count": number,
      "category": "appetizer/entree/dessert/etc",
      "example_context": "short quote showing it's real"
    }}
  ],
  "drinks": [
    {{
      "name": "exact drink name",
      "mention_count": number,
      "type": "cocktail/wine/beer/coffee/tea/sake/etc",
      "example_context": "short quote showing it's real"
    }}
  ],
  "total_extracted": total_count
}}

EXAMPLES OF GOOD EXTRACTION:

✅ Japanese Restaurant:
- "salmon sushi", "tuna sashimi", "spicy tuna roll", "sake (hot)", "plum wine"

✅ Burger Shop:
- "classic beef burger", "chicken burger", "veggie burger", "truffle fries"

✅ Italian Restaurant:
- "margherita pizza", "pepperoni pizza", "carbonara pasta", "chianti wine"

NOW extract ALL specific menu items and drinks (aim for up to {max_items} items):"""
        
        return prompt


# D3-006 & D3-007: Test with sample data
if __name__ == "__main__":
    print("=" * 70)
    print("D3-006: Testing Menu Discovery with Sample Reviews")
    print("=" * 70 + "\n")
    
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Initialize
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    discovery = MenuDiscovery(client=client, model="claude-sonnet-4-20250514")
    
    # D3-006: Sample reviews (simulating Miku Japanese restaurant)
    sample_reviews = [
        "The salmon sushi was absolutely incredible! Fresh and perfectly prepared. Also tried the miso soup which was authentic.",
        "Ordered the spicy tuna roll and it did not disappoint. The presentation was beautiful. Had hot sake with it.",
        "Their aburi salmon is a must-try! Also got the edamame as an appetizer. Green tea was nice.",
        "Best sashimi platter I've ever had. Included salmon, tuna, and hamachi. Paired with a glass of plum wine.",
        "The tempura was crispy and not oily at all. Loved the tempura vegetables too. Great food overall.",
        "California roll was good but the dragon roll was even better. Service was excellent.",
        "Tried their signature Miku roll - amazing! Also ordered gyoza which were perfectly pan-fried.",
        "The tuna tartare was fresh and flavorful. Had it with an Asahi beer. Everything was delicious.",
        "Salmon nigiri melts in your mouth. Also tried the uni which was incredible. Great meal.",
        "Their ramen was hearty and flavorful. Got the tonkotsu broth. Also ordered sake (cold this time).",
    ]
    
    print(f"Analyzing {len(sample_reviews)} reviews...\n")
    
    # Extract menu items
    result = discovery.extract_menu_items(
        reviews=sample_reviews,
        restaurant_name="Miku Restaurant",
        max_items=30
    )
    
    # D3-007: Analyze results for false positives
    print("=" * 70)
    print("EXTRACTION RESULTS")
    print("=" * 70 + "\n")
    
    food_items = result.get('food_items', [])
    drinks = result.get('drinks', [])
    
    print(f"📋 Total Extracted: {result.get('total_extracted', 0)}")
    print(f"   Food Items: {len(food_items)}")
    print(f"   Drinks: {len(drinks)}\n")
    
    # Display food items
    print("FOOD ITEMS:")
    print("-" * 70)
    for item in food_items:
        name = item.get('name', 'Unknown')
        count = item.get('mention_count', 0)
        category = item.get('category', 'N/A')
        context = item.get('example_context', '')[:50]
        print(f"  • {name} (mentions: {count}, category: {category})")
        print(f"    Context: \"{context}...\"")
    
    # Display drinks
    print("\nDRINKS:")
    print("-" * 70)
    for drink in drinks:
        name = drink.get('name', 'Unknown')
        count = drink.get('mention_count', 0)
        drink_type = drink.get('type', 'N/A')
        print(f"  • {name} (mentions: {count}, type: {drink_type})")
    
    # D3-007: Check for false positives
    print("\n" + "=" * 70)
    print("D3-007: FALSE POSITIVE ANALYSIS")
    print("=" * 70 + "\n")
    
    # Check for noise words
    noise_words = ['food', 'meal', 'dish', 'service', 'atmosphere', 'delicious', 'amazing']
    false_positives = []
    
    all_names = [item['name'].lower() for item in food_items] + [drink['name'].lower() for drink in drinks]
    
    for name in all_names:
        for noise in noise_words:
            if noise in name and name == noise:  # Exact match to noise word
                false_positives.append(name)
    
    if false_positives:
        print(f"⚠️  Found {len(false_positives)} potential false positives:")
        for fp in false_positives:
            print(f"  - {fp}")
    else:
        print("✅ No obvious false positives detected")
    
    # Check for expected Japanese items
    print("\n" + "=" * 70)
    print("EXPECTED ITEMS CHECK (Japanese Restaurant)")
    print("=" * 70 + "\n")
    
    expected_items = ['sushi', 'sashimi', 'roll', 'sake', 'tempura', 'miso']
    found_expected = []
    
    for expected in expected_items:
        for name in all_names:
            if expected in name:
                found_expected.append(expected)
                break
    
    print(f"Expected Japanese items found: {len(found_expected)}/{len(expected_items)}")
    for item in found_expected:
        print(f"  ✅ {item}")
    
    missing = set(expected_items) - set(found_expected)
    if missing:
        print(f"\nMissing expected items: {missing}")
    
    # Check granularity
    print("\n" + "=" * 70)
    print("GRANULARITY CHECK")
    print("=" * 70 + "\n")
    
    # Look for specific variants
    salmon_items = [item['name'] for item in food_items if 'salmon' in item['name'].lower()]
    roll_items = [item['name'] for item in food_items if 'roll' in item['name'].lower()]
    
    print(f"Salmon variants found: {len(salmon_items)}")
    for item in salmon_items:
        print(f"  • {item}")
    
    print(f"\nRoll variants found: {len(roll_items)}")
    for item in roll_items:
        print(f"  • {item}")
    
    if len(salmon_items) > 1 or len(roll_items) > 1:
        print("\n✅ Good granularity - keeping items separate!")
    else:
        print("\n⚠️  Low granularity - items might be grouped")
    
    print("\n" + "=" * 70)
    print("🎉 Menu discovery test complete!")
    print("=" * 70)
