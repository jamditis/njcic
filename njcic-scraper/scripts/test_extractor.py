#!/usr/bin/env python3
"""
Quick test of the social media extractor with a sample HTML page.
"""

import sys
sys.path.insert(0, '/home/user/njcic/njcic-scraper/scripts')

from extract_social_urls import SocialMediaExtractor

# Sample HTML with various social media links
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:url" content="https://facebook.com/testorg" />
    <meta name="twitter:site" content="@testorg" />
</head>
<body>
    <header>
        <nav>
            <a href="https://instagram.com/testorg">Instagram</a>
            <a href="https://linkedin.com/company/testorg">LinkedIn</a>
        </nav>
    </header>
    
    <main>
        <p>Follow us on social media!</p>
    </main>
    
    <footer>
        <div class="social-links">
            <a href="https://youtube.com/@testorg">YouTube</a>
            <a href="https://tiktok.com/@testorg">TikTok</a>
            <a href="https://threads.net/@testorg">Threads</a>
            <a href="https://bsky.app/profile/testorg.bsky.social">BlueSky</a>
        </div>
    </footer>
</body>
</html>
"""

def main():
    print("Testing SocialMediaExtractor...")
    print("=" * 60)
    
    extractor = SocialMediaExtractor(SAMPLE_HTML, "https://example.org")
    social = extractor.extract_all()
    
    print("\nExtracted social media URLs:")
    for platform, url in social.items():
        status = "✓" if url else "✗"
        print(f"  {status} {platform:12} {url or '(not found)'}")
    
    print("\n" + "=" * 60)
    found_count = sum(1 for url in social.values() if url)
    print(f"Found {found_count}/{len(social)} social media links")
    print()

if __name__ == '__main__':
    main()
