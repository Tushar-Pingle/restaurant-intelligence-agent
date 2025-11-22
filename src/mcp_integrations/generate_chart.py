"""
Generate Chart MCP Server

Provides both:
- MCP tools (for MCP server)
- Direct Python functions (for agent import)
"""

from fastmcp import FastMCP
from typing import Dict, Any, List
import os

# Initialize FastMCP server
mcp = FastMCP("Restaurant Chart Generator")


# ============ DIRECT PYTHON FUNCTIONS (for agent import) ============

def generate_sentiment_chart_direct(
    items: List[Dict[str, Any]],
    output_path: str = "outputs/sentiment_chart.png",
    chart_type: str = "bar"
) -> str:
    """
    Direct function: Generate sentiment visualization chart.
    
    Args:
        items: List of items with name and sentiment
        output_path: Where to save the chart
        chart_type: Type of chart
    
    Returns:
        Path to saved chart
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        
        names = [item['name'][:20] for item in items[:10]]
        sentiments = [item['sentiment'] for item in items[:10]]
        
        colors = []
        for s in sentiments:
            if s >= 0.7:
                colors.append('#4CAF50')
            elif s >= 0.3:
                colors.append('#FFC107')
            elif s >= 0:
                colors.append('#FF9800')
            else:
                colors.append('#F44336')
        
        fig, ax = plt.subplots(figsize=(12, 8))
        bars = ax.barh(names, [abs(s) for s in sentiments], color=colors)
        
        ax.set_xlabel('Sentiment Score', fontsize=12)
        ax.set_title('Item Sentiment Analysis', fontsize=14, fontweight='bold')
        
        for i, (bar, sentiment) in enumerate(zip(bars, sentiments)):
            width = bar.get_width()
            ax.text(width + 0.02, bar.get_y() + bar.get_height()/2,
                   f'{sentiment:+.2f}',
                   ha='left', va='center', fontsize=10)
        
        green = mpatches.Patch(color='#4CAF50', label='Positive (≥0.7)')
        yellow = mpatches.Patch(color='#FFC107', label='Mixed (0.3-0.7)')
        orange = mpatches.Patch(color='#FF9800', label='Neutral (0-0.3)')
        red = mpatches.Patch(color='#F44336', label='Negative (<0)')
        ax.legend(handles=[green, yellow, orange, red])
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_path
        
    except Exception as e:
        return f"Error generating chart: {str(e)}"


def generate_comparison_chart_direct(
    data: Dict[str, float],
    output_path: str = "outputs/comparison_chart.png",
    title: str = "Comparison"
) -> str:
    """
    Direct function: Generate comparison chart.
    
    Args:
        data: Dict of {name: value} pairs
        output_path: Where to save
        title: Chart title
    
    Returns:
        Path to saved chart
    """
    try:
        import matplotlib.pyplot as plt
        
        names = list(data.keys())[:10]
        values = [data[n] for n in names]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(names, values, color='#2196F3')
        ax.set_ylabel('Value')
        ax.set_title(title, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_path
        
    except Exception as e:
        return f"Error generating chart: {str(e)}"


# ============ MCP TOOLS (for MCP server) ============

@mcp.tool()
def generate_sentiment_chart(
    items: List[Dict[str, Any]],
    output_path: str = "outputs/sentiment_chart.png",
    chart_type: str = "bar"
) -> str:
    """MCP Tool: Generate sentiment chart."""
    return generate_sentiment_chart_direct(items, output_path, chart_type)


@mcp.tool()
def generate_comparison_chart(
    data: Dict[str, float],
    output_path: str = "outputs/comparison_chart.png",
    title: str = "Comparison"
) -> str:
    """MCP Tool: Generate comparison chart."""
    return generate_comparison_chart_direct(data, output_path, title)


# Run the MCP server
if __name__ == "__main__":
    mcp.run()
