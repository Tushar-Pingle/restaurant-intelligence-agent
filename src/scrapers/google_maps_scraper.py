Google Maps Review Scraper - 2025 Production Version
Updated with verified selectors from actual Google Maps DOM inspection.

Key improvements:
1. Updated selectors based on actual HTML structure
2. Better "More" button handling for truncated reviews
3. Improved star rating extraction via aria-label
4. Robust error handling and fallbacks
5. Configurable chromedriver path
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
    ElementClickInterceptedException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
import random


class GoogleMapsScraper:
    """
    Scrapes restaurant reviews from Google Maps.
    
    Selectors updated based on actual DOM inspection (Nov 2025):
    - Review cards: div.jftiEf or div[data-review-id]
    - Reviewer name: div.d4r55
    - Star rating: span with aria-label containing "star"
    - Date: span.rsqaWe (contains "ago")
    - Review text: span.wiI7pd (truncated) or span[jsname='fbQN7e'] (full)
    - More button: Various elements containing "More"
    - Scrollable container: div.m6QErb or div.XiKgde
    """
    
    # Updated selectors based on actual Google Maps DOM (Nov 2025)
    SELECTORS = {
        # Parent container for the business listing
        "business_container": [
            "//div[contains(@class, 'WNBkOb')]",
        ],
        
        # Reviews tab button
        "reviews_tab": [
            "//button[@role='tab'][contains(., 'Reviews')]",
            "//button[contains(@aria-label, 'Reviews')]",
            "//div[@role='tab'][contains(., 'Reviews')]",
            "//button[contains(@data-tab-index, '1')]",  # Reviews is often tab index 1
        ],
        
        # Scrollable reviews container
        "scrollable_div": [
            "//div[contains(@class, 'm6QErb') and contains(@class, 'DxyBCb')]",
            "//div[contains(@class, 'XiKgde')]",
            "//div[@role='feed']",
            "//div[contains(@class, 'm6QErb')][@tabindex='-1']",
        ],
        
        # Individual review cards
        "review_cards": [
            "//div[@data-review-id]",
            "//div[contains(@class, 'jftiEf') and contains(@class, 'fontBodyMedium')]",
            "//div[contains(@class, 'jftiEf')]",
        ],
        
        # Reviewer name - updated without trailing space
        "reviewer_name": [
            ".//div[contains(@class, 'd4r55')]",
            ".//button[contains(@class, 'WEBjve')]",
            ".//div[@role='article']//span[contains(@class, 'd4r55')]",
            ".//a[contains(@class, 'WNBkOb')]//div[1]",
        ],
        
        # Star rating - use aria-label attribute
        "rating": [
            ".//span[@aria-label][contains(@aria-label, 'star')]",
            ".//span[contains(@class, 'kvMYJc')]//span[@aria-label]",
            ".//div[@role='img'][@aria-label]",
        ],
        
        # Review date
        "date": [
            ".//span[contains(@class, 'rsqaWe')]",
            ".//span[contains(text(), 'ago')]",
            ".//span[contains(text(), 'week')]",
            ".//span[contains(text(), 'month')]",
            ".//span[contains(text(), 'day')]",
            ".//span[contains(text(), 'year')]",
        ],
        
        # Review text - both truncated and full versions
        "review_text": [
            ".//span[contains(@class, 'wiI7pd')]",
            ".//span[@jsname='fbQN7e']",  # Full expanded text
            ".//span[@jsname='bN97Pc']",  # Truncated text
            ".//div[contains(@class, 'MyEned')]//span",
        ],
        
        # "More" button for expanding truncated reviews
        "more_button": [
            ".//button[contains(@class, 'w8nwRe')]",
            ".//button[contains(@class, 'kyuUzc')]",
            ".//button[contains(@aria-label, 'More')]",
            ".//button[contains(@aria-label, 'more')]",
            ".//span[text()='More']",
            ".//button[.//span[text()='More']]",
            ".//*[contains(text(), 'More') and not(contains(text(), 'More reviews'))]",
        ],
    }
    
    def __init__(self, headless: bool = True, chromedriver_path: Optional[str] = None):
        """
        Initialize the scraper.
        
        Args:
            headless: Run browser in headless mode
            chromedriver_path: Path to chromedriver (auto-detected if None)
        """
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
            'chromedriver',  # In PATH
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Try webdriver-manager if available
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            return ChromeDriverManager().install()
        except ImportError:
            pass
        except Exception as e:
            print(f"[GMAPS] webdriver-manager failed: {e}")
        
        # Default fallback - will be used on Modal which has chromedriver installed
        return '/usr/local/bin/chromedriver'
    
    def _init_driver(self):
        """Initialize Chrome WebDriver with anti-detection settings."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
        
        # Larger window for better element visibility
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Realistic user agent
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        
        # Anti-detection measures
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Disable images for faster loading (optional - comment out if you need images)
        # prefs = {"profile.managed_default_content_settings.images": 2}
        # chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(self.chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception:
            # Fallback: try without explicit service path
            self.driver = webdriver.Chrome(options=chrome_options)
        
        self.driver.set_page_load_timeout(45)
        self.wait = WebDriverWait(self.driver, 15)
        
        # Additional anti-detection
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
        """Add random delay to mimic human behavior."""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def _find_element_with_fallback(self, parent, selectors: List[str]):
        """Try multiple selectors until one works."""
        for selector in selectors:
            try:
                element = parent.find_element(By.XPATH, selector)
                if element:
                    return element
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return None
    
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
        """
        Extract star rating from review using aria-label.
        Looks for aria-label like "5 stars" or "4 stars".
        """
        for selector in self.SELECTORS["rating"]:
            try:
                elem = review_element.find_element(By.XPATH, selector)
                aria_label = elem.get_attribute('aria-label')
                if aria_label:
                    # Extract number from "5 stars" or "4 stars"
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
        """
        Click 'More' button to expand truncated review text.
        Google Maps uses various elements for the More button.
        """
        for selector in self.SELECTORS["more_button"]:
            try:
                more_btn = review_element.find_element(By.XPATH, selector)
                if more_btn and more_btn.is_displayed():
                    try:
                        # Try regular click first
                        more_btn.click()
                    except ElementClickInterceptedException:
                        # Fallback to JavaScript click
                        self.driver.execute_script("arguments[0].click();", more_btn)
                    self._random_delay(0.3, 0.6)
                    return True
            except (NoSuchElementException, StaleElementReferenceException):
                continue
        return False
    
    def _get_scrollable_element(self):
        """Find the scrollable reviews container."""
        for selector in self.SELECTORS["scrollable_div"]:
            try:
                element = self.driver.find_element(By.XPATH, selector)
                if element:
                    return element
            except NoSuchElementException:
                continue
        return None
    
    def _scroll_reviews(self, scrollable_element, scroll_pause: float = 1.5):
        """
        Scroll the reviews panel to load more reviews.
        Uses JavaScript to scroll the container.
        """
        if not scrollable_element:
            return False
        
        try:
            # Get current scroll height
            last_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", 
                scrollable_element
            )
            
            # Scroll to bottom
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight",
                scrollable_element
            )
            
            # Wait for new content to load
            time.sleep(scroll_pause + random.uniform(0, 0.5))
            
            # Check if new content loaded
            new_height = self.driver.execute_script(
                "return arguments[0].scrollHeight",
                scrollable_element
            )
            
            return new_height > last_height
        except Exception as e:
            print(f"Scroll error: {e}")
            return False
    
    def _click_reviews_tab(self) -> bool:
        """Click on the Reviews tab to show reviews."""
        for selector in self.SELECTORS["reviews_tab"]:
            try:
                tab = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                tab.click()
                time.sleep(3)  # Wait for reviews to load
                return True
            except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
                continue
        return False
    
    def _parse_relative_date(self, date_str: str) -> str:
        """
        Return the date string as-is.
        The UI code handles "X days ago" format already.
        """
        if not date_str:
            return ""
        return date_str.strip()
    
    def _extract_review_data(self, review_element, idx: int) -> Optional[Dict]:
        """
        Extract all data from a single review card.
        Returns None if extraction fails or review is invalid.
        """
        try:
            # Try to expand truncated text first
            self._expand_review_text(review_element)
            
            # Extract reviewer name
            name = self._extract_text(review_element, self.SELECTORS["reviewer_name"])
            
            # Extract date
            date = self._extract_text(review_element, self.SELECTORS["date"])
            
            # Extract star rating
            rating = self._extract_rating(review_element)
            
            # Extract review text (try expanded first, then truncated)
            text = ""
            # First try to get the expanded/full text
            for selector in [".//span[@jsname='fbQN7e']", ".//span[contains(@class, 'wiI7pd')]"]:
                try:
                    elem = review_element.find_element(By.XPATH, selector)
                    t = elem.text.strip()
                    if t and len(t) > len(text):
                        text = t
                except:
                    continue
            
            # Fallback to general text selectors
            if not text:
                text = self._extract_text(review_element, self.SELECTORS["review_text"])
            
            # Validate - must have meaningful text
            if not text or len(text) < 10:
                return None
            
            return {
                'name': name,
                'date': self._parse_relative_date(date),
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
        """
        Scrape reviews from Google Maps restaurant page.
        
        Args:
            url: Google Maps restaurant URL
            max_reviews: Maximum number of reviews to scrape
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dict with reviews data in same format as OpenTable scraper
        """
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
            self.driver.get(url)
            time.sleep(5)  # Wait for initial page load
            
            # Click Reviews tab
            self._log_progress("📋 Looking for Reviews tab...", progress_callback)
            if not self._click_reviews_tab():
                self._log_progress("⚠️  Could not find Reviews tab, trying to scroll anyway...", progress_callback)
            
            time.sleep(3)
            
            # Find scrollable container
            scrollable = self._get_scrollable_element()
            if not scrollable:
                self._log_progress("⚠️  Could not find scrollable reviews container", progress_callback)
            
            # Initialize data containers
            names = []
            dates = []
            ratings = []
            review_texts = []
            
            processed_ids = set()  # Track processed reviews to avoid duplicates
            scroll_count = 0
            no_new_reviews_count = 0
            max_no_new = 5  # Stop after 5 scrolls with no new reviews
            
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
                
                # Process each review card
                for idx, review_elem in enumerate(review_elements):
                    # Check if we've reached the limit
                    if max_reviews and len(review_texts) >= max_reviews:
                        break
                    
                    # Create unique identifier for this review
                    try:
                        review_id = review_elem.get_attribute('data-review-id')
                        if not review_id:
                            # Fallback: use element position
                            review_id = f"pos_{idx}_{review_elem.location['y']}"
                    except:
                        review_id = f"idx_{idx}_{scroll_count}"
                    
                    # Skip if already processed
                    if review_id in processed_ids:
                        continue
                    
                    # Extract review data
                    review_data = self._extract_review_data(review_elem, idx)
                    
                    if review_data:
                        # Additional check: avoid duplicate text
                        if review_data['text'] not in review_texts:
                            names.append(review_data['name'])
                            dates.append(review_data['date'])
                            ratings.append(review_data['rating'])
                            review_texts.append(review_data['text'])
                            new_reviews_this_scroll += 1
                    
                    processed_ids.add(review_id)
                    
                    # Small delay between processing reviews
                    if idx % 5 == 0:
                        self._random_delay(0.1, 0.3)
                
                # Check if we got new reviews
                if new_reviews_this_scroll == 0:
                    no_new_reviews_count += 1
                else:
                    no_new_reviews_count = 0
                
                # Check if we've reached the target
                if max_reviews and len(review_texts) >= max_reviews:
                    self._log_progress(f"🎯 Reached target: {max_reviews} reviews", progress_callback)
                    break
                
                # Scroll for more reviews
                if scrollable:
                    self._scroll_reviews(scrollable)
                else:
                    # Fallback: scroll the page
                    self.driver.execute_script("window.scrollBy(0, 500);")
                    time.sleep(1.5)
            
            self._cleanup()
            
            # Trim to max_reviews if needed
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
                    # Google Maps doesn't have sub-ratings, fill with zeros
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
        """Log progress with emoji indicators."""
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
        (same format as OpenTable scraper for compatibility)
    """
    scraper = GoogleMapsScraper(headless=headless, chromedriver_path=chromedriver_path)
    return scraper.scrape_reviews(url, max_reviews=max_reviews)


