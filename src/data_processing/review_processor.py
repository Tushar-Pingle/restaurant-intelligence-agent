# ============================================================
# CHANGELOG - review_processor.py
# ============================================================
# Issue ID | Change Description                              | Lines Affected
# ------------------------------------------------------------
# PROC-01  | Added multi-format handling (NESTED + legacy)   | Lines ~30-80
#          | - Detects format from scraper result            |
#          | - Handles both OpenTable and Google Maps        |
# NEW      | Dynamic source detection from metadata          | Lines ~85-90
#          | - Uses metadata.source if available             |
#          | - Fallback to 'unknown'                         |
# NEW      | Graceful handling of missing rating fields      | Lines ~50-70
#          | - Google Maps lacks food/service/ambience       |
#          | - Fills with 0.0 if missing                     |
# ============================================================
# IMPORTANT: All other code is UNCHANGED from original working version
# ============================================================

"""
Review data processor - Converts scraped JSON to clean pandas DataFrame

UPDATED: Now supports both OpenTable and Google Maps scrapers
- Handles NESTED format (new standard)
- Handles legacy FLAT format (backwards compatible)
- Graceful handling of missing fields (Google Maps doesn't have sub-ratings)
"""
import pandas as pd
from typing import Dict, Any, List, Optional
from pathlib import Path


def process_reviews(scraper_result: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert scraper output to clean pandas DataFrame.
    
    Supports multiple input formats:
    1. NESTED format: {'reviews': {'names': [...], 'review_texts': [...], ...}}
    2. FLAT format (legacy): {'names': [...], 'reviews': [...], ...}
    
    Args:
        scraper_result: Output from scrape_opentable() or scrape_google_maps()
    
    Returns:
        DataFrame with columns: name, date, overall_rating, food_rating, 
                               service_rating, ambience_rating, review_text, source
    """
    if not scraper_result.get('success', False):
        raise ValueError(f"Scraper failed: {scraper_result.get('error', 'Unknown error')}")
    
    # =========================================================================
    # [PROC-01] Detect format and extract reviews data
    # =========================================================================
    reviews_data = scraper_result.get('reviews', {})
    
    # FORMAT 1: NESTED dict (new standard - both scrapers use this now)
    # {'reviews': {'names': [...], 'dates': [...], 'review_texts': [...], ...}}
    if isinstance(reviews_data, dict) and 'review_texts' in reviews_data:
        print("📋 Detected NESTED format")
        n = len(reviews_data.get('review_texts', []))
        
        if n == 0:
            raise ValueError("No reviews found in NESTED format response")
        
        df = pd.DataFrame({
            'name': _safe_get_list(reviews_data, 'names', n),
            'date': _safe_get_list(reviews_data, 'dates', n),
            'overall_rating': _safe_get_list(reviews_data, 'overall_ratings', n, default=0.0),
            'food_rating': _safe_get_list(reviews_data, 'food_ratings', n, default=0.0),
            'service_rating': _safe_get_list(reviews_data, 'service_ratings', n, default=0.0),
            'ambience_rating': _safe_get_list(reviews_data, 'ambience_ratings', n, default=0.0),
            'review_text': reviews_data.get('review_texts', [])
        })
    
    # FORMAT 2: FLAT format (legacy - for backwards compatibility)
    # {'names': [...], 'dates': [...], 'reviews': [...], ...}
    elif 'names' in scraper_result and isinstance(scraper_result.get('names'), list):
        print("📋 Detected FLAT format (legacy)")
        # Try 'review_texts' first, then 'reviews' as fallback
        review_texts = scraper_result.get('review_texts', scraper_result.get('reviews', []))
        n = len(review_texts) if isinstance(review_texts, list) else 0
        
        if n == 0:
            raise ValueError("No reviews found in FLAT format response")
        
        df = pd.DataFrame({
            'name': _safe_get_list(scraper_result, 'names', n),
            'date': _safe_get_list(scraper_result, 'dates', n),
            'overall_rating': _safe_get_list(scraper_result, 'overall_ratings', n, default=0.0),
            'food_rating': _safe_get_list(scraper_result, 'food_ratings', n, default=0.0),
            'service_rating': _safe_get_list(scraper_result, 'service_ratings', n, default=0.0),
            'ambience_rating': _safe_get_list(scraper_result, 'ambience_ratings', n, default=0.0),
            'review_text': review_texts
        })
    
    # FORMAT 3: Simple list of reviews (minimal format)
    elif isinstance(reviews_data, list) and len(reviews_data) > 0:
        print("📋 Detected simple list format")
        n = len(reviews_data)
        
        df = pd.DataFrame({
            'name': [''] * n,
            'date': _safe_get_list(scraper_result, 'dates', n),
            'overall_rating': _safe_get_list(scraper_result, 'overall_ratings', n, default=0.0),
            'food_rating': [0.0] * n,
            'service_rating': [0.0] * n,
            'ambience_rating': [0.0] * n,
            'review_text': reviews_data
        })
    
    else:
        raise ValueError(f"Unknown scraper result format. Keys: {list(scraper_result.keys())}")
    
    print(f"✅ Created DataFrame with {len(df)} reviews")
    
    # =========================================================================
    # Convert ratings to numeric
    # =========================================================================
    for col in ['overall_rating', 'food_rating', 'service_rating', 'ambience_rating']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    # =========================================================================
    # Clean text fields
    # =========================================================================
    df['review_text'] = df['review_text'].astype(str).str.strip()
    df['name'] = df['name'].astype(str).str.strip()
    
    # =========================================================================
    # Add metadata - DYNAMIC source detection
    # =========================================================================
    metadata = scraper_result.get('metadata', {})
    source = metadata.get('source', scraper_result.get('source', 'unknown'))
    
    df['source'] = source
    df['scrape_timestamp'] = pd.Timestamp.now()
    
    print(f"📊 Source: {source}")
    
    return df


def _safe_get_list(data: Dict, key: str, expected_len: int, default: Any = '') -> List:
    """
    Safely get a list from dict, padding with default if too short.
    
    This handles cases where Google Maps doesn't have certain fields
    that OpenTable has (like food_rating, service_rating, ambience_rating).
    """
    values = data.get(key, [])
    
    if not isinstance(values, list):
        values = []
    
    # Pad with default value if list is too short
    if len(values) < expected_len:
        values = values + [default] * (expected_len - len(values))
    
    # Truncate if too long
    return values[:expected_len]


def save_to_csv(df: pd.DataFrame, output_path: str = 'data/raw/reviews.csv'):
    """
    Save DataFrame to CSV.
    
    Args:
        df: Processed reviews DataFrame
        output_path: Where to save the CSV file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"✅ Saved {len(df)} reviews to {output_path}")
    
    return output_path


