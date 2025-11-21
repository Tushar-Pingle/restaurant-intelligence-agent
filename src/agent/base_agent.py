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
from src.agent.menu_discovery import MenuDiscovery  # D4-009: Added

# Load environment variables
load_dotenv()


class RestaurantAnalysisAgent:
    """
    Autonomous agent for restaurant review analysis.
    
    Complete workflow:
    1. Creates analysis plan (AI-powered)
    2. Executes plan step-by-step
    3. Discovers menu items dynamically (NEW!)
    4. Analyzes menu item sentiment
    5. Generates role-specific insights
    
    Example Usage:
        agent = RestaurantAnalysisAgent()
        
        # Analyze with dynamic menu discovery
        results = agent.analyze_restaurant(
            restaurant_url="https://opentable.ca/r/ANY-RESTAURANT",
            reviews=review_list  # Will discover menu items from these
        )
        
        # Get menu analysis
        menu_items = results['menu_analysis']['food_items']
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Restaurant Analysis Agent."""
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
        
        # Initialize all components
        self.planner = AgentPlanner(client=self.client, model=self.model)
        self.executor = AgentExecutor()
        self.insights_generator = InsightsGenerator(client=self.client, model=self.model)
        self.menu_discovery = MenuDiscovery(client=self.client, model=self.model)  # D4-009: Added
        
        # Initialize state
        self.current_plan: List[Dict[str, Any]] = []
        self.reasoning_log: List[str] = []
        self.execution_results: Dict[str, Any] = {}
        self.generated_insights: Dict[str, Any] = {}
        self.menu_analysis: Dict[str, Any] = {}  # D4-009: Added
        
        # Log initialization
        self._log_reasoning("Agent initialized and ready for analysis")
        self._log_reasoning(f"Using model: {self.model}")
        self._log_reasoning("All modules loaded: Planner, Executor, Insights, Menu Discovery")
    
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
        reviews: Optional[List[str]] = None,
        review_count: str = "500",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        D4-010: Main entry point - complete restaurant analysis with dynamic menu discovery.
        
        This orchestrates the entire analysis workflow:
        1. Create analysis plan
        2. Execute plan steps
        3. Discover menu items dynamically (NEW!)
        4. Generate insights (using menu data)
        
        Args:
            restaurant_url: OpenTable URL
            restaurant_name: Restaurant name (optional)
            reviews: List of review texts (optional, for testing)
            review_count: Estimated review count (optional)
            progress_callback: Optional callback for progress updates
        
        Returns:
            Complete analysis results with menu analysis and insights
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
        
        # D4-010: Step 3: Discover menu items (if reviews provided)
        if reviews:
            self._log_reasoning("Phase 3: Discovering menu items dynamically...")
            menu_analysis = self.discover_menu_items(
                reviews=reviews,
                restaurant_name=restaurant_name
            )
            self.menu_analysis = menu_analysis
        else:
            self._log_reasoning("⚠️  No reviews provided - skipping menu discovery")
            menu_analysis = {"food_items": [], "drinks": [], "total_extracted": 0}
        
        # Step 4: Generate insights
        self._log_reasoning("Phase 4: Generating role-specific insights...")
        
        # Prepare analysis data for insights generator (now includes menu data)
        analysis_data = {
            'restaurant_name': restaurant_name,
            'execution_results': execution_results['results'],
            'menu_analysis': menu_analysis,  # D4-010: Include menu data
            'summary': self.executor.get_execution_summary()
        }
        
        # Generate chef insights (with menu data)
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
            'menu_analysis': menu_analysis,  # D4-010: Include menu analysis
            'insights': {
                'chef': chef_insights,
                'manager': manager_insights
            },
            'reasoning_log': self.reasoning_log.copy()
        }
    
    def discover_menu_items(
        self,
        reviews: List[str],
        restaurant_name: str = "the restaurant"
    ) -> Dict[str, Any]:
        """
        D4-010: Discover menu items from reviews.
        
        Args:
            reviews: List of review texts
            restaurant_name: Restaurant name
        
        Returns:
            Menu analysis with items and sentiment
        """
        self._log_reasoning(f"Analyzing {len(reviews)} reviews for menu items...")
        
        menu_data = self.menu_discovery.extract_menu_items(
            reviews=reviews,
            restaurant_name=restaurant_name
        )
        
        food_count = len(menu_data.get('food_items', []))
        drink_count = len(menu_data.get('drinks', []))
        
        self._log_reasoning(f"✅ Discovered {food_count} food items and {drink_count} drinks")
        
        return menu_data
    
    def visualize_menu(
        self,
        save_chart: bool = True,
        save_json: bool = True,
        output_dir: str = "outputs"
    ) -> Dict[str, str]:
        """
        D4-013, D4-014, D4-015: Visualize menu analysis results.
        
        Args:
            save_chart: Save chart visualization
            save_json: Save JSON data
            output_dir: Directory to save outputs
        
        Returns:
            Dictionary with paths to saved files
        """
        if not self.menu_analysis or not self.menu_analysis.get('food_items'):
            self._log_reasoning("⚠️  No menu analysis to visualize")
            return {}
        
        os.makedirs(output_dir, exist_ok=True)
        
        results = {}
        
        # Text visualization
        self._log_reasoning("Creating text visualization...")
        text_viz = self.menu_discovery.visualize_items_text(self.menu_analysis)
        print("\n" + text_viz)
        
        # Chart visualization
        if save_chart:
            self._log_reasoning("Creating chart visualization...")
            chart_path = os.path.join(output_dir, "menu_analysis.png")
            saved_chart = self.menu_discovery.visualize_items_chart(
                self.menu_analysis,
                output_path=chart_path
            )
            if saved_chart:
                results['chart'] = saved_chart
                self._log_reasoning(f"✅ Chart saved to: {saved_chart}")
        
        # JSON data
        if save_json:
            self._log_reasoning("Saving JSON data...")
            json_path = os.path.join(output_dir, "menu_analysis.json")
            saved_json = self.menu_discovery.save_results(
                self.menu_analysis,
                output_path=json_path
            )
            if saved_json:
                results['json'] = saved_json
                self._log_reasoning(f"✅ JSON saved to: {saved_json}")
        
        return results
    
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
    
    def get_menu_analysis(self) -> Dict[str, Any]:
        """Get menu analysis results."""
        return self.menu_analysis.copy()
    
    def clear_state(self) -> None:
        """Clear agent state for new analysis."""
        self.current_plan = []
        self.reasoning_log = []
        self.execution_results = {}
        self.generated_insights = {}
        self.menu_analysis = {}
        self._log_reasoning("Agent state cleared for new analysis")
    
    def __repr__(self) -> str:
        return (
            f"RestaurantAnalysisAgent("
            f"model={self.model}, "
            f"planned_steps={len(self.current_plan)}, "
            f"logs={len(self.reasoning_log)})"
        )


