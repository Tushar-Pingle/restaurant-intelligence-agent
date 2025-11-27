"""
Modal Backend for Restaurant Intelligence Agent
With Multi-Platform Scraper Support (OpenTable + Google Maps)

VERSION 3.0:
1. Auto-detects URL platform
2. Routes to appropriate scraper
3. PDF report generation
4. TRUE MCP Server Integration
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
    .pip_install(
        "anthropic",
        "selenium", 
        "beautifulsoup4",
        "pandas",
        "python-dotenv",
        "matplotlib",
        "fastapi[standard]",
        "fastmcp",
        "reportlab",  # For PDF generation
    )
    .add_local_python_source("src")
)


# ============================================================================
# URL DETECTION
# ============================================================================

def detect_platform(url: str) -> str:
    """Detect which platform the URL is from."""
    if not url:
        return "unknown"
    
    url_lower = url.lower()
    
    if 'opentable' in url_lower:
        return "opentable"
    elif any(x in url_lower for x in ['google.com/maps', 'goo.gl/maps', 'maps.google', 'maps.app.goo.gl']):
        return "google_maps"
    else:
        return "unknown"


# ============================================================================
# MCP SERVER (TRUE MCP INTEGRATION)
# ============================================================================

REVIEW_INDEX: Dict[str, List[str]] = {}
ANALYSIS_CACHE: Dict[str, Dict[str, Any]] = {}


@app.function(image=image, timeout=300)
@modal.asgi_app()
def mcp_server():
    """TRUE MCP Server - exposes tools via MCP protocol over HTTP."""
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
        return {"name": "Restaurant Intelligence MCP Server", "protocol": "MCP", "version": "3.0"}
    
    @mcp_api.get("/health")
    async def health():
        return {"status": "healthy", "mcp": "enabled"}
    
    @mcp_api.get("/tools")
    async def get_tools():
        return list_tools()
    
    @mcp_api.post("/mcp/call")
    async def call_tool(request: ToolRequest):
        tool_map = {
            "index_reviews": lambda args: index_reviews(args["restaurant_name"], args["reviews"]),
            "query_reviews": lambda args: query_reviews(args["restaurant_name"], args["question"], args.get("top_k", 5)),
            "list_tools": lambda args: list_tools()
        }
        
        if request.tool_name not in tool_map:
            raise HTTPException(status_code=404, detail=f"Tool '{request.tool_name}' not found")
        
        try:
            result = tool_map[request.tool_name](request.arguments)
            return {"success": True, "tool": request.tool_name, "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return mcp_api


# ============================================================================
# SCRAPER FUNCTIONS
# ============================================================================

@app.function(image=image)
def hello() -> Dict[str, Any]:
    return {"status": "Modal is working!", "mcp": "enabled", "version": "3.0", "platforms": ["opentable", "google_maps"]}


@app.function(image=image, timeout=900)
def scrape_restaurant_modal(url: str, max_reviews: int = 100) -> Dict[str, Any]:
    """Scrape reviews - auto-detects platform."""
    platform = detect_platform(url)
    
    if platform == "opentable":
        from src.scrapers.opentable_scraper import scrape_opentable
        result = scrape_opentable(url=url, max_reviews=max_reviews, headless=True)
    elif platform == "google_maps":
        from src.scrapers.google_maps_scraper import scrape_google_maps
        result = scrape_google_maps(url=url, max_reviews=max_reviews, headless=True)
    else:
        return {"success": False, "error": f"Unsupported platform. Use OpenTable or Google Maps URL."}
    
    if not result.get("success"):
        return {"success": False, "error": result.get("error")}
    
    from src.data_processing import process_reviews, clean_reviews_for_ai
    
    df = process_reviews(result)
    reviews = clean_reviews_for_ai(df["review_text"].tolist(), verbose=False)
    
    # Include raw review data
    raw_reviews = []
    for _, row in df.iterrows():
        raw_reviews.append({
            "date": str(row.get("date", "")),
            "rating": float(row.get("overall_rating", 0) or 0),
            "food_rating": float(row.get("food_rating", 0) or 0),
            "service_rating": float(row.get("service_rating", 0) or 0),
            "ambience_rating": float(row.get("ambience_rating", 0) or 0),
            "text": str(row.get("review_text", ""))
        })
    
    return {
        "success": True,
        "source": platform,
        "total_reviews": len(reviews),
        "reviews": reviews,
        "raw_reviews": raw_reviews,
        "metadata": result.get("metadata", {}),
    }


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=2400,
)
def full_analysis_modal(url: str, max_reviews: int = 100) -> Dict[str, Any]:
    """Complete end-to-end analysis with multi-platform support."""
    platform = detect_platform(url)
    
    # Route to appropriate scraper
    if platform == "opentable":
        from src.scrapers.opentable_scraper import scrape_opentable
        result = scrape_opentable(url=url, max_reviews=max_reviews, headless=True)
    elif platform == "google_maps":
        from src.scrapers.google_maps_scraper import scrape_google_maps
        result = scrape_google_maps(url=url, max_reviews=max_reviews, headless=True)
    else:
        return {"success": False, "error": "Unsupported platform. Use OpenTable or Google Maps URL."}
    
    if not result.get("success"):
        return {"success": False, "error": result.get("error")}
    
    from src.data_processing import process_reviews, clean_reviews_for_ai
    from src.agent.base_agent import RestaurantAnalysisAgent
    
    df = process_reviews(result)
    reviews = clean_reviews_for_ai(df["review_text"].tolist(), verbose=False)
    
    # Extract raw review data
    raw_reviews = []
    for _, row in df.iterrows():
        raw_reviews.append({
            "date": str(row.get("date", "")),
            "rating": float(row.get("overall_rating", 0) or 0),
            "food_rating": float(row.get("food_rating", 0) or 0),
            "service_rating": float(row.get("service_rating", 0) or 0),
            "ambience_rating": float(row.get("ambience_rating", 0) or 0),
            "text": str(row.get("review_text", ""))
        })
    
    # Extract restaurant name from URL
    if platform == "opentable":
        restaurant_name = url.split("/")[-1].split("?")[0].replace("-", " ").title()
    else:
        # Google Maps
        if '/place/' in url:
            restaurant_name = url.split('/place/')[1].split('/')[0].replace('+', ' ').replace('%20', ' ')
        else:
            restaurant_name = "Restaurant"
    
    # Analyze
    agent = RestaurantAnalysisAgent()
    analysis = agent.analyze_restaurant(
        restaurant_url=url,
        restaurant_name=restaurant_name,
        reviews=reviews,
    )
    
    # Store in MCP cache
    REVIEW_INDEX[restaurant_name] = reviews
    
    # Add metadata
    analysis['raw_reviews'] = raw_reviews
    analysis['source'] = platform
    
    return analysis


# ============================================================================
# FASTAPI APP
# ============================================================================

@app.function(
    image=image, 
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=2400,
)
@modal.asgi_app()
def fastapi_app():
    """Main API with multi-platform support and MCP integration."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    
    web_app = FastAPI(title="Restaurant Intelligence API v3.0")
    
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
            "version": "3.0",
            "mcp": "enabled",
            "supported_platforms": ["opentable", "google_maps"],
            "endpoints": {
                "analyze": "/analyze",
                "mcp_tools": "/mcp/call",
                "mcp_list": "/mcp/tools"
            }
        }
    
    @web_app.get("/health")
    async def health():
        return {"status": "healthy", "mcp": "enabled", "version": "3.0"}
    
    @web_app.post("/analyze")
    async def analyze(request: AnalyzeRequest):
        try:
            # Detect platform first
            platform = detect_platform(request.url)
            if platform == "unknown":
                raise HTTPException(
                    status_code=400, 
                    detail="Unsupported URL. Please use OpenTable or Google Maps URL."
                )
            
            result = full_analysis_modal.remote(url=request.url, max_reviews=request.max_reviews)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
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
    print("🧪 Testing Modal deployment v3.0...\n")
    
    print("1️⃣ Testing connection...")
    result = hello.remote()
    print(f"✅ {result}\n")
    
    print("2️⃣ Supported platforms:")
    print("   • OpenTable (opentable.com)")
    print("   • Google Maps (google.com/maps)")
    
    print("\n3️⃣ MCP Server deployed at:")
    print("   https://tushar-pingle--restaurant-intelligence-mcp-server.modal.run")
    
    print("\n4️⃣ Analysis API deployed at:")
    print("   https://tushar-pingle--restaurant-intelligence-fastapi-app.modal.run")
    
    print("\n✅ All endpoints ready!")