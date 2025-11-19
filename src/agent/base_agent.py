# Update base_agent.py with the complete base agent
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
        
        # Agent logs its thinking
        agent._log_reasoning("Starting analysis for new restaurant")
        agent._log_reasoning("Discovered 45 menu items from reviews")
        
        # View the reasoning log
        for entry in agent.get_reasoning_log():
            print(entry)
    
    Attributes:
        client: Anthropic API client for Claude
        model: Claude model name to use
        current_plan: List of analysis steps the agent will execute (D1-008)
        reasoning_log: Complete log of agent's decision-making process (D1-007)
        execution_results: Results from each step of analysis
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Restaurant Analysis Agent.
        
        Sets up the agent with Claude API connection and empty storage
        for plans, logs, and results.
        
        Args:
            api_key: Anthropic API key (optional)
                    If not provided, will look for ANTHROPIC_API_KEY in environment
        
        Raises:
            ValueError: If no API key is found
        
        Example:
            agent = RestaurantAnalysisAgent()
            print(agent)  # Shows agent info
        """
        
        # Get the API key
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "❌ No API key found!\n"
                "Please either:\n"
                "1. Set ANTHROPIC_API_KEY in your .env file, OR\n"
                "2. Pass api_key parameter when creating agent\n"
                "Example: agent = RestaurantAnalysisAgent(api_key='your-key')"
            )
        
        # Initialize Claude client
        try:
            self.client = Anthropic(api_key=self.api_key)
        except Exception as e:
            raise ConnectionError(f"❌ Failed to connect to Claude API: {e}")
        
        # Set the Claude model
        self.model = "claude-sonnet-4-20250514"
        
        # D1-008: Initialize current_plan (list of steps to execute)
        self.current_plan: List[Dict[str, Any]] = []
        
        # D1-007: Initialize reasoning_log (tracks agent's thinking)
        self.reasoning_log: List[str] = []
        
        # Initialize execution results storage
        self.execution_results: Dict[str, Any] = {}
        
        # Log that agent is ready
        self._log_reasoning("Agent initialized and ready for analysis")
    
    def _log_reasoning(self, message: str) -> None:
        """
        D1-009: Log the agent's reasoning process.
        
        This method records what the agent is thinking/doing at each step.
        All reasoning is timestamped and stored for transparency.
        
        Args:
            message: The reasoning message to log
        
        Example:
            agent._log_reasoning("Discovered 52 menu items from reviews")
            agent._log_reasoning("Detected service quality issue - alerting manager")
        
        Notes:
            - Logs are stored in self.reasoning_log
            - Each entry has a timestamp
            - Prints to console for real-time visibility
        """
        # Create timestamped log entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # Add to reasoning log
        self.reasoning_log.append(log_entry)
        
        # Print for real-time visibility
        print(f"🤖 {log_entry}")
    
    def get_reasoning_log(self) -> List[str]:
        """
        Get the complete reasoning log.
        
        Returns:
            Copy of the reasoning log (list of timestamped messages)
        
        Example:
            logs = agent.get_reasoning_log()
            for log in logs:
                print(log)
        """
        return self.reasoning_log.copy()
    
    def clear_state(self) -> None:
        """
        Clear agent state for a new analysis.
        
        Resets the plan, logs, and results. Useful when analyzing
        multiple restaurants with the same agent instance.
        
        Example:
            agent.analyze_restaurant("restaurant1")
            agent.clear_state()  # Reset for next analysis
            agent.analyze_restaurant("restaurant2")
        """
        self.current_plan = []
        self.reasoning_log = []
        self.execution_results = {}
        self._log_reasoning("Agent state cleared for new analysis")
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current agent state.
        
        Returns:
            Dictionary with state information
        
        Example:
            state = agent.get_state_summary()
            print(f"Agent has {state['log_entries']} log entries")
        """
        return {
            "model": self.model,
            "planned_steps": len(self.current_plan),
            "log_entries": len(self.reasoning_log),
            "results_stored": len(self.execution_results)
        }
    
    def __repr__(self) -> str:
        """
        String representation of the agent.
        
        Returns:
            String describing the agent's current state
        """
        return (
            f"RestaurantAnalysisAgent("
            f"model={self.model}, "
            f"planned_steps={len(self.current_plan)}, "
            f"logs={len(self.reasoning_log)})"
        )