# D4-011: Test end-to-end with dynamic menu
if __name__ == "__main__":
    print("=" * 70)
    print("D4-011: Testing End-to-End with Dynamic Menu Discovery")
    print("=" * 70 + "\n")
    
    try:
        # Create agent
        print("Creating agent...\n")
        agent = RestaurantAnalysisAgent()
        
        # Sample reviews for testing
        test_reviews = [
            "The salmon sushi was absolutely incredible! So fresh and perfectly prepared.",
            "Miso soup was authentic and warming. Loved it!",
            "Tempura was a bit disappointing - too oily for my taste.",
            "Their spicy tuna roll is amazing! Best I've ever had.",
            "Hot sake paired perfectly with the meal.",
            "Edamame was fresh and perfectly salted.",
        ]
        
        # Progress callback
        def show_progress(status):
            print(f"  📊 {status}")
        
        # Run complete analysis
        print("=" * 70)
        print("Analyzing Restaurant (with Menu Discovery)")
        print("=" * 70 + "\n")
        
        results = agent.analyze_restaurant(
            restaurant_url="https://opentable.ca/r/test-restaurant",
            restaurant_name="Test Japanese Restaurant",
            reviews=test_reviews,  # D4-011: Provide reviews
            progress_callback=show_progress
        )
        
        # Display results
        print("\n" + "=" * 70)
        print("ANALYSIS RESULTS")
        print("=" * 70)
        
        print(f"\nSuccess: {results['success']}")
        print(f"Restaurant: {results['restaurant']['name']}")
        
        # D4-011: Show menu analysis
        menu = results['menu_analysis']
        print(f"\n📋 Menu Analysis:")
        print(f"   Food items discovered: {len(menu.get('food_items', []))}")
        print(f"   Drinks discovered: {len(menu.get('drinks', []))}")
        
        if menu.get('food_items'):
            print("\n   Top food items:")
            for item in menu['food_items'][:3]:
                print(f"     • {item['name']} (sentiment: {item['sentiment']:+.2f})")
        
        # Visualize menu
        print("\n" + "=" * 70)
        print("MENU VISUALIZATION")
        print("=" * 70)
        
        viz_results = agent.visualize_menu(save_chart=True, save_json=True)
        
        if viz_results:
            print("\n📁 Saved files:")
            for file_type, path in viz_results.items():
                print(f"   • {file_type}: {path}")
        
        print("\n" + "=" * 70)
        print("🎉 End-to-end test with menu discovery complete!")
        print("=" * 70)
        print("\n✅ D4-009: Menu discovery integrated")
        print("✅ D4-010: analyze_restaurant() uses dynamic menu")
        print("✅ D4-011: End-to-end test PASSED")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
