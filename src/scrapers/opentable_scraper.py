"""
OpenTable Scraper - FIXED VERSION
Production-ready scraper that doesn't lose reviews.

FIXES:
1. Only counts reviews that have actual text
2. Better selector specificity
3. Logs empty vs real reviews for debugging
4. Continues even if individual reviews fail

Author: Tushar Pingle
Updated: Nov 2024
"""

import time
from typing import Dict, Any, List, Optional, Callable
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


class OpenTableScraper:
    """
    Production OpenTable scraper with improved review extraction.
    """
    
    # Updated selectors - more specific for actual review cards
    SELECTORS = {
        "review_cards": [
            # Most specific first - only match list items that contain actual review content
            "//li[@data-test='reviews-list-item']",
            # Fallback: items in reviews section that have both date AND substantial text
            "//section[@id='reviews']//li[contains(., 'Dined') and .//span[string-length(normalize-space()) > 30]]",
            # Generic fallback
            "//section[.//h2[contains(., 'people are saying') or contains(., 'Reviews')]]//li[.//p[string-length(normalize-space()) > 30] or .//span[string-length(normalize-space()) > 30]]",
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
            # Priority order - most specific first
            ".//span[@data-test='wrapper-tag']",
            ".//div[@data-test='wrapper-tag']",
            ".//p[@data-test='review-text']",
            # Get text content from review body
            ".//div[contains(@class,'review')]//p[string-length(normalize-space()) > 20]",
            ".//div[contains(@class,'review')]//span[string-length(normalize-space()) > 20]",
            # Fallback: any paragraph/span with substantial text that's not date/rating
            ".//p[not(contains(., 'Dined')) and not(contains(., 'Overall')) and not(contains(., 'Food')) and not(contains(., 'Service')) and not(contains(., 'Ambience')) and string-length(normalize-space()) > 20]",
            ".//span[not(contains(., 'Dined')) and not(ancestor::li[contains(., 'Overall')]) and string-length(normalize-space()) > 20]",
        ]
    }
    
    def __init__(self, headless: bool = True, page_load_strategy: str = 'eager'):
        self.headless = headless
        self.page_load_strategy = page_load_strategy
        self.driver = None
        self.wait = None
        self.empty_count = 0  # Track empty reviews for debugging
    
    def scrape_reviews(
        self,
        url: str,
        max_reviews: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Scrape reviews from OpenTable restaurant page.
        
        FIXED: Only counts and returns reviews that have actual text content.
        """
        if not self._validate_url(url):
            return {'success': False, 'error': 'Invalid OpenTable URL', 'reviews': []}
        
        try:
            self._init_driver()
        except Exception as e:
            return {'success': False, 'error': f'Browser init failed: {str(e)}', 'reviews': []}
        
        try:
            self._log_progress("🚀 Starting scraper...", progress_callback)
            self.driver.get(url)
            
            # Wait for page to fully load
            time.sleep(5)
            
            # Initialize data containers
            names = []
            dates = []
            overall_ratings = []
            food_ratings = []
            service_ratings = []
            ambience_ratings = []
            reviews = []
            
            page_count = 0
            review_count = 0  # Only counts VALID reviews with text
            self.empty_count = 0  # Track skipped empty reviews
            
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
                            with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                                f.write(self.driver.page_source)
                            self._log_progress("💾 Saved page source to debug_page_source.html", progress_callback)
                        except:
                            pass
                    break
                
                self._log_progress(f"📋 Found {len(review_elements)} review cards on page", progress_callback)
                
                # Extract data from each review
                page_valid = 0
                page_empty = 0
                
                for idx, review in enumerate(review_elements):
                    if max_reviews and review_count >= max_reviews:
                        self._log_progress(f"🎯 Reached max reviews ({max_reviews}).", progress_callback)
                        break
                    
                    try:
                        # Extract review text FIRST - this is the critical field
                        review_text = self._extract_review_text(review)
                        
                        # FIXED: Skip reviews without actual text content
                        if not review_text or len(review_text.strip()) < 10:
                            page_empty += 1
                            self.empty_count += 1
                            continue  # Don't append, don't count
                        
                        # Now extract other fields
                        name = self._extract_text_with_fallback(review, self.SELECTORS["name"])
                        date = self._extract_text_with_fallback(review, self.SELECTORS["date"])
                        overall_rating = self._extract_text_with_fallback(review, self.SELECTORS["overall_rating"])
                        food_rating = self._extract_text_with_fallback(review, self.SELECTORS["food_rating"])
                        service_rating = self._extract_text_with_fallback(review, self.SELECTORS["service_rating"])
                        ambience_rating = self._extract_text_with_fallback(review, self.SELECTORS["ambience_rating"])
                        
                        # Append valid review
                        names.append(name)
                        dates.append(date)
                        overall_ratings.append(overall_rating)
                        food_ratings.append(food_rating)
                        service_ratings.append(service_rating)
                        ambience_ratings.append(ambience_rating)
                        reviews.append(review_text)
                        
                        review_count += 1
                        page_valid += 1
                        
                        if review_count % 50 == 0:
                            self._log_progress(f"📊 Extracted {review_count} valid reviews so far...", progress_callback)
                        
                    except Exception as e:
                        self._log_progress(f"⚠️  Error on review {idx + 1}: {str(e)}", progress_callback)
                        continue
                
                # Log page summary
                self._log_progress(f"   ✅ Page {page_count}: {page_valid} valid, {page_empty} empty", progress_callback)
                
                if max_reviews and review_count >= max_reviews:
                    break
                
                # Try to click "Next" button
                if not self._click_next():
                    self._log_progress("📍 No more pages. Scraping complete!", progress_callback)
                    break
                
                time.sleep(3)  # Wait for new page to load
            
            self._log_progress(f"✅ DONE! Scraped {review_count} valid reviews from {page_count} pages", progress_callback)
            if self.empty_count > 0:
                self._log_progress(f"   ℹ️  Skipped {self.empty_count} empty/invalid review cards", progress_callback)
            
            # Extract restaurant metadata
            metadata = self._extract_metadata()
            
            return {
                'success': True,
                'total_reviews': review_count,  # Now correctly represents VALID reviews
                'names': names,
                'dates': dates,
                'overall_ratings': overall_ratings,
                'food_ratings': food_ratings,
                'service_ratings': service_ratings,
                'ambience_ratings': ambience_ratings,
                'reviews': reviews,
                'metadata': metadata,
                'stats': {
                    'pages_scraped': page_count,
                    'valid_reviews': review_count,
                    'empty_skipped': self.empty_count
                }
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Scraping error: {str(e)}\n{traceback.format_exc()}"
            self._log_progress(f"❌ {error_msg}", progress_callback)
            return {'success': False, 'error': error_msg, 'reviews': []}
        finally:
            self._cleanup()
    
    def _extract_review_text(self, review_element) -> str:
        """
        Extract review text with multiple fallback strategies.
        Returns empty string if no valid text found.
        """
        # Try each selector
        for selector in self.SELECTORS["review_text"]:
            try:
                elements = review_element.find_elements(By.XPATH, selector)
                for elem in elements:
                    text = elem.text.strip()
                    # Validate it's actual review content
                    if text and len(text) > 20:
                        # Filter out dates and ratings that might have leaked
                        if "Dined on" in text or text.startswith("Overall") or text.startswith("Food"):
                            continue
                        # Filter out very short generic text
                        if text in ["See more", "Read more", "Show more"]:
                            continue
                        return text
            except:
                continue
        
        # Last resort: try to get all text from the review card and extract the main content
        try:
            full_text = review_element.text
            # Split by newlines and find the longest substantial text
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            # Filter out dates, ratings, names
            content_lines = []
            for line in lines:
                if len(line) > 30:  # Substantial text
                    if not any(skip in line for skip in ['Dined on', 'Overall', 'Food', 'Service', 'Ambience', 'VIP']):
                        content_lines.append(line)
            
            if content_lines:
                # Return the longest line as the review
                return max(content_lines, key=len)
        except:
            pass
        
        return ""
    
    def _extract_text_with_fallback(self, parent_element, selectors: List[str]) -> str:
        """Extract text using fallback XPath selectors."""
        for selector in selectors:
            try:
                element = parent_element.find_element(By.XPATH, selector)
                text = element.text.strip()
                if text:
                    return text
            except:
                continue
        return ""
    
    def _find_elements_with_fallback(self, selectors: List[str], by: By) -> List:
        """Try multiple selectors until one works."""
        for selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements:
                    return elements
            except:
                continue
        return []
    
    def _click_next(self) -> bool:
        """Click the next page button."""
        for xp in self.SELECTORS["next_button"]:
            try:
                btn = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, xp))
                )
                
                # Check if disabled
                aria_disabled = (btn.get_attribute("aria-disabled") or "").lower()
                if aria_disabled in ("true", "1"):
                    return False
                
                # Scroll into view
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(0.15)
                except:
                    pass
                
                # Try clicking
                try:
                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, xp)))
                    btn.click()
                except:
                    self.driver.execute_script("arguments[0].click();", btn)
                
                return True
                
            except TimeoutException:
                continue
            except StaleElementReferenceException:
                try:
                    btn = self.driver.find_element(By.XPATH, xp)
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    self.driver.execute_script("arguments[0].click();", btn)
                    return True
                except:
                    continue
            except:
                continue
        
        return False
    
    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract restaurant metadata from page."""
        metadata = {}
        try:
            # Restaurant name
            name_selectors = [
                "//h1",
                "//h1[@data-test='restaurant-name']",
                "//div[contains(@class,'restaurant-name')]//h1"
            ]
            for sel in name_selectors:
                try:
                    elem = self.driver.find_element(By.XPATH, sel)
                    if elem.text.strip():
                        metadata['restaurant_name'] = elem.text.strip()
                        break
                except:
                    continue
            
            # Cuisine type
            cuisine_selectors = [
                "//span[contains(@class,'cuisine')]",
                "//p[contains(@class,'cuisine')]",
                "//div[contains(@class,'cuisine')]"
            ]
            for sel in cuisine_selectors:
                try:
                    elem = self.driver.find_element(By.XPATH, sel)
                    if elem.text.strip():
                        metadata['cuisine'] = elem.text.strip()
                        break
                except:
                    continue
                    
        except:
            pass
        
        return metadata
    
    def _init_driver(self):
        """Initialize Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.page_load_strategy = self.page_load_strategy
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
        
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service('/usr/local/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
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
    
    def __del__(self):
        self._cleanup()


def scrape_opentable(url: str, max_reviews: Optional[int] = None, headless: bool = True) -> Dict[str, Any]:
    """
    Convenience function to scrape OpenTable reviews.
    
    FIXED: Only returns reviews with actual text content.
    """
    scraper = OpenTableScraper(headless=headless)
    return scraper.scrape_reviews(url, max_reviews)


if __name__ == "__main__":
    # Test the scraper
    test_url = "https://www.opentable.ca/r/dockside-restaurant-vancouver-vancouver"
    result = scrape_opentable(test_url, max_reviews=50)
    
    print(f"\n{'='*60}")
    print(f"Results:")
    print(f"  Success: {result.get('success')}")
    print(f"  Total valid reviews: {result.get('total_reviews')}")
    if result.get('stats'):
        print(f"  Empty skipped: {result['stats'].get('empty_skipped', 0)}")
    print(f"{'='*60}")