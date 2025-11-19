# Update the base_agent.py file
"""
Base Agent Class

This file contains the core RestaurantAnalysisAgent class that provides
autonomous analysis capabilities for ANY restaurant.

UNIVERSAL DESIGN:
- Works with ANY OpenTable restaurant URL
- Discovers menu items dynamically (no hardcoding)
- Discovers aspects dynamically (adapts to restaurant type)
- Creates analysis plans autonomously
- Executes with full reasoning transparency
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class RestaurantAnalysisAgent:
    """
    Autonomous agent for restaurant review analysis.
    
    This agent can analyze ANY restaurant without prior configuration.
    It discovers menu items, aspects, and patterns directly from reviews.
    
    Key Features:
    - Universal: Works with any restaurant type (Japanese, Italian, Fast Food, etc.)
    - Adaptive: Discovers what matters to each specific restaurant
    - Autonomous: Plans its own analysis strategy
    - Transparent: Logs all reasoning for visibility
    
    Example Usage:
        # Create agent (works for ANY restaurant)
        agent = RestaurantAnalysisAgent()
        
        # Analyze any restaurant
        results = agent.analyze_restaurant(
            url="https://opentable.ca/r/ANY-RESTAURANT"
        )
        
        # Agent automatically discovers:
        # - Menu items (sushi OR pasta OR burgers - whatever exists)
        # - Aspects (presentation OR speed OR value - whatever matters)
        # - Problems (detects issues proactively)
        # - Insights (generates actionable recommendations)
    
    Attributes:
        client: Anthropic API client for Claude
        model: Claude model name to use
        current_plan: List of analysis steps the agent will execute
        reasoning_log: Complete log of agent's decision-making process
        execution_results: Results from each step of analysis
    
    Methods:
        analyze_restaurant(): Main entry point - analyzes any restaurant
        _log_reasoning(): Records agent's thought process
        _create_plan(): Generates analysis strategy
        _execute_plan(): Carries out the analysis
        _generate_insights(): Creates actionable recommendations
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Restaurant Analysis Agent.
        
        This method sets up the agent when you create it:
        - Connects to Claude API
        - Initializes storage for plans and logs
        - Verifies everything is ready
        
        Args:
            api_key: Anthropic API key (optional)
                    If not provided, will look for ANTHROPIC_API_KEY in environment
        
        Raises:
            ValueError: If no API key is found
        
        Example:
            # Option 1: Use API key from .env file
            agent = RestaurantAnalysisAgent()
            
            # Option 2: Provide API key directly
            agent = RestaurantAnalysisAgent(api_key="your-api-key-here")
        """
        
        # Step 1: Get the API key
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "❌ No API key found!\n"
                "Please either:\n"
                "1. Set ANTHROPIC_API_KEY in your .env file, OR\n"
                "2. Pass api_key parameter when creating agent\n"
                "Example: agent = RestaurantAnalysisAgent(api_key='your-key')"
            )
        
        # Step 2: Initialize Claude client
        try:
            self.client = Anthropic(api_key=self.api_key)
            print("🤖 Connected to Claude API successfully")
        except Exception as e:
            raise ConnectionError(f"❌ Failed to connect to Claude API: {e}")
        
        # Step 3: Set the Claude model to use
        # Using Claude Sonnet 4 - best balance of speed and intelligence
        self.model = "claude-sonnet-4-20250514"
        
        # Step 4: Initialize storage (we'll populate these in next tasks)
        # TODO (D1-007): Initialize reasoning_log
        # TODO (D1-008): Initialize current_plan
        self.current_plan: List[Dict[str, Any]] = []
        self.reasoning_log: List[str] = []
        self.execution_results: Dict[str, Any] = {}
        
        # Step 5: Log that agent is ready
        print(f"✅ RestaurantAnalysisAgent initialized")
        print(f"   Model: {self.model}")
        print(f"   Ready to analyze ANY restaurant!")
    
    def __repr__(self) -> str:
        """
        String representation of the agent.
        
        This is what you see when you print the agent object.
        
        Returns:
            String describing the agent
        """
        return (
            f"RestaurantAnalysisAgent("
            f"model={self.model}, "
            f"planned_steps={len(self.current_plan)}, "
            f"logs={len(self.reasoning_log)})"
        )
    
    # TODO (D1-009): Implement _log_reasoning() method
    # TODO (Later): Implement other methods


# Test code - runs when you execute this file directly
if __name__ == "__main__":
    print("=" * 60)
    print("Testing RestaurantAnalysisAgent __init__ method")
    print("=" * 60 + "\n")
    
    try:
        # Test 1: Create agent (should use API key from .env)
        print("Test 1: Creating agent with .env API key...")
        agent = RestaurantAnalysisAgent()
        print(f"✅ Agent created: {agent}\n")
        
        # Test 2: Check attributes exist
        print("Test 2: Checking agent attributes...")
        assert hasattr(agent, 'client'), "Missing 'client' attribute"
        assert hasattr(agent, 'model'), "Missing 'model' attribute"
        assert hasattr(agent, 'current_plan'), "Missing 'current_plan' attribute"
        assert hasattr(agent, 'reasoning_log'), "Missing 'reasoning_log' attribute"
        assert hasattr(agent, 'execution_results'), "Missing 'execution_results' attribute"
        print("✅ All attributes present\n")
        
        # Test 3: Check initial state
        print("Test 3: Checking initial state...")
        assert len(agent.current_plan) == 0, "Plan should start empty"
        assert len(agent.reasoning_log) == 0, "Log should start empty"
        assert len(agent.execution_results) == 0, "Results should start empty"
        print("✅ Initial state correct\n")
        
        # Test 4: Check repr works
        print("Test 4: Checking string representation...")
        agent_str = str(agent)
        print(f"Agent representation: {agent_str}")
        assert "RestaurantAnalysisAgent" in agent_str
        print("✅ String representation works\n")
        
        print("=" * 60)
        print("🎉 All tests passed! __init__ method working correctly!")
        print("=" * 60)
        
    except ValueError as e:
        print(f"❌ ValueError: {e}")
        print("\nMake sure your .env file has ANTHROPIC_API_KEY set!")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()