"""
Query Reviews MCP Server

Provides both:
- MCP tools (for MCP server)
- Direct Python functions (for agent import)
"""

from fastmcp import FastMCP
from typing import List, Dict, Any
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Restaurant Review Query")

# Store reviews in memory
REVIEW_INDEX: Dict[str, List[str]] = {}


# ============ DIRECT PYTHON FUNCTIONS (for agent import) ============

def index_reviews_direct(restaurant_name: str, reviews: List[str]) -> str:
    """
    Direct function: Index reviews for Q&A.
    
    Args:
        restaurant_name: Name of the restaurant
        reviews: List of review texts to index
    
    Returns:
        Confirmation message
    """
    REVIEW_INDEX[restaurant_name] = reviews
    return f"Indexed {len(reviews)} reviews for {restaurant_name}"


def query_reviews_direct(
    restaurant_name: str,
    question: str,
    max_reviews: int = 10
) -> str:
    """
    Direct function: Ask a question about reviews using RAG.
    
    Args:
        restaurant_name: Name of the restaurant
        question: Question to answer
        max_reviews: Max number of reviews to use
    
    Returns:
        Answer based on reviews
    """
    reviews = REVIEW_INDEX.get(restaurant_name, [])
    
    if not reviews:
        return f"No reviews indexed for {restaurant_name}. Please index reviews first."
    
    review_sample = reviews[:max_reviews]
    reviews_text = "\n\n".join([f"Review {i+1}: {r}" for i, r in enumerate(review_sample)])
    
    prompt = f"""You are answering questions about {restaurant_name} based on customer reviews.

CUSTOMER REVIEWS:
{reviews_text}

QUESTION: {question}

Provide a clear, evidence-based answer using information from the reviews above. Quote specific reviews when relevant.

Answer:"""
    
    try:
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
        
    except Exception as e:
        return f"Error answering question: {str(e)}"


def get_indexed_restaurants_direct() -> List[str]:
    """
    Direct function: Get list of indexed restaurants.
    
    Returns:
        List of restaurant names
    """
    return list(REVIEW_INDEX.keys())


# ============ MCP TOOLS (for MCP server) ============

@mcp.tool()
def index_reviews(restaurant_name: str, reviews: List[str]) -> str:
    """MCP Tool: Index reviews for Q&A."""
    return index_reviews_direct(restaurant_name, reviews)


@mcp.tool()
def query_reviews(restaurant_name: str, question: str, max_reviews: int = 10) -> str:
    """MCP Tool: Ask questions about reviews."""
    return query_reviews_direct(restaurant_name, question, max_reviews)


@mcp.tool()
def get_indexed_restaurants() -> List[str]:
    """MCP Tool: Get indexed restaurants."""
    return get_indexed_restaurants_direct()


# Run the MCP server
if __name__ == "__main__":
    mcp.run()
