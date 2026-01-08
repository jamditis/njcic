#!/usr/bin/env python3
"""
Update grantee detail page navigation to match the main site navigation.

This script:
1. Replaces the existing header/nav structure in grantee pages
2. Adds consistent navigation matching index.html (with ../ prefixes)
3. Adds skip link for accessibility
4. Adds proper breadcrumb with aria-label
5. Sets "Grantees" as the active nav item with aria-current="page"
"""

import os
import re
from pathlib import Path


def get_canonical_nav(grantee_name: str) -> str:
    """
    Generate the canonical nav HTML for grantee pages.

    Args:
        grantee_name: The display name of the grantee for breadcrumb

    Returns:
        HTML string for the navigation section
    """
    return f'''    <!-- Skip Link for Accessibility -->
    <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-white focus:rounded-lg">
        Skip to main content
    </a>

    <!-- Navigation -->
    <nav id="main-nav" class="sticky top-0 z-40 w-full bg-white shadow-sm">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <!-- Logo -->
                <div class="flex-shrink-0 flex items-center gap-2">
                    <a href="../index.html" class="flex items-center gap-2">
                        <div class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white font-bold text-sm">NJ</div>
                        <span class="text-lg font-bold text-slate-900 tracking-tight">NJCIC <span class="text-slate-400 font-normal hidden sm:inline">Dashboard</span></span>
                    </a>
                </div>

                <!-- Desktop Menu -->
                <div class="hidden md:flex items-center space-x-1">
                    <a href="../index.html#overview" class="nav-link px-3 py-2 rounded-md text-sm">Overview</a>
                    <a href="../index.html#grantees" class="nav-link px-3 py-2 rounded-md text-sm font-semibold text-primary" aria-current="page">Grantees</a>
                    <a href="../index.html#rankings" class="nav-link px-3 py-2 rounded-md text-sm">Rankings</a>
                    <a href="../platforms.html" class="nav-link px-3 py-2 rounded-md text-sm">Platforms</a>
                    <a href="../about.html" class="nav-link px-3 py-2 rounded-md text-sm">About</a>
                </div>

                <!-- Mobile Toggle -->
                <div class="flex items-center gap-3">
                    <button id="mobile-menu-btn" class="md:hidden p-2 text-slate-600 hover:text-slate-900" aria-expanded="false" aria-controls="mobile-menu">
                        <span class="sr-only">Open main menu</span>
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                        </svg>
                    </button>
                </div>
            </div>
        </div>

        <!-- Mobile Menu -->
        <div id="mobile-menu" class="hidden md:hidden bg-white border-t border-slate-100 py-2 shadow-lg">
            <a href="../index.html#overview" class="block px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Overview</a>
            <a href="../index.html#grantees" class="block px-4 py-2 text-sm text-primary font-semibold bg-slate-50" aria-current="page">Grantees</a>
            <a href="../index.html#rankings" class="block px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Rankings</a>
            <a href="../platforms.html" class="block px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">Platforms</a>
            <a href="../about.html" class="block px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">About</a>
        </div>
    </nav>

    <!-- Breadcrumb -->
    <nav class="bg-slate-50 border-b border-slate-200" aria-label="Breadcrumb">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
            <ol class="flex items-center text-sm">
                <li>
                    <a href="../index.html" class="text-slate-500 hover:text-primary transition-colors">Dashboard</a>
                </li>
                <li class="flex items-center">
                    <svg class="w-4 h-4 mx-2 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                    <a href="../index.html#grantees" class="text-slate-500 hover:text-primary transition-colors">Grantees</a>
                </li>
                <li class="flex items-center">
                    <svg class="w-4 h-4 mx-2 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                    <span id="breadcrumb-name" class="text-slate-900 font-medium">{grantee_name}</span>
                </li>
            </ol>
        </div>
    </nav>'''


def extract_grantee_name(html_content: str, filename: str) -> str:
    """
    Extract the grantee name from the HTML content.

    Args:
        html_content: The HTML content of the grantee page
        filename: The filename as fallback

    Returns:
        The grantee name for display
    """
    # Try to get from title tag
    title_match = re.search(r'<title>([^<]+?)\s*[-–]\s*NJCIC', html_content)
    if title_match:
        return title_match.group(1).strip()

    # Try to get from h2 with id="grantee-name"
    h2_match = re.search(r'<h2[^>]*id="grantee-name"[^>]*>([^<]+)</h2>', html_content)
    if h2_match:
        return h2_match.group(1).strip()

    # Try to get from breadcrumb-name span
    breadcrumb_match = re.search(r'<span[^>]*id="breadcrumb-name"[^>]*>([^<]+)</span>', html_content)
    if breadcrumb_match:
        return breadcrumb_match.group(1).strip()

    # Fall back to filename
    name = filename.replace('.html', '').replace('-', ' ').title()
    return name


