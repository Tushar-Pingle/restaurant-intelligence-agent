"""
OpenTable Review Scraper - ROBUST VERSION with Retry Logic
Designed to handle Modal's container environment reliably.

IMPROVEMENTS:
1. Retry logic with exponential backoff (3 attempts)
2. Longer timeouts for Modal environment
3. Better Chrome options for containerized environments
4. Graceful degradation on partial failures
5. Memory-efficient processing

Author: Tushar Pingle
Updated: Nov 2024
"""

import time
import random
from typing import List, Dict, Any, Optional, Callable
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


class OpenTableScraper:
    """
    Robust OpenTable scraper with retry logic for containerized environments.
    """
    
    # Production selectors
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
            ".//div[contains(@class,'review')]//p[string-length(normalize-space()) > 20]",
            ".//div[contains(@class,'review')]//span[string-length(normalize-space()) > 20]",
            ".//p[not(contains(., 'Dined')) and not(contains(., 'Overall')) and string-length(normalize-space()) > 20]",
            ".//span[not(contains(., 'Dined')) and not(ancestor::li[contains(., 'Overall')]) and string-length(normalize-space()) > 20]",
        ]
    }
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 15, 30]  # Exponential backoff in seconds
    
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
        """
        Scrape reviews with automatic retry on failure.
        """
        if not self._validate_url(url):
            return {'success': False, 'error': 'Invalid OpenTable URL', 'reviews': []}
        
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                self._log_progress(f"🚀 Attempt {attempt + 1}/{self.MAX_RETRIES}...", progress_callback)
                
                result = self._scrape_with_timeout(url, max_reviews, progress_callback)
                
                if result.get('success'):
                    return result
                else:
                    last_error = result.get('error', 'Unknown error')
                    self._log_progress(f"⚠️ Attempt {attempt + 1} failed: {last_error}", progress_callback)
                    
            except Exception as e:
                last_error = str(e)
                self._log_progress(f"⚠️ Attempt {attempt + 1} exception: {last_error}", progress_callback)
            
            finally:
                # Always cleanup between attempts
                self._cleanup()
            
            # Wait before retry (exponential backoff)
            if attempt < self.MAX_RETRIES - 1:
                delay = self.RETRY_DELAYS[attempt] + random.uniform(0, 5)
                self._log_progress(f"⏳ Waiting {delay:.0f}s before retry...", progress_callback)
                time.sleep(delay)
        
        return {
            'success': False, 
            'error': f'Failed after {self.MAX_RETRIES} attempts. Last error: {last_error}',
            'reviews': []
        }
    
    def _scrape_with_timeout(
        self,
        url: str,
        max_reviews: Optional[int],
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """
        Core scraping logic with improved timeout handling.
        """
        # Initialize driver with robust settings
        self._init_driver_robust()
        
        # Data containers
        names = []
        dates = []
        overall_ratings = []
        food_ratings = []
        service_ratings = []
        ambience_ratings = []
        reviews = []
        
        try:
            self._log_progress("🌐 Loading page...", progress_callback)
            
            # Load page with explicit wait
            self.driver.get(url)
            
            # Wait for page to be interactive
            time.sleep(8)  # Longer initial wait for Modal
            
            # Check if page loaded
            if "OpenTable" not in self.driver.title and "opentable" not in self.driver.current_url:
                return {'success': False, 'error': 'Page did not load correctly', 'reviews': []}
            
            self._log_progress("✅ Page loaded successfully", progress_callback)
            
            page_count = 0
            review_count = 0
            empty_pages = 0
            
            while True:
                page_count += 1
                self._log_progress(f"📄 Scraping page {page_count}...", progress_callback)
                
                # Find review cards
                review_elements = self._find_elements_with_fallback(
                    self.SELECTORS["review_cards"],
                    By.XPATH
                )
                
                if not review_elements:
                    empty_pages += 1
                    self._log_progress(f"⚠️ No reviews found on page {page_count}", progress_callback)
                    
                    if empty_pages >= 2 or page_count == 1:
                        break
                    continue
                
                empty_pages = 0  # Reset counter
                self._log_progress(f"📋 Found {len(review_elements)} review cards", progress_callback)
                
                # Extract from each review
                page_extracted = 0
                for idx, review_elem in enumerate(review_elements):
                    if max_reviews and review_count >= max_reviews:
                        break
                    
                    try:
                        review_text = self._extract_review_text(review_elem)
                        
                        # Skip empty reviews
                        if not review_text or len(review_text.strip()) < 10:
                            continue
                        
                        name = self._extract_text_with_fallback(review_elem, self.SELECTORS["name"])
                        date = self._extract_text_with_fallback(review_elem, self.SELECTORS["date"])
                        overall = self._extract_text_with_fallback(review_elem, self.SELECTORS["overall_rating"])
                        food = self._extract_text_with_fallback(review_elem, self.SELECTORS["food_rating"])
                        service = self._extract_text_with_fallback(review_elem, self.SELECTORS["service_rating"])
                        ambience = self._extract_text_with_fallback(review_elem, self.SELECTORS["ambience_rating"])
                        
                        names.append(name)
                        dates.append(date)
                        overall_ratings.append(overall)
                        food_ratings.append(food)
                        service_ratings.append(service)
                        ambience_ratings.append(ambience)
                        reviews.append(review_text)
                        
                        review_count += 1
                        page_extracted += 1
                        
                    except StaleElementReferenceException:
                        continue
                    except Exception as e:
                        continue
                
                self._log_progress(f"   ✅ Extracted {page_extracted} reviews from page {page_count}", progress_callback)
                
                if max_reviews and review_count >= max_reviews:
                    self._log_progress(f"🎯 Reached target: {max_reviews} reviews", progress_callback)
                    break
                
                # Try next page
                if not self._click_next():
                    self._log_progress("📍 No more pages available", progress_callback)
                    break
                
                # Wait for next page
                time.sleep(4)
            
            self._log_progress(f"✅ Scraping complete: {review_count} reviews from {page_count} pages", progress_callback)
            
            if review_count == 0:
                return {'success': False, 'error': 'No reviews extracted', 'reviews': []}
            
            return {
                'success': True,
                'total_reviews': review_count,
                'names': names,
                'dates': dates,
                'overall_ratings': overall_ratings,
                'food_ratings': food_ratings,
                'service_ratings': service_ratings,
                'ambience_ratings': ambience_ratings,
                'reviews': reviews,
                'metadata': {'pages_scraped': page_count}
            }
            
        except TimeoutException as e:
            return {'success': False, 'error': f'Page load timeout: {str(e)}', 'reviews': []}
        except WebDriverException as e:
            return {'success': False, 'error': f'Browser error: {str(e)}', 'reviews': []}
        except Exception as e:
            return {'success': False, 'error': f'Scraping error: {str(e)}', 'reviews': []}
    
    def _init_driver_robust(self):
        """
        Initialize Chrome with settings optimized for Modal/containerized environments.
        """
        chrome_options = Options()
        
        # Page load strategy - 'eager' is faster but 'normal' is more reliable
        chrome_options.page_load_strategy = 'normal'  # Changed from 'eager' for reliability
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # CRITICAL for containerized environments
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        
        # Memory management
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')  # Faster loading
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        
        # Stability improvements
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-accelerated-2d-canvas')
        chrome_options.add_argument('--disable-accelerated-jpeg-decoding')
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-breakpad')
        chrome_options.add_argument('--disable-client-side-phishing-detection')
        chrome_options.add_argument('--disable-component-update')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-hang-monitor')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-prompt-on-repost')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--disable-translate')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--safebrowsing-disable-auto-update')
        
        # Window size (helps with rendering)
        chrome_options.add_argument('--window-size=1920,1080')
        
        # User agent (avoid bot detection)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        
        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Create driver with longer timeout
        service = Service('/usr/local/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # LONGER timeouts for Modal environment
        self.driver.set_page_load_timeout(60)  # Was 30
        self.driver.set_script_timeout(60)
        self.driver.implicitly_wait(10)
        
        self.wait = WebDriverWait(self.driver, 20)  # Was 10
    
    def _extract_review_text(self, review_element) -> str:
        """Extract review text with multiple fallback strategies."""
        for selector in self.SELECTORS["review_text"]:
            try:
                elements = review_element.find_elements(By.XPATH, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text and len(text) > 20:
                        if "Dined on" in text or text.startswith("Overall"):
                            continue
                        if text in ["See more", "Read more", "Show more"]:
                            continue
                        return text
            except:
                continue
        
        # Last resort: get all text and find longest content
        try:
            full_text = review_element.text
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            content_lines = []
            for line in lines:
                if len(line) > 30:
                    if not any(skip in line for skip in ['Dined on', 'Overall', 'Food', 'Service', 'Ambience', 'VIP']):
                        content_lines.append(line)
            if content_lines:
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
        """Click next page button with robust handling."""
        for xp in self.SELECTORS["next_button"]:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, xp))
                )
                
                aria_disabled = (btn.get_attribute("aria-disabled") or "").lower()
                if aria_disabled in ("true", "1"):
                    return False
                
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(0.3)
                except:
                    pass
                
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
                    self.driver.execute_script("arguments[0].click();", btn)
                    return True
                except:
                    continue
            except:
                continue
        
        return False
    
    def _cleanup(self):
        """Close browser safely."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.wait = None
    
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
    Convenience function to scrape OpenTable reviews with retry logic.
    """
    scraper = OpenTableScraper(headless=headless)
    return scraper.scrape_reviews(url, max_reviews)


if __name__ == "__main__":
    # Test
    test_url = "https://www.opentable.ca/r/dockside-restaurant-vancouver"
    result = scrape_opentable(test_url, max_reviews=30)
    
    print(f"\n{'='*60}")
    print(f"Success: {result.get('success')}")
    print(f"Reviews: {result.get('total_reviews', 0)}")
    if result.get('error'):
        print(f"Error: {result.get('error')}")
    print(f"{'='*60}")