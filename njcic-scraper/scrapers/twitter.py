"""
Twitter/X scraper implementation using Playwright with authentication.
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    PlaywrightTimeout = Exception

try:
    from playwright_stealth.stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    Stealth = None

from .base import BaseScraper


class TwitterScraper(BaseScraper):
    """Scraper for Twitter/X platform using Playwright with authentication."""

    platform_name = "twitter"

    def __init__(self, output_dir: str = "output", max_posts: int = 25, headless: bool = True):
        """
        Initialize Twitter scraper.

        Args:
            output_dir: Base directory for storing scraped data
            max_posts: Maximum number of posts to scrape (default: 25)
            headless: Whether to run browser in headless mode
        """
        super().__init__(Path(output_dir) if isinstance(output_dir, str) else output_dir)
        self.max_posts = max_posts
        self.headless = headless
        self.username = os.getenv('TWITTER_USERNAME')
        self.password = os.getenv('TWITTER_PASSWORD')

        # Cookie persistence
        self.cookies_dir = self.output_dir / '.cookies'
        self.cookies_dir.mkdir(exist_ok=True, parents=True)
        self.cookies_file = self.cookies_dir / 'twitter_cookies.json'

        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            )

        if not STEALTH_AVAILABLE:
            self.logger.warning(
                "playwright-stealth not installed. Install with: pip install playwright-stealth"
            )

    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract username from Twitter/X URL.

        Handles:
        - twitter.com/username
        - x.com/username
        - twitter.com/username/status/...
        - x.com/username/status/...

        Args:
            url: Twitter/X URL

        Returns:
            Extracted username or None if invalid
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if not any(d in domain for d in ['twitter.com', 'x.com']):
                self.logger.error(f"Invalid Twitter/X URL: {url}")
                return None

            path = parsed.path.strip('/')
            if not path:
                return None

            parts = path.split('/')
            username = parts[0].lstrip('@')

            if not re.match(r'^[A-Za-z0-9_]{1,15}$', username):
                self.logger.error(f"Invalid username format: {username}")
                return None

            return username

        except Exception as e:
            self.logger.error(f"Error extracting username from {url}: {e}")
            return None

    def _create_output_directory(self, grantee_name: str, username: str) -> Path:
        """Create and return Twitter-specific output directory."""
        base_path = self.get_output_path(grantee_name)
        username_path = base_path / username
        username_path.mkdir(exist_ok=True, parents=True)
        return username_path

    async def _save_cookies(self, context) -> None:
        """Save browser cookies to file for session persistence."""
        try:
            cookies = await context.cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            self.logger.info(f"Saved {len(cookies)} cookies to {self.cookies_file}")
        except Exception as e:
            self.logger.warning(f"Failed to save cookies: {e}")

    async def _load_cookies(self, context) -> bool:
        """Load saved cookies into browser context."""
        try:
            if not self.cookies_file.exists():
                self.logger.info("No saved cookies found")
                return False

            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)

            if not cookies:
                self.logger.info("No cookies to load")
                return False

            await context.add_cookies(cookies)
            self.logger.info(f"Loaded {len(cookies)} cookies from {self.cookies_file}")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to load cookies: {e}")
            return False

    async def _retry_with_backoff(self, func, max_retries: int = 3, initial_delay: float = 1.0):
        """
        Retry a function with exponential backoff.

        Args:
            func: Async function to retry
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds

        Returns:
            Result of the function call

        Raises:
            Last exception if all retries fail
        """
        delay = initial_delay
        last_exception = None

        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    self.logger.error(f"All {max_retries} attempts failed")

        raise last_exception

    async def _check_login_status(self, page) -> bool:
        """
        Check if already logged in by looking for authenticated user elements.

        Args:
            page: Playwright page object

        Returns:
            True if already logged in, False otherwise
        """
        try:
            await page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)

            # Check for logged-in indicators
            primary_column = await page.query_selector('[data-testid="primaryColumn"]')
            if primary_column:
                self.logger.info("Already logged in via saved cookies!")
                return True

            return False
        except Exception as e:
            self.logger.debug(f"Login check failed: {e}")
            return False

    async def _login(self, page) -> bool:
        """
        Log in to Twitter/X with improved security challenge handling.

        Args:
            page: Playwright page object

        Returns:
            True if login successful, False otherwise
        """
        if not self.username or not self.password:
            self.logger.warning("Twitter credentials not configured in environment")
            return False

        try:
            self.logger.info("Navigating to Twitter login...")
            await page.goto('https://x.com/i/flow/login', wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)

            # Enter username
            self.logger.info("Entering username...")
            username_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[type="text"]'
            ]

            username_input = None
            for selector in username_selectors:
                try:
                    username_input = await page.wait_for_selector(selector, timeout=5000)
                    if username_input:
                        break
                except PlaywrightTimeout:
                    continue

            if not username_input:
                self.logger.error("Could not find username input field")
                return False

            await username_input.fill(self.username)
            await page.wait_for_timeout(1000)

            # Click Next button with multiple selector attempts
            next_button_selectors = [
                '[role="button"]:has-text("Next")',
                'button:has-text("Next")',
                '[data-testid="ocfEnterTextNextButton"]'
            ]

            clicked = False
            for selector in next_button_selectors:
                try:
                    next_button = await page.query_selector(selector)
                    if next_button:
                        await next_button.click()
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                await page.keyboard.press('Enter')

            await page.wait_for_timeout(3000)

            # Handle various security challenges
            await self._handle_security_challenges(page)

            # Enter password with multiple selectors
            self.logger.info("Entering password...")
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="current-password"]'
            ]

            password_input = None
            for selector in password_selectors:
                try:
                    password_input = await page.wait_for_selector(selector, timeout=10000)
                    if password_input:
                        break
                except PlaywrightTimeout:
                    continue

            if not password_input:
                self.logger.error("Could not find password input field - may be blocked by security challenge")
                return False

            await password_input.fill(self.password)
            await page.wait_for_timeout(1000)

            # Click Log in button
            login_button_selectors = [
                '[role="button"]:has-text("Log in")',
                'button:has-text("Log in")',
                '[data-testid="LoginForm_Login_Button"]'
            ]

            clicked = False
            for selector in login_button_selectors:
                try:
                    login_button = await page.query_selector(selector)
                    if login_button:
                        await login_button.click()
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                await page.keyboard.press('Enter')

            await page.wait_for_timeout(5000)

            # Verify login succeeded by checking for home timeline or profile elements
            try:
                await page.wait_for_selector('[data-testid="primaryColumn"]', timeout=15000)
                self.logger.info("Login successful!")
                return True
            except PlaywrightTimeout:
                # Check if there's an error message
                error_texts = await page.query_selector_all('span[data-testid="error-detail"]')
                if error_texts:
                    error_msg = await error_texts[0].inner_text()
                    self.logger.error(f"Login failed with error: {error_msg}")
                else:
                    self.logger.error("Login verification failed - could not find main content")
                return False

        except Exception as e:
            self.logger.error(f"Login failed with exception: {e}", exc_info=True)
            return False

    async def _handle_security_challenges(self, page) -> None:
        """
        Handle various security challenges during login.

        Args:
            page: Playwright page object
        """
        # Check for unusual activity prompt (may ask for email/phone/username verification)
        try:
            unusual_selectors = [
                'input[data-testid="ocfEnterTextTextInput"]',
                'input[name="text"]:not([autocomplete])',
                'input[data-testid="ocfEnterTextTextInput"]'
            ]

            for selector in unusual_selectors:
                unusual_prompt = await page.query_selector(selector)
                if unusual_prompt:
                    self.logger.warning("Detected security challenge - attempting to handle...")

                    # Check what type of verification is requested
                    page_text = await page.inner_text('body')

                    if 'phone' in page_text.lower():
                        self.logger.error("Phone verification required - not implemented")
                        phone = os.getenv('TWITTER_PHONE')
                        if phone:
                            await unusual_prompt.fill(phone)
                        else:
                            self.logger.error("TWITTER_PHONE not set in environment")
                            return

                    elif 'email' in page_text.lower():
                        self.logger.warning("Email verification requested")
                        email = os.getenv('TWITTER_EMAIL')
                        if email:
                            await unusual_prompt.fill(email)
                        else:
                            # Try username as fallback
                            await unusual_prompt.fill(self.username)

                    else:
                        # Default to username
                        self.logger.info("Attempting username verification...")
                        await unusual_prompt.fill(self.username)

                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(3000)
                    break

        except Exception as e:
            self.logger.debug(f"No security challenge detected or error handling it: {e}")

    async def _extract_tweets(self, page) -> List[Dict[str, Any]]:
        """
        Extract tweets from the current page with fallback selectors.

        Args:
            page: Playwright page object

        Returns:
            List of tweet data dictionaries
        """
        tweets = []

        try:
            # Try multiple selectors for tweets with fallbacks
            tweet_article_selectors = [
                'article[data-testid="tweet"]',
                'article[role="article"]',
                '[data-testid="cellInnerDiv"] article'
            ]

            tweet_elements = None
            for selector in tweet_article_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=15000)
                    tweet_elements = await page.query_selector_all(selector)
                    if tweet_elements:
                        self.logger.info(f"Found {len(tweet_elements)} tweets using selector: {selector}")
                        break
                except PlaywrightTimeout:
                    continue

            if not tweet_elements:
                self.logger.error("Could not find any tweets on the page")
                return tweets

            # Extract data from each tweet
            for i, tweet_el in enumerate(tweet_elements[:self.max_posts]):
                try:
                    tweet_data = {}

                    # Extract text with fallback selectors
                    text_selectors = [
                        '[data-testid="tweetText"]',
                        '[lang] span',
                        'div[dir="auto"]'
                    ]

                    text_found = False
                    for text_selector in text_selectors:
                        text_el = await tweet_el.query_selector(text_selector)
                        if text_el:
                            tweet_data['text'] = await text_el.inner_text()
                            text_found = True
                            break

                    if not text_found:
                        tweet_data['text'] = ''

                    # Extract engagement metrics with fallbacks
                    # Likes
                    like_selectors = [
                        '[data-testid="like"] span',
                        '[aria-label*="like"] span',
                        '[data-testid="like"]'
                    ]
                    tweet_data['likes'] = await self._extract_metric(tweet_el, like_selectors)

                    # Retweets
                    retweet_selectors = [
                        '[data-testid="retweet"] span',
                        '[aria-label*="repost"] span',
                        '[aria-label*="retweet"] span'
                    ]
                    tweet_data['retweets'] = await self._extract_metric(tweet_el, retweet_selectors)

                    # Replies
                    reply_selectors = [
                        '[data-testid="reply"] span',
                        '[aria-label*="repl"] span'
                    ]
                    tweet_data['replies'] = await self._extract_metric(tweet_el, reply_selectors)

                    # Views (if available) - with multiple fallbacks
                    view_selectors = [
                        '[data-testid="app-text-transition-container"] span',
                        'a[href*="/analytics"] span',
                        '[aria-label*="view"] span'
                    ]
                    tweet_data['views'] = await self._extract_metric(tweet_el, view_selectors)

                    # Extract time/date
                    time_el = await tweet_el.query_selector('time')
                    if time_el:
                        tweet_data['date'] = await time_el.get_attribute('datetime')
                    else:
                        tweet_data['date'] = None

                    # Only add tweet if we got at least some data
                    if tweet_data.get('text') or any([
                        tweet_data.get('likes', 0) > 0,
                        tweet_data.get('retweets', 0) > 0,
                        tweet_data.get('replies', 0) > 0
                    ]):
                        tweets.append(tweet_data)
                        self.logger.debug(f"Extracted tweet {i+1}: {tweet_data.get('text', '')[:50]}...")
                    else:
                        self.logger.debug(f"Skipping tweet {i+1} - insufficient data")

                except Exception as e:
                    self.logger.warning(f"Error extracting tweet {i+1}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error during tweet extraction: {e}", exc_info=True)

        self.logger.info(f"Successfully extracted {len(tweets)} tweets")
        return tweets

    async def _extract_metric(self, element, selectors: List[str]) -> int:
        """
        Extract a metric value from an element using fallback selectors.

        Args:
            element: Playwright element to search within
            selectors: List of selectors to try

        Returns:
            Parsed metric value (int)
        """
        for selector in selectors:
            try:
                metric_el = await element.query_selector(selector)
                if metric_el:
                    text = await metric_el.inner_text()
                    value = self._parse_count(text)
                    if value > 0 or text.strip() == '0':
                        return value
            except Exception:
                continue
        return 0

    def _parse_count(self, text: str) -> int:
        """Parse engagement count from text (handles K, M suffixes)."""
        if not text or text.strip() == '':
            return 0
        text = text.strip().upper()
        try:
            if 'K' in text:
                return int(float(text.replace('K', '')) * 1000)
            elif 'M' in text:
                return int(float(text.replace('M', '')) * 1000000)
            else:
                return int(text.replace(',', ''))
        except (ValueError, AttributeError):
            return 0

    async def _extract_follower_count(self, page) -> Optional[int]:
        """Extract follower count from profile page."""
        try:
            # Look for followers link/count
            followers_el = await page.query_selector('a[href$="/verified_followers"] span, a[href$="/followers"] span')
            if followers_el:
                text = await followers_el.inner_text()
                return self._parse_count(text)
        except Exception as e:
            self.logger.warning(f"Could not extract follower count: {e}")
        return None

    async def _scrape_async(self, url: str, username: str, grantee_name: str) -> Dict[str, Any]:
        """
        Async scraping implementation using Playwright with stealth and cookie persistence.

        Args:
            url: Twitter profile URL
            username: Extracted username
            grantee_name: Grantee name

        Returns:
            Scraping results dictionary
        """
        errors = []
        tweets = []
        engagement_metrics = {
            'username': username,
            'followers_count': None,
            'total_likes': 0,
            'total_retweets': 0,
            'total_replies': 0,
            'total_views': 0,
            'avg_likes': 0.0,
            'avg_retweets': 0.0,
            'avg_engagement_rate': 0.0,
            'posts_analyzed': 0
        }

        async with async_playwright() as p:
            browser = None
            context = None
            try:
                # Launch browser with enhanced anti-detection
                self.logger.info("Launching browser with stealth mode...")
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-infobars',
                        '--window-size=1920,1080',
                        '--start-maximized',
                        '--disable-extensions',
                        '--disable-gpu'
                    ]
                )

                # Create context with realistic settings
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                    permissions=['geolocation'],
                    extra_http_headers={
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                )

                page = await context.new_page()

                # Apply stealth mode
                if STEALTH_AVAILABLE:
                    self.logger.info("Applying stealth mode to page...")
                    stealth_config = Stealth()
                    await stealth_config.apply_stealth_async(page)
                else:
                    self.logger.warning("Stealth mode not available - detection risk higher")

                # Try to load saved cookies
                cookies_loaded = await self._load_cookies(context)

                # Check if already logged in
                already_logged_in = False
                if cookies_loaded:
                    self.logger.info("Checking login status with saved cookies...")
                    already_logged_in = await self._check_login_status(page)

                # Login if not already authenticated
                if not already_logged_in:
                    self.logger.info("Not logged in - attempting authentication...")
                    login_success = await self._login(page)
                    if login_success:
                        # Save cookies after successful login
                        await self._save_cookies(context)
                    else:
                        errors.append("Failed to login to Twitter")
                        self.logger.warning("Continuing without authentication - data may be limited...")
                else:
                    self.logger.info("Using existing authentication session")

                # Navigate to profile with retry logic
                profile_url = f"https://x.com/{username}"
                self.logger.info(f"Navigating to profile: {profile_url}")

                async def navigate_to_profile():
                    await page.goto(profile_url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(3000)

                try:
                    await self._retry_with_backoff(navigate_to_profile, max_retries=3)
                except Exception as e:
                    self.logger.error(f"Failed to navigate to profile after retries: {e}")
                    errors.append(f"Navigation failed: {str(e)}")
                    raise

                # Extract follower count
                followers = await self._extract_follower_count(page)
                if followers:
                    engagement_metrics['followers_count'] = followers
                    self.logger.info(f"Follower count: {followers:,}")

                # Scroll to load more tweets with progressive loading
                self.logger.info("Loading tweets with progressive scrolling...")
                scroll_attempts = 5  # Increased from 3
                for i in range(scroll_attempts):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await page.wait_for_timeout(2000)
                    self.logger.debug(f"Scroll {i+1}/{scroll_attempts} completed")

                # Extract tweets with retry logic
                async def extract_tweets_wrapper():
                    return await self._extract_tweets(page)

                try:
                    tweets = await self._retry_with_backoff(extract_tweets_wrapper, max_retries=2)
                    self.logger.info(f"Successfully extracted {len(tweets)} tweets")
                except Exception as e:
                    self.logger.error(f"Failed to extract tweets: {e}")
                    errors.append(f"Tweet extraction failed: {str(e)}")
                    tweets = []

                # Calculate metrics
                if tweets:
                    total_likes = sum(t.get('likes', 0) for t in tweets)
                    total_retweets = sum(t.get('retweets', 0) for t in tweets)
                    total_replies = sum(t.get('replies', 0) for t in tweets)
                    total_views = sum(t.get('views', 0) for t in tweets)
                    num_tweets = len(tweets)

                    engagement_metrics.update({
                        'total_likes': total_likes,
                        'total_retweets': total_retweets,
                        'total_replies': total_replies,
                        'total_views': total_views,
                        'avg_likes': round(total_likes / num_tweets, 2) if num_tweets > 0 else 0,
                        'avg_retweets': round(total_retweets / num_tweets, 2) if num_tweets > 0 else 0,
                        'avg_engagement_rate': round(
                            ((total_likes + total_retweets + total_replies) / total_views * 100)
                            if total_views > 0 else 0, 2
                        ),
                        'posts_analyzed': num_tweets
                    })
                    self.logger.info(f"Engagement metrics calculated: {total_likes:,} likes, "
                                   f"{total_retweets:,} retweets, {total_replies:,} replies, "
                                   f"{total_views:,} views")

                # Save output
                output_dir = self._create_output_directory(grantee_name, username)

                # Save metadata
                metadata = {
                    'url': url,
                    'username': username,
                    'grantee_name': grantee_name,
                    'scraped_at': datetime.now().isoformat(),
                    'posts_downloaded': len(tweets),
                    'engagement_metrics': engagement_metrics,
                    'stealth_mode_enabled': STEALTH_AVAILABLE,
                    'authenticated': already_logged_in or (len(errors) == 0 or "Failed to login" not in str(errors))
                }
                self.save_metadata(output_dir, metadata)

                # Save tweets
                if tweets:
                    tweets_file = output_dir / 'tweets.json'
                    with open(tweets_file, 'w', encoding='utf-8') as f:
                        json.dump(tweets, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"Saved tweets to {tweets_file}")

                # Take screenshot
                try:
                    screenshot_path = output_dir / 'screenshot.png'
                    await page.screenshot(path=str(screenshot_path), full_page=False)
                    self.logger.info(f"Screenshot saved to {screenshot_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to save screenshot: {e}")

                # Success if we got follower count OR tweets
                success = len(tweets) > 0 or engagement_metrics.get('followers_count') is not None

                if success:
                    self.logger.info(f"✓ Scraping successful for @{username}")
                else:
                    self.logger.warning(f"⚠ Scraping completed with limited data for @{username}")

                return {
                    'success': success,
                    'posts_downloaded': len(tweets),
                    'errors': errors,
                    'engagement_metrics': engagement_metrics
                }

            except Exception as e:
                self.logger.error(f"Fatal error during scraping: {e}", exc_info=True)
                errors.append(str(e))
                return {
                    'success': False,
                    'posts_downloaded': 0,
                    'errors': errors,
                    'engagement_metrics': engagement_metrics
                }

            finally:
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass
                if browser:
                    try:
                        await browser.close()
                        self.logger.info("Browser closed successfully")
                    except Exception:
                        pass

    def scrape(self, url: str, grantee_name: str, max_posts: Optional[int] = None) -> Dict[str, Any]:
        """
        Scrape Twitter/X profile.

        Args:
            url: Twitter/X profile URL
            grantee_name: Name of the grantee
            max_posts: Maximum posts to scrape (uses self.max_posts if None)

        Returns:
            Dictionary containing scraping results
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': ['Playwright not installed'],
                'engagement_metrics': {}
            }

        # Extract username
        username = self.extract_username(url)
        if not username:
            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': ['Could not extract username from URL'],
                'engagement_metrics': {}
            }

        self.logger.info(f"Starting Twitter scrape for @{username}")

        # Run async scraping
        try:
            result = asyncio.run(self._scrape_async(url, username, grantee_name))
            return result
        except Exception as e:
            self.logger.error(f"Fatal error during scrape: {e}", exc_info=True)
            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': [f'Fatal error: {str(e)}'],
                'engagement_metrics': {}
            }


# Example usage
if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 3:
        print("Usage: python twitter.py <twitter_url> <grantee_name>")
        sys.exit(1)

    twitter_url = sys.argv[1]
    grantee_name = sys.argv[2]

    scraper = TwitterScraper(output_dir="output", max_posts=25)
    result = scraper.scrape(twitter_url, grantee_name)

    print("\n=== Scraping Results ===")
    print(f"Success: {result['success']}")
    print(f"Posts Downloaded: {result['posts_downloaded']}")
    print(f"Errors: {result['errors']}")
    print(f"\nEngagement Metrics:")
    for key, value in result.get('engagement_metrics', {}).items():
        print(f"  {key}: {value}")
