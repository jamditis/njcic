"""
Configuration settings for NJCIC Grantee Social Media Scraper.

This module centralizes all configuration settings including paths,
rate limiting, platform settings, and environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Scraping settings
MAX_POSTS_PER_ACCOUNT = 25  # Maximum posts to download per account
REQUEST_DELAY = 2  # Delay between requests in seconds
TIMEOUT = 30  # Request timeout in seconds
MAX_RETRIES = 3  # Maximum retry attempts for failed requests

# Platform settings
SUPPORTED_PLATFORMS = [
    "facebook",
    "instagram",
    "twitter",
    "youtube",
    "tiktok",
    "linkedin"
]

# API Keys and Authentication (loaded from environment)
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")

FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# TikTok-specific settings
# TIKTOK_PROXY: Optional HTTP/HTTPS proxy for TikTok requests (e.g., "http://proxy:port")
# TIKTOK_API_ENDPOINT: Optional custom TikTok API hostname (defaults to rotating endpoints)
# HTTP_PROXY: Alternative proxy setting (TIKTOK_PROXY takes precedence)
TIKTOK_PROXY = os.getenv("TIKTOK_PROXY", "")
TIKTOK_API_ENDPOINT = os.getenv("TIKTOK_API_ENDPOINT", "")

# User agent for requests
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Output format settings
OUTPUT_FORMAT = "json"  # json, csv, or both
SAVE_MEDIA = True  # Whether to download media files (images, videos)
SAVE_METADATA = True  # Whether to save metadata files

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / "scraper.log"

# Data validation
REQUIRED_POST_FIELDS = [
    "post_id",
    "text",
    "timestamp",
    "author",
    "platform",
    "url"
]

# Engagement metrics to track
ENGAGEMENT_METRICS = [
    "likes",
    "comments",
    "shares",
    "views",
    "reactions"
]

# Error handling
SKIP_ON_ERROR = True  # Continue scraping even if individual posts fail
SAVE_ERRORS = True  # Save error logs for failed scrapes
