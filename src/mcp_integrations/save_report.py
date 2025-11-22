"""
Save Report MCP Server

Provides both:
- MCP tools (for MCP server)
- Direct Python functions (for agent import)
"""

from fastmcp import FastMCP
import json
import os
from datetime import datetime
from typing import Dict, Any

# Initialize FastMCP server
mcp = FastMCP("Restaurant Report Saver")


# ============ DIRECT PYTHON FUNCTIONS (for agent import) ============

def save_json_report_direct(
    restaurant_name: str,
    analysis_data: Dict[str, Any],
    output_dir: str = "reports"
) -> str:
    """
    Direct function: Save analysis report as JSON.
    
    Args:
        restaurant_name: Name of the restaurant
        analysis_data: Complete analysis results
        output_dir: Directory to save report
    
    Returns:
        Path to saved report
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = restaurant_name.lower().replace(" ", "_")
    filename = f"{safe_name}_report_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
    
    return filepath


def list_saved_reports_direct(output_dir: str = "reports") -> list:
    """
    Direct function: List all saved reports.
    
    Args:
        output_dir: Directory containing reports
    
    Returns:
        List of report filenames
    """
    if not os.path.exists(output_dir):
        return []
    
    reports = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    return sorted(reports, reverse=True)


# ============ MCP TOOLS (for MCP server) ============

@mcp.tool()
def save_json_report(
    restaurant_name: str,
    analysis_data: Dict[str, Any],
    output_dir: str = "reports"
) -> str:
    """MCP Tool: Save analysis report as JSON."""
    return save_json_report_direct(restaurant_name, analysis_data, output_dir)


@mcp.tool()
def list_saved_reports(output_dir: str = "reports") -> list:
    """MCP Tool: List all saved reports."""
    return list_saved_reports_direct(output_dir)


# Run the MCP server
if __name__ == "__main__":
    mcp.run()