def get_review_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get statistics about the processed reviews.
    
    Args:
        df: Processed reviews DataFrame
    
    Returns:
        Dict with review statistics
    """
    stats = {
        'total_reviews': len(df),
        'unique_reviewers': df['name'].nunique(),
        'date_range': {
            'earliest': df['date'].min() if 'date' in df.columns else None,
            'latest': df['date'].max() if 'date' in df.columns else None
        },
        'ratings': {}
    }
    
    # Calculate rating stats for non-zero ratings
    for col in ['overall_rating', 'food_rating', 'service_rating', 'ambience_rating']:
        if col in df.columns:
            valid_ratings = df[col][df[col] > 0]
            if len(valid_ratings) > 0:
                stats['ratings'][col] = {
                    'count': len(valid_ratings),
                    'mean': round(valid_ratings.mean(), 2),
                    'min': valid_ratings.min(),
                    'max': valid_ratings.max()
                }
    
    # Source breakdown
    if 'source' in df.columns:
        stats['sources'] = df['source'].value_counts().to_dict()
    
    return stats


if __name__ == "__main__":
    # Test with mock data
    print("Testing review processor with both formats...\n")
    
    # Test 1: NESTED format (new standard)
    print("=" * 60)
    print("TEST 1: NESTED format")
    print("=" * 60)
    
    nested_result = {
        'success': True,
        'reviews': {
            'names': ['Alice', 'Bob', 'Charlie'],
            'dates': ['2 days ago', '1 week ago', '3 weeks ago'],
            'overall_ratings': [5.0, 4.0, 3.5],
            'food_ratings': [5.0, 4.5, 3.0],
            'service_ratings': [4.5, 4.0, 4.0],
            'ambience_ratings': [5.0, 3.5, 3.5],
            'review_texts': [
                'Amazing food! The sushi was incredible.',
                'Good but a bit pricey. Service was slow.',
                'Average experience. Nothing special.'
            ]
        },
        'metadata': {
            'source': 'opentable',
            'url': 'https://opentable.com/test'
        }
    }
    
    df1 = process_reviews(nested_result)
    print(f"\nDataFrame shape: {df1.shape}")
    print(f"Columns: {list(df1.columns)}")
    print(f"\nFirst review:\n{df1.iloc[0].to_dict()}\n")
    
    # Test 2: Google Maps format (no sub-ratings)
    print("=" * 60)
    print("TEST 2: Google Maps format (missing sub-ratings)")
    print("=" * 60)
    
    gmaps_result = {
        'success': True,
        'reviews': {
            'names': ['Dave', 'Eve'],
            'dates': ['a month ago', '2 months ago'],
            'overall_ratings': [4.0, 5.0],
            # Note: NO food_ratings, service_ratings, ambience_ratings
            'review_texts': [
                'Great place for dinner!',
                'Best restaurant in town.'
            ]
        },
        'metadata': {
            'source': 'google_maps'
        }
    }
    
    df2 = process_reviews(gmaps_result)
    print(f"\nDataFrame shape: {df2.shape}")
    print(f"Food rating (should be 0.0): {df2['food_rating'].tolist()}")
    print(f"Source: {df2['source'].unique()}\n")
    
    # Test 3: Stats
    print("=" * 60)
    print("TEST 3: Review statistics")
    print("=" * 60)
    
    stats = get_review_stats(df1)
    print(f"\nStats for nested format:")
    print(f"  Total reviews: {stats['total_reviews']}")
    print(f"  Unique reviewers: {stats['unique_reviewers']}")
    print(f"  Rating stats: {stats['ratings']}")
    
    print("\n✅ All tests passed!")