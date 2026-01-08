"""
Base scraper class for social media platforms.

This module provides an abstract base class that all platform-specific
scrapers should inherit from, ensuring consistent interface and behavior.
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import config


class BaseScraper(ABC):
    """
    Abstract base class for social media scrapers.

    All platform-specific scrapers should inherit from this class and
    implement the required abstract methods.

    Attributes:
        platform_name (str): Name of the platform (e.g., 'facebook', 'instagram')
        output_dir (Path): Directory where scraped data will be saved
        logger (logging.Logger): Logger instance for this scraper
    """

    platform_name: str = "base"  # Must be overridden by subclasses

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the scraper.

        Args:
            output_dir: Base output directory. If None, uses config.OUTPUT_DIR
        """
        self.output_dir = output_dir or config.OUTPUT_DIR
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Set up logging
        self.logger = logging.getLogger(f"{__name__}.{self.platform_name}")
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL))

        # Add file handler if not already present
        if not self.logger.handlers:
            handler = logging.FileHandler(config.LOG_FILE)
            handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
            self.logger.addHandler(handler)

            # Also add console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
            self.logger.addHandler(console_handler)

        self._last_request_time = 0
        self.logger.info(f"Initialized {self.platform_name} scraper")

    def get_output_path(self, grantee_name: str) -> Path:
        """
        Create and return platform-specific output directory for a grantee.

        Args:
            grantee_name: Name of the grantee organization

        Returns:
            Path object for the output directory
        """
        # Sanitize grantee name for filesystem
        safe_name = "".join(
            c if c.isalnum() or c in (' ', '-', '_') else '_'
            for c in grantee_name
        ).strip().replace(' ', '_')

        # Create path: output/{grantee_name}/{platform_name}
        output_path = self.output_dir / safe_name / self.platform_name
        output_path.mkdir(exist_ok=True, parents=True)

        self.logger.debug(f"Output path for {grantee_name}: {output_path}")
        return output_path

    def save_metadata(self, output_path: Path, metadata: Dict[str, Any]) -> None:
        """
        Save scraping metadata to a JSON file.

        Args:
            output_path: Directory where metadata should be saved
            metadata: Dictionary containing metadata to save
        """
        metadata_file = output_path / "metadata.json"

        # Add timestamp and platform info
        metadata.update({
            "platform": self.platform_name,
            "scraped_at": datetime.now().isoformat(),
            "scraper_version": "1.0.0"
        })

        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved metadata to {metadata_file}")
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
            if not config.SKIP_ON_ERROR:
                raise

    def rate_limit(self) -> None:
        """
        Implement rate limiting to respect platform guidelines.

        Ensures minimum delay between requests as specified in config.REQUEST_DELAY.
        """
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time

        if time_since_last_request < config.REQUEST_DELAY:
            sleep_time = config.REQUEST_DELAY - time_since_last_request
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def save_posts(
        self,
        posts: List[Dict[str, Any]],
        output_path: Path,
        filename: str = "posts.json"
    ) -> None:
        """
        Save scraped posts to a JSON file.

        Args:
            posts: List of post dictionaries
            output_path: Directory where posts should be saved
            filename: Name of the output file
        """
        output_file = output_path / filename

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved {len(posts)} posts to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save posts: {e}")
            if not config.SKIP_ON_ERROR:
                raise

    def save_errors(
        self,
        errors: List[Dict[str, Any]],
        output_path: Path,
        filename: str = "errors.json"
    ) -> None:
        """
        Save error information to a JSON file.

        Args:
            errors: List of error dictionaries
            output_path: Directory where errors should be saved
            filename: Name of the error file
        """
        if not config.SAVE_ERRORS or not errors:
            return

        error_file = output_path / filename

        try:
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(errors, f, indent=2, ensure_ascii=False)
            self.logger.warning(f"Saved {len(errors)} errors to {error_file}")
        except Exception as e:
            self.logger.error(f"Failed to save errors: {e}")

    def calculate_engagement_metrics(
        self,
        posts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate aggregate engagement metrics from posts.

        Args:
            posts: List of post dictionaries

        Returns:
            Dictionary containing engagement metrics
        """
        if not posts:
            return {metric: 0 for metric in config.ENGAGEMENT_METRICS}

        metrics = {metric: 0 for metric in config.ENGAGEMENT_METRICS}

        for post in posts:
            for metric in config.ENGAGEMENT_METRICS:
                if metric in post and isinstance(post[metric], (int, float)):
                    metrics[metric] += post[metric]

        # Calculate averages
        num_posts = len(posts)
        avg_metrics = {
            f"avg_{metric}": round(value / num_posts, 2)
            for metric, value in metrics.items()
        }

        # Combine total and average metrics
        metrics.update(avg_metrics)
        metrics["total_posts"] = num_posts

        return metrics

    @abstractmethod
    def extract_username(self, url: str) -> Optional[str]:
        """
        Extract username/handle from a platform URL.

        Args:
            url: Social media profile or post URL

        Returns:
            Extracted username or None if extraction fails
        """
        pass

    @abstractmethod
    def scrape(
        self,
        url: str,
        grantee_name: str,
        max_posts: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scrape posts from the given URL.

        Args:
            url: URL to scrape (profile, page, or channel)
            grantee_name: Name of the grantee organization
            max_posts: Maximum number of posts to scrape (defaults to config value)

        Returns:
            Dictionary with scraping results:
            {
                'success': bool,
                'posts_downloaded': int,
                'errors': List[Dict],
                'engagement_metrics': Dict[str, Any],
                'output_path': str
            }
        """
        pass

    def validate_post(self, post: Dict[str, Any]) -> bool:
        """
        Validate that a post contains required fields.

        Args:
            post: Post dictionary to validate

        Returns:
            True if post is valid, False otherwise
        """
        for field in config.REQUIRED_POST_FIELDS:
            if field not in post or post[field] is None:
                self.logger.warning(f"Post missing required field: {field}")
                return False
        return True

    def __repr__(self) -> str:
        """String representation of the scraper."""
        return f"{self.__class__.__name__}(platform='{self.platform_name}')"
