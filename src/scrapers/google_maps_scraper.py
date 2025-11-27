"""
Google Maps Review Scraper - ROBUST VERSION
Updated for 2024/2025 Google Maps DOM structure with retry logic.

FEATURES:
1. Updated selectors for current Google Maps DOM
2. Retry logic with exponential backoff
3. Multiple strategies to find reviews
4. Works in containerized environments (Modal)

Author: Tushar Pingle
Updated: Nov 2024
"""

import time
import random
from typing import List, Dict, Any, Optional, Callable
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException
)


class GoogleMapsScraper:
    """
    Robust Google Maps review scraper with multiple fallback strategies.
    """
    
    # Updated selectors for 2024/2025 Google Maps
    SELECTORS = {
        # Reviews tab button - multiple options
        "reviews_tab": [
            "//button[contains(@aria-label, 'Reviews')]",
            "//button[.//div[contains(text(), 'Reviews')]]",
            "//div[@role='tab'][contains(., 'Reviews')]",
            "//button[@data-tab-index='1']",
            "//div[contains(@class, 'Gpq6kf')]/button[2]",  # Second tab is usually Reviews
        ],
        
        # Scrollable container for reviews
        "scroll_container": [
            "//div[contains(@class, 'm6QErb') and contains(@class, 'DxyBCb')]",
            "//div[@role='feed']",
            "//div[contains(@class, 'review-dialog-list')]",
            "//div[contains(@class, 'm6QErb')]//div[contains(@class, 'DxyBCb')]",
            "//div[@tabindex='-1' and contains(@class, 'm6QErb')]",
        ],
        
        # Individual review cards
        "review_cards": [
            "//div[@data-review-id]",
            "//div[contains(@class, 'jftiEf')]",
            "//div[contains(@class, 'WMbnJf')]//div[contains(@class, 'jftiEf')]",
            "//div[@jscontroller and contains(@class, 'fontBodyMedium')]//ancestor::div[@data-review-id]",
        ],
        
        # Review text within a card
        "review_text": [
            ".//span[contains(@class, 'wiI7pd')]",
            ".//div[contains(@class, 'MyEned')]//span",
            ".//span[@class='wiI7pd']",
            ".//div[@data-expandable-section]//span",
        ],
        
        # "More" button to expand text
        "more_button": [
            ".//button[contains(@aria-label, 'See more')]",
            ".//button[contains(text(), 'More')]",
            ".//button[contains(@class, 'w8nwRe')]",
        ],
        
        # Rating stars
        "rating": [
            ".//span[contains(@aria-label, 'star')]",
            ".//span[contains(@class, 'kvMYJc')]",
            ".//div[contains(@class, 'DU9Pgb')]//span",
        ],
        
        # Review date
        "date": [
            ".//span[contains(@class, 'rsqaWe')]",
            ".//span[contains(text(), 'ago')]",
            ".//span[contains(text(), 'month') or contains(text(), 'year') or contains(text(), 'week') or contains(text(), 'day')]",
        ],
        
        # Reviewer name
        "reviewer_name": [
            ".//div[contains(@class, 'd4r55')]",
            ".//button[contains(@class, 'WEBjve')]",
            ".//a[contains(@class, 'WNxzHc')]",
        ],
    }
    
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 15, 30]
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
    
    def scrape_reviews(
        self,
        url: str,
        max_reviews: Optional[int] = 100,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Scrape reviews with automatic retry on failure.
        """
        if not self._validate_url(url):
            return {'success': False, 'error': 'Invalid Google Maps URL', 'reviews': []}
        
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                self._log(f"🚀 Attempt {attempt + 1}/{self.MAX_RETRIES}...", progress_callback)
                
                result = self._scrape_with_retry(url, max_reviews, progress_callback)
                
                if result.get('success') and result.get('total_reviews', 0) > 0:
                    return result
                elif result.get('total_reviews', 0) == 0:
                    last_error = "No reviews found - selectors may need updating"
                    self._log(f"⚠️ Attempt {attempt + 1}: {last_error}", progress_callback)
                else:
                    last_error = result.get('error', 'Unknown error')
                    self._log(f"⚠️ Attempt {attempt + 1} failed: {last_error}", progress_callback)
                    
            except Exception as e:
                last_error = str(e)
                self._log(f"⚠️ Attempt {attempt + 1} exception: {last_error}", progress_callback)
            
            finally:
                self._cleanup()
            
            # Wait before retry
            if attempt < self.MAX_RETRIES - 1:
                delay = self.RETRY_DELAYS[attempt] + random.uniform(0, 5)
                self._log(f"⏳ Waiting {delay:.0f}s before retry...", progress_callback)
                time.sleep(delay)
        
        return {
            'success': False,
            'error': f'Failed after {self.MAX_RETRIES} attempts. Last error: {last_error}',
            'reviews': [],
            'total_reviews': 0
        }
    
    def _scrape_with_retry(
        self,
        url: str,
        max_reviews: Optional[int],
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """
        Core scraping logic.
        """
        self._init_driver()
        
        reviews = []
        dates = []
        ratings = []
        names = []
        
        try:
            self._log("🌐 Loading Google Maps page...", progress_callback)
            self.driver.get(url)
            time.sleep(5)  # Wait for initial load
            
            # Accept cookies if prompted
            self._handle_consent_dialog()
            
            # Try to click on Reviews tab
            self._log("📋 Looking for Reviews tab...", progress_callback)
            if not self._click_reviews_tab(progress_callback):
                self._log("⚠️ Could not find Reviews tab, trying alternative methods...", progress_callback)
                # Try scrolling on the main panel anyway
            
            time.sleep(3)
            
            # Find scrollable container
            scroll_container = self._find_scroll_container(progress_callback)
            
            if not scroll_container:
                self._log("⚠️ Could not find scrollable container, trying body scroll...", progress_callback)
                scroll_container = self.driver.find_element(By.TAG_NAME, "body")
            
            # Scroll and collect reviews
            collected_ids = set()
            no_new_reviews_count = 0
            scroll_count = 0
            max_scrolls = max(50, (max_reviews or 100) // 3)  # Estimate scrolls needed
            
            while len(reviews) < (max_reviews or 100) and scroll_count < max_scrolls:
                scroll_count += 1
                
                # Find review cards
                review_cards = self._find_review_cards()
                
                new_count = 0
                for card in review_cards:
                    try:
                        # Get unique identifier
                        card_id = card.get_attribute('data-review-id') or card.id
                        
                        if card_id in collected_ids:
                            continue
                        
                        # Expand "More" text if available
                        self._expand_review_text(card)
                        
                        # Extract data
                        text = self._extract_review_text(card)
                        
                        if text and len(text.strip()) > 10:
                            collected_ids.add(card_id)
                            reviews.append(text)
                            dates.append(self._extract_date(card))
                            ratings.append(self._extract_rating(card))
                            names.append(self._extract_name(card))
                            new_count += 1
                            
                            if len(reviews) >= (max_reviews or 100):
                                break
                    
                    except StaleElementReferenceException:
                        continue
                    except Exception:
                        continue
                
                self._log(f"📄 Scroll {scroll_count}: Found {len(review_cards)} cards, collected {len(reviews)} unique reviews", progress_callback)
                
                if new_count == 0:
                    no_new_reviews_count += 1
                    if no_new_reviews_count >= 5:
                        self._log("📍 No new reviews found after 5 scrolls, stopping", progress_callback)
                        break
                else:
                    no_new_reviews_count = 0
                
                # Scroll down
                try:
                    if scroll_container:
                        self.driver.execute_script(
                            "arguments[0].scrollTop = arguments[0].scrollTop + arguments[0].offsetHeight * 0.8",
                            scroll_container
                        )
                    else:
                        ActionChains(self.driver).send_keys(Keys.PAGE_DOWN).perform()
                except:
                    ActionChains(self.driver).send_keys(Keys.PAGE_DOWN).perform()
                
                time.sleep(1.5)
            
            self._log(f"✅ Scraped {len(reviews)} reviews from Google Maps", progress_callback)
            
            return {
                'success': True,
                'total_reviews': len(reviews),
                'reviews': reviews,
                'dates': dates,
                'ratings': ratings,
                'names': names,
                'source': 'google_maps'
            }
            
        except TimeoutException as e:
            return {'success': False, 'error': f'Page load timeout: {str(e)}', 'reviews': [], 'total_reviews': 0}
        except WebDriverException as e:
            return {'success': False, 'error': f'Browser error: {str(e)}', 'reviews': [], 'total_reviews': 0}
        except Exception as e:
            return {'success': False, 'error': f'Scraping error: {str(e)}', 'reviews': [], 'total_reviews': 0}
    
    def _handle_consent_dialog(self):
        """Handle Google consent/cookie dialog if it appears."""
        try:
            consent_buttons = [
                "//button[contains(., 'Accept')]",
                "//button[contains(., 'Reject')]",
                "//button[contains(., 'I agree')]",
                "//form//button",
            ]
            for selector in consent_buttons:
                try:
                    btn = self.driver.find_element(By.XPATH, selector)
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(1)
                        return
                except:
                    continue
        except:
            pass
    
    def _click_reviews_tab(self, progress_callback: Optional[Callable]) -> bool:
        """Try to click the Reviews tab."""
        for selector in self.SELECTORS["reviews_tab"]:
            try:
                tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                tab.click()
                self._log("✅ Clicked Reviews tab", progress_callback)
                return True
            except:
                continue
        
        # Alternative: try clicking based on visible text
        try:
            tabs = self.driver.find_elements(By.XPATH, "//button[@role='tab']")
            for tab in tabs:
                if 'review' in tab.text.lower():
                    tab.click()
                    self._log("✅ Clicked Reviews tab (text match)", progress_callback)
                    return True
        except:
            pass
        
        return False
    
    def _find_scroll_container(self, progress_callback: Optional[Callable]):
        """Find the scrollable reviews container."""
        for selector in self.SELECTORS["scroll_container"]:
            try:
                container = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                # Verify it's scrollable
                scroll_height = self.driver.execute_script("return arguments[0].scrollHeight", container)
                if scroll_height > 100:
                    self._log(f"✅ Found scrollable container", progress_callback)
                    return container
            except:
                continue
        
        self._log("⚠️ Could not find scrollable reviews container", progress_callback)
        return None
    
    def _find_review_cards(self) -> List:
        """Find all review cards on the page."""
        for selector in self.SELECTORS["review_cards"]:
            try:
                cards = self.driver.find_elements(By.XPATH, selector)
                if cards:
                    return cards
            except:
                continue
        return []
    
    def _expand_review_text(self, card):
        """Click "More" button to expand review text."""
        for selector in self.SELECTORS["more_button"]:
            try:
                btn = card.find_element(By.XPATH, selector)
                if btn.is_displayed():
                    btn.click()
                    time.sleep(0.3)
                    return
            except:
                continue
    
    def _extract_review_text(self, card) -> str:
        """Extract review text from a card."""
        for selector in self.SELECTORS["review_text"]:
            try:
                elem = card.find_element(By.XPATH, selector)
                text = elem.text.strip()
                if text and len(text) > 10:
                    return text
            except:
                continue
        
        # Fallback: get all text and filter
        try:
            full_text = card.text
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            # Find longest line that looks like a review
            for line in sorted(lines, key=len, reverse=True):
                if len(line) > 30 and not any(x in line.lower() for x in ['star', 'ago', 'review', 'photo']):
                    return line
        except:
            pass
        
        return ""
    
    def _extract_rating(self, card) -> float:
        """Extract star rating from a card."""
        for selector in self.SELECTORS["rating"]:
            try:
                elem = card.find_element(By.XPATH, selector)
                aria_label = elem.get_attribute('aria-label') or ""
                # Parse "5 stars" or "4 star" etc
                for word in aria_label.split():
                    try:
                        return float(word)
                    except:
                        continue
            except:
                continue
        return 0.0
    
    def _extract_date(self, card) -> str:
        """Extract date from a card."""
        for selector in self.SELECTORS["date"]:
            try:
                elem = card.find_element(By.XPATH, selector)
                return elem.text.strip()
            except:
                continue
        return ""
    
    def _extract_name(self, card) -> str:
        """Extract reviewer name from a card."""
        for selector in self.SELECTORS["reviewer_name"]:
            try:
                elem = card.find_element(By.XPATH, selector)
                return elem.text.strip()
            except:
                continue
        return ""
    
    def _init_driver(self):
        """Initialize Chrome with robust settings for containers."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # Container-friendly options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Avoid bot detection
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service('/usr/local/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(60)
        self.driver.set_script_timeout(60)
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 20)
    
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
        """Validate Google Maps URL."""
        url_lower = url.lower()
        return any(x in url_lower for x in ['google.com/maps', 'goo.gl/maps', 'maps.google', 'maps.app.goo.gl'])
    
    def _log(self, message: str, callback: Optional[Callable]):
        """Log progress."""
        print(message)
        if callback:
            callback(message)
    
    def __del__(self):
        self._cleanup()


def scrape_google_maps(url: str, max_reviews: Optional[int] = 100, headless: bool = True) -> Dict[str, Any]:
    """
    Convenience function to scrape Google Maps reviews.
    """
    scraper = GoogleMapsScraper(headless=headless)
    return scraper.scrape_reviews(url, max_reviews)


if __name__ == "__main__":
    # Test
    test_url = "https://www.google.com/maps/place/Nightingale/@49.2784422,-123.1214336,17z"
    result = scrape_google_maps(test_url, max_reviews=20)
    
    print(f"\n{'='*60}")
    print(f"Success: {result.get('success')}")
    print(f"Reviews: {result.get('total_reviews', 0)}")
    if result.get('error'):
        print(f"Error: {result.get('error')}")
    if result.get('reviews'):
        print(f"\nFirst review: {result['reviews'][0][:100]}...")
    print(f"{'='*60}")