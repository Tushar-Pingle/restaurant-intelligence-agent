"""
Base Agent Class

Complete autonomous agent with MCP tool integration.
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

# Import agent components
from src.agent.planner import AgentPlanner
from src.agent.executor import AgentExecutor
from src.agent.insights_generator import InsightsGenerator
from src.agent.menu_discovery import MenuDiscovery
from src.agent.aspect_discovery import AspectDiscovery

# Import MCP tools
from src.mcp_integrations.save_report import save_json_report_direct, list_saved_reports_direct
from src.mcp_integrations.query_reviews import index_reviews_direct, query_reviews_direct
from src.mcp_integrations.generate_chart import generate_sentiment_chart_direct, generate_comparison_chart_direct

load_dotenv()


class RestaurantAnalysisAgent:
    """
    Autonomous agent with MCP tool integration.
    
    MCP Tools Available:
    - save_report: Save analysis to files
    - query_reviews: RAG Q&A on reviews
    - generate_chart: Create visualizations
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Restaurant Analysis Agent with MCP tools."""
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
        
        # Summary storage
        self.menu_summaries = {"food": {}, "drinks": {}}
        self.aspect_summaries = {}
        
        # Store reviews for Q&A
        self.reviews: List[str] = []
        self.restaurant_name: str = ""
        
        self._log_reasoning("Agent initialized with MCP tools")
        self._log_reasoning(f"Using model: {self.model}")
        self._log_reasoning("MCP tools: save_report, query_reviews, generate_chart")
    
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
        Main entry point - complete restaurant analysis with MCP tools.
        
        MCP tools used:
        - index_reviews (for Q&A)
        - save_report (exports)
        - generate_chart (visualizations)
        """
        self._log_reasoning(f"Starting analysis for: {restaurant_name}")
        
        # Store for later use
        self.restaurant_name = restaurant_name
        self.reviews = reviews or []
        
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
            
            # MCP TOOL: Index reviews for Q&A
            self._log_reasoning("MCP Tool: Indexing reviews for Q&A...")
            index_result = index_reviews_direct(restaurant_name, reviews)
            self._log_reasoning(f"✅ {index_result}")
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
    
    def ask_question(self, question: str) -> str:
        """
        MCP TOOL: Ask a question about the reviews using RAG.
        
        Args:
            question: Question to ask
        
        Returns:
            Answer based on reviews
        """
        if not self.restaurant_name or not self.reviews:
            return "No analysis has been run yet. Please analyze a restaurant first."
        
        self._log_reasoning(f"MCP Tool: Querying reviews - '{question}'")
        answer = query_reviews_direct(self.restaurant_name, question)
        return answer
    
    def save_analysis_report(self, output_dir: str = "reports") -> str:
        """
        MCP TOOL: Save complete analysis report.
        
        Args:
            output_dir: Directory to save report
        
        Returns:
            Path to saved report
        """
        self._log_reasoning("MCP Tool: Saving analysis report...")
        
        complete_analysis = {
            "restaurant": self.restaurant_name,
            "timestamp": datetime.now().isoformat(),
            "menu_analysis": self.menu_analysis,
            "aspect_analysis": self.aspect_analysis,
            "insights": self.generated_insights,
            "summary": self.executor.get_execution_summary()
        }
        
        filepath = save_json_report_direct(self.restaurant_name, complete_analysis, output_dir)
        self._log_reasoning(f"✅ Report saved to: {filepath}")
        
        return filepath
    
    def generate_visualizations(self) -> Dict[str, str]:
        """
        MCP TOOL: Generate all visualizations.
        
        Returns:
            Dict with paths to generated charts
        """
        self._log_reasoning("MCP Tool: Generating visualizations...")
        
        charts = {}
        
        # Menu sentiment chart
        if self.menu_analysis.get('food_items'):
            food_items = self.menu_analysis['food_items'][:10]
            menu_chart = generate_sentiment_chart_direct(
                food_items,
                "outputs/menu_sentiment.png"
            )
            charts['menu'] = menu_chart
            self._log_reasoning(f"✅ Menu chart: {menu_chart}")
        
        # Aspect comparison chart
        if self.aspect_analysis.get('aspects'):
            aspect_data = {
                a['name']: a['sentiment'] 
                for a in self.aspect_analysis['aspects'][:10]
            }
            aspect_chart = generate_comparison_chart_direct(
                aspect_data,
                "outputs/aspect_comparison.png",
                "Aspect Sentiment Comparison"
            )
            charts['aspects'] = aspect_chart
            self._log_reasoning(f"✅ Aspect chart: {aspect_chart}")
        
        return charts
    
    # ... (keep all other existing methods)
    
    def get_item_summary(
        self, item_name: str, item_type: str = "food", restaurant_name: str = "the restaurant"
    ) -> Dict[str, Any]:
        """Get or generate summary for a menu item."""
        if item_name in self.menu_summaries[item_type]:
            return self.menu_summaries[item_type][item_name]
        
        items = self.menu_analysis.get('food_items' if item_type == 'food' else 'drinks', [])
        
        for item in items:
            if item.get('name', '').lower() == item_name.lower():
                summary_text = self.menu_discovery.generate_item_summary(item, restaurant_name)
                
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
        """Get or generate summary for an aspect."""
        if aspect_name in self.aspect_summaries:
            return self.aspect_summaries[aspect_name]
        
        for aspect in self.aspect_analysis.get('aspects', []):
            if aspect.get('name', '').lower() == aspect_name.lower():
                summary_text = self.aspect_discovery.generate_aspect_summary(aspect, restaurant_name)
                
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
        """Export organized analysis data to JSON files."""
        os.makedirs(output_dir, exist_ok=True)
        saved_files = {}
        
        menu_path = os.path.join(output_dir, "menu_analysis.json")
        with open(menu_path, 'w', encoding='utf-8') as f:
            json.dump(self.menu_analysis, f, indent=2, ensure_ascii=False)
        saved_files['menu'] = menu_path
        
        aspect_path = os.path.join(output_dir, "aspect_analysis.json")
        with open(aspect_path, 'w', encoding='utf-8') as f:
            json.dump(self.aspect_analysis, f, indent=2, ensure_ascii=False)
        saved_files['aspects'] = aspect_path
        
        insights_path = os.path.join(output_dir, "insights.json")
        with open(insights_path, 'w', encoding='utf-8') as f:
            json.dump(self.generated_insights, f, indent=2, ensure_ascii=False)
        saved_files['insights'] = insights_path
        
        menu_summaries_path = os.path.join(output_dir, "summaries_menu.json")
        with open(menu_summaries_path, 'w', encoding='utf-8') as f:
            json.dump(self.menu_summaries, f, indent=2, ensure_ascii=False)
        saved_files['summaries_menu'] = menu_summaries_path
        
        aspect_summaries_path = os.path.join(output_dir, "summaries_aspects.json")
        with open(aspect_summaries_path, 'w', encoding='utf-8') as f:
            json.dump(self.aspect_summaries, f, indent=2, ensure_ascii=False)
        saved_files['summaries_aspects'] = aspect_summaries_path
        
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
        self.reviews = []
        self.restaurant_name = ""
    
    def __repr__(self) -> str:
        items = self.get_all_menu_items()
        total = len(items['food']) + len(items['drinks'])
        return f"RestaurantAnalysisAgent(items={total}, aspects={len(self.get_all_aspects())})"


