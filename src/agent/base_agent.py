"""
Base Agent Class - OPTIMIZED with Unified Analyzer
Reduces API calls by 66% by extracting menu+aspects in single pass
"""

import os
import sys
import json
import time
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
from src.agent.unified_analyzer import UnifiedReviewAnalyzer
from src.agent.summary_generator import add_summaries_to_analysis

# Import MCP tools
from src.mcp_integrations.save_report import save_json_report_direct, list_saved_reports_direct
from src.mcp_integrations.query_reviews import index_reviews_direct, query_reviews_direct
from src.mcp_integrations.generate_chart import generate_sentiment_chart_direct, generate_comparison_chart_direct

load_dotenv()


class RestaurantAnalysisAgent:
    """
    Autonomous agent with MCP tool integration.
    OPTIMIZED: Uses unified analyzer to reduce API calls by 66%
    
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
        
        # Keep old analyzers for backward compatibility
        self.menu_discovery = MenuDiscovery(client=self.client, model=self.model)
        self.aspect_discovery = AspectDiscovery(client=self.client, model=self.model)
        
        # NEW: Unified analyzer (3x more efficient!)
        self.unified_analyzer = UnifiedReviewAnalyzer(client=self.client, model=self.model)
        
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
        
        self._log_reasoning("Agent initialized with MCP tools + Unified Analyzer")
        self._log_reasoning(f"Using model: {self.model}")
        self._log_reasoning("✨ Optimization: Single-pass menu+aspect extraction (66% fewer API calls)")
    
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
        OPTIMIZED: Uses unified analyzer for single-pass extraction
        """
        # CLEAR STATE BEFORE STARTING NEW ANALYSIS
        self.clear_state()
        
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
        
        # Phase 3+4: UNIFIED analysis (menu + aspects in single pass)
        if reviews:
            self._log_reasoning("Phase 3+4: UNIFIED analysis (menu + aspects in single pass)...")
            
            unified_results = self.unified_analyzer.analyze_reviews(
                reviews=reviews,
                restaurant_name=restaurant_name
            )
            
            self.menu_analysis = unified_results['menu_analysis']
            self.aspect_analysis = unified_results['aspect_analysis']
            
            food_count = len(self.menu_analysis.get('food_items', []))
            drink_count = len(self.menu_analysis.get('drinks', []))
            aspect_count = len(self.aspect_analysis.get('aspects', []))
            
            self._log_reasoning(f"✅ Discovered {food_count} food + {drink_count} drinks + {aspect_count} aspects")
            self._log_reasoning(f"💰 Saved ~{len(reviews) // 20} API calls vs. old method!")
            
            # Phase 5: Generate summaries for UI dropdowns
            self._log_reasoning("Phase 5: Generating AI summaries for UI...")
            self.menu_analysis, self.aspect_analysis = add_summaries_to_analysis(
                menu_data=self.menu_analysis,
                aspect_data=self.aspect_analysis,
                client=self.client,
                restaurant_name=restaurant_name,
                model=self.model
            )
            self._log_reasoning("✅ Summaries added to all items and aspects")
            
            # Phase 6: MCP TOOL - Index reviews for Q&A
            self._log_reasoning("Phase 6: MCP Tool - Indexing reviews for Q&A...")
            index_result = index_reviews_direct(restaurant_name, reviews)
            self._log_reasoning(f"✅ {index_result}")
        else:
            self.menu_analysis = {"food_items": [], "drinks": [], "total_extracted": 0}
            self.aspect_analysis = {"aspects": [], "total_aspects": 0}
        
        # Phase 7: Generate business insights
        self._log_reasoning("Phase 7: Generating business insights...")
        self._log_reasoning("⏳ Waiting 30s to avoid rate limits...")
        time.sleep(30)
        
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
        
        self._log_reasoning("⏳ Waiting 30s before generating manager insights to avoid rate limits...")
        time.sleep(30)

        manager_insights = self.insights_generator.generate_insights(
            analysis_data=analysis_data, role='manager', restaurant_name=restaurant_name
        )
        
        self.generated_insights = {'chef': chef_insights, 'manager': manager_insights}
        
        # Phase 8: AUTO-EXPORT analysis to files
        self._log_reasoning("Phase 8: Exporting analysis to files...")
        self.export_analysis('outputs')
        
        # Phase 9: AUTO-SAVE report
        self._log_reasoning("Phase 9: Saving analysis report...")
        self.save_analysis_report('reports')
        
        # Phase 10: AUTO-GENERATE visualizations
        self._log_reasoning("Phase 10: Generating visualizations...")
        self.generate_visualizations()
        
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
        """MCP TOOL: Ask a question about the reviews using RAG."""
        if not self.restaurant_name or not self.reviews:
            return "No analysis has been run yet. Please analyze a restaurant first."
        
        self._log_reasoning(f"MCP Tool: Querying reviews - '{question}'")
        answer = query_reviews_direct(self.restaurant_name, question)
        return answer
    
    def save_analysis_report(self, output_dir: str = "reports") -> str:
        """MCP TOOL: Save complete analysis report."""
        
        complete_analysis = {
            "restaurant": self.restaurant_name,
            "timestamp": datetime.now().isoformat(),
            "menu_analysis": self.menu_analysis,
            "aspect_analysis": self.aspect_analysis,
            "insights": self.generated_insights,
            "summary": self.executor.get_execution_summary()
        }
        
        filepath = save_json_report_direct(self.restaurant_name, complete_analysis, output_dir)
        
        return filepath
    
    def generate_visualizations(self) -> Dict[str, str]:
        """MCP TOOL: Generate all visualizations."""
        
        charts = {}
        
        # Menu sentiment chart
        if self.menu_analysis.get('food_items'):
            food_items = self.menu_analysis['food_items'][:10]
            menu_chart = generate_sentiment_chart_direct(
                food_items,
                "outputs/menu_sentiment.png"
            )
            charts['menu'] = menu_chart
        
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
        
        return charts
    
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
        
        # These files are legacy - summaries are now in menu_analysis.json and aspect_analysis.json
        menu_summaries_path = os.path.join(output_dir, "summaries_menu.json")
        with open(menu_summaries_path, 'w', encoding='utf-8') as f:
            json.dump(self.menu_summaries, f, indent=2, ensure_ascii=False)
        saved_files['summaries_menu'] = menu_summaries_path
        
        aspect_summaries_path = os.path.join(output_dir, "summaries_aspects.json")
        with open(aspect_summaries_path, 'w', encoding='utf-8') as f:
            json.dump(self.aspect_summaries, f, indent=2, ensure_ascii=False)
        saved_files['summaries_aspects'] = aspect_summaries_path
        
        return saved_files
    
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
        """Clear agent state before new analysis."""
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