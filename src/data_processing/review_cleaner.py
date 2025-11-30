# ============================================================
# CHANGELOG - review_cleaner.py
# ============================================================
# Issue ID | Change Description                              | Lines Affected
# ------------------------------------------------------------
# PROC-02  | Added duplicate review detection with similarity | Lines ~95-130
#          | - Added _is_duplicate() method with fuzzy match  |
#          | - Added 'removed_duplicates' to stats tracking   |
#          | - Uses simple word overlap similarity (no deps)  |
#          | - Threshold: 85% similarity = duplicate          |
# ============================================================
# IMPORTANT: All other code is UNCHANGED from original working version
# ============================================================

"""
Review Text Cleaner - FIXED VERSION
Less aggressive cleaning that preserves more reviews.

FIXES:
1. Don't discard reviews just because they're short
2. Keep reviews with minimal cleaning
3. Better handling of special characters
4. Log what's being cleaned for debugging
5. [PROC-02] Detect and remove duplicate reviews

Author: Tushar Pingle
Updated: Nov 2024
"""

import re
import unicodedata
from typing import List, Tuple, Set


class ReviewCleaner:
    """
    Cleans review text while preserving as much content as possible.
    Now includes duplicate detection.
    """
    
    # Minimum length for a valid review (characters)
    MIN_REVIEW_LENGTH = 10  # Very permissive
    
    # [PROC-02] Similarity threshold for duplicate detection (0.0 to 1.0)
    DUPLICATE_SIMILARITY_THRESHOLD = 0.85
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stats = {
            'total': 0,
            'kept': 0,
            'removed_empty': 0,
            'removed_short': 0,
            'removed_duplicates': 0,  # [PROC-02] Added
            'chars_original': 0,
            'chars_cleaned': 0
        }
    
    def clean_review(self, text: str) -> str:
        """
        Clean a single review text.
        
        FIXED: Less aggressive cleaning, preserves more content.
        """
        if not text or not isinstance(text, str):
            return ""
        
        original_len = len(text)
        
        # 1. Basic whitespace normalization (gentle)
        text = ' '.join(text.split())
        
        # 2. Remove only truly problematic emojis (keep basic punctuation)
        text = self._remove_emojis(text)
        
        # 3. Normalize quotes (don't remove them)
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace("'", "'").replace("'", "'")
        
        # 4. Remove control characters only (keep newlines as spaces)
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char == ' ')
        
        # 5. Normalize multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # 6. Truncate very long reviews (>1500 chars) - increased limit
        if len(text) > 1500:
            text = text[:1497] + "..."
        
        # 7. Strip whitespace
        text = text.strip()
        
        # Track stats
        self.stats['chars_original'] += original_len
        self.stats['chars_cleaned'] += len(text)
        
        return text
    
    def _remove_emojis(self, text: str) -> str:
        """
        Remove emojis but keep more unicode characters.
        FIXED: Less aggressive pattern.
        """
        # Only remove actual emoji pictographs, not all unicode
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs  
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U0001F900-\U0001F9FF"  # supplemental symbols
            "\U0001FA00-\U0001FA6F"  # chess symbols
            "\U0001FA70-\U0001FAFF"  # symbols extended
            "\U00002702-\U000027B0"  # dingbats
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub('', text)
    
    # =========================================================================
    # [PROC-02] DUPLICATE DETECTION - NEW METHOD
    # =========================================================================
    def _get_word_set(self, text: str) -> Set[str]:
        """
        Extract set of meaningful words from text for comparison.
        Ignores common stop words and very short words.
        """
        # Simple stop words (common words that don't help identify duplicates)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'was', 'are', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'we', 'you', 'they', 'it', 'my', 'our', 'your', 'their', 'its',
            'very', 'really', 'so', 'just', 'also', 'as', 'if', 'when', 'where'
        }
        
        # Extract words (alphanumeric only, lowercase)
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        # Filter out stop words and very short words
        meaningful = {w for w in words if len(w) > 2 and w not in stop_words}
        
        return meaningful
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using Jaccard similarity.
        Returns value from 0.0 (completely different) to 1.0 (identical).
        
        This is a simple, dependency-free implementation.
        """
        words1 = self._get_word_set(text1)
        words2 = self._get_word_set(text2)
        
        # Handle edge cases
        if not words1 and not words2:
            return 1.0  # Both empty = same
        if not words1 or not words2:
            return 0.0  # One empty = different
        
        # Jaccard similarity: intersection / union
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _is_duplicate(self, text: str, existing_reviews: List[str]) -> bool:
        """
        Check if text is a duplicate of any existing review.
        Uses fuzzy matching to catch near-duplicates.
        
        Returns True if text is a duplicate, False otherwise.
        """
        # Quick exact match check first (fast)
        if text in existing_reviews:
            return True
        
        # Fuzzy match for near-duplicates
        for existing in existing_reviews:
            similarity = self._calculate_similarity(text, existing)
            if similarity >= self.DUPLICATE_SIMILARITY_THRESHOLD:
                if self.verbose:
                    print(f"   🔄 Found duplicate ({similarity:.0%} similar)")
                return True
        
        return False
    # =========================================================================
    # END [PROC-02] DUPLICATE DETECTION
    # =========================================================================
    
    def clean_reviews(self, reviews: List[str]) -> List[str]:
        """
        Clean a list of reviews.
        
        FIXED: Only removes truly empty reviews, not short ones.
        [PROC-02] Now also removes duplicate reviews.
        """
        self.stats = {
            'total': len(reviews),
            'kept': 0,
            'removed_empty': 0,
            'removed_short': 0,
            'removed_duplicates': 0,  # [PROC-02] Added
            'chars_original': 0,
            'chars_cleaned': 0
        }
        
        cleaned = []
        for i, review in enumerate(reviews):
            # Clean the review
            cleaned_text = self.clean_review(review)
            
            # Check if it's still valid
            if not cleaned_text:
                self.stats['removed_empty'] += 1
                if self.verbose:
                    print(f"   ⚠️  Review {i} was empty/None, skipping")
                continue
            
            if len(cleaned_text) < self.MIN_REVIEW_LENGTH:
                self.stats['removed_short'] += 1
                if self.verbose:
                    print(f"   ⚠️  Review {i} too short ({len(cleaned_text)} chars): '{cleaned_text[:50]}'")
                continue
            
            # [PROC-02] Check for duplicates
            if self._is_duplicate(cleaned_text, cleaned):
                self.stats['removed_duplicates'] += 1
                if self.verbose:
                    print(f"   🔄 Review {i} is a duplicate, skipping")
                continue
            
            cleaned.append(cleaned_text)
            self.stats['kept'] += 1
        
        return cleaned
    
    def get_cleaning_stats(self) -> dict:
        """Get statistics about the cleaning process."""
        return {
            "original_count": self.stats['total'],
            "cleaned_count": self.stats['kept'],
            "removed_empty": self.stats['removed_empty'],
            "removed_short": self.stats['removed_short'],
            "removed_duplicates": self.stats['removed_duplicates'],  # [PROC-02] Added
            "original_chars": self.stats['chars_original'],
            "cleaned_chars": self.stats['chars_cleaned'],
            "retention_rate": round(self.stats['kept'] / max(self.stats['total'], 1) * 100, 1)
        }


def clean_reviews_for_ai(reviews: List[str], verbose: bool = True) -> List[str]:
    """
    Convenience function to clean reviews.
    
    FIXED: Better stats reporting, less aggressive cleaning.
    [PROC-02] Now includes duplicate detection.
    """
    cleaner = ReviewCleaner(verbose=False)  # Don't spam individual messages
    cleaned = cleaner.clean_reviews(reviews)
    
    if verbose:
        stats = cleaner.get_cleaning_stats()
        print(f"🧹 Cleaned {stats['original_count']} reviews:")
        print(f"   ✅ Kept: {stats['cleaned_count']} ({stats['retention_rate']}%)")
        if stats['removed_empty'] > 0:
            print(f"   ❌ Empty: {stats['removed_empty']}")
        if stats['removed_short'] > 0:
            print(f"   ❌ Too short: {stats['removed_short']}")
        # [PROC-02] Report duplicates
        if stats['removed_duplicates'] > 0:
            print(f"   🔄 Duplicates: {stats['removed_duplicates']}")
        
        # Warn if we're losing too many reviews
        if stats['retention_rate'] < 50:
            print(f"   ⚠️  WARNING: Only {stats['retention_rate']}% retention! Check scraper.")
    
    return cleaned


# Also add a debug function
def analyze_review_loss(reviews: List[str]) -> None:
    """
    Debug function to understand why reviews are being lost.
    """
    print(f"\n{'='*60}")
    print("REVIEW LOSS ANALYSIS")
    print(f"{'='*60}\n")
    
    empty_count = 0
    short_count = 0
    valid_count = 0
    
    print("Sample of problematic reviews:\n")
    
    for i, review in enumerate(reviews):
        if not review or not isinstance(review, str):
            empty_count += 1
            if empty_count <= 3:
                print(f"  [{i}] EMPTY: {repr(review)}")
        elif len(review.strip()) < 10:
            short_count += 1
            if short_count <= 3:
                print(f"  [{i}] SHORT ({len(review)} chars): '{review[:50]}'")
        else:
            valid_count += 1
    
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Total: {len(reviews)}")
    print(f"  Valid: {valid_count} ({valid_count/len(reviews)*100:.1f}%)")
    print(f"  Empty: {empty_count}")
    print(f"  Short: {short_count}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Test the cleaner
    test_reviews = [
        'This place is "amazing"! The food was incredible.',
        "The food was great but service was slow. Would come back!",
        'Chef said "it\'s the best" and I agree! Great experience.',
        "Loved everything! Best Italian in town.",
        "",  # Empty
        "Good",  # Too short
        "   ",  # Just whitespace
        None,  # None
        "The pasta was perfectly cooked, al dente just how I like it.",
        # [PROC-02] Test duplicates
        "The food was great but service was slow. Would come back!",  # Exact duplicate
        "The food was great but the service was slow. Would come back again!",  # Near duplicate
    ]
    
    print("Testing review cleaner with duplicate detection...\n")
    
    # First analyze
    analyze_review_loss(test_reviews)
    
    # Then clean
    cleaned = clean_reviews_for_ai(test_reviews, verbose=True)
    
    print(f"\nCleaned reviews ({len(cleaned)}):")
    for i, review in enumerate(cleaned):
        print(f"  {i+1}. {review[:60]}...")
    
    print("\n✅ Duplicate detection test complete!")