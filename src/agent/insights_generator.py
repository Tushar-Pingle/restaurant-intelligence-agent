"""
Insight Generation Module

Generates actionable, role-specific insights from restaurant review analysis.

Stakeholder-specific outputs:
- Chef: Food quality, menu items, presentation, taste
- Manager: Service, operations, staffing, customer experience
"""

from typing import Dict, Any
from anthropic import Anthropic
import json
import re


class InsightsGenerator:
    """
    Generates role-specific insights from analysis results.
    """
    
    def __init__(self, client: Anthropic, model: str):
        """
        Initialize the insights generator.
        
        Args:
            client: Anthropic client instance
            model: Claude model to use
        """
        self.client = client
        self.model = model
    
    def generate_insights(
        self,
        analysis_data: Dict[str, Any],
        role: str = 'chef',
        restaurant_name: str = 'the restaurant'
    ) -> Dict[str, Any]:
        """
        Generate role-specific insights.
        
        Args:
            analysis_data: Results from analysis
            role: Target role ('chef' or 'manager')
            restaurant_name: Name of the restaurant
        
        Returns:
            Dictionary with summary, strengths, concerns, recommendations
        """
        # Build the prompt based on role
        if role.lower() == 'chef':
            prompt = self._build_chef_prompt(analysis_data, restaurant_name)
        elif role.lower() == 'manager':
            prompt = self._build_manager_prompt(analysis_data, restaurant_name)
        else:
            raise ValueError(f"Unknown role: {role}. Must be 'chef' or 'manager'")
        
        # Call Claude to generate insights
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract insights
            insights_text = response.content[0].text
            
            # Clean up response
            insights_text = insights_text.replace('```json', '').replace('```', '').strip()
            
            # Remove any trailing commas before closing braces/brackets
            insights_text = re.sub(r',(\s*[}\]])', r'\1', insights_text)
            
            # Parse JSON response
            insights = json.loads(insights_text)
            
            # Validate structure
            if not all(key in insights for key in ['summary', 'strengths', 'concerns', 'recommendations']):
                print(f"⚠️  Incomplete insights structure, using fallback")
                return self._get_fallback_insights(role)
            
            return insights
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse insights as JSON: {e}")
            print(f"Raw response: {insights_text[:200]}...")
            return self._get_fallback_insights(role)
        except Exception as e:
            print(f"❌ Error generating insights: {e}")
            return self._get_fallback_insights(role)
    
    def _build_chef_prompt(
        self,
        analysis_data: Dict[str, Any],
        restaurant_name: str
    ) -> str:
        """
        Build prompt for chef-focused insights.
        """
        # Prepare summary of analysis data
        menu_summary = self._summarize_menu_data(analysis_data)
        aspect_summary = self._summarize_aspect_data(analysis_data, focus='food')
        
        prompt = f"""You are an expert culinary consultant analyzing customer feedback for {restaurant_name}.

MENU PERFORMANCE:
{menu_summary}

FOOD-RELATED ASPECTS:
{aspect_summary}

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
2. Be specific with evidence from reviews
3. Make recommendations actionable
4. Output ONLY valid JSON, no other text

OUTPUT FORMAT (JSON):
{{
  "summary": "2-3 sentence executive summary",
  "strengths": ["Specific strength 1", "Specific strength 2", "Specific strength 3"],
  "concerns": ["Specific concern 1", "Specific concern 2"],
  "recommendations": [
    {{
      "priority": "high",
      "action": "Specific action to take",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }}
  ]
}}

IMPORTANT: Ensure all JSON is properly formatted with no trailing commas.

Generate chef insights:"""
        
        return prompt
    
    def _build_manager_prompt(
        self,
        analysis_data: Dict[str, Any],
        restaurant_name: str
    ) -> str:
        """
        Build prompt for manager-focused insights.
        """
        # Prepare summary of analysis data
        aspect_summary = self._summarize_aspect_data(analysis_data, focus='operations')
        
        prompt = f"""You are an expert restaurant operations consultant analyzing customer feedback for {restaurant_name}.

OPERATIONAL ASPECTS:
{aspect_summary}

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
2. Be specific with evidence from reviews
3. Make recommendations actionable
4. Output ONLY valid JSON, no other text

OUTPUT FORMAT (JSON):
{{
  "summary": "2-3 sentence executive summary",
  "strengths": ["Specific strength 1", "Specific strength 2", "Specific strength 3"],
  "concerns": ["Specific concern 1", "Specific concern 2"],
  "recommendations": [
    {{
      "priority": "high",
      "action": "Specific action to take",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }}
  ]
}}

IMPORTANT: Ensure all JSON is properly formatted with no trailing commas.

Generate manager insights:"""
        
        return prompt
    
    def _summarize_menu_data(self, analysis_data: Dict[str, Any]) -> str:
        """Summarize menu analysis for prompts."""
        menu_data = analysis_data.get('menu_analysis', {})
        food_items = menu_data.get('food_items', [])[:10]  # Top 10
        drinks = menu_data.get('drinks', [])[:5]  # Top 5
        
        summary = []
        
        if food_items:
            summary.append("TOP FOOD ITEMS:")
            for item in food_items:
                sentiment = item.get('sentiment', 0)
                mentions = item.get('mention_count', 0)
                summary.append(f"  - {item.get('name', 'unknown')}: sentiment {sentiment:+.2f}, {mentions} mentions")
        
        if drinks:
            summary.append("\nTOP DRINKS:")
            for drink in drinks:
                sentiment = drink.get('sentiment', 0)
                mentions = drink.get('mention_count', 0)
                summary.append(f"  - {drink.get('name', 'unknown')}: sentiment {sentiment:+.2f}, {mentions} mentions")
        
        return '\n'.join(summary) if summary else "No menu data available"
    
    def _summarize_aspect_data(self, analysis_data: Dict[str, Any], focus: str = 'all') -> str:
        """Summarize aspect analysis for prompts."""
        aspect_data = analysis_data.get('aspect_analysis', {})
        aspects = aspect_data.get('aspects', [])
        
        # Filter aspects based on focus
        if focus == 'food':
            food_keywords = ['food', 'taste', 'flavor', 'quality', 'presentation', 'freshness', 'portion']
            aspects = [a for a in aspects if any(kw in a.get('name', '').lower() for kw in food_keywords)]
        elif focus == 'operations':
            ops_keywords = ['service', 'staff', 'wait', 'ambience', 'atmosphere', 'value', 'price', 'clean']
            aspects = [a for a in aspects if any(kw in a.get('name', '').lower() for kw in ops_keywords)]
        
        aspects = aspects[:10]  # Top 10
        
        summary = []
        for aspect in aspects:
            sentiment = aspect.get('sentiment', 0)
            mentions = aspect.get('mention_count', 0)
            summary.append(f"  - {aspect.get('name', 'unknown')}: sentiment {sentiment:+.2f}, {mentions} mentions")
        
        return '\n'.join(summary) if summary else "No aspect data available"
    
    def _get_fallback_insights(self, role: str) -> Dict[str, Any]:
        """
        Return fallback insights if generation fails.
        """
        return {
            "summary": f"Unable to generate {role} insights at this time.",
            "strengths": ["Analysis data available for review"],
            "concerns": ["Insight generation encountered an error"],
            "recommendations": [
                {
                    "priority": "high",
                    "action": "Retry insight generation",
                    "reason": "Complete analysis requires insights",
                    "evidence": "System error"
                }
            ]
        }