# Test with MCP tools
if __name__ == "__main__":
    print("=" * 70)
    print("Testing Agent with MCP Tools")
    print("=" * 70 + "\n")
    
    agent = RestaurantAnalysisAgent()
    
    test_reviews = [
        "Salmon sushi was incredible! So fresh and perfectly prepared.",
        "Service was slow - we waited 25 minutes for our food.",
        "Miso soup was authentic and warming.",
        "Presentation is absolutely stunning! Every dish is art.",
        "Hot sake paired perfectly with the meal.",
    ]
    
    # Run analysis
    results = agent.analyze_restaurant(
        restaurant_url="https://test.com",
        restaurant_name="Test Restaurant",
        reviews=test_reviews
    )
    
    print("\n" + "=" * 70)
    print("TESTING MCP TOOLS")
    print("=" * 70 + "\n")
    
    # Test Q&A
    print("MCP Tool: query_reviews")
    print("-" * 70)
    answer = agent.ask_question("What do customers say about the salmon sushi?")
    print(f"Q: What do customers say about the salmon sushi?")
    print(f"A: {answer}\n")
    
    # Test save report
    print("MCP Tool: save_report")
    print("-" * 70)
    report_path = agent.save_analysis_report()
    print(f"✅ Report saved to: {report_path}\n")
    
    # Test generate charts
    print("MCP Tool: generate_chart")
    print("-" * 70)
    charts = agent.generate_visualizations()
    for chart_type, path in charts.items():
        print(f"✅ {chart_type} chart: {path}")
    
    print("\n" + "=" * 70)
    print("🎉 Agent + MCP Tools working together!")
    print("=" * 70)
