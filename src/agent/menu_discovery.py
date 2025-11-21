"""
Menu Discovery Module

Dynamically discovers menu items and drinks from restaurant reviews.
Calculates sentiment per item based on context.

Key Features:
- Extracts food items AND drinks
- Maintains granularity (salmon sushi ≠ salmon roll)
- Lowercase normalization (avoids duplicates)
- Sentiment analysis per item (context-based)
- Works with ANY cuisine type

UNIVERSAL DESIGN:
- Japanese: discovers sushi, sashimi, tempura variants
- Italian: discovers pizza types, pasta dishes, wines
- Mexican: discovers taco variants, margaritas, tequilas
"""

from typing import List, Dict, Any, Optional
from anthropic import Anthropic
import json


class MenuDiscovery:
    """
    Discovers menu items and drinks from reviews using AI.
    Calculates sentiment for each discovered item.
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
        # Build extraction prompt
        prompt = self._build_extraction_prompt(reviews, restaurant_name, max_items)
        
        try:
            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON
            result_text = response.content[0].text
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            extracted_data = json.loads(result_text)
            
            # D3-010: Normalize to lowercase
            extracted_data = self._normalize_items(extracted_data)
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse menu items: {e}")
            return {"food_items": [], "drinks": [], "total_extracted": 0}
        except Exception as e:
            print(f"❌ Error extracting menu items: {e}")
            return {"food_items": [], "drinks": [], "total_extracted": 0}
    
    def _normalize_items(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        D3-010: Normalize item names to lowercase.
        
        Avoids duplicates like "Miku Roll" vs "miku roll"
        """
        for item in data.get('food_items', []):
            if 'name' in item:
                item['name'] = item['name'].lower()
        
        for drink in data.get('drinks', []):
            if 'name' in drink:
                drink['name'] = drink['name'].lower()
        
        return data
    
    def _build_extraction_prompt(
        self,
        reviews: List[str],
        restaurant_name: str,
        max_items: int
    ) -> str:
        """
        Build menu extraction prompt with sentiment analysis.
        
        D3-016: Added sentiment per item
        """
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

2. SENTIMENT ANALYSIS (D3-016):
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