def update_grantee_nav(filepath: Path) -> bool:
    """
    Update the navigation in a grantee page.

    Args:
        filepath: Path to the HTML file

    Returns:
        True if updated successfully, False otherwise
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract grantee name
        grantee_name = extract_grantee_name(content, filepath.name)

        # Generate the new nav
        new_nav = get_canonical_nav(grantee_name)

        # Pattern to find the old header section (from after main-content div to before hero section)
        # The old structure has a header with nav inside it
        old_header_pattern = re.compile(
            r'(<div id="main-content"[^>]*>)\s*'
            r'(?:<!-- Skip Link[^>]*>.*?</a>\s*)?'  # Optional existing skip link
            r'(?:<!-- Navigation -->.*?</nav>\s*)?'  # Optional existing nav
            r'(?:<!-- Breadcrumb -->.*?</nav>\s*)?'  # Optional existing breadcrumb
            r'(?:<!-- Header[^>]*>)?\s*'
            r'<header[^>]*>.*?</header>\s*',
            re.DOTALL
        )

        # Check if old pattern matches
        if old_header_pattern.search(content):
            # Replace the old header with new nav
            new_content = old_header_pattern.sub(
                r'\1\n' + new_nav + '\n\n',
                content
            )
        else:
            # Try alternative pattern - just after main-content div opening
            alt_pattern = re.compile(
                r'(<div id="main-content"[^>]*>)\s*'
                r'(<!-- Skip Link.*?</a>\s*)?'
                r'(<!-- Navigation -->.*?</nav>\s*)?'
                r'(<!-- Breadcrumb -->.*?</nav>\s*)?'
                r'(<header[^>]*>.*?</header>)',
                re.DOTALL
            )

            if alt_pattern.search(content):
                new_content = alt_pattern.sub(
                    r'\1\n' + new_nav + '\n\n',
                    content
                )
            else:
                # Last resort: just find header and replace
                header_only_pattern = re.compile(
                    r'<header[^>]*class="[^"]*bg-njcic-dark[^"]*"[^>]*>.*?</header>',
                    re.DOTALL
                )

                if header_only_pattern.search(content):
                    # Find the position after main-content opening
                    main_content_match = re.search(r'(<div id="main-content"[^>]*>)', content)
                    if main_content_match:
                        insert_pos = main_content_match.end()
                        # Remove old header
                        content_no_header = header_only_pattern.sub('', content)
                        # Also remove any existing skip link and nav
                        content_no_header = re.sub(
                            r'<!-- Skip Link[^>]*>.*?</a>\s*',
                            '',
                            content_no_header,
                            flags=re.DOTALL
                        )
                        # Insert new nav after main-content opening
                        main_content_match = re.search(r'(<div id="main-content"[^>]*>)', content_no_header)
                        if main_content_match:
                            insert_pos = main_content_match.end()
                            new_content = (
                                content_no_header[:insert_pos] +
                                '\n' + new_nav + '\n\n' +
                                content_no_header[insert_pos:].lstrip()
                            )
                        else:
                            print(f"  Warning: Could not find main-content div in {filepath.name}")
                            return False
                    else:
                        print(f"  Warning: Could not find main-content div in {filepath.name}")
                        return False
                else:
                    print(f"  Warning: Could not find header pattern in {filepath.name}")
                    return False

        # Write the updated content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"  Updated: {filepath.name} (grantee: {grantee_name})")
        return True

    except Exception as e:
        print(f"  Error processing {filepath.name}: {e}")
        return False


def main():
    """Main entry point."""
    # Get the script directory and navigate to grantees folder
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    grantees_dir = project_root / 'dashboard' / 'grantees'

    if not grantees_dir.exists():
        print(f"Error: Grantees directory not found at {grantees_dir}")
        return

    print(f"Processing grantee pages in: {grantees_dir}")
    print("-" * 60)

    html_files = list(grantees_dir.glob('*.html'))

    if not html_files:
        print("No HTML files found in grantees directory.")
        return

    print(f"Found {len(html_files)} grantee pages to update.\n")

    success_count = 0
    error_count = 0

    for html_file in sorted(html_files):
        if update_grantee_nav(html_file):
            success_count += 1
        else:
            error_count += 1

    print("-" * 60)
    print(f"Complete! Updated {success_count} pages, {error_count} errors.")


if __name__ == '__main__':
    main()
