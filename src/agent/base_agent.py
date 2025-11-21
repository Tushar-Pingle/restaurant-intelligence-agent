"""
Base Agent Class

Complete autonomous agent for restaurant review analysis.
Exports organized data in separate files for easy UI access.
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.agent.planner import AgentPlanner
from src.agent.executor import AgentExecutor
from src.agent.insights_generator import InsightsGenerator
from src.agent.menu_discovery import MenuDiscovery
from src.agent.aspect_discovery import AspectDiscovery

load_dotenv()


class RestaurantAnalysisAgent:
    """Autonomous agent for restaurant review analysis."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Restaurant Analysis Agent."""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError("❌ No API key found!")
        
        try:
            self.client = Anthropic(api_key=self.api_key)
        except Exception as e:
            raise ConnectionError(f"❌ Failed to connect to Claude API: {e}")
        
        self.model = "claude-sonnet-4-20250514"
        
        # Initialize components
        self.planner = AgentPlanner(client=self.client, model=self.model)
        self.executor = AgentExecutor()
        self.insights_generator = InsightsGenerator(client=self.client, model=self.model)
        self.menu_discovery = MenuDiscovery(client=self.client, model=self.model)
        self.aspect_discovery = AspectDiscovery(client=self.client, model=self.model)
        
        # State storage
        self.current_plan: List[Dict[str, Any]] = []
        self.reasoning_log: List[str] = []
        self.execution_results: Dict[str, Any] = {}
        self.generated_insights: Dict[str, Any] = {}
        self.menu_analysis: Dict[str, Any] = {}
        self.aspect_analysis: Dict[str, Any] = {}
        
        # Organized summary storage (separate structures)
        self.menu_summaries = {
            "food": {},   # {item_name: {name, sentiment, summary, ...}}
            "drinks": {}  # {drink_name: {name, sentiment, summary, ...}}
        }
        
        self.aspect_summaries = {}  # {aspect_name: {name, sentiment, summary, ...}}
        
        self._log_reasoning("Agent initialized and ready for analysis")
        self._log_reasoning(f"Using model: {self.model}")
    
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
        """Main entry point - complete restaurant analysis."""
        self._log_reasoning(f"Starting analysis for: {restaurant_name}")
        
        # Create plan
        plan = self.create_analysis_plan(restaurant_url, restaurant_name, review_count)
        if not plan:
            return {'success': False, 'error': 'Failed to create plan'}
        
        # Execute plan
        execution_results = self.executor.execute_plan(
            plan=plan, progress_callback=progress_callback,
            context={'url': restaurant_url, 'name': restaurant_name}
        )
        self.execution_results = execution_results
        
        # Discover menu & aspects
        if reviews:
            self._log_reasoning("Phase 3: Discovering menu items...")
            self.menu_analysis = self.discover_menu_items(reviews, restaurant_name)
            
            self._log_reasoning("Phase 4: Discovering aspects...")
            self.aspect_analysis = self.discover_aspects(reviews, restaurant_name)
        else:
            self.menu_analysis = {"food_items": [], "drinks": [], "total_extracted": 0}
            self.aspect_analysis = {"aspects": [], "total_aspects": 0}
        
        # Generate insights
        analysis_data = {
            'restaurant_name': restaurant_name,
            'execution_results': execution_results['results'],
            'menu_analysis': self.menu_analysis,
            'aspect_analysis': self.aspect_analysis,
            'summary': self.executor.get_execution_summary()
        }
        
        chef_insights = self.insights_generator.generate_insights(
            analysis_data=analysis_data, role='chef', restaurant_name=restaurant_name
        )
        
        manager_insights = self.insights_generator.generate_insights(
            analysis_data=analysis_data, role='manager', restaurant_name=restaurant_name
        )
        
        self.generated_insights = {'chef': chef_insights, 'manager': manager_insights}
        
        self._log_reasoning("✅ Analysis complete!")
        
        return {
            'success': True,
            'restaurant': {'name': restaurant_name, 'url': restaurant_url},
            'plan': plan,
            'execution': execution_results,
            'menu_analysis': self.menu_analysis,
            'aspect_analysis': self.aspect_analysis,
            'insights': self.generated_insights,
            'reasoning_log': self.reasoning_log.copy()
        }
    
    def get_item_summary(
        self, item_name: str, item_type: str = "food", restaurant_name: str = "the restaurant"
    ) -> Dict[str, Any]:
        """
        Get or generate summary for a menu item.
        
        Args:
            item_name: Name of item (lowercase)
            item_type: "food" or "drinks"
            restaurant_name: Restaurant name
        
        Returns:
            Dict with name, sentiment, summary, etc.
        """
        # Check cache
        if item_name in self.menu_summaries[item_type]:
            self._log_reasoning(f"Returning cached summary for: {item_name}")
            return self.menu_summaries[item_type][item_name]
        
        # Find and generate
        items = self.menu_analysis.get('food_items' if item_type == 'food' else 'drinks', [])
        
        for item in items:
            if item.get('name', '').lower() == item_name.lower():
                self._log_reasoning(f"Generating summary for: {item_name}")
                summary_text = self.menu_discovery.generate_item_summary(item, restaurant_name)
                
                # Store in cache
                self.menu_summaries[item_type][item_name] = {
                    "name": item['name'],
                    "sentiment": item.get('sentiment', 0),
                    "mention_count": item.get('mention_count', 0),
                    "category": item.get('category', 'unknown'),
                    "summary": summary_text
                }
                
                return self.menu_summaries[item_type][item_name]
        
        return {"name": item_name, "summary": f"No data found for {item_name}"}
    
    def get_aspect_summary(self, aspect_name: str, restaurant_name: str = "the restaurant") -> Dict[str, Any]:
        """
        Get or generate summary for an aspect.
        
        Args:
            aspect_name: Name of aspect (lowercase)
            restaurant_name: Restaurant name
        
        Returns:
            Dict with name, sentiment, summary, etc.
        """
        # Check cache
        if aspect_name in self.aspect_summaries:
            self._log_reasoning(f"Returning cached summary for: {aspect_name}")
            return self.aspect_summaries[aspect_name]
        
        # Find and generate
        for aspect in self.aspect_analysis.get('aspects', []):
            if aspect.get('name', '').lower() == aspect_name.lower():
                self._log_reasoning(f"Generating summary for: {aspect_name}")
                summary_text = self.aspect_discovery.generate_aspect_summary(aspect, restaurant_name)
                
                # Store in cache
                self.aspect_summaries[aspect_name] = {
                    "name": aspect['name'],
                    "sentiment": aspect.get('sentiment', 0),
                    "mention_count": aspect.get('mention_count', 0),
                    "description": aspect.get('description', ''),
                    "summary": summary_text
                }
                
                return self.aspect_summaries[aspect_name]
        
        return {"name": aspect_name, "summary": f"No data found for {aspect_name}"}
    
    def get_all_menu_items(self) -> Dict[str, List[str]]:
        """Get organized list of menu items."""
        food = [item['name'] for item in self.menu_analysis.get('food_items', [])]
        drinks = [drink['name'] for drink in self.menu_analysis.get('drinks', [])]
        return {"food": food, "drinks": drinks}
    
    def get_all_aspects(self) -> List[str]:
        """Get list of all aspects."""
        return [aspect['name'] for aspect in self.aspect_analysis.get('aspects', [])]
    
    def export_analysis(self, output_dir: str = "outputs") -> Dict[str, str]:
        """
        Export organized analysis data to SEPARATE JSON files.
        
        Creates:
        - menu_analysis.json (raw menu data)
        - aspect_analysis.json (raw aspect data)
        - insights.json (chef + manager insights)
        - summaries_menu.json (organized menu summaries for UI)
        - summaries_aspects.json (organized aspect summaries for UI)
        """
        os.makedirs(output_dir, exist_ok=True)
        saved_files = {}
        
        # Raw menu data
        menu_path = os.path.join(output_dir, "menu_analysis.json")
        with open(menu_path, 'w', encoding='utf-8') as f:
            json.dump(self.menu_analysis, f, indent=2, ensure_ascii=False)
        saved_files['menu_raw'] = menu_path
        
        # Raw aspect data
        aspect_path = os.path.join(output_dir, "aspect_analysis.json")
        with open(aspect_path, 'w', encoding='utf-8') as f:
            json.dump(self.aspect_analysis, f, indent=2, ensure_ascii=False)
        saved_files['aspects_raw'] = aspect_path
        
        # Insights
        insights_path = os.path.join(output_dir, "insights.json")
        with open(insights_path, 'w', encoding='utf-8') as f:
            json.dump(self.generated_insights, f, indent=2, ensure_ascii=False)
        saved_files['insights'] = insights_path
        
        # SEPARATE: Menu summaries (for UI)
        menu_summaries_path = os.path.join(output_dir, "summaries_menu.json")
        with open(menu_summaries_path, 'w', encoding='utf-8') as f:
            json.dump(self.menu_summaries, f, indent=2, ensure_ascii=False)
        saved_files['summaries_menu'] = menu_summaries_path
        
        # SEPARATE: Aspect summaries (for UI)
        aspect_summaries_path = os.path.join(output_dir, "summaries_aspects.json")
        with open(aspect_summaries_path, 'w', encoding='utf-8') as f:
            json.dump(self.aspect_summaries, f, indent=2, ensure_ascii=False)
        saved_files['summaries_aspects'] = aspect_summaries_path
        
        self._log_reasoning(f"✅ Exported to {output_dir}/ (separate menu & aspect summaries)")
        
        return saved_files
    
    def discover_menu_items(self, reviews: List[str], restaurant_name: str) -> Dict[str, Any]:
        """Discover menu items."""
        menu_data = self.menu_discovery.extract_menu_items(reviews, restaurant_name)
        food_count = len(menu_data.get('food_items', []))
        drink_count = len(menu_data.get('drinks', []))
        self._log_reasoning(f"✅ Discovered {food_count} food + {drink_count} drinks")
        return menu_data
    
    def discover_aspects(self, reviews: List[str], restaurant_name: str) -> Dict[str, Any]:
        """Discover aspects."""
        aspect_data = self.aspect_discovery.discover_aspects(reviews, restaurant_name)
        aspect_count = len(aspect_data.get('aspects', []))
        self._log_reasoning(f"✅ Discovered {aspect_count} aspects")
        return aspect_data
    
    def create_analysis_plan(
        self, restaurant_url: str, restaurant_name: str = "Unknown", review_count: str = "500"
    ) -> List[Dict[str, Any]]:
        """Create analysis plan."""
        context = {
            "restaurant_name": restaurant_name,
            "data_source": restaurant_url,
            "review_count": review_count,
            "goals": "Comprehensive analysis"
        }
        plan = self.planner.create_plan(context)
        self.current_plan = plan
        return plan
    
    def visualize_menu(self, save_chart: bool = True, output_dir: str = "outputs") -> Dict[str, str]:
        """Visualize menu."""
        if not self.menu_analysis.get('food_items'):
            return {}
        
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        
        text_viz = self.menu_discovery.visualize_items_text(self.menu_analysis)
        print("\n" + text_viz)
        
        if save_chart:
            chart_path = os.path.join(output_dir, "menu_chart.png")
            saved = self.menu_discovery.visualize_items_chart(self.menu_analysis, chart_path)
            if saved:
                results['chart'] = saved
        
        return results
    
    def clear_state(self) -> None:
        """Clear agent state."""
        self.current_plan = []
        self.reasoning_log = []
        self.execution_results = {}
        self.generated_insights = {}
        self.menu_analysis = {}
        self.aspect_analysis = {}
        self.menu_summaries = {"food": {}, "drinks": {}}
        self.aspect_summaries = {}
        self._log_reasoning("Agent state cleared")
    
    def __repr__(self) -> str:
        items = self.get_all_menu_items()
        total = len(items['food']) + len(items['drinks'])
        return f"RestaurantAnalysisAgent(items={total}, aspects={len(self.get_all_aspects())})"


