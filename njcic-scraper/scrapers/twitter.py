"""
Twitter/X scraper implementation using Playwright with authentication.
"""

import asyncio
import json
import os
import re
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

        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning(
                "Playwright not installed. Install with: pip install playwright && playwright install"
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

    async def _login(self, page) -> bool:
        """
        Log in to Twitter/X.

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
            await page.wait_for_timeout(2000)

            # Wait for page to fully load
            await page.wait_for_timeout(3000)

            # Enter username
            self.logger.info("Entering username...")
            username_input = await page.wait_for_selector('input[autocomplete="username"], input[name="text"]', timeout=15000)
            await username_input.fill(self.username)
            await page.wait_for_timeout(500)

            # Click Next button
            next_button = await page.query_selector('[role="button"]:has-text("Next"), button:has-text("Next")')
            if next_button:
                await next_button.click()
            else:
                await page.keyboard.press('Enter')
            await page.wait_for_timeout(3000)

            # Check for unusual activity prompt (may ask for email/phone/username verification)
            unusual_prompt = await page.query_selector('input[data-testid="ocfEnterTextTextInput"], input[name="text"]:not([autocomplete])')
            if unusual_prompt:
                self.logger.info("Handling unusual activity verification...")
                await unusual_prompt.fill(self.username)
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(2000)

            # Enter password
            self.logger.info("Entering password...")
            password_input = await page.wait_for_selector('input[name="password"], input[type="password"]', timeout=15000)
            await password_input.fill(self.password)
            await page.wait_for_timeout(500)

            # Click Log in button
            login_button = await page.query_selector('[role="button"]:has-text("Log in"), button:has-text("Log in")')
            if login_button:
                await login_button.click()
            else:
                await page.keyboard.press('Enter')
            await page.wait_for_timeout(5000)

            # Verify login succeeded by checking for home timeline or profile elements
            try:
                await page.wait_for_selector('[data-testid="primaryColumn"]', timeout=15000)
                self.logger.info("Login successful!")
                return True
            except PlaywrightTimeout:
                self.logger.error("Login verification failed - could not find main content")
                return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def _extract_tweets(self, page) -> List[Dict[str, Any]]:
        """
        Extract tweets from the current page.

        Args:
            page: Playwright page object

        Returns:
            List of tweet data dictionaries
        """
        tweets = []

        try:
            # Try multiple selectors for tweets
            await page.wait_for_selector('article[data-testid="tweet"], article[role="article"], [data-testid="cellInnerDiv"] article', timeout=15000)

            # Get all tweet articles
            tweet_elements = await page.query_selector_all('article[data-testid="tweet"]')

            for i, tweet_el in enumerate(tweet_elements[:self.max_posts]):
                try:
                    tweet_data = {}

                    # Extract text
                    text_el = await tweet_el.query_selector('[data-testid="tweetText"]')
                    if text_el:
                        tweet_data['text'] = await text_el.inner_text()
                    else:
                        tweet_data['text'] = ''

                    # Extract engagement metrics
                    # Likes
                    like_el = await tweet_el.query_selector('[data-testid="like"] span')
                    tweet_data['likes'] = self._parse_count(await like_el.inner_text() if like_el else '0')

                    # Retweets
                    retweet_el = await tweet_el.query_selector('[data-testid="retweet"] span')
                    tweet_data['retweets'] = self._parse_count(await retweet_el.inner_text() if retweet_el else '0')

                    # Replies
                    reply_el = await tweet_el.query_selector('[data-testid="reply"] span')
                    tweet_data['replies'] = self._parse_count(await reply_el.inner_text() if reply_el else '0')

                    # Views (if available)
                    view_el = await tweet_el.query_selector('[data-testid="app-text-transition-container"] span')
                    tweet_data['views'] = self._parse_count(await view_el.inner_text() if view_el else '0')

                    # Extract time/date
                    time_el = await tweet_el.query_selector('time')
                    if time_el:
                        tweet_data['date'] = await time_el.get_attribute('datetime')
                    else:
                        tweet_data['date'] = None

                    tweets.append(tweet_data)

                except Exception as e:
                    self.logger.warning(f"Error extracting tweet {i}: {e}")
                    continue

        except PlaywrightTimeout:
            self.logger.warning("Timeout waiting for tweets to load")
        except Exception as e:
            self.logger.error(f"Error extracting tweets: {e}")

        return tweets

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
        Async scraping implementation using Playwright.

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
            try:
                # Launch browser
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )

                # Create context
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York'
                )

                page = await context.new_page()

                # Login first
                login_success = await self._login(page)
                if not login_success:
                    errors.append("Failed to login to Twitter")
                    # Try without login anyway
                    self.logger.info("Attempting to scrape without login...")

                # Navigate to profile
                profile_url = f"https://x.com/{username}"
                self.logger.info(f"Navigating to {profile_url}")
                await page.goto(profile_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(3000)

                # Extract follower count
                followers = await self._extract_follower_count(page)
                if followers:
                    engagement_metrics['followers_count'] = followers
                    self.logger.info(f"Found {followers} followers")

                # Scroll to load more tweets
                self.logger.info("Scrolling to load tweets...")
                for _ in range(3):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await page.wait_for_timeout(2000)

                # Extract tweets
                tweets = await self._extract_tweets(page)
                self.logger.info(f"Extracted {len(tweets)} tweets")

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

                # Save output
                output_dir = self._create_output_directory(grantee_name, username)

                # Save metadata
                metadata = {
                    'url': url,
                    'username': username,
                    'grantee_name': grantee_name,
                    'scraped_at': datetime.now().isoformat(),
                    'posts_downloaded': len(tweets),
                    'engagement_metrics': engagement_metrics
                }
                self.save_metadata(output_dir, metadata)

                # Save tweets
                tweets_file = output_dir / 'tweets.json'
                with open(tweets_file, 'w', encoding='utf-8') as f:
                    json.dump(tweets, f, indent=2, ensure_ascii=False)

                # Take screenshot
                screenshot_path = output_dir / 'screenshot.png'
                await page.screenshot(path=str(screenshot_path), full_page=False)

                # Success if we got follower count OR tweets
                success = len(tweets) > 0 or engagement_metrics.get('followers_count') is not None
                return {
                    'success': success,
                    'posts_downloaded': len(tweets),
                    'errors': errors,
                    'engagement_metrics': engagement_metrics
                }

            except Exception as e:
                self.logger.error(f"Error during scraping: {e}")
                errors.append(str(e))
                return {
                    'success': False,
                    'posts_downloaded': 0,
                    'errors': errors,
                    'engagement_metrics': engagement_metrics
                }

            finally:
                if browser:
                    await browser.close()

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
