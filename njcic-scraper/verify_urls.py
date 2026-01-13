#!/usr/bin/env python
"""
Extract and display all grantee social media URLs for verification.
"""

import json
from pathlib import Path

GRANTEES_DIR = Path(__file__).parent.parent / "dashboard" / "data" / "grantees"

def main():
    grantees = []

    for json_file in sorted(GRANTEES_DIR.glob("*.json")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            grantees.append({
                'name': data.get('name', json_file.stem),
                'slug': json_file.stem,
                'website': data.get('website', ''),
                'social': data.get('social', {})
            })
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    print(f"Found {len(grantees)} grantees\n")
    print("="*100)

    for g in grantees:
        print(f"\n## {g['name']}")
        print(f"   Website: {g['website']}")

        social = g['social']
        if social:
            for platform, url in sorted(social.items()):
                if url:
                    print(f"   {platform:12}: {url}")
        else:
            print("   (no social media URLs)")

    print("\n" + "="*100)
    print(f"\nTotal: {len(grantees)} grantees")

if __name__ == "__main__":
    main()