# D3-018, D3-019, D3-020: Test with multiple cuisine types
if __name__ == "__main__":
    print("=" * 70)
    print("D3-018: Testing Menu Discovery - Multiple Cuisine Types")
    print("=" * 70 + "\n")
    
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    discovery = MenuDiscovery(client=client, model="claude-sonnet-4-20250514")
    
    # D3-018: Test 1 - Japanese (Complex human-like reviews)
    print("=" * 70)
    print("TEST 1: JAPANESE RESTAURANT (Miku)")
    print("=" * 70 + "\n")
    
    japanese_reviews = [
        "So I went to Miku last night and omg the salmon sushi was absolutely incredible!! Like seriously the best I've ever had. The fish was so fresh it practically melted in my mouth. We also got their famous aburi salmon roll which was phenomenal - that torch-seared flavor is just *chef's kiss*",
        "Tried the spicy tuna roll today and honestly? I was a bit disappointed. It wasn't as spicy as I expected and the fish seemed kinda off. The presentation was beautiful though I'll give them that. Also ordered hot sake which was perfect temperature",
        "Their miso soup is THE BEST. I'm not even joking, it's so much better than any other Japanese place I've been to. The broth is rich and flavorful without being too salty. Got the tempura too - super crispy and not greasy at all!",
        "The sashimi platter here is insane. We got salmon, tuna, and hamachi and every single piece was perfection. Paired it with a glass of plum wine that complemented everything so well. Honestly can't stop thinking about it",
        "Okay so the california roll was decent but nothing special tbh. BUT the dragon roll?? Now THAT was amazing. Also their edamame was really fresh and perfectly salted. We had green tea which was nice and soothing",
        "Just had the Miku signature roll and WOW. This is why people rave about this place. The combination of flavors is just unreal. Also tried their gyoza which were perfectly crispy on the bottom. 10/10 would recommend",
        "The tuna tartare was super fresh and the presentation was gorgeous! Had it with an Asahi beer and it was such a good combo. Everything tasted really high quality",
        "Their salmon nigiri is literally perfection. Like it just melts in your mouth you know? Also ordered the uni and honestly I wasn't sure I'd like it but it was surprisingly delicious! Really creamy texture",
        "So we got the tonkotsu ramen and omg the broth was so rich and flavorful. Been craving it ever since!! Also had cold sake this time which was super refreshing with the hot ramen",
        "The tempura vegetables were amazing - so light and crispy! But I gotta say the shrimp tempura was even better. Perfect batter. Whole meal was just really really good"
    ]
    
    japanese_result = discovery.extract_menu_items(
        reviews=japanese_reviews,
        restaurant_name="Miku Restaurant"
    )
    
    print(f"📊 Japanese Results:")
    print(f"   Food items: {len(japanese_result.get('food_items', []))}")
    print(f"   Drinks: {len(japanese_result.get('drinks', []))}\n")
    
    print("Top Japanese Food Items (with sentiment):")
    for item in japanese_result.get('food_items', [])[:5]:
        name = item.get('name', 'unknown')
        sentiment = item.get('sentiment', 0)
        mentions = item.get('mention_count', 0)
        emoji = "😊" if sentiment > 0.5 else "😐" if sentiment > 0 else "😞"
        print(f"  {emoji} {name} (sentiment: {sentiment:+.2f}, mentions: {mentions})")
    
    # D3-018: Test 2 - Italian (Complex human-like reviews)
    print("\n" + "=" * 70)
    print("TEST 2: ITALIAN RESTAURANT")
    print("=" * 70 + "\n")
    
    italian_reviews = [
        "Just came back from this Italian spot and the margherita pizza was honestly life-changing. Like the dough was perfectly charred and the sauce was so fresh and sweet. You could taste the quality of everything. Also got a glass of chianti that was really smooth",
        "Had the carbonara pasta last night and I'm still thinking about it lol. The sauce was so creamy and rich, and they don't skimp on the guanciale. Paired it with a nice pinot grigio which cut through the richness perfectly",
        "So disappointed with the pepperoni pizza :( The crust was kinda soggy and there was way too much grease. The bruschetta appetizer was good though - tomatoes were really fresh. Got a cappuccino after which was decent",
        "Their tiramisu is absolutely divine!! Best I've had outside of Italy honestly. The espresso flavor really comes through and it's not too sweet. Also tried the panna cotta which was silky smooth",
        "The lasagna here is HUGE and so rich. Like you definitely need to share it lol. Layers upon layers of pasta, meat sauce, and cheese. Washed it down with a bottle of montepulciano",
        "Got the arugula salad with parmesan and it was so simple but so good. Sometimes less is more you know? The balsamic was really high quality. Also had their focaccia bread which was amazing - so fluffy inside",
        "Their seafood pasta was incredible! So many mussels, clams, and shrimp in a light white wine sauce. Not heavy at all. Had it with a glass of prosecco which was perfect for the meal",
        "The four cheese pizza (quattro formaggi) was wayyyy too rich for me. Like I love cheese but this was overwhelming. The crust was good though. Espresso at the end was strong and good",
        "Just had the best gnocchi of my life here!! They make it fresh daily and you can tell - so pillowy soft. The brown butter sage sauce was perfection. Red wine was a nice sangiovese",
        "Their Caesar salad with grilled chicken was really fresh and the dressing was made from scratch. Simple but done right. Finished with an amaretto which was a nice digestif"
    ]
    
    italian_result = discovery.extract_menu_items(
        reviews=italian_reviews,
        restaurant_name="Italian Bistro"
    )
    
    print(f"📊 Italian Results:")
    print(f"   Food items: {len(italian_result.get('food_items', []))}")
    print(f"   Drinks: {len(italian_result.get('drinks', []))}\n")
    
    print("Top Italian Food Items (with sentiment):")
    for item in italian_result.get('food_items', [])[:5]:
        name = item.get('name', 'unknown')
        sentiment = item.get('sentiment', 0)
        mentions = item.get('mention_count', 0)
        emoji = "😊" if sentiment > 0.5 else "😐" if sentiment > 0 else "😞"
        print(f"  {emoji} {name} (sentiment: {sentiment:+.2f}, mentions: {mentions})")
    
    # D3-018: Test 3 - Mexican (Complex human-like reviews)
    print("\n" + "=" * 70)
    print("TEST 3: MEXICAN RESTAURANT")
    print("=" * 70 + "\n")
    
    mexican_reviews = [
        "OMG the tacos al pastor here are absolutely insane!! The pork is so juicy and flavorful, and that pineapple on top just takes it to another level. Got a frozen margarita with it and it was the perfect combo on a hot day",
        "So I ordered the chicken burrito and it was massive but honestly kinda bland? Like it needed more seasoning. The guacamole on the side was really fresh though - you could tell it was made to order. Had a Corona which was ice cold",
        "Their carne asada tacos are where it's at!! The meat is so tender and charred perfectly. Comes with the best salsa verde I've ever had. Also tried their horchata which was sweet and creamy - so good!",
        "Just had the fish tacos and wow they were so light and fresh! The slaw on top had a nice tang to it. This is definitely my new go-to spot. Paired it with a modelo and watched the game",
        "The quesadilla was good but nothing mind-blowing tbh. Cheese was nicely melted though. BUT the chips and salsa they bring out? Addictive! I could eat those all day. Had a jarritos tamarind soda which was refreshing",
        "So the mole enchiladas here are absolutely incredible. The sauce is so rich and complex - you can taste all the different spices. Takes hours to make and you can tell. Also ordered a shot of tequila which was smooth",
        "Their carnitas are LEGIT. Slow-cooked pork that's crispy on the outside and tender inside. Put it in a torta with beans and avocado and it was heaven. Washed down with a michelada",
        "Tried the vegetarian burrito bowl and honestly? Really impressed! Usually veggie options are afterthoughts but this was packed with flavor. Black beans, grilled veggies, pico de gallo all fresh. Had agua fresca on the side",
        "The churros here omg. Crispy outside, soft inside, covered in cinnamon sugar. Came with chocolate sauce for dipping. Perfect way to end the meal! Also had Mexican hot chocolate which was thick and rich",
        "Got the shrimp ceviche and it was so fresh and zesty! Perfect amount of lime juice. Really refreshing appetizer. Followed it up with fish tacos and a paloma cocktail with grapefruit"
    ]
    
    mexican_result = discovery.extract_menu_items(
        reviews=mexican_reviews,
        restaurant_name="Mexican Cantina"
    )
    
    print(f"📊 Mexican Results:")
    print(f"   Food items: {len(mexican_result.get('food_items', []))}")
    print(f"   Drinks: {len(mexican_result.get('drinks', []))}\n")
    
    print("Top Mexican Food Items (with sentiment):")
    for item in mexican_result.get('food_items', [])[:5]:
        name = item.get('name', 'unknown')
        sentiment = item.get('sentiment', 0)
        mentions = item.get('mention_count', 0)
        emoji = "😊" if sentiment > 0.5 else "😐" if sentiment > 0 else "😞"
        print(f"  {emoji} {name} (sentiment: {sentiment:+.2f}, mentions: {mentions})")
    
    # D3-019: Accuracy Analysis
    print("\n" + "=" * 70)
    print("D3-019: ACCURACY ANALYSIS")
    print("=" * 70 + "\n")
    
    # Check if expected items were found
    japanese_names = [item['name'] for item in japanese_result.get('food_items', [])]
    italian_names = [item['name'] for item in italian_result.get('food_items', [])]
    mexican_names = [item['name'] for item in mexican_result.get('food_items', [])]
    
    # Expected items
    expected_japanese = ['sushi', 'roll', 'sashimi', 'tempura', 'ramen']
    expected_italian = ['pizza', 'pasta', 'tiramisu']
    expected_mexican = ['tacos', 'burrito', 'enchiladas', 'ceviche']
    
    def check_expected(names, expected, cuisine):
        found = []
        for exp in expected:
            if any(exp in name for name in names):
                found.append(exp)
        
        print(f"{cuisine} Cuisine:")
        print(f"  Expected items found: {len(found)}/{len(expected)}")
        for item in found:
            print(f"    ✅ {item}")
        missing = set(expected) - set(found)
        if missing:
            print(f"  Missing: {missing}")
        return len(found) / len(expected)
    
    japanese_acc = check_expected(japanese_names, expected_japanese, "Japanese")
    print()
    italian_acc = check_expected(italian_names, expected_italian, "Italian")
    print()
    mexican_acc = check_expected(mexican_names, expected_mexican, "Mexican")
    
    overall_acc = (japanese_acc + italian_acc + mexican_acc) / 3
    print(f"\n📊 Overall Accuracy: {overall_acc*100:.1f}%")
    
    # Check lowercase normalization
    print("\n" + "=" * 70)
    print("LOWERCASE NORMALIZATION CHECK")
    print("=" * 70)
    
    all_items = japanese_names + italian_names + mexican_names
    has_uppercase = any(name != name.lower() for name in all_items)
    
    if has_uppercase:
        print("⚠️  Found uppercase in names")
    else:
        print("✅ All names properly lowercase")
    
    # Check sentiment range
    print("\n" + "=" * 70)
    print("SENTIMENT VALIDATION")
    print("=" * 70 + "\n")
    
    all_results = japanese_result.get('food_items', []) + italian_result.get('food_items', []) + mexican_result.get('food_items', [])
    
    sentiments = [item.get('sentiment', 0) for item in all_results]
    
    if sentiments:
        avg_sentiment = sum(sentiments) / len(sentiments)
        min_sentiment = min(sentiments)
        max_sentiment = max(sentiments)
        
        print(f"Sentiment range: {min_sentiment:.2f} to {max_sentiment:.2f}")
        print(f"Average sentiment: {avg_sentiment:.2f}")
        
        valid = all(-1.0 <= s <= 1.0 for s in sentiments)
        print(f"All sentiments in range [-1, 1]: {valid}")
    
    print("\n" + "=" * 70)
    print("🎉 Multi-cuisine test complete!")
    print("=" * 70)
    print("\n✅ D3-010: Lowercase normalization - COMPLETE")
    print("✅ D3-016: Sentiment per item - COMPLETE")
    print("✅ D3-018: Multi-cuisine testing - COMPLETE")
    print("✅ D3-019: Accuracy validation - COMPLETE")