"""
Agent Planning Module

Creates strategic analysis plans using Claude AI.
Plans adapt to any restaurant type and include comprehensive validation.

UNIVERSAL DESIGN:
- Works with ANY restaurant
- Claude generates custom plans
- Full data quality validation
- Transparent reasoning
"""

import json
from typing import List, Dict, Any, Optional
from anthropic import Anthropic


class AgentPlanner:
    """
    Creates and validates analysis plans for restaurant reviews.
    
    Uses Claude AI to generate intelligent, adaptive plans that work
    for any restaurant type (Japanese, Italian, Fast Food, etc.)
    
    Features:
    - AI-generated plans (not hardcoded)
    - Comprehensive validation (null checks, data quality)
    - Adapts to restaurant context
    
    Example:
        planner = AgentPlanner(client, model)
        
        context = {
            "restaurant_name": "Any Restaurant",
            "data_source": "https://opentable.ca/r/any-restaurant",
            "review_count": "500"
        }
        
        plan = planner.create_plan(context)
        validation = planner.validate_plan(plan)
    """
    
    def __init__(self, client: Anthropic, model: str):
        """
        Initialize the planner.
        
        Args:
            client: Anthropic client instance
            model: Claude model to use
        """
        self.client = client
        self.model = model
        
        # Define allowed actions for validation
        self.allowed_actions = [
            "scrape_reviews",
            "discover_menu_items",
            "discover_aspects",
            "analyze_sentiment",
            "analyze_menu_performance",
            "analyze_aspects",
            "detect_anomalies",
            "generate_insights_chef",
            "generate_insights_manager",
            "save_to_drive",
            "send_alerts",
            "index_for_rag"
        ]
    
    def create_plan(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create an analysis plan using Claude AI.
        
        Args:
            context: Dictionary with:
                - restaurant_name: Name (or "Unknown")
                - data_source: URL or data source
                - review_count: Estimated number of reviews
                - goals: Analysis goals (optional)
        
        Returns:
            List of plan steps, each with:
                - step: Integer step number
                - action: Action name
                - params: Parameters dict
                - reason: Why this step is needed
                - estimated_time: Time estimate
        """
        # Build the prompt for Claude
        prompt = self._build_planning_prompt(context)
        
        # Call Claude to generate plan
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for consistent planning
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract and parse the plan
            plan_text = response.content[0].text
            
            # Remove markdown code blocks if present
            plan_text = plan_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            plan = json.loads(plan_text)
            
            return plan
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse plan as JSON: {e}")
            print(f"Raw response: {plan_text[:500]}")
            return []
        except Exception as e:
            print(f"❌ Error creating plan: {e}")
            return []
    
    def _build_planning_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build the prompt for Claude to generate a plan.
        
        Args:
            context: Context dictionary
        
        Returns:
            Formatted prompt string
        """
        restaurant_name = context.get('restaurant_name', 'Unknown Restaurant')
        data_source = context.get('data_source', 'OpenTable URL')
        review_count = context.get('review_count', '500')
        goals = context.get('goals', 'Comprehensive analysis with actionable insights')
        
        prompt = f"""You are an expert AI agent specialized in restaurant analytics. Create a detailed, executable plan for analyzing customer reviews.

CONTEXT:
- Restaurant: {restaurant_name}
- Data Source: {data_source}
- Review Count: {review_count} reviews (estimated)
- Goals: {goals}

YOUR TASK:
Create a comprehensive step-by-step plan to analyze these reviews and deliver actionable insights.

REQUIREMENTS:

1. **Dynamic Discovery** (CRITICAL):
   - MUST discover menu items from review text (NO hardcoding)
   - MUST discover aspects customers care about (adapts to restaurant type)
   - Restaurant could be Japanese, Italian, Mexican, Fast Food, etc.

2. **Complete Analysis**:
   - Overall sentiment trends
   - Menu item performance (what's loved/hated)
   - Aspect-based analysis (service, food, ambience, etc.)
   - Anomaly detection (recent problems, complaint spikes)

3. **Actionable Outputs**:
   - Role-specific summaries (Chef vs Manager)
   - Specific recommendations with evidence
   - Automated saves (MCP to Google Drive)
   - Automated alerts (MCP to Slack for critical issues)

4. **Enable Q&A**:
   - Index reviews for RAG-based question answering

AVAILABLE ACTIONS (use these exact names):
- scrape_reviews: Get reviews from URL
- discover_menu_items: Extract mentioned food/drink items using AI
- discover_aspects: Identify what aspects customers discuss using AI
- analyze_sentiment: Calculate overall sentiment scores
- analyze_menu_performance: Sentiment analysis per menu item
- analyze_aspects: Sentiment analysis per aspect
- detect_anomalies: Compare current vs historical data
- generate_insights_chef: Create chef-focused summary
- generate_insights_manager: Create manager-focused summary
- save_to_drive: Save reports to Google Drive via MCP
- send_alerts: Send Slack alerts via MCP for critical issues
- index_for_rag: Prepare reviews for Q&A system

OUTPUT FORMAT (CRITICAL):
Return ONLY valid JSON array. Each step MUST have:
- step: Integer (1, 2, 3...)
- action: String (one of the available actions above)
- params: Object (parameters for this action, can be empty dict)
- reason: String (why this step is necessary)
- estimated_time: String (e.g., "2 minutes", "30 seconds")

EXAMPLE:
[
  {{
    "step": 1,
    "action": "scrape_reviews",
    "params": {{"url": "{data_source}"}},
    "reason": "Must collect review data before analysis can begin",
    "estimated_time": "3 minutes"
  }},
  {{
    "step": 2,
    "action": "discover_menu_items",
    "params": {{"reviews": "scraped_reviews", "max_items": 50}},
    "reason": "Need to identify what dishes customers mention - adapts to ANY restaurant",
    "estimated_time": "45 seconds"
  }}
]

Now create the COMPLETE analysis plan as a JSON array (aim for 10-12 steps):"""
        
        return prompt
    
    def validate_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate plan structure, logic, and data quality.
        
        Checks:
        - Required actions present
        - No null/empty values
        - Correct data types
        - Valid action names
        - Logical ordering
        
        Args:
            plan: List of plan steps
        
        Returns:
            Dict with:
                - valid: Boolean
                - issues: List of problems found
                - suggestions: List of improvements
        """
        issues = []
        suggestions = []
        
        # Check 1: Plan exists and not empty
        if not plan:
            issues.append("Plan is empty or null")
            return {
                "valid": False,
                "issues": issues,
                "suggestions": ["Generate a new plan"]
            }
        
        # Check 2: Plan length is reasonable
        if len(plan) < 5:
            issues.append(f"Plan too short ({len(plan)} steps) - needs at least 5 steps")
        if len(plan) > 20:
            issues.append(f"Plan too long ({len(plan)} steps) - should be under 20 steps")
        
        # Check 3: Required actions are present
        actions = [step.get('action') for step in plan]
        required_actions = ['scrape_reviews', 'discover_menu_items', 'discover_aspects']
        
        for required in required_actions:
            if required not in actions:
                issues.append(f"Missing required action: {required}")
        
        # Check 4: Validate each step
        for i, step in enumerate(plan, start=1):
            step_id = f"Step {i}"
            
            # Null/empty checks
            if 'action' not in step or not step['action']:
                issues.append(f"{step_id}: Missing or empty 'action' field")
            
            if 'reason' not in step or not step['reason']:
                issues.append(f"{step_id}: Missing or empty 'reason' field")
            
            if 'params' not in step:
                issues.append(f"{step_id}: Missing 'params' field")
            
            if 'step' not in step:
                issues.append(f"{step_id}: Missing 'step' field")
            
            # Data type checks
            if 'step' in step and not isinstance(step['step'], int):
                issues.append(f"{step_id}: 'step' must be integer, got {type(step['step'])}")
            
            if 'action' in step and not isinstance(step['action'], str):
                issues.append(f"{step_id}: 'action' must be string, got {type(step['action'])}")
            
            if 'params' in step and not isinstance(step['params'], dict):
                issues.append(f"{step_id}: 'params' must be dict, got {type(step['params'])}")
            
            if 'reason' in step and not isinstance(step['reason'], str):
                issues.append(f"{step_id}: 'reason' must be string, got {type(step['reason'])}")
            
            # Value validity checks
            if 'action' in step and step['action'] not in self.allowed_actions:
                issues.append(f"{step_id}: Unknown action '{step['action']}'")
            
            # Step numbering check
            if 'step' in step and step['step'] != i:
                issues.append(f"{step_id}: Step number mismatch (expected {i}, got {step['step']})")
            
            # Usability checks
            if 'reason' in step and len(step['reason']) < 10:
                issues.append(f"{step_id}: Reason too short ('{step['reason']}')")
        
        # Check 5: Logical ordering
        if 'scrape_reviews' in actions:
            scrape_index = actions.index('scrape_reviews')
            # Scraping should be first or very early
            if scrape_index > 2:
                suggestions.append("'scrape_reviews' should happen earlier in the plan")
        
        # Check 6: Completeness suggestions
        if 'save_to_drive' not in actions:
            suggestions.append("Consider adding 'save_to_drive' to persist results")
        
        if 'detect_anomalies' not in actions:
            suggestions.append("Consider adding 'detect_anomalies' for proactive insights")
        
        if 'send_alerts' not in actions:
            suggestions.append("Consider adding 'send_alerts' for critical issue notifications")
        
        # Final validation result
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions
        }


# Test code
if __name__ == "__main__":
    print("=" * 70)
    print("Testing AgentPlanner")
    print("=" * 70 + "\n")
    
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Initialize
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    planner = AgentPlanner(client=client, model="claude-sonnet-4-20250514")
    
    # Test context
    context = {
        "restaurant_name": "Test Restaurant (Any Type)",
        "data_source": "https://opentable.ca/r/test-restaurant",
        "review_count": "500",
        "goals": "Comprehensive analysis with actionable insights"
    }
    
    print("🤖 Creating analysis plan...")
    print(f"Context: {context}\n")
    
    plan = planner.create_plan(context)
    
    if plan:
        print(f"✅ Generated plan with {len(plan)} steps:\n")
        for step in plan:
            print(f"  {step['step']}. {step['action']}")
            print(f"     Reason: {step['reason']}")
            print(f"     Time: {step.get('estimated_time', 'N/A')}\n")
        
        print("🔍 Validating plan...\n")
        validation = planner.validate_plan(plan)
        
        print(f"Valid: {validation['valid']}")
        
        if validation['issues']:
            print(f"\n❌ Issues found:")
            for issue in validation['issues']:
                print(f"  - {issue}")
        else:
            print("✅ No issues found")
        
        if validation['suggestions']:
            print(f"\n💡 Suggestions:")
            for suggestion in validation['suggestions']:
                print(f"  - {suggestion}")
        
        print("\n" + "=" * 70)
        if validation['valid']:
            print("🎉 Plan is valid and ready to execute!")
        else:
            print("⚠️  Plan needs fixes before execution")
        print("=" * 70)
    else:
        print("❌ Failed to generate plan")
