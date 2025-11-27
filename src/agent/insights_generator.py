"""
Restaurant Insights Generator - EXPANDED VERSION
Generates role-specific insights for Chef and Manager personas.

UPDATED v3: 
- New sentiment scale (>= 0.6 positive, 0-0.59 neutral, < 0 negative)
- Clearer guidance on strengths vs concerns
- Top 20 items/aspects for comprehensive insights
"""

import json
import re
from typing import Any, Dict, Optional


class InsightsGenerator:
    """
    Generates actionable insights for different restaurant roles.
    
    UPDATED: 
    - New sentiment thresholds (0.6/0 instead of 0.3/-0.3)
    - Expanded to use top 20 menu items and aspects
    - Clearer mapping of sentiment to strengths/concerns
    """
    
    def __init__(self, client, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the insights generator.
        
        Args:
            client: Anthropic client instance
            model: Model to use for generation
        """
        self.client = client
        self.model = model
    
    def generate_insights(
        self, 
        analysis_data: Dict[str, Any],
        role: str = 'chef',
        restaurant_name: str = "the restaurant"
    ) -> Dict[str, Any]:
        """
        Generate role-specific insights from analysis data.
        
        Args:
            analysis_data: Complete analysis including menu and aspects
            role: Either 'chef' or 'manager'
            restaurant_name: Name of the restaurant
        
        Returns:
            Dict with summary, strengths, concerns, and recommendations
        """
        try:
            if role == 'chef':
                prompt = self._build_chef_prompt(analysis_data, restaurant_name)
            else:
                prompt = self._build_manager_prompt(analysis_data, restaurant_name)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            
            # Parse JSON from response
            insights = self._parse_json_response(response_text)
            
            if insights:
                return insights
            else:
                return self._get_fallback_insights(role)
                
        except Exception as e:
            print(f"[INSIGHTS] Error generating {role} insights: {e}")
            return self._get_fallback_insights(role)
    
    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """Parse JSON from response, handling markdown fences."""
        # Remove markdown code fences
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return None
    
    def _build_chef_prompt(
        self,
        analysis_data: Dict[str, Any],
        restaurant_name: str
    ) -> str:
        """Build prompt for chef-focused insights - EXPANDED to 20 items."""
        # Get EXPANDED menu summary (20 items instead of 10)
        menu_summary = self._summarize_menu_data(analysis_data, max_food=20, max_drinks=10)
        aspect_summary = self._summarize_aspect_data(analysis_data, focus='food', max_aspects=15)
        
        prompt = f"""You are an expert culinary consultant analyzing customer feedback for {restaurant_name}.

MENU PERFORMANCE (Top items by customer mentions):
{menu_summary}

FOOD-RELATED ASPECTS:
{aspect_summary}

SENTIMENT SCALE:
- 🟢 POSITIVE (0.6 to 1.0): Customers love this - highlight as a STRENGTH
- 🟡 NEUTRAL (0.0 to 0.59): Mixed or average feedback - room for improvement
- 🔴 NEGATIVE (below 0): Customers complained - flag as a CONCERN

YOUR TASK:
Generate actionable insights specifically for the HEAD CHEF. Focus on:
- Food quality and taste
- Menu items (what's working, what's not)
- Ingredient quality and freshness
- Presentation and plating
- Portion sizes
- Recipe consistency
- Kitchen execution

CRITICAL RULES:
1. Focus ONLY on food/kitchen topics
2. STRENGTHS should come from items/aspects with sentiment >= 0.6 (🟢 positive)
3. CONCERNS should come from items/aspects with sentiment < 0 (🔴 negative)
4. Be specific with evidence from reviews
5. Make recommendations actionable
6. Reference specific menu items by name
7. Output ONLY valid JSON, no other text

OUTPUT FORMAT (JSON):
{{
  "summary": "2-3 sentence executive summary covering overall kitchen performance",
  "strengths": [
    "Specific strength 1 - reference a 🟢 positive item with sentiment >= 0.6",
    "Specific strength 2 - reference a 🟢 positive item with sentiment >= 0.6",
    "Specific strength 3 - reference a 🟢 positive item with sentiment >= 0.6",
    "Specific strength 4 - reference a 🟢 positive item with sentiment >= 0.6",
    "Specific strength 5 - reference a 🟢 positive item with sentiment >= 0.6"
  ],
  "concerns": [
    "Specific concern 1 - reference a 🔴 negative item with sentiment < 0",
    "Specific concern 2 - reference a 🔴 negative item with sentiment < 0",
    "Specific concern 3 - reference a 🔴 negative item with sentiment < 0"
  ],
  "recommendations": [
    {{
      "priority": "high",
      "action": "Specific action to fix a negative sentiment item",
      "reason": "Why this matters based on review data",
      "evidence": "Supporting data from reviews"
    }},
    {{
      "priority": "high",
      "action": "Another high priority action",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }},
    {{
      "priority": "medium",
      "action": "Medium priority action",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }},
    {{
      "priority": "medium",
      "action": "Another medium priority action",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }},
    {{
      "priority": "low",
      "action": "Lower priority improvement",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }}
  ]
}}

IMPORTANT: 
- Provide at least 5 strengths (from 🟢 items) and 5 recommendations
- If there are no negative items, focus recommendations on improving neutral items
- Reference actual menu items from the data above
- Ensure all JSON is properly formatted with no trailing commas

Generate chef insights:"""
        
        return prompt

    def _build_manager_prompt(
        self,
        analysis_data: Dict[str, Any],
        restaurant_name: str
    ) -> str:
        """Build prompt for manager-focused insights - EXPANDED to 20 aspects."""
        # Get EXPANDED aspect summary (20 aspects instead of 10)
        aspect_summary = self._summarize_aspect_data(analysis_data, focus='operations', max_aspects=20)
        
        # Also include menu overview for context
        menu_summary = self._summarize_menu_data(analysis_data, max_food=10, max_drinks=5)
        
        prompt = f"""You are an expert restaurant operations consultant analyzing customer feedback for {restaurant_name}.

OPERATIONAL ASPECTS (All discovered from reviews):
{aspect_summary}

MENU OVERVIEW (for context):
{menu_summary}

SENTIMENT SCALE:
- 🟢 POSITIVE (0.6 to 1.0): Customers love this - highlight as a STRENGTH
- 🟡 NEUTRAL (0.0 to 0.59): Mixed or average feedback - room for improvement
- 🔴 NEGATIVE (below 0): Customers complained - flag as a CONCERN

YOUR TASK:
Generate actionable insights specifically for the RESTAURANT MANAGER. Focus on:
- Service quality and speed
- Staff performance and training needs
- Wait times and reservations
- Customer experience and satisfaction
- Operational efficiency
- Ambience and atmosphere
- Value for money
- Cleanliness and maintenance

CRITICAL RULES:
1. Focus ONLY on operations/service topics
2. STRENGTHS should come from aspects with sentiment >= 0.6 (🟢 positive)
3. CONCERNS should come from aspects with sentiment < 0 (🔴 negative)
4. Be specific with evidence from reviews
5. Make recommendations actionable
6. Reference specific aspects by name
7. Output ONLY valid JSON, no other text

OUTPUT FORMAT (JSON):
{{
  "summary": "2-3 sentence executive summary covering overall operations",
  "strengths": [
    "Specific operational strength 1 - reference a 🟢 positive aspect with sentiment >= 0.6",
    "Specific operational strength 2 - reference a 🟢 positive aspect with sentiment >= 0.6",
    "Specific operational strength 3 - reference a 🟢 positive aspect with sentiment >= 0.6",
    "Specific operational strength 4 - reference a 🟢 positive aspect with sentiment >= 0.6",
    "Specific operational strength 5 - reference a 🟢 positive aspect with sentiment >= 0.6"
  ],
  "concerns": [
    "Specific operational concern 1 - reference a 🔴 negative aspect with sentiment < 0",
    "Specific operational concern 2 - reference a 🔴 negative aspect with sentiment < 0",
    "Specific operational concern 3 - reference a 🔴 negative aspect with sentiment < 0"
  ],
  "recommendations": [
    {{
      "priority": "high",
      "action": "Specific action to fix a negative sentiment aspect",
      "reason": "Why this matters based on review data",
      "evidence": "Supporting data from reviews"
    }},
    {{
      "priority": "high",
      "action": "Another high priority action",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }},
    {{
      "priority": "medium",
      "action": "Medium priority action",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }},
    {{
      "priority": "medium",
      "action": "Another medium priority action",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }},
    {{
      "priority": "low",
      "action": "Lower priority improvement",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }}
  ]
}}

IMPORTANT: 
- Provide at least 5 strengths (from 🟢 aspects) and 5 recommendations
- If there are no negative aspects, focus recommendations on improving neutral aspects
- Reference actual aspects from the data above
- Ensure all JSON is properly formatted with no trailing commas

Generate manager insights:"""
        
        return prompt

    def _summarize_menu_data(
        self, 
        analysis_data: Dict[str, Any],
        max_food: int = 20,
        max_drinks: int = 10
    ) -> str:
        """
        Summarize menu analysis for prompts.
        
        UPDATED: New sentiment thresholds (0.6/0 instead of 0.3/-0.3)
        """
        menu_data = analysis_data.get('menu_analysis', {})
        food_items = menu_data.get('food_items', [])[:max_food]
        drinks = menu_data.get('drinks', [])[:max_drinks]
        
        summary = []
        
        if food_items:
            summary.append(f"TOP {len(food_items)} FOOD ITEMS:")
            for item in food_items:
                sentiment = item.get('sentiment', 0)
                mentions = item.get('mention_count', 0)
                # NEW thresholds: >= 0.6 positive, >= 0 neutral, < 0 negative
                indicator = "🟢" if sentiment >= 0.6 else "🟡" if sentiment >= 0 else "🔴"
                summary.append(f"  {indicator} {item.get('name', 'unknown')}: sentiment {sentiment:+.2f}, {mentions} mentions")
        
        if drinks:
            summary.append(f"\nTOP {len(drinks)} DRINKS:")
            for drink in drinks:
                sentiment = drink.get('sentiment', 0)
                mentions = drink.get('mention_count', 0)
                # NEW thresholds: >= 0.6 positive, >= 0 neutral, < 0 negative
                indicator = "🟢" if sentiment >= 0.6 else "🟡" if sentiment >= 0 else "🔴"
                summary.append(f"  {indicator} {drink.get('name', 'unknown')}: sentiment {sentiment:+.2f}, {mentions} mentions")
        
        # Add overall stats
        total_food = len(menu_data.get('food_items', []))
        total_drinks = len(menu_data.get('drinks', []))
        summary.append(f"\n(Total: {total_food} food items, {total_drinks} drinks discovered)")
        
        return '\n'.join(summary) if summary else "No menu data available"
    
    def _summarize_aspect_data(
        self, 
        analysis_data: Dict[str, Any], 
        focus: str = 'all',
        max_aspects: int = 20
    ) -> str:
        """
        Summarize aspect analysis for prompts.
        
        UPDATED: New sentiment thresholds (0.6/0 instead of 0.3/-0.3)
        """
        aspect_data = analysis_data.get('aspect_analysis', {})
        aspects = aspect_data.get('aspects', [])
        
        # Filter aspects based on focus
        if focus == 'food':
            food_keywords = ['food', 'taste', 'flavor', 'quality', 'presentation', 'freshness', 
                           'portion', 'dish', 'menu', 'ingredient', 'cook', 'season', 'texture']
            aspects = [a for a in aspects if any(kw in a.get('name', '').lower() for kw in food_keywords)]
        elif focus == 'operations':
            ops_keywords = ['service', 'staff', 'wait', 'ambience', 'atmosphere', 'value', 'price', 
                          'clean', 'reservation', 'host', 'server', 'attentive', 'friendly', 
                          'noise', 'music', 'parking', 'location', 'decor', 'vibe']
            aspects = [a for a in aspects if any(kw in a.get('name', '').lower() for kw in ops_keywords)]
        
        aspects = aspects[:max_aspects]
        
        summary = []
        summary.append(f"ASPECTS ({len(aspects)} found):")
        
        for aspect in aspects:
            sentiment = aspect.get('sentiment', 0)
            mentions = aspect.get('mention_count', 0)
            # NEW thresholds: >= 0.6 positive, >= 0 neutral, < 0 negative
            indicator = "🟢" if sentiment >= 0.6 else "🟡" if sentiment >= 0 else "🔴"
            summary.append(f"  {indicator} {aspect.get('name', 'unknown')}: sentiment {sentiment:+.2f}, {mentions} mentions")
        
        # Add total count
        total_aspects = len(aspect_data.get('aspects', []))
        summary.append(f"\n(Total: {total_aspects} aspects discovered from reviews)")
        
        return '\n'.join(summary) if summary else "No aspect data available"
    
    def _get_fallback_insights(self, role: str) -> Dict[str, Any]:
        """Return fallback insights if generation fails."""
        return {
            "summary": f"Unable to generate {role} insights at this time. Please try again.",
            "strengths": ["Analysis in progress"],
            "concerns": ["No data available"],
            "recommendations": [
                {
                    "priority": "medium",
                    "action": "Re-run analysis with more reviews",
                    "reason": "Insufficient data for detailed insights",
                    "evidence": "N/A"
                }
            ]
        }