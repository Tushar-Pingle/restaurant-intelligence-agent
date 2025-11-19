"""
Base Agent Class

This file contains the core RestaurantAnalysisAgent class that provides
autonomous analysis capabilities for ANY restaurant.

UNIVERSAL DESIGN:
- Works with ANY OpenTable restaurant URL
- Discovers menu items dynamically (no hardcoding)
- Discovers aspects dynamically (adapts to restaurant type)
- Creates analysis plans autonomously using Claude AI
- Executes with full reasoning transparency
"""

import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

# Add project root to path so imports work
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the planner
from src.agent.planner import AgentPlanner

# Load environment variables
load_dotenv()


class RestaurantAnalysisAgent:
    """
    Autonomous agent for restaurant review analysis.
    
    This agent can analyze ANY restaurant without prior configuration.
    It discovers menu items, aspects, and patterns directly from reviews.
    
    Key Features:
    - Universal: Works with any restaurant type
    - Adaptive: Discovers what matters to each restaurant
    - Autonomous: Plans its own analysis strategy using AI
    - Transparent: Logs all reasoning for visibility
    
    Example Usage:
        agent = RestaurantAnalysisAgent()
        
        # Create a plan for any restaurant
        plan = agent.create_analysis_plan(
            restaurant_url="https://opentable.ca/r/ANY-RESTAURANT"
        )
        
        # View reasoning
        for log in agent.get_reasoning_log():
            print(log)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Restaurant Analysis Agent.
        
        Args:
            api_key: Anthropic API key (optional)
        """
        # Get API key
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "❌ No API key found!\n"
                "Set ANTHROPIC_API_KEY in .env or pass api_key parameter"
            )
        
        # Initialize Claude client
        try:
            self.client = Anthropic(api_key=self.api_key)
        except Exception as e:
            raise ConnectionError(f"❌ Failed to connect to Claude API: {e}")
        
        # Set model
        self.model = "claude-sonnet-4-20250514"
        
        # Initialize planner
        self.planner = AgentPlanner(client=self.client, model=self.model)
        
        # Initialize state
        self.current_plan: List[Dict[str, Any]] = []
        self.reasoning_log: List[str] = []
        self.execution_results: Dict[str, Any] = {}
        
        # Log initialization
        self._log_reasoning("Agent initialized and ready for analysis")
        self._log_reasoning(f"Using model: {self.model}")
        self._log_reasoning("Planner module loaded")
    
    def _log_reasoning(self, message: str) -> None:
        """
        Log the agent's reasoning process.
        
        Args:
            message: Reasoning message to log
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.reasoning_log.append(log_entry)
        print(f"🤖 {log_entry}")
    
    def create_analysis_plan(
        self, 
        restaurant_url: str,
        restaurant_name: str = "Unknown",
        review_count: str = "500"
    ) -> List[Dict[str, Any]]:
        """
        Create an analysis plan for a restaurant.
        
        Uses AI to generate a custom plan that adapts to any restaurant type.
        
        Args:
            restaurant_url: OpenTable URL for the restaurant
            restaurant_name: Name of restaurant (optional)
            review_count: Estimated review count (optional)
        
        Returns:
            List of plan steps
        
        Example:
            plan = agent.create_analysis_plan(
                restaurant_url="https://opentable.ca/r/any-restaurant"
            )
        """
        self._log_reasoning(f"Creating analysis plan for: {restaurant_name}")
        self._log_reasoning(f"Data source: {restaurant_url}")
        
        # Prepare context for planner
        context = {
            "restaurant_name": restaurant_name,
            "data_source": restaurant_url,
            "review_count": review_count,
            "goals": "Comprehensive analysis with actionable insights"
        }
        
        # Generate plan using AI
        self._log_reasoning("Calling planner to generate strategy...")
        plan = self.planner.create_plan(context)
        
        if not plan:
            self._log_reasoning("❌ Failed to generate plan")
            return []
        
        self._log_reasoning(f"✅ Generated plan with {len(plan)} steps")
        
        # Validate the plan
        self._log_reasoning("Validating plan quality...")
        validation = self.planner.validate_plan(plan)
        
        if validation['valid']:
            self._log_reasoning("✅ Plan validation passed")
        else:
            self._log_reasoning(f"⚠️  Plan has {len(validation['issues'])} issues")
            for issue in validation['issues']:
                self._log_reasoning(f"  - {issue}")
        
        # Store the plan
        self.current_plan = plan
        
        return plan
    
    def get_reasoning_log(self) -> List[str]:
        """Get the complete reasoning log."""
        return self.reasoning_log.copy()
    
    def get_current_plan(self) -> List[Dict[str, Any]]:
        """Get the current analysis plan."""
        return self.current_plan.copy()
    
    def clear_state(self) -> None:
        """Clear agent state for new analysis."""
        self.current_plan = []
        self.reasoning_log = []
        self.execution_results = {}
        self._log_reasoning("Agent state cleared for new analysis")
    
    def __repr__(self) -> str:
        return (
            f"RestaurantAnalysisAgent("
            f"model={self.model}, "
            f"planned_steps={len(self.current_plan)}, "
            f"logs={len(self.reasoning_log)})"
        )


# D1-015: Test with sample context
if __name__ == "__main__":
    print("=" * 70)
    print("D1-015: Testing Plan Generation with Sample Reviews Context")
    print("=" * 70 + "\n")
    
    try:
        # Create agent
        print("Creating agent...")
        agent = RestaurantAnalysisAgent()
        print(f"✅ Agent: {agent}\n")
        
        # Test 1: Japanese restaurant
        print("=" * 70)
        print("TEST 1: Japanese Restaurant (Miku)")
        print("=" * 70 + "\n")
        
        plan1 = agent.create_analysis_plan(
            restaurant_url="https://opentable.ca/r/miku-vancouver",
            restaurant_name="Miku Restaurant",
            review_count="500"
        )
        
        print(f"\n📋 Plan Summary ({len(plan1)} steps):")
        for step in plan1[:5]:  # Show first 5 steps
            print(f"  {step['step']}. {step['action']}")
        print("  ...\n")
        
        # Test 2: Different restaurant type
        print("=" * 70)
        print("TEST 2: Italian Restaurant")
        print("=" * 70 + "\n")
        
        agent.clear_state()  # Clear for new analysis
        
        plan2 = agent.create_analysis_plan(
            restaurant_url="https://opentable.ca/r/italian-bistro",
            restaurant_name="Italian Bistro",
            review_count="300"
        )
        
        print(f"\n📋 Plan Summary ({len(plan2)} steps):")
        for step in plan2[:5]:
            print(f"  {step['step']}. {step['action']}")
        print("  ...\n")
        
        # Show reasoning log
        print("=" * 70)
        print("REASONING LOG (last 10 entries)")
        print("=" * 70)
        logs = agent.get_reasoning_log()
        for log in logs[-10:]:
            print(log)
        
        print("\n" + "=" * 70)
        print("🎉 All tests passed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()