# Test separate JSON exports
if __name__ == "__main__":
    print("=" * 70)
    print("Testing Separate JSON Exports")
    print("=" * 70 + "\n")
    
    agent = RestaurantAnalysisAgent()
    
    test_reviews = [
        "Salmon sushi was incredible! So fresh.",
        "Service speed slow - waited 25 minutes.",
        "Hot sake paired perfectly.",
        "Presentation stunning!",
    ]
    
    results = agent.analyze_restaurant(
        restaurant_url="https://test.com",
        restaurant_name="Test Restaurant",
        reviews=test_reviews
    )
    
    # Generate some summaries
    items = agent.get_all_menu_items()
    aspects = agent.get_all_aspects()
    
    if items['food']:
        agent.get_item_summary(items['food'][0], "food", "Test Restaurant")
    
    if items['drinks']:
        agent.get_item_summary(items['drinks'][0], "drinks", "Test Restaurant")
    
    if aspects:
        agent.get_aspect_summary(aspects[0], "Test Restaurant")
    
    # Export
    print("\n" + "=" * 70)
    print("EXPORTING SEPARATE JSONs")
    print("=" * 70 + "\n")
    
    files = agent.export_analysis()
    for file_type, path in files.items():
        print(f"✅ {file_type}: {path}")
    
    print("\n" + "=" * 70)
    print("📁 Check outputs/ folder:")
    print("   - summaries_menu.json (food + drinks)")
    print("   - summaries_aspects.json (aspects)")
    print("=" * 70)
