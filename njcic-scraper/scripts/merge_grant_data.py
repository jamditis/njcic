#!/usr/bin/env python3
"""
Merge grant data from njcic-grantees-map into dashboard grantee JSON files.
This script adds grant descriptions, funding amounts, focus areas, and other
grant-related information to each grantee's social media data file.
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional
import urllib.request
import ssl

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"
GRANTEES_DATA_DIR = DASHBOARD_DIR / "data" / "grantees"

# Remote grant data URL
GRANTS_DATA_URL = "https://raw.githubusercontent.com/jamditis/njcic-grantees-map/main/data/grantees.json"


def slugify(name: str) -> str:
    """Convert name to slug format matching dashboard naming convention."""
    # Convert to lowercase
    slug = name.lower()
    # Replace special characters and spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def fetch_grant_data() -> Dict:
    """Fetch grant data from GitHub."""
    print("Fetching grant data from GitHub...")

    # Create SSL context that doesn't verify (for some environments)
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(GRANTS_DATA_URL, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"  Fetched data for {len(data.get('grantees', []))} grantees")
            return data
    except Exception as e:
        print(f"  Error fetching from GitHub: {e}")
        # Try to load from local cache if available
        local_cache = Path("/tmp/njcic-grantees-map.json")
        if local_cache.exists():
            print("  Loading from local cache...")
            with open(local_cache, 'r', encoding='utf-8') as f:
                return json.load(f)
        raise


def build_grant_lookup(grant_data: Dict) -> Dict[str, Dict]:
    """
    Build a lookup dictionary mapping slugified names to grant info.
    Also builds alternative lookups for common name variations.
    """
    lookup = {}

    for grantee in grant_data.get('grantees', []):
        name = grantee.get('name', '')
        slug = slugify(name)

        # Store the grant info
        grant_info = {
            'name': name,
            'county': grantee.get('county'),
            'city': grantee.get('city'),
            'years': grantee.get('years', []),
            'totalFunding': grantee.get('amount') or grantee.get('totalAmount'),
            'status': grantee.get('status'),
            'website': grantee.get('website'),
            'focusArea': grantee.get('focusArea'),
            'description': grantee.get('description'),
            'grants': grantee.get('grants'),
            'hasMultipleGrants': grantee.get('hasMultipleGrants', False),
            'grantCount': grantee.get('grantCount', 1)
        }

        lookup[slug] = grant_info

        # Also store with common variations
        # Handle parentheticals like "Chalkbeat Newark (Civic News Company)"
        if '(' in name:
            base_name = name.split('(')[0].strip()
            base_slug = slugify(base_name)
            if base_slug not in lookup:
                lookup[base_slug] = grant_info

        # Handle "The" prefix variations
        if name.lower().startswith('the '):
            without_the = slugify(name[4:])
            if without_the not in lookup:
                lookup[without_the] = grant_info

    return lookup


def find_grant_for_grantee(grantee_slug: str, grantee_name: str, lookup: Dict) -> Optional[Dict]:
    """
    Find grant info for a grantee using various matching strategies.
    """
    # Direct slug match
    if grantee_slug in lookup:
        return lookup[grantee_slug]

    # Try slugified grantee name
    name_slug = slugify(grantee_name)
    if name_slug in lookup:
        return lookup[name_slug]

    # Try without common suffixes
    variations = [
        grantee_slug.replace('-inc', ''),
        grantee_slug.replace('-llc', ''),
        grantee_slug.replace('-nj', ''),
        grantee_slug.replace('the-', ''),
    ]

    for variation in variations:
        if variation in lookup:
            return lookup[variation]

    # Fuzzy matching: find best partial match
    for grant_slug, grant_info in lookup.items():
        # Check if one contains the other
        if grant_slug in grantee_slug or grantee_slug in grant_slug:
            return grant_info

        # Check if names are similar (case-insensitive partial match)
        grant_name_lower = grant_info['name'].lower()
        grantee_name_lower = grantee_name.lower()
        if grant_name_lower in grantee_name_lower or grantee_name_lower in grant_name_lower:
            return grant_info

    return None


def format_currency(amount: float) -> str:
    """Format amount as currency string."""
    if amount >= 1000000:
        return f"${amount/1000000:.1f}M"
    elif amount >= 1000:
        return f"${amount/1000:.0f}K"
    else:
        return f"${amount:,.0f}"


def clean_description(desc: str) -> str:
    """Clean up grant description text."""
    if not desc:
        return desc

    # Remove leading "Received funding " or similar
    desc = re.sub(r'^Received funding\s*', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'^to\s+', 'To ', desc)

    # Clean up whitespace
    desc = ' '.join(desc.split())

    # Ensure it ends with proper punctuation
    if desc and not desc[-1] in '.!?':
        desc += '.'

    return desc.strip()


def merge_grant_data_into_grantee(grantee_data: Dict, grant_info: Dict) -> Dict:
    """
    Merge grant info into existing grantee data.
    """
    # Create grantInfo section
    grant_section = {
        'totalFunding': grant_info.get('totalFunding'),
        'formattedFunding': format_currency(grant_info.get('totalFunding', 0)),
        'years': grant_info.get('years', []),
        'status': grant_info.get('status'),
        'county': grant_info.get('county'),
        'city': grant_info.get('city'),
        'focusArea': grant_info.get('focusArea'),
        'grantCount': grant_info.get('grantCount', 1),
        'hasMultipleGrants': grant_info.get('hasMultipleGrants', False)
    }

    # Process grants (either single or multiple)
    grants = grant_info.get('grants')
    if grants:
        # Multiple grants
        processed_grants = []
        for grant in grants:
            processed_grants.append({
                'id': grant.get('id'),
                'years': grant.get('years', []),
                'amount': grant.get('amount'),
                'formattedAmount': format_currency(grant.get('amount', 0)),
                'description': clean_description(grant.get('description', '')),
                'focusArea': grant.get('focusArea'),
                'status': grant.get('status')
            })
        grant_section['grants'] = processed_grants
    else:
        # Single grant
        grant_section['grants'] = [{
            'id': 1,
            'years': grant_info.get('years', []),
            'amount': grant_info.get('totalFunding'),
            'formattedAmount': format_currency(grant_info.get('totalFunding', 0)),
            'description': clean_description(grant_info.get('description', '')),
            'focusArea': grant_info.get('focusArea'),
            'status': grant_info.get('status')
        }]

    # Update grantee data
    grantee_data['grantInfo'] = grant_section

    # Also set website if not already present
    if not grantee_data.get('website') and grant_info.get('website'):
        website = grant_info['website']
        # Ensure it has protocol
        if website and not website.startswith('http'):
            website = 'https://' + website
        grantee_data['website'] = website

    return grantee_data


def main():
    """Main function to merge grant data into all grantee JSON files."""
    print("=" * 60)
    print("Merging Grant Data into Grantee Files")
    print("=" * 60)

    # Fetch grant data
    grant_data = fetch_grant_data()

    # Build lookup
    print("\nBuilding grant lookup table...")
    lookup = build_grant_lookup(grant_data)
    print(f"  Created lookup with {len(lookup)} entries")

    # Find all grantee JSON files
    grantee_files = list(GRANTEES_DATA_DIR.glob("*.json"))
    print(f"\nProcessing {len(grantee_files)} grantee files...")

    matched = 0
    unmatched = []

    for json_file in sorted(grantee_files):
        slug = json_file.stem

        # Read existing data
        with open(json_file, 'r', encoding='utf-8') as f:
            grantee_data = json.load(f)

        name = grantee_data.get('name', slug.replace('-', ' ').title())

        # Find matching grant info
        grant_info = find_grant_for_grantee(slug, name, lookup)

        if grant_info:
            # Merge grant data
            grantee_data = merge_grant_data_into_grantee(grantee_data, grant_info)

            # Write back
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(grantee_data, f, indent=2, ensure_ascii=False)

            funding = format_currency(grant_info.get('totalFunding', 0))
            grants = grant_info.get('grantCount', 1)
            print(f"  ✓ {name}: {funding} ({grants} grant{'s' if grants > 1 else ''})")
            matched += 1
        else:
            print(f"  ✗ {name}: No matching grant found")
            unmatched.append(name)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Matched: {matched}/{len(grantee_files)} grantees")
    print(f"  Unmatched: {len(unmatched)} grantees")

    if unmatched:
        print("\nUnmatched grantees:")
        for name in unmatched:
            print(f"  - {name}")

    print("\nDone!")


if __name__ == '__main__':
    main()
