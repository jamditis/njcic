#!/usr/bin/env python
"""
Batch scraper for all NJCIC grantees.
Reads grantee JSON files and generates scraping commands or runs them.

Usage:
    # List all grantees and their social URLs
    python batch_scrape.py --list

    # Generate scraping commands for a specific platform
    python batch_scrape.py --commands twitter

    # Export grantee social URLs to CSV
    python batch_scrape.py --export grantees_social.csv
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Path to grantee data files
GRANTEES_DIR = Path(__file__).parent.parent / "dashboard" / "data" / "grantees"


def load_all_grantees():
    """Load all grantee JSON files and extract social media info."""
    grantees = []

    if not GRANTEES_DIR.exists():
        print(f"ERROR: Grantees directory not found: {GRANTEES_DIR}")
        return []

    for json_file in GRANTEES_DIR.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            grantee = {
                'name': data.get('name', json_file.stem),
                'slug': data.get('slug', json_file.stem),
                'file': json_file.name,
                'social': data.get('social', {}),
                'website': data.get('website', ''),
            }
            grantees.append(grantee)
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return sorted(grantees, key=lambda x: x['name'])


def list_grantees(grantees):
    """Print all grantees and their social media presence."""
    print(f"\nFound {len(grantees)} grantees:\n")
    print("-" * 80)

    for g in grantees:
        platforms = list(g['social'].keys())
        platform_str = ", ".join(platforms) if platforms else "(no social)"
        print(f"{g['name']}")
        print(f"  Platforms: {platform_str}")
        print()


def generate_commands(grantees, platform):
    """Generate scraping commands for a specific platform."""
    platform = platform.lower()
    commands = []

    for g in grantees:
        url = g['social'].get(platform)
        if url:
            cmd = f'python scrape_grantee.py -p {platform} -g "{g["name"]}" -u "{url}"'
            commands.append({
                'grantee': g['name'],
                'platform': platform,
                'url': url,
                'command': cmd
            })

    print(f"\n{len(commands)} grantees have {platform}:\n")
    print("-" * 80)

    for c in commands:
        print(f"# {c['grantee']}")
        print(c['command'])
        print()

    return commands


def export_csv(grantees, filename):
    """Export all grantee social URLs to CSV."""
    import csv

    platforms = ['twitter', 'instagram', 'facebook', 'tiktok', 'youtube', 'linkedin', 'bluesky', 'threads']

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        header = ['grantee_name', 'slug', 'website'] + platforms
        writer.writerow(header)

        # Data
        for g in grantees:
            row = [g['name'], g['slug'], g['website']]
            for p in platforms:
                row.append(g['social'].get(p, ''))
            writer.writerow(row)

    print(f"\nExported {len(grantees)} grantees to {filename}")


def platform_summary(grantees):
    """Show summary of how many grantees have each platform."""
    platforms = ['twitter', 'instagram', 'facebook', 'tiktok', 'youtube', 'linkedin', 'bluesky', 'threads']

    print("\nPlatform coverage:\n")
    print("-" * 40)

    for p in platforms:
        count = sum(1 for g in grantees if g['social'].get(p))
        pct = (count / len(grantees)) * 100 if grantees else 0
        bar = "=" * int(pct / 5)
        print(f"{p:12} {count:3} ({pct:5.1f}%) {bar}")

    print("-" * 40)
    print(f"Total grantees: {len(grantees)}")


def main():
    parser = argparse.ArgumentParser(
        description='Batch utilities for NJCIC grantee social media scraping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python batch_scrape.py --list
    python batch_scrape.py --summary
    python batch_scrape.py --commands twitter
    python batch_scrape.py --commands instagram
    python batch_scrape.py --export grantees_social.csv
        '''
    )

    parser.add_argument('--list', action='store_true',
                        help='List all grantees and their platforms')
    parser.add_argument('--summary', action='store_true',
                        help='Show platform coverage summary')
    parser.add_argument('--commands', metavar='PLATFORM',
                        help='Generate scraping commands for a platform')
    parser.add_argument('--export', metavar='FILENAME',
                        help='Export grantee social URLs to CSV')

    args = parser.parse_args()

    grantees = load_all_grantees()

    if not grantees:
        print("No grantees found!")
        return

    if args.list:
        list_grantees(grantees)
    elif args.summary:
        platform_summary(grantees)
    elif args.commands:
        generate_commands(grantees, args.commands)
    elif args.export:
        export_csv(grantees, args.export)
    else:
        # Default: show summary
        platform_summary(grantees)


if __name__ == "__main__":
    main()
