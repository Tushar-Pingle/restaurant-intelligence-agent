"""
Google Maps Review Scraper - 2025 Production Version
Updated with VERIFIED selectors from actual Google Maps DOM inspection.

Key fixes based on selector documentation:
1. Reviews tab: button with aria-label="Reviews" or containing "Reviews" text
2. Scrollable container: div.m6QErb.DxyBCb OR div.XiKgde OR div[role='feed']
3. Review cards: div.jftiEf.fontBodyMedium with data-review-id
4. Reviewer name: div.d4r55 (no trailing space)
5. Star rating: span.kvMYJc child span with aria-label
6. Date: span.rsqaWe
7. Review text: span.wiI7pd (truncated) or span[jsname='fbQN7e'] (full)
8. More button: button.w8nwRe or button.kyuUzc
"""

import time
import re
import os
from typing import List, Dict, Any, Optional, Callable
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import random


class GoogleMapsScraper:
    """
    Scrapes restaurant reviews from Google Maps.
    
    VERIFIED selectors (Nov 2025):
    - Review cards: div.jftiEf.fontBodyMedium with data-review-id
    - Reviewer name: div.d4r55
    - Star rating: span.kvMYJc > span[aria-label*="star"]
    - Date: span.rsqaWe
    - Review text: span.wiI7pd (truncated) or span[jsname='fbQN7e'] (full)
    - More button: button.w8nwRe or button.kyuUzc
    - Scrollable container: div.m6QErb.DxyBCb or div.XiKgde
    """
    
    # VERIFIED selectors from documentation
    SELECTORS = {
        # Reviews tab button - multiple fallbacks
        "reviews_tab": [
            "//button[contains(@aria-label, 'Reviews')]",
            "//button[@role='tab'][contains(., 'Reviews')]",
            "//button[@role='tab'][contains(., 'reviews')]",
            "//div[@role='tablist']//button[contains(., 'Review')]",
            "//button[@data-tab-index='1']",
            "//button[contains(@class, 'hh2c6')]",
        ],
        
        # Scrollable reviews container - VERIFIED classes
        "scrollable_div": [
            "//div[contains(@class, 'm6QErb') and contains(@class, 'DxyBCb')]",
            "//div[contains(@class, 'XiKgde')]",
            "//div[@role='feed']",
            "//div[contains(@class, 'm6QErb')][@tabindex='-1']",
            "//div[contains(@class, 'm6QErb')]",
        ],
        
        # Individual review cards - VERIFIED: div.jftiEf with data-review-id
        "review_cards": [
            "//div[@data-review-id]",
            "//div[contains(@class, 'jftiEf') and contains(@class, 'fontBodyMedium')]",
            "//div[contains(@class, 'jftiEf')]",
        ],
        
        # Reviewer name - VERIFIED: div.d4r55 (no trailing space!)
        "reviewer_name": [
            ".//div[contains(@class, 'd4r55')]",
            ".//button[contains(@class, 'WEBjve')]//div",
            ".//a[contains(@class, 'WNBkOb')]//div[1]",
        ],
        
        # Star rating - VERIFIED: span.kvMYJc child with aria-label
        "rating": [
            ".//span[contains(@class, 'kvMYJc')]//span[@aria-label]",
            ".//span[@aria-label][contains(@aria-label, 'star')]",
            ".//div[@role='img'][@aria-label]",
        ],
        
        # Review date - VERIFIED: span.rsqaWe
        "date": [
            ".//span[contains(@class, 'rsqaWe')]",
            ".//span[contains(text(), 'ago')]",
            ".//span[contains(text(), 'week')]",
            ".//span[contains(text(), 'month')]",
            ".//span[contains(text(), 'day')]",
            ".//span[contains(text(), 'year')]",
        ],
        
        # Review text - VERIFIED: span.wiI7pd and jsname variants
        "review_text": [
            ".//span[contains(@class, 'wiI7pd')]",
            ".//span[@jsname='fbQN7e']",  # Full expanded text
            ".//span[@jsname='bN97Pc']",  # Truncated text
            ".//div[contains(@class, 'MyEned')]//span",
        ],
        
        # "More" button - VERIFIED: button.w8nwRe or button.kyuUzc
        "more_button": [
            ".//button[contains(@class, 'w8nwRe')]",
            ".//button[contains(@class, 'kyuUzc')]",
            ".//button[@aria-expanded='false']",
            ".//button[contains(@aria-label, 'More')]",
            ".//button[contains(@aria-label, 'more')]",
            ".//span[text()='More']/parent::button",
            ".//button[.//span[text()='More']]",
        ],
    }
    
    def __init__(self, headless: bool = True, chromedriver_path: Optional[str] = None):
        """Initialize the scraper."""
        self.headless = headless
        self.driver = None
        self.wait = None
        self.chromedriver_path = chromedriver_path or self._find_chromedriver()
    
    def _find_chromedriver(self) -> str:
        """Find chromedriver in common locations."""
        common_paths = [
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver',
            '/opt/chromedriver',
            'chromedriver',
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            return ChromeDriverManager().install()
        except:
            pass
        
        return '/usr/local/bin/chromedriver'
    
    def _init_driver(self):
        """Initialize Chrome WebDriver with anti-detection settings."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
        
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--lang=en-US')
        
        # Realistic user agent
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        
        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        try:
            service = Service(self.chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception:
            self.driver = webdriver.Chrome(options=chrome_options)
        
        self.driver.set_page_load_timeout(60)
        self.wait = WebDriverWait(self.driver, 20)
        
        # Anti-detection CDP
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            '''
        })
    
    def _cleanup(self):
        """Close browser."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _random_delay(self, min_sec: float = 0.5, max_sec: float = 1.5):
        """Add random delay."""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def _find_elements_with_fallback(self, selectors: List[str]) -> List:
        """Try multiple selectors until one returns elements."""
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements:
                    return elements
            except:
                continue
        return []
    
    def _extract_rating(self, review_element) -> float:
        """Extract star rating using aria-label."""
        for selector in self.SELECTORS["rating"]:
            try:
                elem = review_element.find_element(By.XPATH, selector)
                aria_label = elem.get_attribute('aria-label')
                if aria_label:
                    match = re.search(r'(\d+)\s*star', aria_label.lower())
                    if match:
                        return float(match.group(1))
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return 0.0
    
    def _extract_text(self, parent, selectors: List[str]) -> str:
        """Extract text using fallback selectors."""
        for selector in selectors:
            try:
                element = parent.find_element(By.XPATH, selector)
                text = element.text.strip()
                if text:
                    return text
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return ""
    
    def _expand_review_text(self, review_element):
        """Click 'More' button to expand truncated review."""
        for selector in self.SELECTORS["more_button"]:
            try:
                more_btn = review_element.find_element(By.XPATH, selector)
                if more_btn and more_btn.is_displayed():
                    try:
                        more_btn.click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", more_btn)
                    self._random_delay(0.3, 0.6)
                    return True
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return False
    
    def _get_scrollable_element(self, progress_callback=None):
        """Find the scrollable reviews container."""
        for selector in self.SELECTORS["scrollable_div"]:
            try:
                element = self.driver.find_element(By.XPATH, selector)
                if element:
                    self._log_progress(f"✅ Found scrollable container with: {selector[:50]}...", progress_callback)
                    return element
            except NoSuchElementException:
                continue
        return None
    
    def _scroll_reviews(self, scrollable_element, scroll_pause: float = 1.5):
        """Scroll the reviews panel to load more."""
        if not scrollable_element:
            return False
        
        try:
            last_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", 
                scrollable_element
            )
            
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight",
                scrollable_element
            )
            
            time.sleep(scroll_pause + random.uniform(0, 0.5))
            
            new_height = self.driver.execute_script(
                "return arguments[0].scrollHeight",
                scrollable_element
            )
            
            return new_height > last_height
        except Exception as e:
            print(f"Scroll error: {e}")
            return False
    
    def _click_reviews_tab(self, progress_callback=None) -> bool:
        """Click on the Reviews tab."""
        # First, wait for page to fully load
        time.sleep(3)
        
        # Try each selector
        for selector in self.SELECTORS["reviews_tab"]:
            try:
                self._log_progress(f"🔍 Trying selector: {selector[:60]}...", progress_callback)
                tab = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                tab.click()
                self._log_progress("✅ Clicked Reviews tab", progress_callback)
                time.sleep(3)
                return True
            except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
                continue
        
        # Fallback: Try finding any button with "Review" text
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                try:
                    btn_text = btn.text.lower()
                    btn_aria = (btn.get_attribute('aria-label') or '').lower()
                    if 'review' in btn_text or 'review' in btn_aria:
                        self._log_progress(f"🔍 Found button with text: {btn.text[:30]}", progress_callback)
                        btn.click()
                        time.sleep(3)
                        return True
                except:
                    continue
        except:
            pass
        
        # Last resort: Try clicking on the reviews count text
        try:
            review_count_elem = self.driver.find_element(By.XPATH, "//button[contains(., 'review')]")
            review_count_elem.click()
            time.sleep(3)
            return True
        except:
            pass
        
        return False
    
    def _handle_consent_dialog(self, progress_callback=None):
        """Handle Google consent/cookie dialog if it appears."""
        try:
            consent_selectors = [
                "//button[contains(., 'Accept all')]",
                "//button[contains(., 'Accept')]",
                "//button[contains(., 'Reject all')]",
                "//button[contains(., 'I agree')]",
                "//form//button",
            ]
            
            for selector in consent_selectors:
                try:
                    btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if btn.is_displayed():
                        self._log_progress("🍪 Handling consent dialog...", progress_callback)
                        btn.click()
                        time.sleep(2)
                        return True
                except:
                    continue
        except:
            pass
        return False
    
    def _debug_page_state(self, progress_callback=None):
        """Debug: Log page state to help diagnose issues."""
        try:
            # Get page title
            title = self.driver.title
            self._log_progress(f"📄 Page title: {title}", progress_callback)
            
            # Check if we're on the right page
            url = self.driver.current_url
            self._log_progress(f"📄 Current URL: {url[:80]}...", progress_callback)
            
            # Count some elements
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            all_divs = self.driver.find_elements(By.TAG_NAME, "div")
            self._log_progress(f"📄 Page has {len(all_buttons)} buttons, {len(all_divs)} divs", progress_callback)
            
            # Look for any tab-like elements
            tabs = self.driver.find_elements(By.XPATH, "//button[@role='tab']")
            self._log_progress(f"📄 Found {len(tabs)} tab buttons", progress_callback)
            for tab in tabs[:5]:
                try:
                    tab_text = tab.text[:30] if tab.text else "(no text)"
                    tab_aria = tab.get_attribute('aria-label') or "(no aria)"
                    self._log_progress(f"   Tab: {tab_text} | aria: {tab_aria[:30]}", progress_callback)
                except:
                    pass
            
            # Look for review-related elements
            review_elements = self.driver.find_elements(By.XPATH, "//*[contains(@class, 'jftiEf')]")
            self._log_progress(f"📄 Found {len(review_elements)} elements with 'jftiEf' class", progress_callback)
            
        except Exception as e:
            self._log_progress(f"⚠️ Debug error: {e}", progress_callback)
    
    def _extract_review_data(self, review_element, idx: int) -> Optional[Dict]:
        """Extract all data from a single review card."""
        try:
            # Try to expand truncated text
            self._expand_review_text(review_element)
            
            # Extract reviewer name
            name = self._extract_text(review_element, self.SELECTORS["reviewer_name"])
            
            # Extract date
            date = self._extract_text(review_element, self.SELECTORS["date"])
            
            # Extract star rating
            rating = self._extract_rating(review_element)
            
            # Extract review text (try expanded first, then truncated)
            text = ""
            for selector in [".//span[@jsname='fbQN7e']", ".//span[contains(@class, 'wiI7pd')]"]:
                try:
                    elem = review_element.find_element(By.XPATH, selector)
                    t = elem.text.strip()
                    if t and len(t) > len(text):
                        text = t
                except:
                    continue
            
            if not text:
                text = self._extract_text(review_element, self.SELECTORS["review_text"])
            
            # Validate
            if not text or len(text) < 10:
                return None
            
            return {
                'name': name,
                'date': date.strip() if date else "",
                'rating': rating,
                'text': text
            }
        
        except StaleElementReferenceException:
            return None
        except Exception as e:
            print(f"[GMAPS] Error extracting review {idx}: {e}")
            return None
    
    def scrape_reviews(
        self,
        url: str,
        max_reviews: Optional[int] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Scrape reviews from Google Maps restaurant page."""
        
        if not self._validate_url(url):
            return {
                'success': False, 
                'error': 'Invalid Google Maps URL. Use google.com/maps or goo.gl/maps', 
                'reviews': {}
            }
        
        try:
            self._init_driver()
        except Exception as e:
            return {
                'success': False, 
                'error': f'Browser initialization failed: {str(e)}', 
                'reviews': {}
            }
        
        try:
            self._log_progress("🚀 Starting Google Maps scraper...", progress_callback)
            
            # Load the page
            self.driver.get(url)
            time.sleep(5)
            
            # Handle consent dialog if present
            self._handle_consent_dialog(progress_callback)
            
            # Debug: check page state
            self._debug_page_state(progress_callback)
            
            # Click Reviews tab
            self._log_progress("📋 Looking for Reviews tab...", progress_callback)
            if not self._click_reviews_tab(progress_callback):
                self._log_progress("⚠️ Could not find Reviews tab, trying to scroll anyway...", progress_callback)
                # Try scrolling down to trigger lazy loading
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(2)
            
            time.sleep(3)
            
            # Debug again after clicking tab
            self._debug_page_state(progress_callback)
            
            # Find scrollable container
            scrollable = self._get_scrollable_element(progress_callback)
            if not scrollable:
                self._log_progress("⚠️ Could not find scrollable reviews container", progress_callback)
            
            # Initialize data containers
            names = []
            dates = []
            ratings = []
            review_texts = []
            
            processed_ids = set()
            scroll_count = 0
            no_new_reviews_count = 0
            max_no_new = 5
            
            max_scrolls = (max_reviews // 3) + 20 if max_reviews else 100
            
            while scroll_count < max_scrolls and no_new_reviews_count < max_no_new:
                scroll_count += 1
                
                # Find all review cards
                review_elements = self._find_elements_with_fallback(self.SELECTORS["review_cards"])
                
                self._log_progress(
                    f"📄 Scroll {scroll_count}: Found {len(review_elements)} review cards, "
                    f"collected {len(review_texts)} unique reviews", 
                    progress_callback
                )
                
                new_reviews_this_scroll = 0
                
                for idx, review_elem in enumerate(review_elements):
                    if max_reviews and len(review_texts) >= max_reviews:
                        break
                    
                    try:
                        review_id = review_elem.get_attribute('data-review-id')
                        if not review_id:
                            review_id = f"pos_{idx}_{review_elem.location['y']}"
                    except:
                        review_id = f"idx_{idx}_{scroll_count}"
                    
                    if review_id in processed_ids:
                        continue
                    
                    review_data = self._extract_review_data(review_elem, idx)
                    
                    if review_data:
                        if review_data['text'] not in review_texts:
                            names.append(review_data['name'])
                            dates.append(review_data['date'])
                            ratings.append(review_data['rating'])
                            review_texts.append(review_data['text'])
                            new_reviews_this_scroll += 1
                    
                    processed_ids.add(review_id)
                    
                    if idx % 5 == 0:
                        self._random_delay(0.1, 0.3)
                
                if new_reviews_this_scroll == 0:
                    no_new_reviews_count += 1
                else:
                    no_new_reviews_count = 0
                
                if max_reviews and len(review_texts) >= max_reviews:
                    self._log_progress(f"🎯 Reached target: {max_reviews} reviews", progress_callback)
                    break
                
                # Scroll
                if scrollable:
                    self._scroll_reviews(scrollable)
                else:
                    self.driver.execute_script("window.scrollBy(0, 500);")
                    time.sleep(1.5)
            
            self._cleanup()
            
            # Trim to max_reviews
            if max_reviews:
                names = names[:max_reviews]
                dates = dates[:max_reviews]
                ratings = ratings[:max_reviews]
                review_texts = review_texts[:max_reviews]
            
            self._log_progress(
                f"✅ Scraped {len(review_texts)} reviews from Google Maps", 
                progress_callback
            )
            
            return {
                'success': True,
                'total_reviews': len(review_texts),
                'total_pages': scroll_count,
                'reviews': {
                    'names': names,
                    'dates': dates,
                    'overall_ratings': ratings,
                    'food_ratings': [0.0] * len(ratings),
                    'service_ratings': [0.0] * len(ratings),
                    'ambience_ratings': [0.0] * len(ratings),
                    'review_texts': review_texts
                },
                'metadata': {
                    'source': 'google_maps',
                    'url': url,
                    'scroll_count': scroll_count
                }
            }
            
        except Exception as e:
            self._cleanup()
            import traceback
            traceback.print_exc()
            return {
                'success': False, 
                'error': str(e), 
                'reviews': {}
            }
    
    def _validate_url(self, url: str) -> bool:
        """Validate Google Maps URL."""
        if not url:
            return False
        url_lower = url.lower()
        return any(x in url_lower for x in [
            'google.com/maps', 
            'goo.gl/maps', 
            'maps.google',
            'maps.app.goo.gl'
        ])
    
    def _log_progress(self, message: str, callback: Optional[Callable]):
        """Log progress."""
        print(message)
        if callback:
            callback(message)
    
    def __del__(self):
        self._cleanup()


def scrape_google_maps(
    url: str, 
    max_reviews: Optional[int] = None, 
    headless: bool = True,
    chromedriver_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scrape reviews from Google Maps.
    
    Args:
        url: Google Maps restaurant URL
        max_reviews: Maximum number of reviews to scrape (None = all available)
        headless: Run browser in headless mode
        chromedriver_path: Optional path to chromedriver
    
    Returns:
        Dict with 'success', 'total_reviews', and 'reviews' data
    """
    scraper = GoogleMapsScraper(headless=headless, chromedriver_path=chromedriver_path)
    return scraper.scrape_reviews(url, max_reviews=max_reviews)


if __name__ == "__main__":
    print("=" * 80)
    print("Google Maps Review Scraper - Production Test (Nov 2025)")
    print("=" * 80 + "\n")
    
    test_url = "https://www.google.com/maps/place/Tutto+Italian+Restaurant+%26+Bar"
    
    print(f"Target: {test_url}")
    print("Limit: 20 reviews (test mode)")
    print("Mode: HEADLESS\n")
    
    result = scrape_google_maps(test_url, max_reviews=20, headless=True)
    
    print("\n" + "=" * 80)
    if result['success']:
        print("SUCCESS!")
        print(f"   Total reviews scraped: {result['total_reviews']}")
        print(f"   Scroll iterations: {result.get('total_pages', 'N/A')}")
        
        if result['total_reviews'] > 0:
            print(f"\n   Sample (first review):")
            print(f"   Name: {result['reviews']['names'][0]}")
            print(f"   Date: {result['reviews']['dates'][0]}")
            print(f"   Rating: {result['reviews']['overall_ratings'][0]}")
            text = result['reviews']['review_texts'][0]
            print(f"   Review: {text[:150]}{'...' if len(text) > 150 else ''}")
    else:
        print("FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    print("=" * 80)