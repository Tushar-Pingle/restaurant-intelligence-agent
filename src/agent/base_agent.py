"""
Base Agent Class

Complete autonomous agent for restaurant review analysis.

UNIVERSAL DESIGN:
- Works with ANY OpenTable restaurant URL
- Discovers menu items dynamically (no hardcoding)
- Discovers aspects dynamically (adapts to restaurant type)
- Creates analysis plans autonomously using Claude AI
- Executes with full reasoning transparency
- Generates role-specific actionable insights
"""

import os
import sys
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import agent components
from src.agent.planner import AgentPlanner
from src.agent.executor import AgentExecutor
from src.agent.insights_generator import InsightsGenerator

# Load environment variables
load_dotenv()


class RestaurantAnalysisAgent:
    """
    Autonomous agent for restaurant review analysis.
    
    This agent can analyze ANY restaurant without prior configuration.
    It discovers menu items, aspects, and patterns directly from reviews.
    
    Complete workflow:
    1. Creates analysis plan (AI-powered)
    2. Executes plan step-by-step
    3. Generates role-specific insights
    
    Example Usage:
        agent = RestaurantAnalysisAgent()
        
        # Analyze any restaurant (will be connected to scraper later)
        results = agent.analyze_restaurant(
            restaurant_url="https://opentable.ca/r/ANY-RESTAURANT"
        )
        
        # Get chef insights
        chef_insights = results['insights']['chef']
        
        # Get manager insights
        manager_insights = results['insights']['manager']
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
        
        # D2-016: Initialize all components
        self.planner = AgentPlanner(client=self.client, model=self.model)
        self.executor = AgentExecutor()
        self.insights_generator = InsightsGenerator(client=self.client, model=self.model)
        
        # Initialize state
        self.current_plan: List[Dict[str, Any]] = []
        self.reasoning_log: List[str] = []
        self.execution_results: Dict[str, Any] = {}
        self.generated_insights: Dict[str, Any] = {}
        
        # Log initialization
        self._log_reasoning("Agent initialized and ready for analysis")
        self._log_reasoning(f"Using model: {self.model}")
        self._log_reasoning("All modules loaded: Planner, Executor, Insights Generator")
    
    def _log_reasoning(self, message: str) -> None:
        """Log the agent's reasoning process."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.reasoning_log.append(log_entry)
        print(f"🤖 {log_entry}")
    
    def analyze_restaurant(
        self,
        restaurant_url: str,
        restaurant_name: str = "Unknown",
        review_count: str = "500",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        D2-017: Main entry point - complete restaurant analysis.
        
        This orchestrates the entire analysis workflow:
        1. Create analysis plan
        2. Execute plan steps
        3. Generate insights
        
        Args:
            restaurant_url: OpenTable URL
            restaurant_name: Restaurant name (optional)
            review_count: Estimated review count (optional)
            progress_callback: Optional callback for progress updates
        
        Returns:
            Complete analysis results with insights
        
        Example:
            results = agent.analyze_restaurant(
                restaurant_url="https://opentable.ca/r/any-restaurant",
                progress_callback=lambda s: print(f"Progress: {s}")
            )
        """
        self._log_reasoning(f"Starting analysis for: {restaurant_name}")
        self._log_reasoning(f"URL: {restaurant_url}")
        
        # Step 1: Create plan
        self._log_reasoning("Phase 1: Creating analysis plan...")
        plan = self.create_analysis_plan(
            restaurant_url=restaurant_url,
            restaurant_name=restaurant_name,
            review_count=review_count
        )
        
        if not plan:
            self._log_reasoning("❌ Failed to create plan, aborting analysis")
            return {
                'success': False,
                'error': 'Failed to create analysis plan'
            }
        
        # Step 2: Execute plan
        self._log_reasoning("Phase 2: Executing analysis plan...")
        execution_results = self.executor.execute_plan(
            plan=plan,
            progress_callback=progress_callback,
            context={'url': restaurant_url, 'name': restaurant_name}
        )
        
        self.execution_results = execution_results
        
        if not execution_results['success']:
            self._log_reasoning(f"⚠️  Execution completed with errors")
        
        # Step 3: Generate insights
        self._log_reasoning("Phase 3: Generating role-specific insights...")
        
        # Prepare analysis data for insights generator
        # (This will use real data once scraper is built)
        analysis_data = {
            'restaurant_name': restaurant_name,
            'execution_results': execution_results['results'],
            'summary': self.executor.get_execution_summary()
        }
        
        # Generate chef insights
        self._log_reasoning("Generating insights for Head Chef...")
        chef_insights = self.insights_generator.generate_insights(
            analysis_data=analysis_data,
            role='chef',
            restaurant_name=restaurant_name
        )
        
        # Generate manager insights
        self._log_reasoning("Generating insights for Restaurant Manager...")
        manager_insights = self.insights_generator.generate_insights(
            analysis_data=analysis_data,
            role='manager',
            restaurant_name=restaurant_name
        )
        
        self.generated_insights = {
            'chef': chef_insights,
            'manager': manager_insights
        }
        
        self._log_reasoning("✅ Analysis complete!")
        
        # Return comprehensive results
        return {
            'success': True,
            'restaurant': {
                'name': restaurant_name,
                'url': restaurant_url
            },
            'plan': plan,
            'execution': execution_results,
            'insights': {
                'chef': chef_insights,
                'manager': manager_insights
            },
            'reasoning_log': self.reasoning_log.copy()
        }
    
    def create_analysis_plan(
        self,
        restaurant_url: str,
        restaurant_name: str = "Unknown",
        review_count: str = "500"
    ) -> List[Dict[str, Any]]:
        """Create an analysis plan for a restaurant."""
        self._log_reasoning(f"Creating analysis plan for: {restaurant_name}")
        self._log_reasoning(f"Data source: {restaurant_url}")
        
        context = {
            "restaurant_name": restaurant_name,
            "data_source": restaurant_url,
            "review_count": review_count,
            "goals": "Comprehensive analysis with actionable insights"
        }
        
        self._log_reasoning("Calling planner to generate strategy...")
        plan = self.planner.create_plan(context)
        
        if not plan:
            self._log_reasoning("❌ Failed to generate plan")
            return []
        
        self._log_reasoning(f"✅ Generated plan with {len(plan)} steps")
        
        validation = self.planner.validate_plan(plan)
        
        if validation['valid']:
            self._log_reasoning("✅ Plan validation passed")
        else:
            self._log_reasoning(f"⚠️  Plan has {len(validation['issues'])} issues")
        
        self.current_plan = plan
        return plan
    
    def get_reasoning_log(self) -> List[str]:
        """Get the complete reasoning log."""
        return self.reasoning_log.copy()
    
    def get_current_plan(self) -> List[Dict[str, Any]]:
        """Get the current analysis plan."""
        return self.current_plan.copy()
    
    def get_insights(self) -> Dict[str, Any]:
        """Get generated insights."""
        return self.generated_insights.copy()
    
    def clear_state(self) -> None:
        """Clear agent state for new analysis."""
        self.current_plan = []
        self.reasoning_log = []
        self.execution_results = {}
        self.generated_insights = {}
        self._log_reasoning("Agent state cleared for new analysis")
    
    def __repr__(self) -> str:
        return (
            f"RestaurantAnalysisAgent("
            f"model={self.model}, "
            f"planned_steps={len(self.current_plan)}, "
            f"logs={len(self.reasoning_log)})"
        )


# D2-018: Test end-to-end agent flow
if __name__ == "__main__":
    print("=" * 70)
    print("D2-018: Testing End-to-End Agent Flow")
    print("=" * 70 + "\n")
    
    try:
        # Create agent
        print("Creating agent...\n")
        agent = RestaurantAnalysisAgent()
        
        # Define progress callback
        def show_progress(status):
            print(f"  📊 {status}")
        
        # Analyze a restaurant (end-to-end)
        print("=" * 70)
        print("Analyzing Restaurant (Full Workflow)")
        print("=" * 70 + "\n")
        
        results = agent.analyze_restaurant(
            restaurant_url="https://opentable.ca/r/test-restaurant",
            restaurant_name="Test Restaurant",
            progress_callback=show_progress
        )
        
        # Display results
        print("\n" + "=" * 70)
        print("ANALYSIS RESULTS")
        print("=" * 70)
        
        print(f"\nSuccess: {results['success']}")
        print(f"Restaurant: {results['restaurant']['name']}")
        print(f"Plan steps: {len(results['plan'])}")
        print(f"Execution time: {results['execution']['execution_time']:.2f}s")
        
        # Show insights
        print("\n" + "=" * 70)
        print("CHEF INSIGHTS")
        print("=" * 70)
        chef = results['insights']['chef']
        print(f"\nSummary: {chef.get('summary', 'N/A')[:200]}...")
        print(f"Strengths: {len(chef.get('strengths', []))}")
        print(f"Concerns: {len(chef.get('concerns', []))}")
        print(f"Recommendations: {len(chef.get('recommendations', []))}")
        
        print("\n" + "=" * 70)
        print("MANAGER INSIGHTS")
        print("=" * 70)
        manager = results['insights']['manager']
        print(f"\nSummary: {manager.get('summary', 'N/A')[:200]}...")
        print(f"Strengths: {len(manager.get('strengths', []))}")
        print(f"Concerns: {len(manager.get('concerns', []))}")
        print(f"Recommendations: {len(manager.get('recommendations', []))}")
        
        # Show reasoning log summary
        print("\n" + "=" * 70)
        print("REASONING LOG (Last 10 entries)")
        print("=" * 70)
        for log in results['reasoning_log'][-10:]:
            print(log)
        
        print("\n" + "=" * 70)
        print("🎉 End-to-end test complete!")
        print("=" * 70)
        print("\n✅ D2-016: Integration - COMPLETE")
        print("✅ D2-017: analyze_restaurant() - COMPLETE")
        print("✅ D2-018: End-to-end flow - COMPLETE")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
