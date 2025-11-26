"""
Modal Backend for Restaurant Intelligence Agent
Deploys scraper and analysis as serverless functions

FIXED: Increased FastAPI timeout for long-running analysis
"""

import modal
from typing import Dict, Any, List

# Create Modal app
app = modal.App("restaurant-intelligence")

# Base image with chromedriver symlink fix
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("chromium", "chromium-driver")
    .run_commands("ls -la /usr/bin/chrom* || true")
    .run_commands("ls -la /usr/local/bin/chrom* || true")
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


@app.function(image=image)
def hello() -> Dict[str, Any]:
    """Test that Modal is working."""
    return {"status": "Modal is working!", "message": "MCP ready"}


@app.function(
    image=image,
    timeout=600,
)
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
    timeout=1800,
)
def analyze_restaurant_modal(
    url: str,
    restaurant_name: str,
    reviews: List[str],
) -> Dict[str, Any]:
    """Run AI analysis on reviews only."""
    from src.agent.base_agent import RestaurantAnalysisAgent
    
    agent = RestaurantAnalysisAgent()
    analysis = agent.analyze_restaurant(
        restaurant_url=url,
        restaurant_name=restaurant_name,
        reviews=reviews,
    )
    return analysis


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=2400,  # 40 minutes
)
def full_analysis_modal(url: str, max_reviews: int = 100) -> Dict[str, Any]:
    """Complete end-to-end analysis."""
    from src.scrapers.opentable_scraper import scrape_opentable
    from src.data_processing import process_reviews, clean_reviews_for_ai
    from src.agent.base_agent import RestaurantAnalysisAgent
    
    result = scrape_opentable(url=url, max_reviews=max_reviews, headless=True)

    if not result.get("success"):
        return {"success": False, "error": result.get("error")}

    df = process_reviews(result)
    reviews = clean_reviews_for_ai(df["review_text"].tolist(), verbose=False)

    restaurant_name = (
        url.split("/")[-1].split("?")[0].replace("-", " ").title()
    )

    agent = RestaurantAnalysisAgent()
    analysis = agent.analyze_restaurant(
        restaurant_url=url,
        restaurant_name=restaurant_name,
        reviews=reviews,
    )

    return analysis


# FIXED: Added timeout to FastAPI function
@app.function(
    image=image, 
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=2400,  # 40 minutes - matches full_analysis_modal
)
@modal.asgi_app()
def fastapi_app():
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    web_app = FastAPI(title="Restaurant Intelligence API")

    class AnalyzeRequest(BaseModel):
        url: str
        max_reviews: int = 100

    @web_app.get("/")
    async def root():
        return {
            "name": "Restaurant Intelligence API",
            "version": "1.0",
            "mcp": "enabled",
        }

    @web_app.get("/health")
    async def health():
        return {"status": "healthy"}

    @web_app.post("/analyze")
    async def analyze(request: AnalyzeRequest):
        try:
            # Call with spawn to avoid blocking
            result = full_analysis_modal.remote(
                url=request.url,
                max_reviews=request.max_reviews,
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @web_app.post("/scrape")
    async def scrape(request: AnalyzeRequest):
        try:
            result = scrape_restaurant_modal.remote(
                url=request.url,
                max_reviews=request.max_reviews,
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return web_app


@app.local_entrypoint()
def main():
    print("🧪 Testing Modal deployment...\n")

    print("1️⃣ Testing connection...")
    result = hello.remote()
    print(f"✅ {result}\n")

    print("2️⃣ Testing analysis with 20 reviews...")
    test_url = "https://www.opentable.ca/r/miku-restaurant-vancouver"

    analysis = full_analysis_modal.remote(url=test_url, max_reviews=20)

    if analysis.get("success"):
        print("\n✅ Analysis complete!")
        print(f"   Menu items: {len(analysis.get('menu_analysis', {}).get('food_items', []))}")
        print(f"   Aspects: {len(analysis.get('aspect_analysis', {}).get('aspects', []))}")
        print(f"   Chef insights: {'✅' if analysis.get('insights', {}).get('chef') else '❌'}")
        print(f"   Manager insights: {'✅' if analysis.get('insights', {}).get('manager') else '❌'}")
    else:
        print(f"\n❌ Analysis failed: {analysis.get('error')}")