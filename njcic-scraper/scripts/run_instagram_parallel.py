#!/usr/bin/env python3
"""
Parallel Instagram Scraper Runner

Splits Instagram grantees into batches and runs them across multiple processes
with proper rate limiting to avoid being blocked.

Usage:
    python scripts/run_instagram_parallel.py              # Run with 3 workers (default)
    python scripts/run_instagram_parallel.py --workers 4  # Run with 4 workers
    python scripts/run_instagram_parallel.py --test       # Test with first 5 grantees
"""

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from scrapers.instagram import InstagramScraper
import config


def get_instagram_grantees() -> List[Dict[str, Any]]:
    """Load grantees that have Instagram URLs."""
    data_path = Path(__file__).resolve().parent.parent / "data" / "grantees_with_social.json"

    with open(data_path, 'r') as f:
        data = json.load(f)

    grantees = data.get('grantees', [])
    return [g for g in grantees if g.get('social', {}).get('instagram')]


def scrape_batch(batch: List[Dict[str, Any]], worker_id: int, results_queue: mp.Queue) -> None:
    """
    Scrape a batch of Instagram grantees.

    Args:
        batch: List of grantee dictionaries
        worker_id: Worker process ID
        results_queue: Queue for returning results
    """
    print(f"[Worker {worker_id}] Starting with {len(batch)} grantees")

    # Initialize scraper
    scraper = InstagramScraper(
        output_dir=str(config.OUTPUT_DIR),
        session_file=None
    )

    results = []

    for i, grantee in enumerate(batch):
        name = grantee.get('name', 'Unknown')
        url = grantee.get('social', {}).get('instagram', '')

        print(f"[Worker {worker_id}] ({i+1}/{len(batch)}) Scraping: {name}")

        try:
            result = scraper.scrape(url=url, grantee_name=name)
            result['grantee_name'] = name
            result['url'] = url
            results.append(result)

            status = "SUCCESS" if result.get('success') else "FAILED"
            posts = result.get('posts_downloaded', 0)
            print(f"[Worker {worker_id}] ({i+1}/{len(batch)}) {status}: {name} - {posts} posts")

        except Exception as e:
            print(f"[Worker {worker_id}] ({i+1}/{len(batch)}) ERROR: {name} - {str(e)}")
            results.append({
                'grantee_name': name,
                'url': url,
                'success': False,
                'error': str(e),
                'posts_downloaded': 0
            })

        # Extra delay between grantees in the same batch
        if i < len(batch) - 1:
            delay = 10 + (worker_id * 2)  # Stagger delays by worker ID
            print(f"[Worker {worker_id}] Waiting {delay}s before next grantee...")
            time.sleep(delay)

    print(f"[Worker {worker_id}] Completed batch. Sending {len(results)} results.")
    results_queue.put((worker_id, results))


def split_into_batches(items: List, num_batches: int) -> List[List]:
    """Split a list into roughly equal batches."""
    batch_size = len(items) // num_batches
    remainder = len(items) % num_batches

    batches = []
    start = 0

    for i in range(num_batches):
        # Distribute remainder across first batches
        end = start + batch_size + (1 if i < remainder else 0)
        batches.append(items[start:end])
        start = end

    return [b for b in batches if b]  # Remove empty batches


def main():
    parser = argparse.ArgumentParser(description="Parallel Instagram Scraper")
    parser.add_argument('--workers', type=int, default=3, help='Number of parallel workers (default: 3)')
    parser.add_argument('--test', action='store_true', help='Test mode: only process first 5 grantees')
    parser.add_argument('--start', type=int, default=0, help='Start index')
    parser.add_argument('--end', type=int, default=None, help='End index')
    args = parser.parse_args()

    # Check credentials
    if not os.getenv('INSTAGRAM_USERNAME') or not os.getenv('INSTAGRAM_PASSWORD'):
        print("ERROR: INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in .env")
        sys.exit(1)

    # Get Instagram grantees
    grantees = get_instagram_grantees()
    print(f"Found {len(grantees)} grantees with Instagram URLs")

    # Apply range
    if args.test:
        grantees = grantees[:5]
        print("TEST MODE: Processing only first 5 grantees")
    elif args.end:
        grantees = grantees[args.start:args.end]
    elif args.start > 0:
        grantees = grantees[args.start:]

    if not grantees:
        print("No grantees to process")
        return

    print(f"Processing {len(grantees)} grantees with {args.workers} workers")
    print("=" * 60)

    # Split into batches
    batches = split_into_batches(grantees, args.workers)

    for i, batch in enumerate(batches):
        print(f"Batch {i+1}: {len(batch)} grantees")

    print("=" * 60)

    # Create results queue
    results_queue = mp.Queue()

    # Start worker processes with staggered delays
    processes = []
    for i, batch in enumerate(batches):
        if i > 0:
            # Stagger process starts to avoid rate limit spikes
            print(f"Waiting 15s before starting worker {i+1}...")
            time.sleep(15)

        p = mp.Process(target=scrape_batch, args=(batch, i+1, results_queue))
        p.start()
        processes.append(p)
        print(f"Started worker {i+1}")

    # Collect results
    all_results = []
    for _ in range(len(batches)):
        worker_id, results = results_queue.get()
        all_results.extend(results)
        print(f"Received results from worker {worker_id}")

    # Wait for all processes
    for p in processes:
        p.join()

    # Summary
    print("\n" + "=" * 60)
    print("INSTAGRAM SCRAPING COMPLETE")
    print("=" * 60)

    successful = sum(1 for r in all_results if r.get('success'))
    failed = len(all_results) - successful
    total_posts = sum(r.get('posts_downloaded', 0) for r in all_results)

    print(f"Total grantees: {len(all_results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total posts collected: {total_posts}")

    # Save results
    results_path = config.OUTPUT_DIR / 'instagram_scraping_results.json'
    with open(results_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_grantees': len(all_results),
            'successful': successful,
            'failed': failed,
            'total_posts': total_posts,
            'results': all_results
        }, f, indent=2)

    print(f"\nResults saved to: {results_path}")


if __name__ == '__main__':
    main()
