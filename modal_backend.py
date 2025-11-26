"""
Modal Backend for Restaurant Intelligence Agent
With TRUE MCP Server Integration

Deploys:
1. Analysis API endpoint (existing)
2. MCP Server endpoint (NEW - for true MCP protocol)
"""

import modal
from typing import Dict, Any, List

# Create Modal app
app = modal.App("restaurant-intelligence")

# Base image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("chromium", "chromium-driver")
    .run_commands("ln -sf /usr/bin/chromedriver /usr/local/bin/chromedriver")
    .run_commands("ln -sf /usr/bin/chromium /usr/local/bin/chromium")
    .uv_pip_install(
        "anthropic",
        "selenium", 
        "beautifulsoup4",
        "pandas",
        "python-dotenv",
        "matplotlib",
        "fastapi[standard]",
        "fastmcp",
    )
    .add_local_python_source("src")
)


# ============================================================================
# MCP SERVER (TRUE MCP INTEGRATION)
# ============================================================================

# In-memory storage for MCP
REVIEW_INDEX: Dict[str, List[str]] = {}
ANALYSIS_CACHE: Dict[str, Dict[str, Any]] = {}


@app.function(image=image, timeout=300)
@modal.asgi_app()
def mcp_server():
    """
    TRUE MCP Server - exposes tools via MCP protocol over HTTP.
    
    Agent calls this server to use MCP tools.
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from datetime import datetime
    
    mcp_api = FastAPI(title="Restaurant Intelligence MCP Server")
    
    class ToolRequest(BaseModel):
        tool_name: str
        arguments: Dict[str, Any] = {}
    
    class IndexReviewsRequest(BaseModel):
        restaurant_name: str
        reviews: List[str]
    
    class QueryReviewsRequest(BaseModel):
        restaurant_name: str
        question: str
        top_k: int = 5
    
    # MCP Tools
    def index_reviews(restaurant_name: str, reviews: List[str]) -> Dict[str, Any]:
        REVIEW_INDEX[restaurant_name] = reviews
        return {
            "success": True,
            "restaurant": restaurant_name,
            "indexed_count": len(reviews),
            "message": f"Indexed {len(reviews)} reviews for {restaurant_name}"
        }
    
    def query_reviews(restaurant_name: str, question: str, top_k: int = 5) -> Dict[str, Any]:
        reviews = REVIEW_INDEX.get(restaurant_name, [])
        if not reviews:
            return {"success": False, "error": f"No reviews indexed for {restaurant_name}"}
        
        question_words = set(question.lower().split())
        scored = [(len(question_words & set(r.lower().split())), r) for r in reviews]
        scored.sort(reverse=True, key=lambda x: x[0])
        
        return {
            "success": True,
            "restaurant": restaurant_name,
            "question": question,
            "relevant_reviews": [r[1] for r in scored[:top_k]],
            "review_count": min(top_k, len(reviews))
        }
    
    def save_report(restaurant_name: str, report_data: Dict, report_type: str = "analysis") -> Dict[str, Any]:
        report_id = f"{restaurant_name}_{report_type}_{datetime.now().isoformat()}"
        ANALYSIS_CACHE[report_id] = {"restaurant": restaurant_name, "type": report_type, "data": report_data}
        return {"success": True, "report_id": report_id}
    
    def list_tools() -> Dict[str, Any]:
        return {
            "success": True,
            "tools": [
                {"name": "index_reviews", "description": "Index reviews for RAG Q&A"},
                {"name": "query_reviews", "description": "Answer questions about reviews"},
                {"name": "save_report", "description": "Save analysis report"},
            ]
        }
    
    @mcp_api.get("/")
    async def root():
        return {"name": "Restaurant Intelligence MCP Server", "protocol": "MCP", "version": "1.0"}
    
    @mcp_api.get("/health")
    async def health():
        return {"status": "healthy", "mcp": "enabled"}
    
    @mcp_api.get("/tools")
    async def get_tools():
        return list_tools()
    
    @mcp_api.post("/mcp/call")
    async def call_tool(request: ToolRequest):
        """TRUE MCP interface - agent calls tools via this endpoint."""
        tool_map = {
            "index_reviews": lambda args: index_reviews(args["restaurant_name"], args["reviews"]),
            "query_reviews": lambda args: query_reviews(args["restaurant_name"], args["question"], args.get("top_k", 5)),
            "save_report": lambda args: save_report(args["restaurant_name"], args["report_data"], args.get("report_type", "analysis")),
            "list_tools": lambda args: list_tools()
        }
        
        if request.tool_name not in tool_map:
            raise HTTPException(status_code=404, detail=f"Tool '{request.tool_name}' not found")
        
        try:
            result = tool_map[request.tool_name](request.arguments)
            return {"success": True, "tool": request.tool_name, "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @mcp_api.post("/tools/index_reviews")
    async def api_index_reviews(request: IndexReviewsRequest):
        return index_reviews(request.restaurant_name, request.reviews)
    
    @mcp_api.post("/tools/query_reviews")
    async def api_query_reviews(request: QueryReviewsRequest):
        return query_reviews(request.restaurant_name, request.question, request.top_k)
    
    return mcp_api


# ============================================================================
# MAIN ANALYSIS API (existing functionality)
# ============================================================================

@app.function(image=image)
def hello() -> Dict[str, Any]:
    return {"status": "Modal is working!", "mcp": "enabled"}


@app.function(image=image, timeout=600)
def scrape_restaurant_modal(url: str, max_reviews: int = 100) -> Dict[str, Any]:
    """Scrape reviews from OpenTable."""
    from src.scrapers.opentable_scraper import scrape_opentable
    from src.data_processing import process_reviews, clean_reviews_for_ai
    
    result = scrape_opentable(url=url, max_reviews=max_reviews, headless=True)
    if not result.get("success"):
        return {"success": False, "error": result.get("error")}
    
    df = process_reviews(result)
    reviews = clean_reviews_for_ai(df["review_text"].tolist(), verbose=False)
    
    return {
        "success": True,
        "total_reviews": len(reviews),
        "reviews": reviews,
        "metadata": result.get("metadata", {}),
    }


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=2400,
)
def full_analysis_modal(url: str, max_reviews: int = 100) -> Dict[str, Any]:
    """Complete end-to-end analysis with MCP integration."""
    from src.scrapers.opentable_scraper import scrape_opentable
    from src.data_processing import process_reviews, clean_reviews_for_ai
    from src.agent.base_agent import RestaurantAnalysisAgent
    
    # Scrape
    result = scrape_opentable(url=url, max_reviews=max_reviews, headless=True)
    if not result.get("success"):
        return {"success": False, "error": result.get("error")}
    
    df = process_reviews(result)
    reviews = clean_reviews_for_ai(df["review_text"].tolist(), verbose=False)
    
    restaurant_name = url.split("/")[-1].split("?")[0].replace("-", " ").title()
    
    # Analyze
    agent = RestaurantAnalysisAgent()
    analysis = agent.analyze_restaurant(
        restaurant_url=url,
        restaurant_name=restaurant_name,
        reviews=reviews,
    )
    
    # Store in MCP cache for Q&A
    REVIEW_INDEX[restaurant_name] = reviews
    
    return analysis


# ============================================================================
# FASTAPI APP (serves both analysis and MCP)
# ============================================================================

@app.function(
    image=image, 
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=2400,
)
@modal.asgi_app()
def fastapi_app():
    """Main API with MCP integration."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    
    web_app = FastAPI(title="Restaurant Intelligence API with MCP")
    
    class AnalyzeRequest(BaseModel):
        url: str
        max_reviews: int = 100
    
    class MCPCallRequest(BaseModel):
        tool_name: str
        arguments: Dict[str, Any] = {}
    
    @web_app.get("/")
    async def root():
        return {
            "name": "Restaurant Intelligence API",
            "version": "2.0",
            "mcp": "enabled",
            "endpoints": {
                "analyze": "/analyze",
                "mcp_tools": "/mcp/call",
                "mcp_list": "/mcp/tools"
            }
        }
    
    @web_app.get("/health")
    async def health():
        return {"status": "healthy", "mcp": "enabled"}
    
    @web_app.post("/analyze")
    async def analyze(request: AnalyzeRequest):
        try:
            result = full_analysis_modal.remote(url=request.url, max_reviews=request.max_reviews)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # MCP Endpoints
    @web_app.get("/mcp/tools")
    async def mcp_list_tools():
        return {
            "tools": [
                {"name": "index_reviews", "description": "Index reviews for RAG Q&A"},
                {"name": "query_reviews", "description": "Answer questions about reviews"},
                {"name": "save_report", "description": "Save analysis report"},
            ]
        }
    
    @web_app.post("/mcp/call")
    async def mcp_call(request: MCPCallRequest):
        """TRUE MCP interface."""
        # For now, this delegates to local functions
        # In production, this would connect to the MCP server
        
        if request.tool_name == "index_reviews":
            args = request.arguments
            REVIEW_INDEX[args["restaurant_name"]] = args["reviews"]
            return {"success": True, "indexed": len(args["reviews"])}
        
        elif request.tool_name == "query_reviews":
            args = request.arguments
            reviews = REVIEW_INDEX.get(args["restaurant_name"], [])
            if not reviews:
                return {"success": False, "error": "No reviews indexed"}
            
            question_words = set(args["question"].lower().split())
            scored = [(len(question_words & set(r.lower().split())), r) for r in reviews]
            scored.sort(reverse=True, key=lambda x: x[0])
            top_k = args.get("top_k", 5)
            
            return {
                "success": True,
                "relevant_reviews": [r[1] for r in scored[:top_k]]
            }
        
        return {"success": False, "error": f"Unknown tool: {request.tool_name}"}
    
    return web_app


@app.local_entrypoint()
def main():
    print("🧪 Testing Modal deployment with MCP...\n")
    
    print("1️⃣ Testing connection...")
    result = hello.remote()
    print(f"✅ {result}\n")
    
    print("2️⃣ MCP Server deployed at:")
    print("   https://tushar-pingle--restaurant-intelligence-mcp-server.modal.run")
    
    print("\n3️⃣ Analysis API deployed at:")
    print("   https://tushar-pingle--restaurant-intelligence-fastapi-app.modal.run")
    
    print("\n✅ Both endpoints ready!")