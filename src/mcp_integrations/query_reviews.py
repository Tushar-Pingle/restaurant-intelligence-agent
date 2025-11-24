"""
Query Reviews MCP Server

Provides both:
- MCP tools (for MCP server)
- Direct Python functions (for agent import)

Now with smart keyword-based review filtering for better Q&A!
"""

from fastmcp import FastMCP
from typing import List, Dict, Any
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Restaurant Review Query")

# Store reviews in memory (shared across all calls)
REVIEW_INDEX: Dict[str, List[str]] = {}


# ============ HELPER FUNCTIONS ============

def find_relevant_reviews(reviews: List[str], question: str, max_reviews: int = 20) -> List[str]:
    """
    Find reviews most likely to contain answer to question.
    Uses simple keyword matching to score reviews.
    
    Args:
        reviews: All available reviews
        question: User's question
        max_reviews: Maximum number of reviews to return
    
    Returns:
        List of most relevant reviews
    """
    # Extract keywords from question (remove common stop words)
    keywords = question.lower().split()
    stop_words = {
        'what', 'how', 'why', 'when', 'where', 'who', 'which',
        'do', 'does', 'did', 'is', 'are', 'was', 'were', 'been',
        'about', 'the', 'a', 'an', 'to', 'for', 'of', 'in', 'on', 'at',
        'say', 'tell', 'me', 'customers', 'customer', 'people', 'guests'
    }
    keywords = [k.strip('?,!.;:') for k in keywords if k not in stop_words]
    
    print(f"DEBUG find_relevant_reviews: Extracted keywords: {keywords}")
    
    # Score each review based on keyword matches
    scored_reviews = []
    for review in reviews:
        review_lower = review.lower()
        # Count how many keywords appear in this review
        score = sum(1 for keyword in keywords if keyword in review_lower)
        
        # Bonus points for exact phrase match
        if len(keywords) > 1:
            phrase = ' '.join(keywords)
            if phrase in review_lower:
                score += 3
        
        if score > 0:
            scored_reviews.append((score, review))
    
    # Sort by score (highest first)
    scored_reviews.sort(reverse=True, key=lambda x: x[0])
    
    print(f"DEBUG find_relevant_reviews: Found {len(scored_reviews)} relevant reviews")
    
    # Return top matches (or all reviews if no matches)
    if scored_reviews:
        return [review for score, review in scored_reviews[:max_reviews]]
    else:
        print(f"DEBUG find_relevant_reviews: No keyword matches, using first {max_reviews} reviews")
        return reviews[:max_reviews]


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
    # Normalize restaurant name (lowercase, strip whitespace)
    restaurant_key = restaurant_name.strip().lower()
    
    REVIEW_INDEX[restaurant_key] = reviews
    
    print(f"✅ Indexed {len(reviews)} reviews for '{restaurant_key}'")
    print(f"   Total restaurants in index: {len(REVIEW_INDEX)}")
    
    return f"Indexed {len(reviews)} reviews for {restaurant_name}"


def query_reviews_direct(
    restaurant_name: str,
    question: str,
    max_reviews: int = 50  # Increased from 10 to 50
) -> str:
    """
    Direct function: Ask a question about reviews using RAG with keyword filtering.
    
    Args:
        restaurant_name: Name of the restaurant
        question: Question to answer
        max_reviews: Max number of reviews to use (default 50)
    
    Returns:
        Answer based on reviews
    """
    # Normalize restaurant name
    restaurant_key = restaurant_name.strip().lower()
    
    print(f"\n{'='*60}")
    print(f"🔍 Q&A Query")
    print(f"{'='*60}")
    print(f"Restaurant: '{restaurant_name}' (key: '{restaurant_key}')")
    print(f"Question: '{question}'")
    
    # Try to get reviews
    reviews = REVIEW_INDEX.get(restaurant_key, [])
    
    print(f"Reviews in index: {len(reviews)}")
    
    if not reviews:
        # Try case-insensitive search
        for key in REVIEW_INDEX.keys():
            if key.lower() == restaurant_key:
                reviews = REVIEW_INDEX[key]
                print(f"Found match with case-insensitive search: '{key}'")
                break
    
    if not reviews:
        available = list(REVIEW_INDEX.keys())
        return f"❌ No reviews indexed for '{restaurant_name}'.\n\nAvailable restaurants: {available if available else 'None'}\n\nPlease analyze a restaurant first."
    
    # Use keyword filtering to find most relevant reviews
    print(f"Finding relevant reviews from {len(reviews)} total reviews...")
    review_sample = find_relevant_reviews(reviews, question, max_reviews)
    
    print(f"Selected {len(review_sample)} relevant reviews for analysis")
    
    # Format reviews for Claude
    reviews_text = "\n\n".join([f"Review {i+1}: {r}" for i, r in enumerate(review_sample)])
    
    # Build prompt
    prompt = f"""You are answering questions about {restaurant_name} based on customer reviews.

CUSTOMER REVIEWS (filtered for relevance to the question):
{reviews_text}

QUESTION: {question}

INSTRUCTIONS:
1. If the reviews above mention the topic, provide a detailed, evidence-based answer with specific quotes
2. If the reviews DON'T specifically mention the topic, clearly state: "The reviews provided don't specifically mention [topic]"
3. Always cite review numbers when referencing information (e.g., "Review 3 mentions...")
4. Be conversational but precise
5. Keep your answer focused and concise (3-5 sentences)

Answer:"""
    
    try:
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        print(f"Calling Claude API...")
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        
        answer = response.content[0].text
        
        print(f"✅ Answer generated ({len(answer)} characters)")
        print(f"{'='*60}\n")
        
        return answer
        
    except Exception as e:
        error_msg = f"❌ Error answering question: {str(e)}"
        print(error_msg)
        return error_msg


def get_indexed_restaurants_direct() -> List[str]:
    """
    Direct function: Get list of indexed restaurants.
    
    Returns:
        List of restaurant names
    """
    return list(REVIEW_INDEX.keys())


def clear_index_direct() -> str:
    """
    Direct function: Clear the review index.
    
    Returns:
        Confirmation message
    """
    count = len(REVIEW_INDEX)
    REVIEW_INDEX.clear()
    print(f"🗑️  Cleared review index ({count} restaurants removed)")
    return f"Cleared index ({count} restaurants removed)"


# ============ MCP TOOLS (for MCP server) ============

@mcp.tool()
def index_reviews(restaurant_name: str, reviews: List[str]) -> str:
    """MCP Tool: Index reviews for Q&A."""
    return index_reviews_direct(restaurant_name, reviews)


@mcp.tool()
def query_reviews(restaurant_name: str, question: str, max_reviews: int = 50) -> str:
    """MCP Tool: Ask questions about reviews with smart keyword filtering."""
    return query_reviews_direct(restaurant_name, question, max_reviews)


@mcp.tool()
def get_indexed_restaurants() -> List[str]:
    """MCP Tool: Get indexed restaurants."""
    return get_indexed_restaurants_direct()


@mcp.tool()
def clear_index() -> str:
    """MCP Tool: Clear review index."""
    return clear_index_direct()


# Run the MCP server
if __name__ == "__main__":
    mcp.run()