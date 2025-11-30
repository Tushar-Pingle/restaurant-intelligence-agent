# ============================================================
# CHANGELOG - opentable_scraper.py
# ============================================================
# Issue ID | Change Description                          | Lines Affected
# ------------------------------------------------------------
# INIT-01  | Added chromedriver_path param + auto-detect | __init__ (line ~95), _find_chromedriver() (lines ~100-120), _init_driver() (line ~140)
# INIT-03  | Enhanced error message on browser init fail | scrape_reviews() (line ~165)
# NAV-01   | WebDriverWait instead of fixed 5s sleep     | scrape_reviews() (lines ~175-185)
# FMT-01   | Changed return format from FLAT to NESTED   | scrape_reviews() return (lines ~280-300)
# ============================================================
# IMPORTANT: All other code is UNCHANGED from original working version
# ============================================================

"""
OpenTable Review Scraper - ORIGINAL WORKING VERSION
This is the scraper that WAS working. Only change: returns data in correct format.

DO NOT ADD:
- Retry logic with delays (breaks things)
- page_load_strategy = 'normal' (too slow)
- Complex _extract_review_text fallbacks (hangs)
- 20+ Chrome options (unnecessary)
"""

import time
import os
from typing import List, Dict, Any, Optional, Callable
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


class OpenTableScraper:
    """Scrapes restaurant reviews from OpenTable using production-tested selectors."""
    
    # Production selectors discovered from live DOM inspection (Jan 2025)
    SELECTORS = {
        "review_cards": [
            "//li[@data-test='reviews-list-item']",
            "//section[@id='reviews']//li[contains(., 'Dined')]",
            "//section[.//h2[contains(., 'people are saying') or contains(., 'Reviews')]]//li[.//p or .//span or .//time]",
            "//li[@data-test='review']"
        ],
        "next_button": [
            "//a[@aria-label='Go to the next page']",
            "//*[@data-test='pagination-next']/ancestor::a[1]",
            "//div[@data-test='pagination-next']/ancestor::a[1]",
            "//a[@rel='next' or contains(@href,'page=')][not(@aria-disabled='true')]"
        ],
        "name": [
            ".//p[@data-test='reviewer-name']",
            ".//header//p[1]",
            ".//header//span[1]",
            ".//p[1]"
        ],
        "date": [
            ".//p[contains(., 'Dined')]",
            ".//time",
            ".//p[contains(@class,'date')]",
            ".//div[contains(@class,'date')]"
        ],
        "overall_rating": [
            ".//li[.//*[contains(., 'Overall')]]//span[normalize-space()]",
            ".//li[contains(., 'Overall')]//span",
            ".//span[contains(@data-test,'overall')]"
        ],
        "food_rating": [
            ".//li[.//*[contains(., 'Food')]]//span[normalize-space()]",
            ".//li[contains(., 'Food')]//span"
        ],
        "service_rating": [
            ".//li[.//*[contains(., 'Service')]]//span[normalize-space()]",
            ".//li[contains(., 'Service')]//span"
        ],
        "ambience_rating": [
            ".//li[.//*[contains(., 'Ambience')]]//span[normalize-space()]",
            ".//li[contains(., 'Ambience')]//span"
        ],
        "review_text": [
            ".//span[@data-test='wrapper-tag']",
            ".//div[@data-test='wrapper-tag']",
            ".//p[@data-test='review-text']",
            ".//div[contains(@class,'review')]/p",
            ".//div[contains(@class,'review')]/span",
            ".//p[not(contains(., 'Dined')) and not(.//*) and string-length(normalize-space())>20]",
            ".//span[not(contains(., 'Dined')) and not(.//*) and string-length(normalize-space())>20]"
        ],
        # [INIT-01] Added selector for page load verification (used in NAV-01)
        "page_loaded": [
            "//section[@id='reviews']",
            "//section[contains(@class, 'review')]",
            "//li[@data-test='reviews-list-item']",
            "//h2[contains(., 'people are saying') or contains(., 'Reviews')]"
        ]
    }
    
    # [INIT-01] Added chromedriver_path parameter
    def __init__(self, headless: bool = True, page_load_strategy: str = 'eager', chromedriver_path: Optional[str] = None):
        self.headless = headless
        self.page_load_strategy = page_load_strategy  # KEEP 'eager' - it works!
        self.driver = None
        self.wait = None
        # [INIT-01] Use provided path or auto-detect
        self.chromedriver_path = chromedriver_path or self._find_chromedriver()
    
    # [INIT-01] NEW METHOD - Auto-detect chromedriver location
    def _find_chromedriver(self) -> str:
        """Find chromedriver in common locations."""
        common_paths = [
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver',
            '/opt/chromedriver',
            'chromedriver',  # Current directory or PATH
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Try webdriver_manager as fallback
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            return ChromeDriverManager().install()
        except ImportError:
            pass
        except Exception:
            pass
        
        # Default fallback (Modal uses this path)
        return '/usr/local/bin/chromedriver'
    
    def _init_driver(self):
        """Initialize Chrome WebDriver with production settings."""
        chrome_options = Options()
        chrome_options.page_load_strategy = self.page_load_strategy  # 'eager' is fast!
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
        
        # Realistic user agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        
        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # [INIT-01] Use configurable chromedriver path
        service = Service(self.chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)  # 30s is enough
        
        self.wait = WebDriverWait(self.driver, 10)
    
    def _cleanup(self):
        """Close browser."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _validate_url(self, url: str) -> bool:
        """Validate OpenTable URL."""
        return 'opentable.c' in url.lower()
    
    def _log_progress(self, message: str, callback: Optional[Callable]):
        """Log progress."""
        print(message)
        if callback:
            callback(message)
    
    def _find_elements_with_fallback(self, selectors: List[str], by: By = By.XPATH) -> List:
        """Try multiple selectors until one returns elements."""
        for selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements:
                    return elements
            except:
                continue
        return []
    
    def _extract_text_with_fallback(self, parent_element, selectors: List[str]) -> str:
        """Try multiple selectors to extract text."""
        for selector in selectors:
            try:
                element = parent_element.find_element(By.XPATH, selector)
                text = element.text.strip()
                if text:
                    return text
            except:
                continue
        return ""
    
    def _click_next(self) -> bool:
        """Click 'Next' button with robust error handling."""
        for selector in self.SELECTORS["next_button"]:
            try:
                next_btn = self.driver.find_element(By.XPATH, selector)
                if next_btn and next_btn.is_displayed() and next_btn.is_enabled():
                    next_btn.click()
                    return True
            except (NoSuchElementException, StaleElementReferenceException):
                continue
            except Exception:
                continue
        return False
    
    # [NAV-01] NEW METHOD - Wait for page to load with specific element
    def _wait_for_page_load(self, timeout: int = 10) -> bool:
        """
        Wait for page to load by checking for review section elements.
        Returns True if page loaded, False if timeout.
        """
        for selector in self.SELECTORS["page_loaded"]:
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                return True
            except TimeoutException:
                continue
        return False
    
    def scrape_reviews(
        self,
        url: str,
        max_reviews: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Scrape reviews from OpenTable restaurant page."""
        if not self._validate_url(url):
            return {'success': False, 'error': 'Invalid OpenTable URL', 'reviews': {}}
        
        # [INIT-03] Enhanced error handling with user-friendly message
        try:
            self._init_driver()
        except FileNotFoundError as e:
            return {
                'success': False, 
                'error': f'Chromedriver not found at {self.chromedriver_path}. Please install Chrome/Chromedriver or set the correct path.',
                'reviews': {}
            }
        except Exception as e:
            error_msg = str(e).lower()
            if 'chromedriver' in error_msg or 'chrome' in error_msg:
                return {
                    'success': False,
                    'error': f'Browser initialization failed. Please ensure Chrome and Chromedriver are installed and compatible. Details: {str(e)[:200]}',
                    'reviews': {}
                }
            return {'success': False, 'error': f'Browser init failed: {str(e)}', 'reviews': {}}
        
        try:
            self._log_progress("🚀 Starting scraper...", progress_callback)
            self.driver.get(url)
            
            # [NAV-01] Use WebDriverWait instead of fixed 5s sleep
            self._log_progress("⏳ Waiting for page to load...", progress_callback)
            if not self._wait_for_page_load(timeout=10):
                # Fallback to short sleep if element not found (page might still work)
                self._log_progress("⚠️ Page load check timed out, continuing with fallback...", progress_callback)
                time.sleep(3)
            else:
                self._log_progress("✅ Page loaded successfully", progress_callback)
            
            # Initialize data containers
            names = []
            dates = []
            overall_ratings = []
            food_ratings = []
            service_ratings = []
            ambience_ratings = []
            review_texts = []  # [FMT-01] Renamed from 'reviews' to 'review_texts' for consistency
            
            page_count = 0
            review_count = 0
            
            while True:
                page_count += 1
                self._log_progress(f"📄 Scraping page {page_count}...", progress_callback)
                
                # Find review cards
                review_elements = self._find_elements_with_fallback(
                    self.SELECTORS["review_cards"],
                    By.XPATH
                )
                
                if not review_elements:
                    self._log_progress("⚠️  No reviews found on page.", progress_callback)
                    if page_count == 1:
                        # Save page source for debugging
                        try:
                            with open('/tmp/debug_page_source.html', 'w', encoding='utf-8') as f:
                                f.write(self.driver.page_source)
                            self._log_progress("💾 Saved page source for debugging", progress_callback)
                        except:
                            pass
                    break
                
                self._log_progress(f"✅ Found {len(review_elements)} review cards", progress_callback)
                
                # Extract data from each review
                for idx, review in enumerate(review_elements):
                    if max_reviews and review_count >= max_reviews:
                        self._log_progress(f"🎯 Reached max reviews ({max_reviews}).", progress_callback)
                        break
                    
                    try:
                        name = self._extract_text_with_fallback(review, self.SELECTORS["name"])
                        date = self._extract_text_with_fallback(review, self.SELECTORS["date"])
                        overall_rating = self._extract_text_with_fallback(review, self.SELECTORS["overall_rating"])
                        food_rating = self._extract_text_with_fallback(review, self.SELECTORS["food_rating"])
                        service_rating = self._extract_text_with_fallback(review, self.SELECTORS["service_rating"])
                        ambience_rating = self._extract_text_with_fallback(review, self.SELECTORS["ambience_rating"])
                        review_text = self._extract_text_with_fallback(review, self.SELECTORS["review_text"])
                        
                        # Clean review text (remove date if it leaked in)
                        if review_text and "Dined on" in review_text:
                            review_text = ""
                        
                        # Only count reviews with actual text
                        if review_text and len(review_text.strip()) > 10:
                            names.append(name)
                            dates.append(date)
                            overall_ratings.append(overall_rating)
                            food_ratings.append(food_rating)
                            service_ratings.append(service_rating)
                            ambience_ratings.append(ambience_rating)
                            review_texts.append(review_text)  # [FMT-01] Using review_texts
                            
                            review_count += 1
                            
                            if review_count % 10 == 0:
                                self._log_progress(f"📊 Extracted {review_count} reviews so far...", progress_callback)
                        
                    except Exception as e:
                        self._log_progress(f"⚠️  Error on review {idx + 1}: {str(e)}", progress_callback)
                        continue
                
                if max_reviews and review_count >= max_reviews:
                    break
                
                # Try to click "Next" button
                if not self._click_next():
                    self._log_progress("📍 No more pages. Scraping complete!", progress_callback)
                    break
                
                time.sleep(3)  # Wait for new page to load
            
            self._log_progress(f"✅ DONE! Scraped {review_count} reviews from {page_count} pages", progress_callback)
            
            # [FMT-01] Return data in NESTED format (matching Google Maps structure)
            return {
                'success': True,
                'total_reviews': review_count,
                'total_pages': page_count,
                'reviews': {  # NESTED structure - same as Google Maps
                    'names': names,
                    'dates': dates,
                    'overall_ratings': overall_ratings,
                    'food_ratings': food_ratings,
                    'service_ratings': service_ratings,
                    'ambience_ratings': ambience_ratings,
                    'review_texts': review_texts  # Using 'review_texts' key like Google Maps
                },
                'metadata': {
                    'source': 'opentable',
                    'url': url,
                    'pages_scraped': page_count
                }
            }
            
        except Exception as e:
            self._log_progress(f"❌ Fatal error: {str(e)}", progress_callback)
            return {'success': False, 'error': str(e), 'reviews': {}}
        
        finally:
            self._cleanup()
    
    def __del__(self):
        self._cleanup()


# [INIT-01] Updated function signature to accept chromedriver_path
def scrape_opentable(
    url: str, 
    max_reviews: Optional[int] = None, 
    headless: bool = True,
    chromedriver_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scrape reviews from OpenTable.
    
    Args:
        url: OpenTable restaurant URL
        max_reviews: Maximum number of reviews to scrape (None = all available)
        headless: Run browser in headless mode
        chromedriver_path: Optional path to chromedriver (auto-detects if not provided)
    
    Returns:
        Dict with 'success', 'total_reviews', and 'reviews' data in NESTED format
    """
    scraper = OpenTableScraper(headless=headless, chromedriver_path=chromedriver_path)
    return scraper.scrape_reviews(url, max_reviews=max_reviews)


if __name__ == "__main__":
    test_url = "https://www.opentable.ca/r/dockside-restaurant-vancouver"
    result = scrape_opentable(test_url, max_reviews=30)
    
    print(f"\n{'='*60}")
    print(f"Success: {result.get('success')}")
    print(f"Reviews: {result.get('total_reviews', 0)}")
    if result.get('error'):
        print(f"Error: {result.get('error')}")
    
    # [FMT-01] Show nested structure
    if result.get('success') and result.get('reviews'):
        reviews_data = result['reviews']
        print(f"Reviews data keys: {list(reviews_data.keys())}")
        print(f"Sample review text: {reviews_data['review_texts'][0][:100] if reviews_data.get('review_texts') else 'N/A'}...")
    print(f"{'='*60}")