"""
LinkedIn scraper implementation.

Note: LinkedIn has strict anti-scraping measures. This scraper attempts
to collect publicly available information on a best-effort basis.
Supports optional authentication via LINKEDIN_EMAIL and LINKEDIN_PASSWORD
environment variables.
"""
from __future__ import annotations

import os
import re
import time
import random
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING
from urllib.parse import urlparse, unquote
from datetime import datetime

if TYPE_CHECKING:
    from playwright.sync_api import Page, Browser, BrowserContext

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    sync_playwright = None

from dotenv import load_dotenv
from .base import BaseScraper

# Load environment variables
load_dotenv()


class LinkedInScraper(BaseScraper):
    """
    Scraper for LinkedIn company and personal profile pages.

    Due to LinkedIn's strict anti-scraping policies, this scraper:
    - Only attempts to access public information
    - Uses realistic browser behavior
    - Implements rate limiting and timeouts
    - Gracefully handles access restrictions
    """

    platform_name = "linkedin"

    def __init__(self, output_dir: str = "output", headless: bool = True):
        """
        Initialize LinkedIn scraper.

        Args:
            output_dir: Directory to save scraped data
            headless: Whether to run browser in headless mode
        """
        super().__init__(Path(output_dir) if isinstance(output_dir, str) else output_dir)
        self.headless = headless
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        self._logged_in = False

        # Session persistence
        self.session_dir = self.output_dir / ".sessions" / "linkedin"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        if sync_playwright is None:
            raise ImportError(
                "Playwright is required for LinkedIn scraping. "
                "Install with: pip install playwright && playwright install chromium"
            )

    def _random_delay(self, min_seconds: float = 0.5, max_seconds: float = 2.5) -> None:
        """
        Add a random delay to simulate human behavior.

        Args:
            min_seconds: Minimum delay in seconds
            max_seconds: Maximum delay in seconds
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def _apply_stealth_techniques(self, page: Page) -> None:
        """
        Apply stealth techniques to avoid detection.
        Removes webdriver properties and adds realistic browser fingerprints.

        Args:
            page: Playwright page object
        """
        try:
            # Remove webdriver property and other automation indicators
            stealth_js = """
            () => {
                // Override the navigator.webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Override the plugins property
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Override the languages property
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });

                // Override Chrome property
                window.chrome = {
                    runtime: {}
                };

                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            }
            """
            page.add_init_script(stealth_js)
            self.logger.debug("Applied stealth techniques to page")
        except Exception as e:
            self.logger.warning(f"Could not apply stealth techniques: {e}")

    def _simulate_human_behavior(self, page: Page) -> None:
        """
        Simulate human-like browsing behavior with scrolling and mouse movements.

        Args:
            page: Playwright page object
        """
        try:
            # Random scrolling
            scroll_script = """
            (scrollDistance) => {
                window.scrollBy({
                    top: scrollDistance,
                    behavior: 'smooth'
                });
            }
            """

            # Scroll down in random increments
            for _ in range(random.randint(2, 4)):
                scroll_amount = random.randint(200, 500)
                page.evaluate(scroll_script, scroll_amount)
                self._random_delay(0.3, 0.8)

            # Scroll back up a bit
            page.evaluate(scroll_script, -random.randint(100, 300))
            self._random_delay(0.5, 1.0)

            # Random mouse movements
            for _ in range(random.randint(1, 3)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                page.mouse.move(x, y)
                self._random_delay(0.2, 0.5)

            self.logger.debug("Simulated human browsing behavior")
        except Exception as e:
            self.logger.warning(f"Could not simulate human behavior: {e}")

    def _save_session(self, context: BrowserContext, username: str) -> None:
        """
        Save browser session state for future use.

        Args:
            context: Playwright browser context
            username: Username identifier for the session
        """
        try:
            session_file = self.session_dir / f"{username}_state.json"
            context.storage_state(path=str(session_file))
            self.logger.info(f"Saved session state to {session_file}")
        except Exception as e:
            self.logger.warning(f"Could not save session: {e}")

    def _load_session(self, username: str) -> Optional[str]:
        """
        Load saved browser session state.

        Args:
            username: Username identifier for the session

        Returns:
            Path to session file if it exists and is recent, None otherwise
        """
        try:
            session_file = self.session_dir / f"{username}_state.json"
            if session_file.exists():
                # Check if session is less than 24 hours old
                file_age = time.time() - session_file.stat().st_mtime
                if file_age < 86400:  # 24 hours
                    self.logger.info(f"Loading session state from {session_file}")
                    return str(session_file)
                else:
                    self.logger.debug("Session file is too old, will create new session")
            return None
        except Exception as e:
            self.logger.warning(f"Could not load session: {e}")
            return None

    def _retry_with_backoff(self, func, max_retries: int = 3, *args, **kwargs) -> Any:
        """
        Retry a function with exponential backoff.

        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result if successful

        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {max_retries} attempts failed")

        raise last_exception

    def _login(self, page: Page) -> bool:
        """
        Log in to LinkedIn using credentials from environment variables.

        Args:
            page: Playwright page object

        Returns:
            True if login successful, False otherwise
        """
        if not self.email or not self.password:
            self.logger.warning("LinkedIn credentials not found in environment variables")
            return False

        try:
            self.logger.info("Attempting LinkedIn login...")

            # Navigate to login page
            page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded', timeout=30000)
            self._random_delay(1.5, 3.0)

            # Fill in credentials with human-like typing
            email_selectors = ['#username', 'input[name="session_key"]', 'input[autocomplete="username"]']
            password_selectors = ['#password', 'input[name="session_password"]', 'input[autocomplete="current-password"]']

            email_input = None
            for selector in email_selectors:
                email_input = page.query_selector(selector)
                if email_input:
                    break

            password_input = None
            for selector in password_selectors:
                password_input = page.query_selector(selector)
                if password_input:
                    break

            if not email_input or not password_input:
                self.logger.error("Could not find login form fields")
                return False

            # Type with realistic delays
            email_input.click()
            self._random_delay(0.3, 0.7)
            email_input.type(self.email, delay=random.randint(50, 150))
            self._random_delay(0.5, 1.0)

            password_input.click()
            self._random_delay(0.3, 0.7)
            password_input.type(self.password, delay=random.randint(50, 150))
            self._random_delay(0.5, 1.5)

            # Click sign in button
            button_selectors = [
                'button[type="submit"]',
                'button[data-litms-control-urn="login-submit"]',
                '.btn__primary--large'
            ]

            sign_in_btn = None
            for selector in button_selectors:
                sign_in_btn = page.query_selector(selector)
                if sign_in_btn:
                    break

            if sign_in_btn:
                sign_in_btn.click()
            else:
                page.keyboard.press('Enter')

            # Wait for navigation with timeout
            self._random_delay(3.0, 6.0)

            # Check if login was successful
            current_url = page.url
            if '/feed' in current_url or '/mynetwork' in current_url or '/in/' in current_url:
                self.logger.info("LinkedIn login successful")
                self._logged_in = True
                return True

            # Check for security challenge
            if 'checkpoint' in current_url or 'challenge' in current_url:
                self.logger.warning(
                    "LinkedIn security challenge detected - manual intervention may be required. "
                    "Consider running in non-headless mode to solve CAPTCHA."
                )
                # Give user time to manually solve if not headless
                if not self.headless:
                    self.logger.info("Waiting 30 seconds for manual challenge resolution...")
                    time.sleep(30)
                    if '/feed' in page.url or '/mynetwork' in page.url:
                        self.logger.info("Challenge appears to be resolved")
                        self._logged_in = True
                        return True
                return False

            # Check for error messages
            error_selectors = ['.form__label--error', '.alert-content', '.error-message', '[role="alert"]']
            for selector in error_selectors:
                error_msg = page.query_selector(selector)
                if error_msg:
                    self.logger.error(f"Login failed: {error_msg.inner_text()}")
                    return False

            self.logger.warning(f"Login status unclear, current URL: {current_url}")
            return False

        except Exception as e:
            self.logger.error(f"Error during login: {e}")
            return False

    def extract_username(self, url: str) -> str:
        """
        Extract username or company name from LinkedIn URL.

        Handles:
        - linkedin.com/company/companyname
        - linkedin.com/in/username (personal profiles)
        - Various URL formats with query parameters

        Args:
            url: LinkedIn URL

        Returns:
            Username or company identifier

        Raises:
            ValueError: If URL format is not recognized
        """
        try:
            # Clean URL
            url = url.strip().rstrip('/')
            parsed = urlparse(url)

            # Extract path
            path = unquote(parsed.path)

            # Match company page: /company/name
            company_match = re.search(r'/company/([^/\?]+)', path, re.IGNORECASE)
            if company_match:
                return company_match.group(1)

            # Match personal profile: /in/username
            profile_match = re.search(r'/in/([^/\?]+)', path, re.IGNORECASE)
            if profile_match:
                return profile_match.group(1)

            # If we can't extract, raise error
            raise ValueError(
                f"Could not extract username from LinkedIn URL: {url}. "
                "Expected format: linkedin.com/company/name or linkedin.com/in/username"
            )

        except Exception as e:
            self.logger.error(f"Error extracting username from URL {url}: {e}")
            raise ValueError(f"Invalid LinkedIn URL format: {url}")

    def _is_company_url(self, url: str) -> bool:
        """Check if URL is a company page (vs personal profile)."""
        return '/company/' in url.lower()

    def _wait_for_content(self, page: Page, timeout: int = 10000) -> bool:
        """
        Wait for page content to load.

        Args:
            page: Playwright page object
            timeout: Timeout in milliseconds

        Returns:
            True if content loaded, False otherwise
        """
        try:
            # Wait for main content container
            page.wait_for_selector('main', timeout=timeout)
            time.sleep(2)  # Additional wait for dynamic content
            return True
        except PlaywrightTimeout:
            self.logger.warning("Timeout waiting for page content")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for content: {e}")
            return False

    def _check_access_restrictions(self, page: Page) -> Optional[str]:
        """
        Check if page access is restricted.

        Returns:
            Error message if restricted, None if accessible
        """
        content = page.content().lower()

        # Check for login wall
        authwall_indicators = [
            'authwall',
            'join now',
            'sign in to see',
            'sign up to view',
            'member-only'
        ]
        if any(indicator in content for indicator in authwall_indicators):
            signin_selectors = [
                'form[data-id="sign-in-form"]',
                '.authwall',
                '[data-tracking-control-name="guest_homepage-basic_nav-header-signin"]'
            ]
            for selector in signin_selectors:
                if page.query_selector(selector):
                    self.logger.debug(f"Auth wall detected with selector: {selector}")
                    return "LinkedIn requires authentication to view this content"

        # Check for rate limiting
        rate_limit_indicators = [
            'too many requests',
            'rate limit',
            'temporarily restricted',
            'unusual activity',
            'try again later'
        ]
        if any(indicator in content for indicator in rate_limit_indicators):
            self.logger.warning("Rate limiting or unusual activity detected")
            return "Rate limited by LinkedIn - please wait before retrying"

        # Check for profile unavailable
        unavailable_indicators = [
            'profile unavailable',
            'page not found',
            'this page doesn\'t exist',
            'no longer available',
            '404',
            'member not found'
        ]
        if any(indicator in content for indicator in unavailable_indicators):
            return "Profile or page not found"

        # Check for CAPTCHA
        captcha_indicators = ['captcha', 'security check', 'verify you\'re human']
        if any(indicator in content for indicator in captcha_indicators):
            self.logger.warning("CAPTCHA or security check detected")
            return "CAPTCHA required - consider running in non-headless mode"

        return None

    def _extract_company_data(self, page: Page) -> Dict[str, Any]:
        """
        Extract company page data with graceful degradation.

        Args:
            page: Playwright page object

        Returns:
            Dictionary with company metrics
        """
        data = {
            'company_name': None,
            'followers_count': None,
            'employee_count': None,
            'posts_found': 0,
            'description': None,
            'industry': None,
            'website': None,
            'partial_data': False,
        }

        fields_extracted = 0

        try:
            # Extract company name - more comprehensive selectors
            name_selectors = [
                'h1.org-top-card-summary__title',
                'h1[data-anonymize="company-name"]',
                'h1.top-card-layout__title',
                '.org-top-card-summary__title',
                'h1.organization-top-card-summary__title',
                'h1[class*="top-card"]',
                'h1[class*="org-"]',
            ]
            for selector in name_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        name = element.inner_text().strip()
                        if name:
                            data['company_name'] = name
                            fields_extracted += 1
                            self.logger.debug(f"Extracted company name: {name}")
                            break
                except Exception as e:
                    self.logger.debug(f"Could not extract name with selector {selector}: {e}")
                    continue

            # Extract follower count - improved pattern matching
            follower_selectors = [
                '.org-top-card-summary-info-list__info-item',
                '.top-card-layout__first-subline',
                '.org-top-card-primary-actions__inner',
                '[class*="follower"]',
                '.org-page-navigation__item-count',
            ]
            for selector in follower_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        text = element.inner_text().lower()
                        if 'follower' in text:
                            # Extract number - handles K, M notation
                            match = re.search(r'([\d,\.]+)\s*([km])?\s*follower', text, re.IGNORECASE)
                            if match:
                                num_str = match.group(1).replace(',', '')
                                multiplier = 1
                                if match.group(2):
                                    multiplier = 1000 if match.group(2).lower() == 'k' else 1000000
                                data['followers_count'] = int(float(num_str) * multiplier)
                                fields_extracted += 1
                                self.logger.debug(f"Extracted follower count: {data['followers_count']}")
                                break
                    if data['followers_count']:
                        break
                except Exception as e:
                    self.logger.debug(f"Could not extract followers with selector {selector}: {e}")
                    continue

            # Extract employee count
            employee_selectors = [
                '.org-top-card-summary-info-list__info-item',
                '.org-about-company-module__company-size-definition-text',
                '[class*="employee"]',
            ]
            for selector in employee_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        text = element.inner_text().lower()
                        if 'employee' in text or 'employees' in text:
                            # Extract range or number
                            match = re.search(r'([\d,\-]+)\s*employee', text)
                            if match:
                                data['employee_count'] = match.group(1).replace(',', '')
                                fields_extracted += 1
                                self.logger.debug(f"Extracted employee count: {data['employee_count']}")
                                break
                    if data['employee_count']:
                        break
                except Exception as e:
                    self.logger.debug(f"Could not extract employees with selector {selector}: {e}")
                    continue

            # Extract description
            desc_selectors = [
                '.org-top-card-summary__tagline',
                'p.break-words',
                '.org-about-us-organization-description__text',
                '[class*="tagline"]',
                '.org-top-card-summary-info-list',
            ]
            for selector in desc_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        desc = element.inner_text().strip()
                        if len(desc) > 10:  # Ensure it's meaningful
                            data['description'] = desc
                            fields_extracted += 1
                            self.logger.debug(f"Extracted description: {desc[:50]}...")
                            break
                except Exception as e:
                    self.logger.debug(f"Could not extract description with selector {selector}: {e}")
                    continue

            # Count posts/updates (if visible)
            post_selectors = [
                '.feed-shared-update-v2',
                'article[data-id]',
                '.occludable-update',
                '[data-urn*="activity"]',
                '.feed-shared-update',
                'li.profile-creator-shared-feed-update__container',
            ]
            for selector in post_selectors:
                try:
                    posts = page.query_selector_all(selector)
                    if posts and len(posts) > 0:
                        data['posts_found'] = len(posts)
                        self.logger.debug(f"Found {len(posts)} posts")
                        break
                except Exception as e:
                    self.logger.debug(f"Could not count posts with selector {selector}: {e}")
                    continue

            # Mark as partial if we got some but not all fields
            data['partial_data'] = fields_extracted > 0 and fields_extracted < 3

            if fields_extracted > 0:
                self.logger.info(f"Successfully extracted {fields_extracted} fields for company: {data.get('company_name', 'Unknown')}")
            else:
                self.logger.warning("Could not extract any company data - possible access restriction")

        except Exception as e:
            self.logger.error(f"Error extracting company data: {e}", exc_info=True)

        return data

    def _extract_profile_data(self, page: Page) -> Dict[str, Any]:
        """
        Extract personal profile data with graceful degradation.

        Args:
            page: Playwright page object

        Returns:
            Dictionary with profile metrics
        """
        data = {
            'name': None,
            'headline': None,
            'followers_count': None,
            'connections_count': None,
            'posts_found': 0,
            'partial_data': False,
        }

        fields_extracted = 0

        try:
            # Extract name - more comprehensive selectors
            name_selectors = [
                'h1.text-heading-xlarge',
                'h1[data-anonymize="person-name"]',
                '.pv-top-card--list h1',
                'h1.inline',
                'h1[class*="top-card"]',
                '.pv-text-details__left-panel h1',
            ]
            for selector in name_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        name = element.inner_text().strip()
                        if name:
                            data['name'] = name
                            fields_extracted += 1
                            self.logger.debug(f"Extracted name: {name}")
                            break
                except Exception as e:
                    self.logger.debug(f"Could not extract name with selector {selector}: {e}")
                    continue

            # Extract headline
            headline_selectors = [
                '.text-body-medium',
                'div[data-anonymize="headline"]',
                '.pv-top-card--list .text-body-medium',
                '.pv-text-details__left-panel .text-body-medium',
                'div.text-body-medium.break-words',
            ]
            for selector in headline_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        headline = element.inner_text().strip()
                        if len(headline) > 5 and headline != data['name']:
                            data['headline'] = headline
                            fields_extracted += 1
                            self.logger.debug(f"Extracted headline: {headline[:50]}...")
                            break
                except Exception as e:
                    self.logger.debug(f"Could not extract headline with selector {selector}: {e}")
                    continue

            # Extract follower/connection count (often restricted)
            # Try multiple selector patterns
            count_selectors = [
                '.pv-top-card--list-bullet li',
                '.pv-top-card--list-bullet .pvs-header__subtitle',
                '.text-body-small',
                'span.t-black--light',
            ]

            for selector in count_selectors:
                try:
                    info_elements = page.query_selector_all(selector)
                    for element in info_elements:
                        text = element.inner_text().lower()

                        # Check for followers
                        if 'follower' in text and not data['followers_count']:
                            # Handle K, M notation
                            match = re.search(r'([\d,\.]+)\s*([km])?\s*follower', text, re.IGNORECASE)
                            if match:
                                num_str = match.group(1).replace(',', '')
                                multiplier = 1
                                if match.group(2):
                                    multiplier = 1000 if match.group(2).lower() == 'k' else 1000000
                                data['followers_count'] = int(float(num_str) * multiplier)
                                fields_extracted += 1
                                self.logger.debug(f"Extracted followers: {data['followers_count']}")

                        # Check for connections
                        elif 'connection' in text and not data['connections_count']:
                            match = re.search(r'([\d,\.]+)\s*([km])?\s*connection', text, re.IGNORECASE)
                            if match:
                                num_str = match.group(1).replace(',', '')
                                multiplier = 1
                                if match.group(2):
                                    multiplier = 1000 if match.group(2).lower() == 'k' else 1000000
                                data['connections_count'] = int(float(num_str) * multiplier)
                                fields_extracted += 1
                                self.logger.debug(f"Extracted connections: {data['connections_count']}")
                except Exception as e:
                    self.logger.debug(f"Could not extract counts with selector {selector}: {e}")
                    continue

            # Count posts (usually very limited on profiles)
            post_selectors = [
                '.feed-shared-update-v2',
                'article[data-id]',
                'article.feed-shared-update',
                'li.profile-creator-shared-feed-update__container',
                '[data-urn*="activity"]',
            ]
            for selector in post_selectors:
                try:
                    posts = page.query_selector_all(selector)
                    if posts and len(posts) > 0:
                        data['posts_found'] = len(posts)
                        self.logger.debug(f"Found {len(posts)} posts")
                        break
                except Exception as e:
                    self.logger.debug(f"Could not count posts with selector {selector}: {e}")
                    continue

            # Mark as partial if we got some but not all fields
            data['partial_data'] = fields_extracted > 0 and fields_extracted < 2

            if fields_extracted > 0:
                self.logger.info(f"Successfully extracted {fields_extracted} fields for profile: {data.get('name', 'Unknown')}")
            else:
                self.logger.warning("Could not extract any profile data - possible access restriction")

        except Exception as e:
            self.logger.error(f"Error extracting profile data: {e}", exc_info=True)

        return data

    def scrape(self, url: str, grantee_name: str, max_posts: int = 25) -> Dict[str, Any]:
        """
        Scrape LinkedIn company or profile page.

        Args:
            url: LinkedIn URL to scrape
            grantee_name: Name of the grantee (for organization)
            max_posts: Maximum posts to scrape

        Returns:
            Dictionary with:
                - success: bool
                - posts_downloaded: int
                - errors: list
                - engagement_metrics: dict
        """
        errors = []
        engagement_metrics = {}
        posts_downloaded = 0

        try:
            # Extract username and determine page type
            username = self.extract_username(url)
            is_company = self._is_company_url(url)
            page_type = "company" if is_company else "profile"

            self.logger.info(f"Starting LinkedIn {page_type} scrape for: {username}")

            # Create output directory (follows standard structure: output/{grantee}/{platform}/{username})
            base_output = self.get_output_path(grantee_name)
            output_path = base_output / username
            output_path.mkdir(parents=True, exist_ok=True)

            # Initialize Playwright
            with sync_playwright() as p:
                # Launch browser with enhanced stealth settings
                browser: Browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                    ]
                )

                # Try to load existing session
                session_state = self._load_session(username)

                # Create context with realistic settings and optional session
                context_params = {
                    'viewport': {
                        'width': random.randint(1366, 1920),
                        'height': random.randint(768, 1080)
                    },
                    'user_agent': (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        f'Chrome/{random.randint(118, 122)}.0.0.0 Safari/537.36'
                    ),
                    'locale': 'en-US',
                    'timezone_id': 'America/New_York',
                    'permissions': ['geolocation'],
                    'device_scale_factor': random.choice([1, 1.25, 1.5, 2]),
                    'has_touch': random.choice([True, False]),
                }

                # Add session state if available
                if session_state:
                    context_params['storage_state'] = session_state

                context = browser.new_context(**context_params)

                page = context.new_page()

                # Apply stealth techniques
                self._apply_stealth_techniques(page)

                try:
                    # Attempt login if credentials are available and no session loaded
                    if self.email and self.password and not session_state:
                        if not self._login(page):
                            self.logger.warning("Login failed, continuing without authentication")
                        else:
                            self._random_delay(1.5, 3.0)
                            # Save session for future use
                            self._save_session(context, username)

                    # Navigate to page with timeout
                    self.logger.info(f"Navigating to: {url}")

                    # Use retry logic for navigation
                    def navigate():
                        return page.goto(url, wait_until='domcontentloaded', timeout=30000)

                    try:
                        response = self._retry_with_backoff(navigate, max_retries=2)
                    except Exception as e:
                        error_msg = f"Failed to navigate to page after retries: {e}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                        return {
                            'success': False,
                            'posts_downloaded': 0,
                            'errors': errors,
                            'engagement_metrics': {},
                        }

                    if not response or response.status >= 400:
                        error_msg = f"Failed to load page: HTTP {response.status if response else 'unknown'}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                        return {
                            'success': False,
                            'posts_downloaded': 0,
                            'errors': errors,
                            'engagement_metrics': {},
                        }

                    # Random delay after page load
                    self._random_delay(1.0, 2.5)

                    # Wait for content
                    if not self._wait_for_content(page):
                        errors.append("Page content did not load within timeout")

                    # Simulate human browsing behavior
                    self._simulate_human_behavior(page)

                    # Check for access restrictions
                    restriction = self._check_access_restrictions(page)
                    if restriction:
                        errors.append(restriction)
                        self.logger.warning(f"Access restricted: {restriction}")
                        # Continue anyway to extract what we can

                    # Extract data based on page type
                    if is_company:
                        extracted_data = self._extract_company_data(page)
                        engagement_metrics = {
                            'followers_count': extracted_data.get('followers_count'),
                            'employee_count': extracted_data.get('employee_count'),
                            'posts_found': extracted_data.get('posts_found', 0),
                        }
                    else:
                        extracted_data = self._extract_profile_data(page)
                        engagement_metrics = {
                            'followers_count': extracted_data.get('followers_count'),
                            'connections_count': extracted_data.get('connections_count'),
                            'posts_found': extracted_data.get('posts_found', 0),
                        }

                    posts_downloaded = extracted_data.get('posts_found', 0)

                    # Take screenshot for reference
                    screenshot_path = output_path / 'screenshot.png'
                    try:
                        page.screenshot(path=str(screenshot_path), full_page=False)
                        self.logger.info(f"Screenshot saved to {screenshot_path}")
                    except Exception as e:
                        self.logger.warning(f"Could not save screenshot: {e}")

                    # Save metadata with enhanced details
                    metadata = {
                        'platform': self.platform_name,
                        'grantee_name': grantee_name,
                        'username': username,
                        'url': url,
                        'page_type': page_type,
                        'scraped_at': datetime.now().isoformat(),
                        'data': extracted_data,
                        'engagement_metrics': engagement_metrics,
                        'success': len(errors) == 0 or any(v is not None for v in engagement_metrics.values()),
                        'partial_data': extracted_data.get('partial_data', False),
                        'authenticated': self._logged_in,
                        'session_used': session_state is not None,
                        'errors': errors,
                        'notes': [
                            "LinkedIn heavily restricts scraping",
                            "Only public information was accessed",
                            "Some metrics may be unavailable without authentication",
                            "Scraper uses stealth techniques and human-like behavior",
                            "Session persistence enabled for better access",
                        ]
                    }

                    self.save_metadata(output_path, metadata)

                except PlaywrightTimeout as e:
                    error_msg = f"Timeout navigating to page: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)

                except Exception as e:
                    error_msg = f"Error during scraping: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)

                finally:
                    # Cleanup
                    try:
                        page.close()
                        context.close()
                        browser.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing browser: {e}")

            # Determine overall success
            # Success if we extracted at least some data
            success = (
                len(errors) == 0 or
                any(v is not None and v != 0 for v in engagement_metrics.values())
            )

            if success:
                self.logger.info(f"Successfully scraped LinkedIn {page_type}: {username}")
            else:
                self.logger.warning(f"Scrape completed with errors for: {username}")

            return {
                'success': success,
                'posts_downloaded': posts_downloaded,
                'errors': errors,
                'engagement_metrics': engagement_metrics,
            }

        except ValueError as e:
            # URL parsing error
            error_msg = str(e)
            errors.append(error_msg)
            self.logger.error(error_msg)

            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': errors,
                'engagement_metrics': {},
            }

        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg, exc_info=True)

            return {
                'success': False,
                'posts_downloaded': 0,
                'errors': errors,
                'engagement_metrics': {},
            }