if __name__ == "__main__":
    print("=" * 80)
    print("🗺️  Google Maps Review Scraper - Production Test (Nov 2025)")
    print("=" * 80 + "\n")
    
    # Test URL - Tutto Italian Restaurant & Bar
    test_url = "https://www.google.com/maps/place/Tutto+Italian+Restaurant+%26+Bar"
    
    print(f"🎯 Target: {test_url}")
    print("📊 Limit: 20 reviews (test mode)")
    print("🤖 Mode: HEADLESS\n")
    
    result = scrape_google_maps(test_url, max_reviews=20, headless=True)
    
    print("\n" + "=" * 80)
    if result['success']:
        print("✅ SUCCESS!")
        print(f"   📊 Total reviews scraped: {result['total_reviews']}")
        print(f"   📜 Scroll iterations: {result.get('total_pages', 'N/A')}")
        
        if result['total_reviews'] > 0:
            print(f"\n   🔍 Sample (first review):")
            print(f"   👤 Name: {result['reviews']['names'][0]}")
            print(f"   📅 Date: {result['reviews']['dates'][0]}")
            print(f"   ⭐ Rating: {result['reviews']['overall_ratings'][0]}")
            text = result['reviews']['review_texts'][0]
            print(f"   💬 Review: {text[:150]}{'...' if len(text) > 150 else ''}")
            
            print(f"\n   📊 Rating distribution:")
            ratings = result['reviews']['overall_ratings']
            for star in range(5, 0, -1):
                count = ratings.count(float(star))
                print(f"   {'⭐' * star}: {count} reviews")
    else:
        print("❌ FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    print("=" * 80)