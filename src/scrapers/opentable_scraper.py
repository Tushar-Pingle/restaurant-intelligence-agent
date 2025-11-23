"""
OpenTable Review Scraper - 2025 Production Version
Fixed review text extraction based on actual DOM structure.
"""

import time
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
            # NEW: Based on actual DOM structure from screenshot
            ".//span[@data-test='wrapper-tag']",
            ".//div[@data-test='wrapper-tag']",
            ".//p[@data-test='review-text']",
            ".//div[contains(@class,'review')]/p",
            ".//div[contains(@class,'review')]/span",
            # Fallback: Get any paragraph/span with substantial text, excluding ratings/dates
            ".//p[not(contains(., 'Dined')) and not(.//*) and string-length(normalize-space())>20]",
            ".//span[not(contains(., 'Dined')) and not(.//*) and string-length(normalize-space())>20]"
        ]
    }
    
    def __init__(self, headless: bool = True, page_load_strategy: str = 'eager'):
        self.headless = headless
        self.page_load_strategy = page_load_strategy
        self.driver = None
        self.wait = None
    
    def scrape_reviews(
        self,
        url: str,
        max_reviews: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Scrape reviews from OpenTable restaurant page."""
        
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
                        with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        self._log_progress("💾 Saved page source to debug_page_source.html", progress_callback)
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
                        
                        names.append(name)
                        dates.append(date)
                        overall_ratings.append(overall_rating)
                        food_ratings.append(food_rating)
                        service_ratings.append(service_rating)
                        ambience_ratings.append(ambience_rating)
                        reviews.append(review_text)
                        
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
            
            return {
                'success': True,
                'total_reviews': review_count,
                'total_pages': page_count,
                'reviews': {
                    'names': names,
                    'dates': dates,
                    'overall_ratings': overall_ratings,
                    'food_ratings': food_ratings,
                    'service_ratings': service_ratings,
                    'ambience_ratings': ambience_ratings,
                    'review_texts': reviews
                }
            }
            
        except Exception as e:
            self._log_progress(f"❌ Fatal error: {str(e)}", progress_callback)
            return {'success': False, 'error': str(e), 'reviews': []}
        
        finally:
            self._cleanup()
    
    def _click_next(self) -> bool:
        """Click 'Next' button with robust error handling."""
        xpaths = self.SELECTORS["next_button"]
        
        for xp in xpaths:
            try:
                # Wait until present & visible
                btn = self.wait.until(EC.presence_of_element_located((By.XPATH, xp)))
                
                # If we matched the inner <div data-test="pagination-next">, climb to <a>
                if btn.tag_name.lower() != "a":
                    try:
                        btn = btn.find_element(By.XPATH, "ancestor::a[1]")
                    except Exception:
                        pass
                
                # Guard: disabled?
                aria_disabled = (btn.get_attribute("aria-disabled") or "").lower()
                if aria_disabled in ("true", "1"):
                    return False
                
                # Bring into view
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(0.15)
                except Exception:
                    pass
                
                # Try native click first
                try:
                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, xp)))
                    btn.click()
                except Exception:
                    # JS fallback (needed in headless mode)
                    self.driver.execute_script("arguments[0].click();", btn)
                
                return True
                
            except TimeoutException:
                continue
            except StaleElementReferenceException:
                # Re-find once
                try:
                    btn = self.driver.find_element(By.XPATH, xp)
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    self.driver.execute_script("arguments[0].click();", btn)
                    return True
                except Exception:
                    continue
            except Exception:
                continue
        
        return False
    
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
    
    def _find_element_with_fallback(self, selectors: List[str], by: By):
        """Try multiple selectors until one works."""
        for selector in selectors:
            try:
                element = self.driver.find_element(by, selector)
                if element:
                    return element
            except:
                continue
        return None
    
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
    
    def _init_driver(self):
        """Initialize Chrome WebDriver with production settings."""
        chrome_options = Options()
        chrome_options.page_load_strategy = self.page_load_strategy
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
        
        # Realistic user agent to avoid bot detection
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        
        # Additional anti-detection measures
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service('/usr/local/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
        
        # Initialize WebDriverWait
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
        """Log progress with emoji indicators."""
        print(message)
        if callback:
            callback(message)
    
    def __del__(self):
        self._cleanup()


def scrape_opentable(url: str, max_reviews: Optional[int] = None, headless: bool = True) -> Dict[str, Any]:
    """
    Scrape reviews from OpenTable.
    
    Args:
        url: OpenTable restaurant URL
        max_reviews: Maximum number of reviews to scrape (None = all)
        headless: Run browser in headless mode
    
    Returns:
        Dict with 'success', 'total_reviews', 'total_pages', and 'reviews' data
    """
    scraper = OpenTableScraper(headless=headless)
    return scraper.scrape_reviews(url, max_reviews=max_reviews)


if __name__ == "__main__":
    print("=" * 80)
    print("🍽️  OpenTable Review Scraper - Production Test (2025)")
    print("=" * 80 + "\n")
    
    test_url = "https://www.opentable.ca/r/miku-restaurant-vancouver"
    
    print(f"🎯 Target: {test_url}")
    print("📊 Limit: 20 reviews (test mode)")
    print("🤖 Mode: HEADLESS\n")
    
    result = scrape_opentable(test_url, max_reviews=20, headless=True)
    
    print("\n" + "=" * 80)
    if result['success']:
        print("✅ SUCCESS!")
        print(f"   📊 Total reviews scraped: {result['total_reviews']}")
        print(f"   📄 Total pages visited: {result['total_pages']}")
        
        if result['total_reviews'] > 0:
            print(f"\n   🔍 Sample (first review):")
            print(f"   👤 Name: {result['reviews']['names'][0]}")
            print(f"   📅 Date: {result['reviews']['dates'][0]}")
            print(f"   ⭐ Overall: {result['reviews']['overall_ratings'][0]}")
            print(f"   🍜 Food: {result['reviews']['food_ratings'][0]}")
            print(f"   💁 Service: {result['reviews']['service_ratings'][0]}")
            print(f"   🏮 Ambience: {result['reviews']['ambience_ratings'][0]}")
            print(f"   💬 Review: {result['reviews']['review_texts'][0][:150]}...")
    else:
        print("❌ FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    print("=" * 80)
