"""
Scraper Router - Auto-detects URL type and routes to appropriate scraper

Supports:
- OpenTable (opentable.com, opentable.ca, etc.)
- Google Maps (google.com/maps, goo.gl/maps)
"""

from typing import Dict, Any, Optional
from enum import Enum


class ScraperType(Enum):
    OPENTABLE = "opentable"
    GOOGLE_MAPS = "google_maps"
    UNKNOWN = "unknown"


def detect_scraper_type(url: str) -> ScraperType:
    """
    Detect which scraper to use based on URL.
    
    Args:
        url: Restaurant review URL
    
    Returns:
        ScraperType enum value
    """
    if not url:
        return ScraperType.UNKNOWN
    
    url_lower = url.lower()
    
    # OpenTable detection
    if 'opentable' in url_lower:
        return ScraperType.OPENTABLE
    
    # Google Maps detection
    if any(x in url_lower for x in ['google.com/maps', 'goo.gl/maps', 'maps.google', 'maps.app.goo.gl']):
        return ScraperType.GOOGLE_MAPS
    
    return ScraperType.UNKNOWN


def scrape_reviews(url: str, max_reviews: Optional[int] = None, headless: bool = True) -> Dict[str, Any]:
    """
    Universal scraper function - auto-detects URL type and uses appropriate scraper.
    
    Args:
        url: Restaurant review URL (OpenTable or Google Maps)
        max_reviews: Maximum number of reviews to scrape
        headless: Run browser in headless mode
    
    Returns:
        Dict with standardized review data:
        {
            'success': bool,
            'source': 'opentable' | 'google_maps',
            'total_reviews': int,
            'reviews': {
                'names': [...],
                'dates': [...],
                'overall_ratings': [...],
                'food_ratings': [...],
                'service_ratings': [...],
                'ambience_ratings': [...],
                'review_texts': [...]
            },
            'metadata': {...}
        }
    """
    scraper_type = detect_scraper_type(url)
    
    if scraper_type == ScraperType.OPENTABLE:
        from src.scrapers.opentable_scraper import scrape_opentable
        result = scrape_opentable(url=url, max_reviews=max_reviews, headless=headless)
        result['source'] = 'opentable'
        return result
    
    elif scraper_type == ScraperType.GOOGLE_MAPS:
        from src.scrapers.google_maps_scraper import scrape_google_maps
        result = scrape_google_maps(url=url, max_reviews=max_reviews, headless=headless)
        result['source'] = 'google_maps'
        return result
    
    else:
        return {
            'success': False,
            'error': f'Unsupported URL type. Please use OpenTable or Google Maps URL.',
            'source': 'unknown',
            'reviews': []
        }


def get_supported_platforms() -> list:
    """Return list of supported review platforms."""
    return [
        {
            'name': 'OpenTable',
            'domains': ['opentable.com', 'opentable.ca', 'opentable.co.uk'],
            'example': 'https://www.opentable.com/r/restaurant-name'
        },
        {
            'name': 'Google Maps',
            'domains': ['google.com/maps', 'goo.gl/maps', 'maps.google.com'],
            'example': 'https://www.google.com/maps/place/Restaurant+Name'
        }
    ]


def validate_url(url: str) -> Dict[str, Any]:
    """
    Validate URL and return info about detected platform.
    
    Args:
        url: URL to validate
    
    Returns:
        Dict with validation result and platform info
    """
    scraper_type = detect_scraper_type(url)
    
    if scraper_type == ScraperType.UNKNOWN:
        return {
            'valid': False,
            'platform': None,
            'message': 'URL not recognized. Please use OpenTable or Google Maps URL.'
        }
    
    return {
        'valid': True,
        'platform': scraper_type.value,
        'message': f'Valid {scraper_type.value.replace("_", " ").title()} URL detected.'
    }


if __name__ == "__main__":
    # Test URL detection
    test_urls = [
        "https://www.opentable.com/r/miku-restaurant-vancouver",
        "https://www.opentable.ca/r/nightingale-vancouver",
        "https://www.google.com/maps/place/Miku+Restaurant/@49.2876,-123.1145",
        "https://goo.gl/maps/abc123",
        "https://maps.app.goo.gl/abc123",
        "https://www.yelp.com/biz/restaurant-name",  # Not supported
    ]
    
    print("🔍 URL Detection Test\n")
    for url in test_urls:
        scraper_type = detect_scraper_type(url)
        print(f"URL: {url[:50]}...")
        print(f"Detected: {scraper_type.value}\n")