"""
Review Text Cleaner
Sanitizes review text before sending to AI to prevent JSON parsing errors.
"""

import re
import unicodedata
from typing import List


class ReviewCleaner:
    """
    Cleans review text to prevent JSON parsing errors and reduce tokens.
    """
    
    def __init__(self):
        pass
    
    def clean_review(self, text: str) -> str:
        """
        Clean a single review text.
        
        Args:
            text: Raw review text
            
        Returns:
            Cleaned text safe for AI processing
        """
        if not text or not isinstance(text, str):
            return ""
        
        # 1. Remove excessive whitespace
        text = ' '.join(text.split())
        
        # 2. Remove emojis and special unicode
        text = self._remove_emojis(text)
        
        # 3. Fix quotes - replace smart quotes with straight quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace("'", "'").replace("'", "'")
        
        # 4. Remove or escape problematic characters
        text = text.replace('\n', ' ')  # Remove newlines
        text = text.replace('\r', ' ')  # Remove carriage returns
        text = text.replace('\t', ' ')  # Remove tabs
        
        # 5. Remove control characters
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
        
        # 6. Normalize multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # 7. Truncate very long reviews (>1000 chars)
        if len(text) > 1000:
            text = text[:997] + "..."
        
        # 8. Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _remove_emojis(self, text: str) -> str:
        """Remove emojis and other pictographic characters."""
        # Emoji pattern
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', text)
    
    def clean_reviews(self, reviews: List[str]) -> List[str]:
        """
        Clean a list of reviews.
        
        Args:
            reviews: List of raw review texts
            
        Returns:
            List of cleaned review texts
        """
        cleaned = []
        for i, review in enumerate(reviews):
            cleaned_text = self.clean_review(review)
            if cleaned_text:  # Only include non-empty reviews
                cleaned.append(cleaned_text)
            else:
                print(f"   ⚠️  Review {i} became empty after cleaning, skipping")
        
        return cleaned
    
    def get_cleaning_stats(self, original: List[str], cleaned: List[str]) -> dict:
        """Get statistics about the cleaning process."""
        original_chars = sum(len(r) for r in original)
        cleaned_chars = sum(len(r) for r in cleaned)
        
        return {
            "original_count": len(original),
            "cleaned_count": len(cleaned),
            "removed_count": len(original) - len(cleaned),
            "original_chars": original_chars,
            "cleaned_chars": cleaned_chars,
            "chars_saved": original_chars - cleaned_chars,
            "reduction_pct": round((1 - cleaned_chars / original_chars) * 100, 1) if original_chars > 0 else 0
        }


def clean_reviews_for_ai(reviews: List[str], verbose: bool = True) -> List[str]:
    """
    Convenience function to clean reviews.
    
    Args:
        reviews: Raw review texts
        verbose: Print cleaning stats
        
    Returns:
        Cleaned review texts
    """
    cleaner = ReviewCleaner()
    cleaned = cleaner.clean_reviews(reviews)
    
    if verbose:
        stats = cleaner.get_cleaning_stats(reviews, cleaned)
        print(f"🧹 Cleaned {stats['original_count']} reviews:")
        print(f"   Removed: {stats['removed_count']} empty reviews")
        print(f"   Characters: {stats['original_chars']:,} → {stats['cleaned_chars']:,}")
        print(f"   Saved: {stats['chars_saved']:,} chars ({stats['reduction_pct']}% reduction)")
    
    return cleaned


if __name__ == "__main__":
    # Test the cleaner
    test_reviews = [
        'This place is "amazing"! 😍😍😍',
        "The food was great\n\nbut service was slow",
        'Chef said "it\'s the best" and I agree! \t\t\t',
        "🍕🍝🍷 Loved everything!!!",
        "A" * 1500  # Very long review
    ]
    
    cleaner = ReviewCleaner()
    for i, review in enumerate(test_reviews):
        cleaned = cleaner.clean_review(review)
        print(f"Original {i+1}: {review[:50]}...")
        print(f"Cleaned {i+1}:  {cleaned[:50]}...")
        print()