# D1-010: Test code - runs when you execute this file directly
if __name__ == "__main__":
    print("=" * 70)
    print("D1-010: TESTING RestaurantAnalysisAgent Base Structure")
    print("=" * 70 + "\n")
    
    try:
        # Test 1: Create agent
        print("Test 1: Creating agent...")
        agent = RestaurantAnalysisAgent()
        print(f"✅ Agent created: {agent}\n")
        
        # Test 2: Check attributes exist (D1-007, D1-008)
        print("Test 2: Checking attributes (D1-007, D1-008)...")
        assert hasattr(agent, 'client'), "❌ Missing 'client'"
        assert hasattr(agent, 'model'), "❌ Missing 'model'"
        assert hasattr(agent, 'current_plan'), "❌ Missing 'current_plan' (D1-008)"
        assert hasattr(agent, 'reasoning_log'), "❌ Missing 'reasoning_log' (D1-007)"
        assert hasattr(agent, 'execution_results'), "❌ Missing 'execution_results'"
        print("✅ All attributes present\n")
        
        # Test 3: Check initial state
        print("Test 3: Checking initial state...")
        assert len(agent.current_plan) == 0, "❌ Plan should start empty"
        assert len(agent.reasoning_log) == 1, "❌ Should have 1 log entry (initialization)"
        assert len(agent.execution_results) == 0, "❌ Results should start empty"
        print("✅ Initial state correct\n")
        
        # Test 4: Test _log_reasoning() method (D1-009)
        print("Test 4: Testing _log_reasoning() method (D1-009)...")
        initial_log_count = len(agent.reasoning_log)
        
        agent._log_reasoning("Test reasoning message 1")
        agent._log_reasoning("Test reasoning message 2")
        agent._log_reasoning("Analyzing restaurant reviews")
        
        assert len(agent.reasoning_log) == initial_log_count + 3, "❌ Logs not added correctly"
        assert "Test reasoning message 1" in agent.reasoning_log[-3]
        assert "Test reasoning message 2" in agent.reasoning_log[-2]
        assert "Analyzing restaurant reviews" in agent.reasoning_log[-1]
        print("✅ _log_reasoning() working correctly\n")
        
        # Test 5: Test get_reasoning_log()
        print("Test 5: Testing get_reasoning_log()...")
        logs = agent.get_reasoning_log()
        assert isinstance(logs, list), "❌ Should return a list"
        assert len(logs) > 0, "❌ Should have log entries"
        print(f"✅ Retrieved {len(logs)} log entries\n")
        
        # Test 6: Display sample logs
        print("Test 6: Sample reasoning log entries:")
        print("-" * 70)
        for log in logs[-3:]:  # Show last 3 entries
            print(f"  {log}")
        print("-" * 70 + "\n")
        
        # Test 7: Test clear_state()
        print("Test 7: Testing clear_state()...")
        agent.clear_state()
        assert len(agent.current_plan) == 0, "❌ Plan not cleared"
        assert len(agent.reasoning_log) == 1, "❌ Log not cleared (should have 1 entry from clear)"
        assert len(agent.execution_results) == 0, "❌ Results not cleared"
        print("✅ clear_state() working correctly\n")
        
        # Test 8: Test get_state_summary()
        print("Test 8: Testing get_state_summary()...")
        agent._log_reasoning("Adding some test logs")
        agent._log_reasoning("For state summary test")
        state = agent.get_state_summary()
        print(f"State summary: {state}")
        assert 'model' in state
        assert 'planned_steps' in state
        assert 'log_entries' in state
        print("✅ get_state_summary() working correctly\n")
        
        # Test 9: Test __repr__()
        print("Test 9: Testing string representation...")
        agent_str = str(agent)
        print(f"Agent representation: {agent_str}")
        assert "RestaurantAnalysisAgent" in agent_str
        assert "model=" in agent_str
        print("✅ __repr__() working correctly\n")
        
        # Final summary
        print("=" * 70)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        print("\n✅ D1-007: reasoning_log attribute - COMPLETE")
        print("✅ D1-008: current_plan attribute - COMPLETE")
        print("✅ D1-009: _log_reasoning() method - COMPLETE")
        print("✅ D1-010: Basic agent initialization - COMPLETE")
        print("\nAgent is ready for Day 1 completion!")
        
    except ValueError as e:
        print(f"❌ ValueError: {e}")
        print("\nMake sure your .env file has ANTHROPIC_API_KEY set!")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()