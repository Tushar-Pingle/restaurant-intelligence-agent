"""
Insight Generation Module

Generates actionable, role-specific insights from restaurant review analysis.

Stakeholder-specific outputs:
- Chef: Food quality, menu items, presentation, taste
- Manager: Service, operations, staffing, customer experience

UNIVERSAL DESIGN:
- Works with any restaurant type
- Adapts insights to discovered menu items and aspects
- Evidence-based recommendations
- Actionable and specific
"""

from typing import Dict, Any, List, Optional
from anthropic import Anthropic
import json


class InsightsGenerator:
    """
    Generates role-specific insights from analysis results.
    
    Features:
    - Chef-focused insights (food, menu, ingredients)
    - Manager-focused insights (service, operations, experience)
    - Evidence-based recommendations
    - Prioritized by impact
    
    Example:
        generator = InsightsGenerator(client, model)
        
        # Generate chef insights
        chef_insights = generator.generate_insights(
            analysis_data=results,
            role='chef'
        )
        
        # Generate manager insights
        manager_insights = generator.generate_insights(
            analysis_data=results,
            role='manager'
        )
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
        
        D2-011: Core implementation
        D2-012: Role-based filtering
        
        Args:
            analysis_data: Results from analysis (sentiment, menu items, aspects, etc.)
            role: Target role ('chef' or 'manager')
            restaurant_name: Name of the restaurant
        
        Returns:
            Dictionary with:
                - summary: Executive summary
                - strengths: What's working well
                - concerns: Areas needing attention
                - recommendations: Specific action items
                - evidence: Supporting data/quotes
        """
        # D2-010: Build the prompt based on role
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
                temperature=0.4,  # Slightly creative but still focused
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract insights
            insights_text = response.content[0].text
            
            # Parse JSON response
            insights_text = insights_text.replace('```json', '').replace('```', '').strip()
            insights = json.loads(insights_text)
            
            return insights
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse insights as JSON: {e}")
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
        D2-010: Build prompt for chef-focused insights.
        D2-012: Filter for chef-relevant topics
        
        Args:
            analysis_data: Analysis results
            restaurant_name: Restaurant name
        
        Returns:
            Formatted prompt for Claude
        """
        prompt = f"""You are an expert culinary consultant analyzing customer feedback for {restaurant_name}.

ANALYSIS DATA:
{json.dumps(analysis_data, indent=2)}

YOUR TASK:
Generate actionable insights specifically for the HEAD CHEF. Focus on:
- Food quality and taste
- Menu items (what's working, what's not)
- Ingredient quality and freshness
- Presentation and plating
- Portion sizes
- Recipe consistency
- Kitchen execution

CRITICAL - CHEF FOCUS ONLY:
- DO focus on: food, ingredients, recipes, menu, taste, presentation
- DON'T focus on: service speed, wait times, staffing, decor (that's for manager)

OUTPUT FORMAT (JSON):
{{
  "summary": "2-3 sentence executive summary for the chef",
  "strengths": [
    "Specific strength with evidence (e.g., 'Salmon dishes consistently praised for freshness')"
  ],
  "concerns": [
    "Specific concern with evidence (e.g., 'Multiple mentions of oversalted dishes')"
  ],
  "recommendations": [
    {{
      "priority": "high/medium/low",
      "action": "Specific actionable recommendation",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }}
  ]
}}

Generate chef-specific insights now:"""
        
        return prompt
    
    def _build_manager_prompt(
        self,
        analysis_data: Dict[str, Any],
        restaurant_name: str
    ) -> str:
        """
        D2-010: Build prompt for manager-focused insights.
        D2-012: Filter for manager-relevant topics
        
        Args:
            analysis_data: Analysis results
            restaurant_name: Restaurant name
        
        Returns:
            Formatted prompt for Claude
        """
        prompt = f"""You are an expert restaurant operations consultant analyzing customer feedback for {restaurant_name}.

ANALYSIS DATA:
{json.dumps(analysis_data, indent=2)}

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

CRITICAL - MANAGER FOCUS ONLY:
- DO focus on: service, operations, staff, experience, efficiency
- DON'T focus on: specific recipes, ingredient quality, plating (that's for chef)

OUTPUT FORMAT (JSON):
{{
  "summary": "2-3 sentence executive summary for the manager",
  "strengths": [
    "Specific strength with evidence (e.g., 'Front desk staff praised for warmth and efficiency')"
  ],
  "concerns": [
    "Specific concern with evidence (e.g., 'Weekend wait times averaging 45 minutes causing frustration')"
  ],
  "recommendations": [
    {{
      "priority": "high/medium/low",
      "action": "Specific actionable recommendation",
      "reason": "Why this matters",
      "evidence": "Supporting data"
    }}
  ]
}}

Generate manager-specific insights now:"""
        
        return prompt
    
    def _get_fallback_insights(self, role: str) -> Dict[str, Any]:
        """
        Return fallback insights if generation fails.
        
        Args:
            role: Target role
        
        Returns:
            Basic insights structure
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


