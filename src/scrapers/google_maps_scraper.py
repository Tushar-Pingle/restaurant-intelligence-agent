"""
Google Maps Review Scraper - VERIFIED SELECTORS VERSION
Based on confirmed DOM structure research (Nov 2024).

VERIFIED SELECTORS:
- Reviews tab: button.hh2c6.G7m0Af with aria-label="Reviews"
- Scroll container: div.m6QErb.DxyBCb with role="feed"
- Review card: div.jftiEf.fontBodyMedium with data-review-id
- Review text: span.wiI7pd
- More button: button.w8nwRe.kyuRq

NO RETRY DELAYS - keep it simple like the OpenTable scraper that works.
"""

import time
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
    Google Maps review scraper with VERIFIED selectors.
    """
    
    # VERIFIED selectors from DOM research
    SELECTORS = {
        # Reviews tab button
        "reviews_tab": [
            "//button[@aria-label='Reviews']",
            "//button[contains(@class, 'hh2c6')]",
            "//button[@data-tab-index='1']",
            "//div[@role='tablist']//button[contains(., 'Review')]",
        ],
        
        # Scrollable container - VERIFIED: div with role="feed"
        "scroll_container": [
            "//div[@role='feed']",
            "//div[contains(@class, 'm6QErb') and contains(@class, 'DxyBCb')]",
            "//div[contains(@class, 'm6QErb')][@tabindex='-1']",
        ],
        
        # Individual review cards - VERIFIED: div.jftiEf with data-review-id
        "review_cards": [
            "//div[@data-review-id]",
            "//div[contains(@class, 'jftiEf')]",
            "//div[contains(@class, 'jftiEf') and contains(@class, 'fontBodyMedium')]",
        ],
        
        # Review text - VERIFIED: span.wiI7pd
        "review_text": [
            ".//span[@class='wiI7pd']",
            ".//span[contains(@class, 'wiI7pd')]",
            ".//div[contains(@class, 'MyEned')]//span",
        ],
        
        # "More" button to expand text - VERIFIED: button.w8nwRe
        "more_button": [
            ".//button[contains(@class, 'w8nwRe')]",
            ".//button[@aria-expanded='false']",
            ".//button[contains(text(), 'More')]",
        ],
        
        # Rating - span.kvMYJc or aria-label with stars
        "rating": [
            ".//span[contains(@class, 'kvMYJc')]",
            ".//span[contains(@aria-label, 'star')]",
        ],
        
        # Date - span.rsqaWe
        "date": [
            ".//span[contains(@class, 'rsqaWe')]",
            ".//span[contains(text(), 'ago')]",
        ],
        
        # Reviewer name - div.d4r55
        "reviewer_name": [
            ".//div[contains(@class, 'd4r55')]",
            ".//button[contains(@class, 'WEBjve')]//div",
        ],
    }
    
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
        Scrape reviews from Google Maps.
        """
        if not self._validate_url(url):
            return {'success': False, 'error': 'Invalid Google Maps URL', 'reviews': [], 'total_reviews': 0}
        
        try:
            self._init_driver()
        except Exception as e:
            return {'success': False, 'error': f'Browser init failed: {str(e)}', 'reviews': [], 'total_reviews': 0}
        
        reviews = []
        dates = []
        ratings = []
        names = []
        
        try:
            self._log("🚀 Starting Google Maps scraper...", progress_callback)
            self.driver.get(url)
            time.sleep(5)  # Wait for initial load
            
            # Handle consent dialog if it appears
            self._handle_consent_dialog()
            
            # Click on Reviews tab
            self._log("📋 Looking for Reviews tab...", progress_callback)
            if not self._click_reviews_tab(progress_callback):
                self._log("⚠️  Could not find Reviews tab, trying to scroll anyway...", progress_callback)
            
            time.sleep(3)  # Wait for reviews to load
            
            # Find scrollable container
            scroll_container = self._find_scroll_container(progress_callback)
            
            # Scroll and collect reviews
            collected_ids = set()
            no_new_count = 0
            scroll_count = 0
            max_scrolls = min(100, max(20, (max_reviews or 100) // 2))
            
            while len(reviews) < (max_reviews or 100) and scroll_count < max_scrolls:
                scroll_count += 1
                
                # Find review cards
                review_cards = self._find_review_cards()
                
                new_count = 0
                for card in review_cards:
                    try:
                        # Get unique ID
                        card_id = card.get_attribute('data-review-id')
                        if not card_id:
                            card_id = str(id(card))
                        
                        if card_id in collected_ids:
                            continue
                        
                        # Click "More" to expand if needed
                        self._expand_review(card)
                        
                        # Extract text
                        text = self._extract_text(card, self.SELECTORS["review_text"])
                        
                        if text and len(text.strip()) > 10:
                            collected_ids.add(card_id)
                            reviews.append(text)
                            dates.append(self._extract_text(card, self.SELECTORS["date"]))
                            ratings.append(self._extract_rating(card))
                            names.append(self._extract_text(card, self.SELECTORS["reviewer_name"]))
                            new_count += 1
                            
                            if len(reviews) >= (max_reviews or 100):
                                break
                    
                    except StaleElementReferenceException:
                        continue
                    except Exception:
                        continue
                
                self._log(f"📄 Scroll {scroll_count}: Found {len(review_cards)} review cards, collected {len(reviews)} unique reviews", progress_callback)
                
                if new_count == 0:
                    no_new_count += 1
                    if no_new_count >= 5:
                        self._log("📍 No new reviews after 5 scrolls, stopping", progress_callback)
                        break
                else:
                    no_new_count = 0
                
                # Scroll down
                self._scroll_down(scroll_container)
                time.sleep(1.5)
            
            self._log(f"✅ Scraped {len(reviews)} reviews from Google Maps", progress_callback)
            
            if len(reviews) == 0:
                return {
                    'success': False,
                    'error': 'No reviews found. Selectors may need updating.',
                    'reviews': {},
                    'total_reviews': 0
                }
            
            # Return NESTED format matching working version
            return {
                'success': True,
                'total_reviews': len(reviews),
                'total_pages': scroll_count,
                'reviews': {  # NESTED dict like working version
                    'names': names,
                    'dates': dates,
                    'overall_ratings': ratings,
                    'food_ratings': [0.0] * len(ratings),
                    'service_ratings': [0.0] * len(ratings),
                    'ambience_ratings': [0.0] * len(ratings),
                    'review_texts': reviews  # 'review_texts' not 'reviews'
                },
                'metadata': {
                    'source': 'google_maps',
                    'scroll_count': scroll_count
                }
            }
            
        except TimeoutException as e:
            return {'success': False, 'error': f'Page load timeout: {str(e)}', 'reviews': [], 'total_reviews': 0}
        except WebDriverException as e:
            return {'success': False, 'error': f'Browser error: {str(e)}', 'reviews': [], 'total_reviews': 0}
        except Exception as e:
            return {'success': False, 'error': f'Scraping error: {str(e)}', 'reviews': [], 'total_reviews': 0}
        finally:
            self._cleanup()
    
    def _handle_consent_dialog(self):
        """Handle Google consent/cookie dialog."""
        try:
            # Try various consent buttons
            for selector in ["//button[contains(., 'Accept')]", "//button[contains(., 'Reject all')]", "//form//button"]:
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
        """Click the Reviews tab."""
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
        
        # Fallback: look for any button containing "Review" text
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if 'review' in btn.text.lower():
                    btn.click()
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
                self._log("✅ Found scrollable container", progress_callback)
                return container
            except:
                continue
        
        self._log("⚠️  Could not find scrollable reviews container", progress_callback)
        return None
    
    def _find_review_cards(self) -> List:
        """Find all review cards."""
        for selector in self.SELECTORS["review_cards"]:
            try:
                cards = self.driver.find_elements(By.XPATH, selector)
                if cards:
                    return cards
            except:
                continue
        return []
    
    def _expand_review(self, card):
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
    
    def _extract_text(self, card, selectors: List[str]) -> str:
        """Extract text using fallback selectors."""
        for selector in selectors:
            try:
                elem = card.find_element(By.XPATH, selector)
                text = elem.text.strip()
                if text:
                    return text
            except:
                continue
        return ""
    
    def _extract_rating(self, card) -> float:
        """Extract star rating."""
        for selector in self.SELECTORS["rating"]:
            try:
                elem = card.find_element(By.XPATH, selector)
                # Try aria-label first
                aria = elem.get_attribute('aria-label') or ""
                for word in aria.split():
                    try:
                        return float(word)
                    except:
                        continue
                # Try text content
                text = elem.text
                for word in text.split():
                    try:
                        return float(word)
                    except:
                        continue
            except:
                continue
        return 0.0
    
    def _scroll_down(self, container):
        """Scroll down in the container."""
        try:
            if container:
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollTop + arguments[0].offsetHeight * 0.8",
                    container
                )
            else:
                ActionChains(self.driver).send_keys(Keys.PAGE_DOWN).perform()
        except:
            ActionChains(self.driver).send_keys(Keys.PAGE_DOWN).perform()
    
    def _init_driver(self):
        """Initialize Chrome - SIMPLE settings like OpenTable."""
        chrome_options = Options()
        chrome_options.page_load_strategy = 'eager'  # Fast like OpenTable
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
        
        # User agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        
        # Anti-detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service('/usr/local/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 10)
        
        # Anti-detection CDP command (from working version)
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
    Scrape reviews from Google Maps.
    """
    scraper = GoogleMapsScraper(headless=headless)
    return scraper.scrape_reviews(url, max_reviews)


if __name__ == "__main__":
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