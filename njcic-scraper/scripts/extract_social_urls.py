#!/usr/bin/env python3
"""
Social Media URL Extractor for NJCIC Grantees

This script reads grantee data from the NJCIC grantees map JSON file,
fetches each grantee's website, and extracts social media links.

Platforms supported:
- Facebook
- Twitter/X
- Instagram
- LinkedIn
- YouTube
- TikTok
- Threads
- BlueSky

Output: JSON file with grantee info + social media URLs
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


# Configuration
INPUT_FILE = "/home/user/njcic/repos/njcic-grantees-map/data/grantees.json"
OUTPUT_FILE = "/home/user/njcic/njcic-scraper/data/grantees_with_social.json"
REQUEST_TIMEOUT = 10  # seconds
REQUEST_DELAY = 0.5  # seconds between requests
MAX_RETRIES = 2
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class SocialMediaExtractor:
    """Extract social media URLs from website HTML."""

    # Social media patterns - ordered by specificity
    PATTERNS = {
        'facebook': [
            r'(?:https?://)?(?:www\.)?facebook\.com/[a-zA-Z0-9._-]+',
            r'(?:https?://)?(?:www\.)?fb\.com/[a-zA-Z0-9._-]+',
            r'(?:https?://)?(?:www\.)?m\.facebook\.com/[a-zA-Z0-9._-]+',
        ],
        'twitter': [
            r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/[a-zA-Z0-9_]+',
        ],
        'instagram': [
            r'(?:https?://)?(?:www\.)?instagram\.com/[a-zA-Z0-9._]+',
        ],
        'linkedin': [
            r'(?:https?://)?(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9_-]+',
        ],
        'youtube': [
            r'(?:https?://)?(?:www\.)?youtube\.com/(?:c|channel|user|@)[a-zA-Z0-9_-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/@[a-zA-Z0-9_-]+',
        ],
        'tiktok': [
            r'(?:https?://)?(?:www\.)?tiktok\.com/@[a-zA-Z0-9._]+',
        ],
        'threads': [
            r'(?:https?://)?(?:www\.)?threads\.net/@[a-zA-Z0-9._]+',
        ],
        'bluesky': [
            r'(?:https?://)?(?:www\.)?bsky\.app/profile/[a-zA-Z0-9._-]+',
        ],
    }

    # Meta tag mappings
    META_TAGS = {
        'facebook': ['og:url', 'fb:page_id', 'fb:app_id'],
        'twitter': ['twitter:site', 'twitter:creator'],
        'instagram': ['instagram:site'],
    }

    # Common section identifiers (for header/footer detection)
    SECTION_SELECTORS = [
        'footer',
        'header',
        'nav',
        '[class*="footer"]',
        '[class*="header"]',
        '[class*="social"]',
        '[id*="footer"]',
        '[id*="header"]',
        '[id*="social"]',
    ]

    def __init__(self, html: str, base_url: str):
        """
        Initialize extractor with HTML content.

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links
        """
        self.soup = BeautifulSoup(html, 'html.parser')
        self.base_url = base_url
        self.found_urls: Dict[str, str] = {}

    def extract_all(self) -> Dict[str, Optional[str]]:
        """
        Extract all social media URLs from the page.

        Returns:
            Dictionary mapping platform names to URLs (or None if not found)
        """
        # Search in multiple locations
        self._search_meta_tags()
        self._search_links()
        self._search_text_content()

        # Initialize result with all platforms
        result = {platform: None for platform in self.PATTERNS.keys()}
        result.update(self.found_urls)

        return result

    def _search_meta_tags(self) -> None:
        """Search for social media URLs in meta tags."""
        for meta in self.soup.find_all('meta'):
            # Check property attribute (Open Graph)
            prop = meta.get('property', '').lower()
            content = meta.get('content', '')

            # Check name attribute (Twitter cards)
            name = meta.get('name', '').lower()

            for platform, tag_names in self.META_TAGS.items():
                if platform in self.found_urls:
                    continue

                for tag_name in tag_names:
                    if tag_name.lower() in (prop, name):
                        url = self._extract_url_from_text(content, platform)
                        if url:
                            self.found_urls[platform] = url
                            break

    def _search_links(self) -> None:
        """Search for social media URLs in link tags and anchor elements."""
        # Check all <a> tags
        for link in self.soup.find_all('a', href=True):
            href = link.get('href', '')
            abs_url = urljoin(self.base_url, href)

            for platform in self.PATTERNS.keys():
                if platform in self.found_urls:
                    continue

                url = self._extract_url_from_text(abs_url, platform)
                if url:
                    # Prefer links in header/footer sections
                    if self._is_in_section(link):
                        self.found_urls[platform] = url
                    elif platform not in self.found_urls:
                        self.found_urls[platform] = url

    def _search_text_content(self) -> None:
        """Search for social media URLs in text content (fallback)."""
        # Get all text content
        text = self.soup.get_text()

        for platform in self.PATTERNS.keys():
            if platform in self.found_urls:
                continue

            url = self._extract_url_from_text(text, platform)
            if url:
                self.found_urls[platform] = url

    def _extract_url_from_text(self, text: str, platform: str) -> Optional[str]:
        """
        Extract a social media URL for a specific platform from text.

        Args:
            text: Text to search
            platform: Platform name (e.g., 'facebook', 'twitter')

        Returns:
            Normalized URL or None if not found
        """
        if not text:
            return None

        patterns = self.PATTERNS.get(platform, [])

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url = match.group(0)
                return self._normalize_url(url, platform)

        return None

    def _normalize_url(self, url: str, platform: str) -> str:
        """
        Normalize a social media URL.

        Args:
            url: Raw URL
            platform: Platform name

        Returns:
            Normalized URL with https:// and proper format
        """
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Remove trailing slashes and query parameters for cleaner URLs
        url = url.rstrip('/')

        # Platform-specific normalization
        if platform == 'twitter':
            # Normalize x.com to twitter.com for consistency
            url = url.replace('x.com/', 'twitter.com/')

        elif platform == 'facebook':
            # Normalize fb.com and m.facebook.com to www.facebook.com
            url = url.replace('fb.com/', 'facebook.com/')
            url = url.replace('m.facebook.com/', 'www.facebook.com/')
            # Remove common Facebook URL parameters
            url = re.sub(r'\?.*$', '', url)

        elif platform == 'youtube':
            # Keep as-is, multiple valid formats

            pass

        return url

    def _is_in_section(self, element) -> bool:
        """
        Check if an element is inside a header/footer/social section.

        Args:
            element: BeautifulSoup element

        Returns:
            True if element is in a header/footer section
        """
        # Traverse up the tree looking for section markers
        for parent in element.parents:
            if parent.name in ('footer', 'header', 'nav'):
                return True

            # Check class and id attributes
            classes = ' '.join(parent.get('class', []))
            elem_id = parent.get('id', '')

            for keyword in ('footer', 'header', 'social'):
                if keyword in classes.lower() or keyword in elem_id.lower():
                    return True

        return False


def fetch_website(url: str, retries: int = MAX_RETRIES) -> Optional[str]:
    """
    Fetch website HTML with retry logic.

    Args:
        url: Website URL
        retries: Number of retry attempts

    Returns:
        HTML content or None if failed
    """
    # Normalize URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    for attempt in range(retries + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            response.raise_for_status()
            return response.text

        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(1)
                continue
            return None

        except requests.exceptions.RequestException:
            if attempt < retries:
                time.sleep(1)
                continue
            return None

    return None


def process_grantees(grantees: List[Dict]) -> List[Dict]:
    """
    Process all grantees and extract social media URLs.

    Args:
        grantees: List of grantee dictionaries

    Returns:
        List of grantees with social media information
    """
    results = []

    # Filter grantees with websites
    grantees_with_websites = [g for g in grantees if g.get('website')]

    print(f"Processing {len(grantees_with_websites)} grantees with websites...")

    for grantee in tqdm(grantees_with_websites, desc="Extracting social links"):
        website = grantee.get('website', '').strip()
        name = grantee.get('name', 'Unknown')

        # Initialize result
        result = {
            'name': name,
            'website': website,
            'social': {
                'facebook': None,
                'twitter': None,
                'instagram': None,
                'linkedin': None,
                'youtube': None,
                'tiktok': None,
                'threads': None,
                'bluesky': None,
            }
        }

        # Fetch website
        html = fetch_website(website)

        if html:
            try:
                extractor = SocialMediaExtractor(html, website)
                social_urls = extractor.extract_all()
                result['social'] = social_urls

            except Exception as e:
                # Log error but continue processing
                tqdm.write(f"⚠️  Error processing {name}: {str(e)}")

        else:
            tqdm.write(f"⚠️  Failed to fetch website for {name}")

        results.append(result)

        # Rate limiting
        time.sleep(REQUEST_DELAY)

    return results


def main():
    """Main execution function."""
    print("=" * 70)
    print("NJCIC Social Media URL Extractor")
    print("=" * 70)
    print()

    # Load input data
    print(f"Loading grantee data from: {INPUT_FILE}")
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            grantees = data.get('grantees', [])
    except FileNotFoundError:
        print(f"❌ Error: Input file not found: {INPUT_FILE}")
        return
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in input file: {INPUT_FILE}")
        return

    print(f"✓ Loaded {len(grantees)} grantees")
    print()

    # Process grantees
    results = process_grantees(grantees)

    # Generate statistics
    total_processed = len(results)
    platforms = ['facebook', 'twitter', 'instagram', 'linkedin', 'youtube', 'tiktok', 'threads', 'bluesky']
    stats = {platform: sum(1 for r in results if r['social'].get(platform)) for platform in platforms}

    print()
    print("=" * 70)
    print("Extraction Complete!")
    print("=" * 70)
    print(f"Total grantees processed: {total_processed}")
    print()
    print("Social media links found:")
    for platform, count in stats.items():
        percentage = (count / total_processed * 100) if total_processed > 0 else 0
        print(f"  {platform.capitalize():12} {count:3} ({percentage:5.1f}%)")
    print()

    # Save output
    output_data = {
        'grantees': results,
        'metadata': {
            'total_grantees': total_processed,
            'extraction_date': time.strftime('%Y-%m-%d'),
            'source_file': INPUT_FILE,
            'statistics': stats,
        }
    }

    print(f"Saving results to: {OUTPUT_FILE}")
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Results saved successfully!")
    print()


if __name__ == '__main__':
    main()
