"""
Threads scraper using Playwright for browser automation.

Threads doesn't have a public API yet, so we use browser automation
to scrape posts. This implementation includes graceful fallbacks for
anti-bot measures and rate limiting.

Supports authentication via INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD
environment variables (Threads uses Instagram/Meta login).
"""
from __future__ import annotations

import os
import re
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    PlaywrightTimeout = Exception

from dotenv import load_dotenv
from .base import BaseScraper

# Load environment variables
load_dotenv()


class ThreadsScraper(BaseScraper):
    """Scraper for Threads posts using Playwright browser automation."""

    platform_name = "threads"

    def __init__(self, output_dir: str = "output", headless: bool = True, timeout: int = 30000):
        """
        Initialize Threads scraper.

        Args:
            output_dir: Base directory for storing scraped data
            headless: Whether to run browser in headless mode
            timeout: Page load timeout in milliseconds
        """
        super().__init__(Path(output_dir) if isinstance(output_dir, str) else output_dir)
        self.headless = headless
        self.timeout = timeout
        self.max_posts = 25  # Threads specific limit as per requirements
        self.username = os.getenv('INSTAGRAM_USERNAME')
        self.password = os.getenv('INSTAGRAM_PASSWORD')
        self._logged_in = False

        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            )

    async def _login(self, page) -> bool:
        """
        Log in to Threads using Instagram credentials.

        Threads uses Meta/Instagram login, so we authenticate via Instagram.

        Args:
            page: Playwright page object

        Returns:
            True if login successful, False otherwise
        """
        if not self.username or not self.password:
            self.logger.warning("Instagram credentials not found in environment variables")
            return False

        try:
            self.logger.info("Attempting Threads login via Instagram...")

            # Navigate to Threads login page
            await page.goto('https://www.threads.net/login', timeout=self.timeout)
            await asyncio.sleep(3)

            # Look for "Log in with Instagram" button or direct login form
            # Threads may show different login flows
            ig_login_btn = await page.query_selector('text="Log in with Instagram"')
            if ig_login_btn:
                await ig_login_btn.click()
                await asyncio.sleep(3)

            # Try to find login form (may be on same page or redirected)
            username_input = await page.query_selector('input[name="username"], input[aria-label*="username" i], input[type="text"]')
            password_input = await page.query_selector('input[name="password"], input[aria-label*="password" i], input[type="password"]')

            if not username_input or not password_input:
                # May need to click "Log in" first
                login_link = await page.query_selector('text="Log in"')
                if login_link:
                    await login_link.click()
                    await asyncio.sleep(2)
                    username_input = await page.query_selector('input[name="username"], input[type="text"]')
                    password_input = await page.query_selector('input[type="password"]')

            if not username_input or not password_input:
                self.logger.error("Could not find login form fields")
                return False

            # Fill credentials
            await username_input.fill(self.username)
            await asyncio.sleep(0.5)
            await password_input.fill(self.password)
            await asyncio.sleep(0.5)

            # Submit form
            submit_btn = await page.query_selector('button[type="submit"], button:has-text("Log in")')
            if submit_btn:
                await submit_btn.click()
            else:
                await page.keyboard.press('Enter')

            # Wait for navigation
            await asyncio.sleep(5)

            # Check if login was successful
            current_url = page.url
            if ('threads.net' in current_url or 'threads.com' in current_url) and 'login' not in current_url:
                self.logger.info("Threads login successful")
                self._logged_in = True
                return True

            # Check for security challenge
            if 'challenge' in current_url or 'checkpoint' in current_url:
                self.logger.warning("Security challenge detected - manual intervention may be required")
                return False

            self.logger.warning(f"Login status unclear, current URL: {current_url}")
            return False

        except Exception as e:
            self.logger.error(f"Error during login: {e}")
            return False

    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract username from Threads URL.

        Handles patterns:
        - threads.net/@username
        - threads.net/username
        - www.threads.net/@username
        - www.threads.net/username

        Args:
            url: Threads profile URL

        Returns:
            Extracted username (without @) or None if invalid
        """
        if not url or not isinstance(url, str):
            return None

        # Clean up the URL
        url = url.strip()

        # Patterns for Threads URLs (handles both .net and .com)
        patterns = [
            r'threads\.(?:net|com)/@([^/?&#]+)',  # threads.net/@username or threads.com/@username
            r'threads\.(?:net|com)/([^/@?&#]+)',  # threads.net/username or threads.com/username
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                username = match.group(1).strip()
                # Filter out non-username paths
                if username and username not in ['explore', 'settings', 'activity', 'search']:
                    return username

        return None

    def _create_output_directory(self, grantee_name: str, username: str) -> Path:
        """
        Create and return Threads-specific output directory.

        Creates structure: output/threads/{grantee_name}/{username}

        Args:
            grantee_name: Name of the grantee
            username: Threads username

        Returns:
            Path object for the output directory
        """
        # Get base output path from parent class
        base_path = self.get_output_path(grantee_name)

        # Add username subdirectory
        username_path = base_path / username
        username_path.mkdir(exist_ok=True, parents=True)

        return username_path

    async def _wait_for_page_load(self, page, selector: str = 'article', max_wait: int = 10):
        """
        Wait for page to load with progressive timeout.

        Args:
            page: Playwright page object
            selector: CSS selector to wait for
            max_wait: Maximum wait time in seconds
        """
        try:
            await page.wait_for_selector(selector, timeout=max_wait * 1000)
        except PlaywrightTimeout:
            self.logger.warning(f"Timeout waiting for selector: {selector}")

    async def _scroll_to_load_posts(self, page, target_posts: int = 25, max_scrolls: int = 10):
        """
        Scroll page to trigger lazy loading of posts.

        Args:
            page: Playwright page object
            target_posts: Target number of posts to load
            max_scrolls: Maximum scroll attempts

        Returns:
            Number of posts loaded
        """
        previous_height = 0
        scrolls = 0

        while scrolls < max_scrolls:
            # Scroll to bottom
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(2)  # Wait for content to load

            # Check current height
            current_height = await page.evaluate('document.body.scrollHeight')

            # Count visible articles (posts)
            post_count = await page.evaluate('document.querySelectorAll("article").length')

            self.logger.info(f"Loaded {post_count} posts (scroll {scrolls + 1}/{max_scrolls})")

            # Break if we have enough posts or page stopped growing
            if post_count >= target_posts or current_height == previous_height:
                break

            previous_height = current_height
            scrolls += 1

        return post_count

    async def _extract_post_data(self, page) -> List[Dict[str, Any]]:
        """
        Extract post data from the loaded page.

        Args:
            page: Playwright page object

        Returns:
            List of post dictionaries with metadata
        """
        posts = []

        try:
            # Extract posts using JavaScript in the browser context
            posts_data = await page.evaluate('''() => {
                const articles = document.querySelectorAll('article');
                const posts = [];

                articles.forEach((article, index) => {
                    try {
                        // Extract post text - Threads uses various div structures
                        const textElements = article.querySelectorAll('[dir="auto"]');
                        let postText = '';
                        textElements.forEach(el => {
                            const text = el.textContent?.trim();
                            if (text && text.length > postText.length) {
                                postText = text;
                            }
                        });

                        // Extract timestamp - look for time elements
                        const timeElement = article.querySelector('time');
                        const timestamp = timeElement?.getAttribute('datetime') ||
                                        timeElement?.textContent ||
                                        new Date().toISOString();

                        // Extract engagement metrics
                        // Threads shows these as text like "123 likes" or "45 replies"
                        const allText = article.textContent || '';

                        // Try to find likes (matches "X likes", "1 like")
                        const likesMatch = allText.match(/(\\d+)\\s+like/i);
                        const likes = likesMatch ? parseInt(likesMatch[1]) : 0;

                        // Try to find replies (matches "X replies", "1 reply")
                        const repliesMatch = allText.match(/(\\d+)\\s+repl(?:y|ies)/i);
                        const replies = repliesMatch ? parseInt(repliesMatch[1]) : 0;

                        // Try to find reposts/quotes
                        const repostsMatch = allText.match(/(\\d+)\\s+(?:repost|quote)/i);
                        const reposts = repostsMatch ? parseInt(repostsMatch[1]) : 0;

                        // Get post URL if available
                        const linkElement = article.querySelector('a[href*="/post/"]');
                        const postUrl = linkElement?.href || '';

                        posts.push({
                            index: index,
                            text: postText || '[No text content]',
                            timestamp: timestamp,
                            likes: likes,
                            replies: replies,
                            reposts: reposts,
                            url: postUrl,
                            raw_html_length: article.innerHTML?.length || 0
                        });
                    } catch (err) {
                        console.error('Error extracting post:', err);
                    }
                });

                return posts;
            }''')

            posts = posts_data if posts_data else []

        except Exception as e:
            self.logger.error(f"Error extracting post data: {e}")

        return posts

    async def _extract_follower_count(self, page) -> int:
        """
        Extract follower count from profile page.

        Args:
            page: Playwright page object

        Returns:
            Follower count (0 if not found)
        """
        try:
            # Threads shows followers in the format "X followers"
            followers_text = await page.evaluate('''() => {
                const text = document.body.textContent || '';
                const match = text.match(/([\\d,\\.]+[KMB]?)\\s+followers/i);
                return match ? match[1] : '0';
            }''')

            # Convert text like "1.2K" to number
            followers_text = followers_text.replace(',', '')

            if 'K' in followers_text.upper():
                return int(float(followers_text.upper().replace('K', '')) * 1000)
            elif 'M' in followers_text.upper():
                return int(float(followers_text.upper().replace('M', '')) * 1000000)
            elif 'B' in followers_text.upper():
                return int(float(followers_text.upper().replace('B', '')) * 1000000000)
            else:
                return int(followers_text) if followers_text.isdigit() else 0

        except Exception as e:
            self.logger.warning(f"Could not extract follower count: {e}")
            return 0

    async def _scrape_async(self, url: str, username: str, output_dir: Path) -> Dict[str, Any]:
        """
        Async method to scrape Threads profile.

        Args:
            url: Threads profile URL
            username: Extracted username
            output_dir: Output directory for saving data

        Returns:
            Scraping result dictionary
        """
        result = {
            'success': False,
            'posts_downloaded': 0,
            'errors': [],
            'engagement_metrics': {
                'followers_count': 0,
                'total_likes': 0,
                'total_replies': 0,
                'total_reposts': 0,
                'avg_engagement_rate': 0.0
            }
        }

        async with async_playwright() as p:
            browser = None
            try:
                # Launch browser
                self.logger.info(f"Launching browser (headless={self.headless})...")
                browser = await p.chromium.launch(headless=self.headless)

                # Create context with realistic user agent
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )

                page = await context.new_page()

                # Attempt login if credentials are available
                if self.username and self.password:
                    if not await self._login(page):
                        self.logger.warning("Login failed, continuing without authentication")
                    else:
                        await asyncio.sleep(2)  # Brief pause after login

                # Construct profile URL
                profile_url = f"https://www.threads.net/@{username}" if not url.startswith('http') else url

                self.logger.info(f"Navigating to {profile_url}...")

                try:
                    await page.goto(profile_url, timeout=self.timeout, wait_until='domcontentloaded')
                except PlaywrightTimeout:
                    result['errors'].append(f"Timeout loading profile page: {profile_url}")
                    return result

                # Wait for content to load
                await self._wait_for_page_load(page)

                # Check if profile exists (look for error messages)
                page_text = await page.evaluate('document.body.textContent')
                if 'not found' in page_text.lower() or 'doesn\'t exist' in page_text.lower():
                    result['errors'].append(f"Profile @{username} not found")
                    return result

                # Extract follower count
                followers = await self._extract_follower_count(page)
                result['engagement_metrics']['followers_count'] = followers
                self.logger.info(f"Followers: {followers:,}")

                # Scroll to load posts
                self.logger.info(f"Scrolling to load up to {self.max_posts} posts...")
                posts_loaded = await self._scroll_to_load_posts(page, self.max_posts)

                if posts_loaded == 0:
                    result['errors'].append("No posts found on profile")
                    return result

                # Extract post data
                self.logger.info(f"Extracting data from {posts_loaded} posts...")
                posts = await self._extract_post_data(page)

                # Limit to max_posts
                posts = posts[:self.max_posts]

                if not posts:
                    result['errors'].append("Failed to extract post data")
                    return result

                # Calculate engagement metrics
                total_likes = sum(p.get('likes', 0) for p in posts)
                total_replies = sum(p.get('replies', 0) for p in posts)
                total_reposts = sum(p.get('reposts', 0) for p in posts)

                total_engagement = total_likes + total_replies + total_reposts
                avg_engagement_rate = (total_engagement / followers * 100) if followers > 0 else 0.0

                result['engagement_metrics'].update({
                    'total_likes': total_likes,
                    'total_replies': total_replies,
                    'total_reposts': total_reposts,
                    'avg_engagement_rate': round(avg_engagement_rate, 2)
                })

                # Save metadata
                metadata = {
                    'username': username,
                    'profile_url': profile_url,
                    'posts_count': len(posts),
                    'posts': posts,
                    'engagement_metrics': result['engagement_metrics'],
                    'scraped_at': datetime.now().isoformat()
                }

                self.save_metadata(output_dir, metadata)

                result['success'] = True
                result['posts_downloaded'] = len(posts)

                self.logger.info(f"Successfully scraped {len(posts)} posts from @{username}")
                self.logger.info(f"Engagement: {total_likes:,} likes, {total_replies:,} replies, {total_reposts:,} reposts")

            except Exception as e:
                error_msg = f"Error during scraping: {str(e)}"
                self.logger.exception(error_msg)
                result['errors'].append(error_msg)

            finally:
                if browser:
                    await browser.close()

        return result

    def scrape(self, url: str, grantee_name: str, max_posts: int = 25) -> Dict[str, Any]:
        """
        Scrape Threads profile content.

        Args:
            url: Threads profile URL
            grantee_name: Name of the grantee
            max_posts: Maximum posts to scrape

        Returns:
            Dictionary containing:
                - success (bool): Whether scraping was successful
                - posts_downloaded (int): Number of posts downloaded
                - errors (List[str]): List of errors encountered
                - engagement_metrics (Dict): Engagement metrics including:
                    - followers_count: Number of followers
                    - total_likes: Sum of likes across all posts
                    - total_replies: Sum of replies across all posts
                    - total_reposts: Sum of reposts across all posts
                    - avg_engagement_rate: Average engagement rate (%)
        """
        result = {
            'success': False,
            'posts_downloaded': 0,
            'errors': [],
            'engagement_metrics': {
                'followers_count': 0,
                'total_likes': 0,
                'total_replies': 0,
                'total_reposts': 0,
                'avg_engagement_rate': 0.0
            }
        }

        # Extract username
        username = self.extract_username(url)
        if not username:
            result['errors'].append(f"Could not extract username from URL: {url}")
            self.logger.error(result['errors'][-1])
            return result

        self.logger.info(f"Scraping Threads profile: @{username}")

        # Create output directory
        output_dir = self._create_output_directory(grantee_name, username)
        self.logger.info(f"Output directory: {output_dir}")

        # Run async scraper
        try:
            # Check if playwright is installed
            try:
                import playwright
            except ImportError:
                result['errors'].append(
                    "Playwright not installed. Install with: pip install playwright && playwright install chromium"
                )
                self.logger.error(result['errors'][-1])
                return result

            # Run async scraping
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._scrape_async(url, username, output_dir))
            finally:
                loop.close()

        except Exception as e:
            error_msg = f"Fatal error scraping Threads: {str(e)}"
            self.logger.exception(error_msg)
            result['errors'].append(error_msg)

        return result
