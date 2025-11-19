"""
Restaurant Intelligence Agent - Core Module

This module contains the intelligent agent that autonomously analyzes
restaurant reviews from ANY OpenTable restaurant.

Key Features:
- Works with ANY restaurant (no hardcoding)
- Discovers menu items dynamically from reviews
- Discovers relevant aspects dynamically
- Plans analysis strategy autonomously
- Executes with full reasoning transparency

Main Components:
- RestaurantAnalysisAgent: Core agent class (coming in D1-004)
- AgentPlanner: Creates strategic analysis plans (coming later)
- AgentExecutor: Executes planned steps (coming Day 2)
- InsightGenerator: Creates actionable insights (coming Day 2)

Usage Example (once complete):
    from src.agent import RestaurantAnalysisAgent
    
    # Works with ANY restaurant URL
    agent = RestaurantAnalysisAgent()
    results = agent.analyze("https://opentable.ca/r/ANY-RESTAURANT")
    
    # Agent automatically:
    # 1. Scrapes reviews
    # 2. Discovers menu items
    # 3. Discovers aspects
    # 4. Analyzes sentiment
    # 5. Detects problems
    # 6. Generates insights
    # 7. Saves & alerts via MCP
"""

# Version info
__version__ = "0.1.0"
__author__ = "Tushar Pingle"  # Change this to your name!

# When we import components later, they'll be listed here
# For now, this is empty 

# This list will grow as we build:
# __all__ = ['RestaurantAnalysisAgent', 'AgentPlanner', 'AgentExecutor']
__all__ = []  # Empty for now, we'll add to it as we build

print("🤖 Restaurant Intelligence Agent module loaded")