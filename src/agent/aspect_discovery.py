"""
Aspect Discovery Module - FIXED for large review sets
Processes reviews in batches to avoid token limits
"""

from typing import List, Dict, Any, Optional
from anthropic import Anthropic
import json
import os

class AspectDiscovery:
    """
    Discovers customer-care aspects from reviews using AI.
    Handles large review sets by batching.
    """
    
    def __init__(self, client: Anthropic, model: str):
        """Initialize aspect discovery."""
        self.client = client
        self.model = model
    
    def discover_aspects(
        self,
        reviews: List[str],
        restaurant_name: str = "the restaurant",
        max_aspects: int = 12,
        batch_size: int = 15  # NEW: Process in batches
    ) -> Dict[str, Any]:
        """
        Discover aspects in batches to handle large review sets.
        
        Args:
            reviews: List of review texts
            restaurant_name: Restaurant name
            max_aspects: Max aspects to return
            batch_size: Reviews per batch (default 15)
        """
        print(f"🔍 Processing {len(reviews)} reviews in batches of {batch_size}...")
        
        all_aspects = {}
        
        # Process in batches
        for i in range(0, len(reviews), batch_size):
            batch = reviews[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(reviews) + batch_size - 1) // batch_size
            
            print(f"   Batch {batch_num}/{total_batches}: {len(batch)} reviews...")
            
            try:
                batch_result = self._discover_batch(batch, restaurant_name, max_aspects)
                
                # Merge results
                for aspect in batch_result.get('aspects', []):
                    name = aspect['name']
                    if name in all_aspects:
                        # Merge existing aspect
                        all_aspects[name]['mention_count'] += aspect['mention_count']
                        all_aspects[name]['related_reviews'].extend(aspect.get('related_reviews', []))
                        # Average sentiment
                        old_sent = all_aspects[name]['sentiment']
                        new_sent = aspect['sentiment']
                        all_aspects[name]['sentiment'] = (old_sent + new_sent) / 2
                    else:
                        all_aspects[name] = aspect
                
            except Exception as e:
                print(f"   ⚠️  Batch {batch_num} failed: {e}")
                continue
        
        # Convert back to list
        aspects_list = list(all_aspects.values())
        
        # Sort by mention count
        aspects_list.sort(key=lambda x: x['mention_count'], reverse=True)
        
        # Limit results
        aspects_list = aspects_list[:max_aspects]
        
        print(f"✅ Discovered {len(aspects_list)} aspects")
        
        return {
            "aspects": aspects_list,
            "total_aspects": len(aspects_list)
        }
    
    def _discover_batch(
        self,
        reviews: List[str],
        restaurant_name: str,
        max_aspects: int
    ) -> Dict[str, Any]:
        """Discover aspects from a single batch."""
        prompt = self._build_extraction_prompt(reviews, restaurant_name, max_aspects)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            aspects_data = json.loads(result_text)
            aspects_data = self._normalize_aspects(aspects_data)
            
            return aspects_data
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse aspects: {e}")
            return {"aspects": [], "total_aspects": 0}
        except Exception as e:
            print(f"❌ Error discovering aspects: {e}")
            return {"aspects": [], "total_aspects": 0}
    
    def _normalize_aspects(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize aspect names to lowercase."""
        for aspect in data.get('aspects', []):
            if 'name' in aspect:
                aspect['name'] = aspect['name'].lower()
        
        return data
    
    def visualize_aspects_text(
        self,
        aspects_data: Dict[str, Any],
        top_n: int = 10
    ) -> str:
        """Create text visualization for aspects with sentiment color coding."""
        aspects = aspects_data.get('aspects', [])
        
        # Sort by mention count
        aspects_sorted = sorted(aspects, key=lambda x: x.get('mention_count', 0), reverse=True)
        
        output = []
        output.append("=" * 70)
        output.append("DISCOVERED ASPECTS (with sentiment)")
        output.append("=" * 70)
        
        output.append(f"\n📊 ASPECTS (Top {min(top_n, len(aspects_sorted))}):")
        output.append("-" * 70)
        
        for aspect in aspects_sorted[:top_n]:
            name = aspect.get('name', 'unknown')
            sentiment = aspect.get('sentiment', 0)
            mentions = aspect.get('mention_count', 0)
            
            # Sentiment color coding
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
            
            # Create bar visualization
            if aspects_sorted[:top_n]:
                max_mentions = max([a.get('mention_count', 1) for a in aspects_sorted[:top_n]])
                bar_length = int((mentions / max_mentions) * 20)
            else:
                bar_length = 0
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            output.append(f"{emoji} {name:25} [{sentiment:+.2f}] {sentiment_text:8} {bar} {mentions} mentions")
        
        output.append("=" * 70)
        
        return "\n".join(output)
    
    def visualize_aspects_chart(
        self,
        aspects_data: Dict[str, Any],
        output_path: str = "aspect_analysis.png",
        top_n: int = 10
    ) -> str:
        """Create flexible chart for aspects with sentiment colors."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            
            aspects = aspects_data.get('aspects', [])
            aspects_sorted = sorted(aspects, key=lambda x: x.get('mention_count', 0), reverse=True)[:top_n]
            
            if not aspects_sorted:
                return None
            
            # Prepare data
            names = [aspect.get('name', 'unknown')[:25] for aspect in aspects_sorted]
            mentions = [aspect.get('mention_count', 0) for aspect in aspects_sorted]
            sentiments = [aspect.get('sentiment', 0) for aspect in aspects_sorted]
            
            # Color coding by sentiment
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
            ax.set_ylabel('Aspects', fontsize=12)
            ax.set_title('Customer Care Aspects by Mentions (Color = Sentiment)', fontsize=14, fontweight='bold')
            
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
            return None
        except Exception as e:
            print(f"❌ Error creating chart: {e}")
            return None
    
    def save_results(
        self,
        aspects_data: Dict[str, Any],
        output_path: str = "aspect_analysis.json"
    ) -> str:
        """Save aspect analysis results to JSON."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(aspects_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Aspect analysis saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ Error saving results: {e}")
            return None
    
    def generate_aspect_summary(
        self,
        aspect: Dict[str, Any],
        restaurant_name: str = "the restaurant"
    ) -> str:
        """Generate a 2-3 sentence summary for a specific aspect."""
        aspect_name = aspect.get('name', 'unknown')
        sentiment = aspect.get('sentiment', 0)
        related_reviews = aspect.get('related_reviews', [])
        
        if not related_reviews:
            return f"No specific feedback found for {aspect_name}."
        
        review_texts = [r.get('review_text', '') for r in related_reviews[:10]]
        reviews_combined = "\n\n".join(review_texts)
        
        prompt = f"""Summarize customer feedback about "{aspect_name}" for {restaurant_name}.

REVIEWS MENTIONING THIS ASPECT:
{reviews_combined}

TASK:
Create a 2-3 sentence summary of what customers say about {aspect_name}.

- Overall sentiment: {sentiment:+.2f} ({self._sentiment_label(sentiment)})
- Be specific and evidence-based
- Mention both positives and negatives if present

Summary:"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            return f"Unable to generate summary for {aspect_name}."
    
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
        max_aspects: int
    ) -> str:
        """Build aspect discovery prompt with AI-based review matching."""
        # Number reviews for AI reference
        numbered_reviews = []
        for i, review in enumerate(reviews):
            numbered_reviews.append(f"[Review {i}]: {review}")
        
        reviews_text = "\n\n".join(numbered_reviews)
        
        prompt = f"""You are analyzing customer reviews for {restaurant_name} to discover what ASPECTS customers care about.

REVIEWS (numbered for reference):
{reviews_text}

YOUR TASK:
1. Discover what aspects/dimensions customers discuss
2. Calculate sentiment for each aspect
3. IDENTIFY WHICH REVIEWS mention each aspect (use review numbers!)

CRITICAL RULES:

1. ADAPTIVE DISCOVERY:
   - Learn what matters to THIS restaurant
   - Japanese: presentation, freshness, authenticity
   - Italian: portion size, sauce quality, wine pairing
   - Mexican: spice level, authenticity, value
   - DON'T force generic aspects!

2. ASPECT TYPES:
   - Food-related: quality, taste, freshness, presentation, portion size
   - Service-related: speed, friendliness, attentiveness
   - Experience: ambience, atmosphere, noise level, cleanliness
   - Value: pricing, value for money
   - Cuisine-specific: authenticity, spice level, wine selection

3. SENTIMENT PER ASPECT:
   - Calculate average sentiment across reviews
   - Score: -1.0 to +1.0

4. REVIEW EXTRACTION:
   - For EACH aspect, identify which reviews discuss it
   - Use review numbers
   - Include full review text

5. FILTER GENERIC:
   - ❌ Skip: "food", "experience"
   - ✅ Include: "food quality", "service speed"

6. LOWERCASE

OUTPUT FORMAT (JSON):
{{
  "aspects": [
    {{
      "name": "aspect name in lowercase",
      "sentiment": float (-1.0 to 1.0),
      "mention_count": number,
      "description": "brief description",
      "related_reviews": [
        {{
          "review_index": 0,
          "review_text": "full review text",
          "sentiment_context": "quote showing sentiment"
        }}
      ]
    }}
  ],
  "total_aspects": number
}}

Discover up to {max_aspects} aspects:"""
        
        return prompt
