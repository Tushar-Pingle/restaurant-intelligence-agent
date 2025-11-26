"""
MCP Client for Restaurant Intelligence Agent

This client connects to the MCP server and calls tools via HTTP.
This is the TRUE MCP integration - agent uses this to call tools.
"""

import requests
from typing import Dict, Any, List, Optional
import os


class MCPClient:
    """
    Client for calling MCP tools on the server.
    
    Usage:
        client = MCPClient("https://your-mcp-server.modal.run")
        result = client.call_tool("query_reviews", {
            "restaurant_name": "Miku",
            "question": "How is the sushi?"
        })
    """
    
    def __init__(self, server_url: Optional[str] = None):
        """
        Initialize MCP client.
        
        Args:
            server_url: URL of the MCP server
        """
        self.server_url = server_url or os.getenv(
            "MCP_SERVER_URL",
            "https://tushar-pingle--restaurant-intelligence-mcp-server.modal.run"
        )
        self.timeout = 60
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call an MCP tool on the server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
        
        Returns:
            Tool result
        """
        arguments = arguments or {}
        
        try:
            response = requests.post(
                f"{self.server_url}/mcp/call",
                json={
                    "tool_name": tool_name,
                    "arguments": arguments
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"MCP call failed: {response.status_code} - {response.text}"
                }
            
            return response.json()
            
        except requests.exceptions.Timeout:
            return {"success": False, "error": "MCP call timed out"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Could not connect to MCP server"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_tools(self) -> List[Dict[str, str]]:
        """Get list of available MCP tools."""
        result = self.call_tool("list_tools")
        if result.get("success"):
            return result.get("result", {}).get("tools", [])
        return []
    
    def health_check(self) -> bool:
        """Check if MCP server is healthy."""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    # ========================================================================
    # Convenience methods for specific tools
    # ========================================================================
    
    def index_reviews(self, restaurant_name: str, reviews: List[str]) -> Dict[str, Any]:
        """Index reviews for RAG Q&A."""
        return self.call_tool("index_reviews", {
            "restaurant_name": restaurant_name,
            "reviews": reviews
        })
    
    def query_reviews(
        self,
        restaurant_name: str,
        question: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Query reviews using RAG."""
        return self.call_tool("query_reviews", {
            "restaurant_name": restaurant_name,
            "question": question,
            "top_k": top_k
        })
    
    def save_report(
        self,
        restaurant_name: str,
        report_data: Dict[str, Any],
        report_type: str = "analysis"
    ) -> Dict[str, Any]:
        """Save analysis report."""
        return self.call_tool("save_report", {
            "restaurant_name": restaurant_name,
            "report_data": report_data,
            "report_type": report_type
        })
    
    def get_report(self, report_id: str) -> Dict[str, Any]:
        """Retrieve saved report."""
        return self.call_tool("get_report", {"report_id": report_id})


# Global client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get or create global MCP client."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


# ============================================================================
# Direct functions that use MCP client (for backward compatibility)
# ============================================================================

def index_reviews_mcp(restaurant_name: str, reviews: List[str]) -> str:
    """Index reviews via MCP."""
    client = get_mcp_client()
    result = client.index_reviews(restaurant_name, reviews)
    if result.get("success"):
        return result.get("result", {}).get("message", "Indexed successfully")
    return f"Error: {result.get('error')}"


def query_reviews_mcp(restaurant_name: str, question: str, top_k: int = 5) -> Dict[str, Any]:
    """Query reviews via MCP."""
    client = get_mcp_client()
    result = client.query_reviews(restaurant_name, question, top_k)
    if result.get("success"):
        return result.get("result", {})
    return {"error": result.get("error")}


def save_report_mcp(
    restaurant_name: str,
    report_data: Dict[str, Any],
    report_type: str = "analysis"
) -> str:
    """Save report via MCP."""
    client = get_mcp_client()
    result = client.save_report(restaurant_name, report_data, report_type)
    if result.get("success"):
        return result.get("result", {}).get("report_id", "saved")
    return f"Error: {result.get('error')}"


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    print("Testing MCP Client...")
    
    client = MCPClient()
    
    # Health check
    print(f"\n1. Health check: {client.health_check()}")
    
    # List tools
    print(f"\n2. Available tools: {client.list_tools()}")
    
    # Test index reviews
    print("\n3. Testing index_reviews...")
    result = client.index_reviews("Test Restaurant", ["Great food!", "Loved the sushi"])
    print(f"   Result: {result}")
    
    # Test query reviews
    print("\n4. Testing query_reviews...")
    result = client.query_reviews("Test Restaurant", "How was the food?")
    print(f"   Result: {result}")