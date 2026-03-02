# CLAUDE.md - Project instructions for Claude Code


## GitHub Actions suspended (account-wide)

GitHub Actions are disabled on the entire `jamditis` GitHub account until further notice. This means:
- **No CI/CD pipelines will run** — builds, tests, deploys all fail silently
- **GitHub Pages deploys won't work** — even "legacy" static deploys that used Actions under the hood
- **No automated workflows** — PR checks, scheduled jobs, release automation are all dead

**For any project that previously deployed via GitHub Actions or GitHub Pages, you must use an alternative** (manual deploy, Cloudflare Pages, Firebase Hosting, direct FTP, etc.). Do not create or rely on `.github/workflows/` files.

## Repository overview

This repository contains materials for the New Jersey Civic Information Consortium (NJCIC), including:
- Dashboard for tracking grantee social media metrics
- Scraper tools for collecting social media data
- Research documents and analysis
- Branding materials

## Style rules

### Sentence case for all headings and titles

**IMPORTANT: This project uses sentence case for all user-facing text. Title Case is prohibited.**

#### What is sentence case?
Sentence case capitalizes only the first word and proper nouns, like a normal sentence.

#### Examples

| Incorrect (Title Case) | Correct (Sentence case) |
|------------------------|-------------------------|
| About The Dashboard | About the dashboard |
| View All Grantees | View all grantees |
| Platform Analytics | Platform analytics |
| Social Media Performance | Social media performance |
| Getting Started Guide | Getting started guide |

#### What to capitalize in sentence case:
- First word of the heading/title
- Proper nouns (New Jersey, NJCIC, specific organization names)
- Acronyms (API, JSON, HTML, CSS)
- Platform names when they are proper nouns (Instagram, TikTok, YouTube)

#### What NOT to capitalize:
- Common words like "the", "and", "of", "for", "to", "in", "on", "with"
- Generic descriptive words like "dashboard", "analytics", "performance", "guide"
- Any word that isn't the first word or a proper noun

#### Where this applies:
- HTML headings (h1-h6)
- Page titles and meta titles
- Markdown headings (# ## ### etc.)
- Button text and link text
- Navigation items
- Section headers
- Chart titles and labels
- Table headers
- Error messages
- Any other user-facing text

#### Proper nouns to preserve:
- New Jersey
- NJCIC (New Jersey Civic Information Consortium)
- Organization/grantee names (e.g., "NJ Spotlight News", "Inside Climate News")
- Platform names (Instagram, Facebook, TikTok, YouTube, LinkedIn, Threads, Bluesky)
- Technical proper nouns (Playwright, Python, JavaScript)

## Code conventions

- Use camelCase for JavaScript variables and functions
- Use kebab-case for file names and CSS classes
- Keep JSON data files focused on data, not UI labels