# D2-013: Test with sample Miku data
if __name__ == "__main__":
    print("=" * 70)
    print("D2-013: Testing Insights Generator with Sample Data")
    print("=" * 70 + "\n")
    
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Initialize
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    generator = InsightsGenerator(client=client, model="claude-sonnet-4-20250514")
    
    # Sample analysis data (simulating what we'd get from real analysis)
    sample_analysis = {
        "restaurant_name": "Miku Restaurant",
        "overall_sentiment": 0.78,
        "total_reviews": 487,
        "menu_items": {
            "salmon_sushi": {"mentions": 89, "sentiment": 0.92, "top_adjectives": ["fresh", "amazing", "perfect"]},
            "miso_soup": {"mentions": 67, "sentiment": 0.85, "top_adjectives": ["warm", "flavorful", "authentic"]},
            "tempura": {"mentions": 45, "sentiment": 0.65, "top_adjectives": ["crispy", "oily", "heavy"]}
        },
        "aspects": {
            "food_quality": {"sentiment": 0.88, "mention_count": 234},
            "presentation": {"sentiment": 0.91, "mention_count": 156},
            "service_speed": {"sentiment": 0.62, "mention_count": 178},
            "value": {"sentiment": 0.58, "mention_count": 123},
            "ambience": {"sentiment": 0.85, "mention_count": 145}
        },
        "anomalies": [
            "Service speed complaints up 35% in last 2 weeks",
            "Tempura mentions becoming more negative (-15% sentiment drop)"
        ]
    }
    
    # Test 1: Generate chef insights
    print("TEST 1: Generating Chef Insights")
    print("-" * 70 + "\n")
    
    chef_insights = generator.generate_insights(
        analysis_data=sample_analysis,
        role='chef',
        restaurant_name='Miku Restaurant'
    )
    
    print("CHEF INSIGHTS:")
    print(f"\n📋 Summary:\n{chef_insights.get('summary', 'N/A')}")
    
    print(f"\n✅ Strengths:")
    for strength in chef_insights.get('strengths', []):
        print(f"  • {strength}")
    
    print(f"\n⚠️  Concerns:")
    for concern in chef_insights.get('concerns', []):
        print(f"  • {concern}")
    
    print(f"\n💡 Recommendations:")
    for rec in chef_insights.get('recommendations', []):
        print(f"  • [{rec.get('priority', 'N/A').upper()}] {rec.get('action', 'N/A')}")
        print(f"    Reason: {rec.get('reason', 'N/A')}")
    
    # Test 2: Generate manager insights
    print("\n" + "=" * 70)
    print("TEST 2: Generating Manager Insights")
    print("-" * 70 + "\n")
    
    manager_insights = generator.generate_insights(
        analysis_data=sample_analysis,
        role='manager',
        restaurant_name='Miku Restaurant'
    )
    
    print("MANAGER INSIGHTS:")
    print(f"\n📋 Summary:\n{manager_insights.get('summary', 'N/A')}")
    
    print(f"\n✅ Strengths:")
    for strength in manager_insights.get('strengths', []):
        print(f"  • {strength}")
    
    print(f"\n⚠️  Concerns:")
    for concern in manager_insights.get('concerns', []):
        print(f"  • {concern}")
    
    print(f"\n💡 Recommendations:")
    for rec in manager_insights.get('recommendations', []):
        print(f"  • [{rec.get('priority', 'N/A').upper()}] {rec.get('action', 'N/A')}")
        print(f"    Reason: {rec.get('reason', 'N/A')}")
    
    # D2-014: Quality check
    print("\n" + "=" * 70)
    print("D2-014: Quality Check")
    print("=" * 70)
    
    # Check chef insights focus on food
    chef_summary_lower = chef_insights.get('summary', '').lower()
    food_keywords = ['food', 'menu', 'dish', 'ingredient', 'taste', 'flavor', 'recipe']
    chef_food_focused = any(keyword in chef_summary_lower for keyword in food_keywords)
    
    print(f"\n✓ Chef insights food-focused: {chef_food_focused}")
    
    # Check manager insights focus on operations
    manager_summary_lower = manager_insights.get('summary', '').lower()
    ops_keywords = ['service', 'staff', 'operation', 'experience', 'wait', 'customer']
    manager_ops_focused = any(keyword in manager_summary_lower for keyword in ops_keywords)
    
    print(f"✓ Manager insights operations-focused: {manager_ops_focused}")
    
    # Check both have recommendations
    chef_has_recs = len(chef_insights.get('recommendations', [])) > 0
    manager_has_recs = len(manager_insights.get('recommendations', [])) > 0
    
    print(f"✓ Chef has recommendations: {chef_has_recs}")
    print(f"✓ Manager has recommendations: {manager_has_recs}")
    
    print("\n" + "=" * 70)
    print("🎉 Insights generator test complete!")
    print("=" * 70)