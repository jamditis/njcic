"""
LinkedIn scraper implementation.

Note: LinkedIn has strict anti-scraping measures. This scraper attempts
to collect publicly available information on a best-effort basis.
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING
from urllib.parse import urlparse, unquote
from datetime import datetime

if TYPE_CHECKING:
    from playwright.sync_api import Page, Browser

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    sync_playwright = None

from .base import BaseScraper


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
        super().__init__(output_dir)
        self.headless = headless

        if sync_playwright is None:
            raise ImportError(
                "Playwright is required for LinkedIn scraping. "
                "Install with: pip install playwright && playwright install chromium"
            )

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
        if 'authwall' in content or 'join now' in content:
            if page.query_selector('form[data-id="sign-in-form"]'):
                return "LinkedIn requires authentication to view this content"

        # Check for rate limiting
        if 'too many requests' in content or 'rate limit' in content:
            return "Rate limited by LinkedIn"

        # Check for profile unavailable
        if 'profile unavailable' in content or 'page not found' in content:
            return "Profile or page not found"

        return None

    def _extract_company_data(self, page: Page) -> Dict[str, Any]:
        """
        Extract company page data.

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
        }

        try:
            # Extract company name
            name_selectors = [
                'h1.org-top-card-summary__title',
                'h1[data-anonymize="company-name"]',
                'h1.top-card-layout__title',
            ]
            for selector in name_selectors:
                element = page.query_selector(selector)
                if element:
                    data['company_name'] = element.inner_text().strip()
                    break

            # Extract follower count
            follower_selectors = [
                '.org-top-card-summary-info-list__info-item',
                '.top-card-layout__first-subline',
            ]
            for selector in follower_selectors:
                elements = page.query_selector_all(selector)
                for element in elements:
                    text = element.inner_text().lower()
                    if 'follower' in text:
                        # Extract number from text like "1,234 followers"
                        match = re.search(r'([\d,]+)\s*follower', text)
                        if match:
                            data['followers_count'] = match.group(1).replace(',', '')
                            break
                if data['followers_count']:
                    break

            # Extract employee count
            employee_selectors = [
                '.org-top-card-summary-info-list__info-item',
            ]
            for selector in employee_selectors:
                elements = page.query_selector_all(selector)
                for element in elements:
                    text = element.inner_text().lower()
                    if 'employee' in text or 'employees' in text:
                        # Extract number from text like "50-100 employees"
                        match = re.search(r'([\d,\-]+)\s*employee', text)
                        if match:
                            data['employee_count'] = match.group(1).replace(',', '')
                            break
                if data['employee_count']:
                    break

            # Extract description
            desc_selectors = [
                '.org-top-card-summary__tagline',
                'p.break-words',
            ]
            for selector in desc_selectors:
                element = page.query_selector(selector)
                if element:
                    desc = element.inner_text().strip()
                    if len(desc) > 10:  # Ensure it's meaningful
                        data['description'] = desc
                        break

            # Count posts/updates (if visible)
            post_selectors = [
                '.feed-shared-update-v2',
                'article[data-id]',
                '.occludable-update',
            ]
            for selector in post_selectors:
                posts = page.query_selector_all(selector)
                if posts:
                    data['posts_found'] = len(posts)
                    break

            self.logger.info(f"Extracted company data: {data['company_name']}")

        except Exception as e:
            self.logger.error(f"Error extracting company data: {e}")

        return data

    def _extract_profile_data(self, page: Page) -> Dict[str, Any]:
        """
        Extract personal profile data.

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
        }

        try:
            # Extract name
            name_selectors = [
                'h1.text-heading-xlarge',
                'h1[data-anonymize="person-name"]',
            ]
            for selector in name_selectors:
                element = page.query_selector(selector)
                if element:
                    data['name'] = element.inner_text().strip()
                    break

            # Extract headline
            headline_selectors = [
                '.text-body-medium',
                'div[data-anonymize="headline"]',
            ]
            for selector in headline_selectors:
                element = page.query_selector(selector)
                if element:
                    headline = element.inner_text().strip()
                    if len(headline) > 5 and headline != data['name']:
                        data['headline'] = headline
                        break

            # Extract follower/connection count
            # Note: This is often restricted on personal profiles
            info_elements = page.query_selector_all('.pv-top-card--list-bullet li')
            for element in info_elements:
                text = element.inner_text().lower()
                if 'follower' in text:
                    match = re.search(r'([\d,]+)', text)
                    if match:
                        data['followers_count'] = match.group(1).replace(',', '')
                elif 'connection' in text:
                    match = re.search(r'([\d,]+)', text)
                    if match:
                        data['connections_count'] = match.group(1).replace(',', '')

            # Count posts (usually very limited)
            post_selectors = [
                '.feed-shared-update-v2',
                'article',
            ]
            for selector in post_selectors:
                posts = page.query_selector_all(selector)
                if posts:
                    data['posts_found'] = len(posts)
                    break

            self.logger.info(f"Extracted profile data: {data['name']}")

        except Exception as e:
            self.logger.error(f"Error extracting profile data: {e}")

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

            # Create output directory
            output_path = self.output_dir / self.platform_name / grantee_name / username
            output_path.mkdir(parents=True, exist_ok=True)

            # Initialize Playwright
            with sync_playwright() as p:
                # Launch browser with realistic settings
                browser: Browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                    ]
                )

                # Create context with realistic user agent
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=(
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/120.0.0.0 Safari/537.36'
                    ),
                    locale='en-US',
                )

                page = context.new_page()

                try:
                    # Navigate to page with timeout
                    self.logger.info(f"Navigating to: {url}")
                    response = page.goto(url, wait_until='domcontentloaded', timeout=30000)

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

                    # Wait for content
                    if not self._wait_for_content(page):
                        errors.append("Page content did not load within timeout")

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

                    # Save metadata
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
                        'errors': errors,
                        'notes': [
                            "LinkedIn heavily restricts scraping",
                            "Only public information was accessed",
                            "Some metrics may be unavailable without authentication",
                        ]
                    }

                    metadata_path = output_path / 'metadata.json'
                    self.save_metadata(metadata, metadata_path)

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
