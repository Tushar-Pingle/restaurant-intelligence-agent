"""
Review data processor - Converts scraped JSON to clean pandas DataFrame
"""
import pandas as pd
from typing import Dict, Any
from pathlib import Path


def process_reviews(scraper_result: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert scraper output to clean pandas DataFrame.
    
    Args:
        scraper_result: Output from scrape_opentable()
    
    Returns:
        DataFrame with columns: name, date, overall, food, service, ambience, review
    """
    if not scraper_result.get('success', False):
        raise ValueError(f"Scraper failed: {scraper_result.get('error', 'Unknown error')}")
    
    reviews_data = scraper_result['reviews']
    
    df = pd.DataFrame({
        'name': reviews_data['names'],
        'date': reviews_data['dates'],
        'overall_rating': reviews_data['overall_ratings'],
        'food_rating': reviews_data['food_ratings'],
        'service_rating': reviews_data['service_ratings'],
        'ambience_rating': reviews_data['ambience_ratings'],
        'review_text': reviews_data['review_texts']
    })
    
    # Convert ratings to numeric
    df['overall_rating'] = pd.to_numeric(df['overall_rating'], errors='coerce')
    df['food_rating'] = pd.to_numeric(df['food_rating'], errors='coerce')
    df['service_rating'] = pd.to_numeric(df['service_rating'], errors='coerce')
    df['ambience_rating'] = pd.to_numeric(df['ambience_rating'], errors='coerce')
    
    # Clean text fields
    df['review_text'] = df['review_text'].str.strip()
    df['name'] = df['name'].str.strip()
    
    # Add metadata
    df['source'] = 'OpenTable'
    df['scrape_timestamp'] = pd.Timestamp.now()
    
    return df


def save_to_csv(df: pd.DataFrame, output_path: str = 'data/raw/opentable_reviews.csv'):
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


if __name__ == "__main__":
    # Test with the scraped data
    import json
    
    print("Testing review processor...")
    
    # Load the scraped data
    with open('scraped_reviews.json', 'r') as f:
        result = json.load(f)
    
    # Process it
    df = process_reviews(result)
    
    print(f"\n✅ Processed {len(df)} reviews")
    print(f"\nDataFrame shape: {df.shape}")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nFirst review:")
    print(df.iloc[0].to_dict())
    
    # Save to CSV
    save_to_csv(df)
    
    print("\n✅ Done!")
