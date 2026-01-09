# NJCIC digital style guide

**New Jersey Civic Information Consortium**

*Version 1.0 | January 2026*

---

## 1. Brand overview

### Mission and purpose

The New Jersey Civic Information Consortium (NJCIC) is a first-of-its-kind 501(c)(3) nonprofit established by the State of New Jersey to support the revitalization of local news and civic information across the state.

**Core purpose:** To advance research and innovation in media and technology that benefits New Jersey's civic life and evolving information needs.

**Key objectives:**
- Improve the quantity and quality of civic information in New Jersey communities
- Give residents enhanced access to government data and public information
- Train students, professionals, and community members in journalism and media production
- Nurture civic engagement and dialogue between New Jersey communities
- Serve underserved communities, including low-income and communities of color
- Invest in sustainable media practices and research

### Brand personality

**Voice attributes:**
- **Authoritative but accessible** - We speak with expertise while remaining approachable
- **Civic-minded** - Our focus is public service and community benefit
- **Trustworthy** - We represent transparency and reliability in information
- **Forward-looking** - We embrace innovation while respecting journalism traditions
- **Inclusive** - We speak to and serve all New Jersey communities

### Target audiences

**Primary:**
- New Jersey residents seeking local news and civic information
- Local news organizations and journalists
- Academic institutions and researchers
- Community organizations and nonprofits

**Secondary:**
- State legislators and policymakers
- Philanthropic organizations
- Media industry stakeholders
- Students in journalism and communications

---

## 2. Logo

### Primary logo

The NJCIC logo features a circular design that symbolizes community connection and the cyclical nature of information flow. The logo is available in:

- **Circle logo (full color)** - `NJCIC-Circle-Logo-Full-Color.png`
- **Rectangular/header version** - For horizontal applications

### Usage guidelines

**Minimum clear space:**
- Maintain clear space equal to the height of "NJ" on all sides
- Never crowd the logo with other elements

**Minimum sizes:**
- Desktop display: 75px width
- Mobile/collapsed navigation: 62px width
- Print: 0.75 inches minimum width

**Logo placement:**
- Always position on solid backgrounds
- Preferred placement is top-left for digital applications
- For the dashboard, use a circular gradient version with "NJ" text

### Logo don'ts

- Do not stretch or distort the logo
- Do not change the logo colors outside approved palette
- Do not add effects (shadows, glows, bevels) to the logo
- Do not place on busy backgrounds without sufficient contrast
- Do not rotate the logo

---

## 3. Color palette

### Primary colors

| Color | Name | Hex | RGB | Usage |
|-------|------|-----|-----|-------|
| ![#2dc8d2](https://via.placeholder.com/20/2dc8d2/2dc8d2.png) | **NJCIC Teal** | `#2dc8d2` | `45, 200, 210` | Brand accent, decorative elements, icons, gradients |
| ![#f34213](https://via.placeholder.com/20/f34213/f34213.png) | **NJCIC Orange** | `#f34213` | `243, 66, 19` | Secondary accent, calls-to-action, energy elements |
| ![#183642](https://via.placeholder.com/20/183642/183642.png) | **NJCIC Dark Navy** | `#183642` | `24, 54, 66` | Primary backgrounds, headers, navigation |

### Extended teal palette (accessibility-compliant)

| Color | Name | Hex | Usage |
|-------|------|-----|-------|
| ![#2dc8d2](https://via.placeholder.com/20/2dc8d2/2dc8d2.png) | Teal (bright) | `#2dc8d2` | Decorative use only - fails WCAG on white |
| ![#0e7c86](https://via.placeholder.com/20/0e7c86/0e7c86.png) | **Teal Dark** | `#0e7c86` | **Primary text/links on light backgrounds** (5.7:1 contrast) |
| ![#095057](https://via.placeholder.com/20/095057/095057.png) | Teal Darker | `#095057` | Small text, hover states |

### Extended orange palette

| Color | Name | Hex | Usage |
|-------|------|-----|-------|
| ![#f34213](https://via.placeholder.com/20/f34213/f34213.png) | Orange (primary) | `#f34213` | Accent elements, progress indicators |
| ![#c73610](https://via.placeholder.com/20/c73610/c73610.png) | Orange Dark | `#c73610` | Text on light backgrounds, accessible buttons |

### Neutral colors

| Color | Name | Hex | Usage |
|-------|------|-----|-------|
| ![#2b3436](https://via.placeholder.com/20/2b3436/2b3436.png) | NJCIC Gray | `#2b3436` | Secondary dark backgrounds, footer |
| ![#475569](https://via.placeholder.com/20/475569/475569.png) | Slate 600 | `#475569` | Body text on light backgrounds |
| ![#64748b](https://via.placeholder.com/20/64748b/64748b.png) | Slate 500 | `#64748b` | Secondary text, labels |
| ![#94a3b8](https://via.placeholder.com/20/94a3b8/94a3b8.png) | Slate 400 | `#94a3b8` | Placeholder text |
| ![#cbd5e1](https://via.placeholder.com/20/cbd5e1/cbd5e1.png) | Slate 300 | `#cbd5e1` | Text on dark backgrounds |
| ![#e2e8f0](https://via.placeholder.com/20/e2e8f0/e2e8f0.png) | Slate 200 | `#e2e8f0` | Borders, dividers |
| ![#f1f5f9](https://via.placeholder.com/20/f1f5f9/f1f5f9.png) | Slate 100 | `#f1f5f9` | Light backgrounds |
| ![#f8fafc](https://via.placeholder.com/20/f8fafc/f8fafc.png) | Slate 50 | `#f8fafc` | Page backgrounds |
| ![#e8f9fa](https://via.placeholder.com/20/e8f9fa/e8f9fa.png) | NJCIC Light | `#e8f9fa` | Tinted backgrounds |

### Background colors

| Use case | Color | Hex |
|----------|-------|-----|
| Page background | Slate 50 | `#f8fafc` |
| Card background | White | `#ffffff` |
| Header/navigation | NJCIC Dark Navy | `#183642` |
| Footer top | NJCIC Gray | `#2b3436` |
| Footer bottom | Dark | `#202628` |
| Highlighted sections | NJCIC Light | `#e8f9fa` |

### Gradients

**Primary gradient (teal to dark):**
```css
background: linear-gradient(135deg, #2dc8d2 0%, #183642 100%);
```

**Accent stripe:**
```css
background: linear-gradient(to right, #2dc8d2, #f34213, #2dc8d2);
```

**Hero section:**
```css
background: linear-gradient(to bottom right, #183642, #2b3436, #183642);
```

### Color usage guidelines

1. **Never use bright teal (#2dc8d2) for text on white** - It fails WCAG AA contrast requirements
2. **Use #0e7c86 for clickable text/links** - This provides 5.7:1 contrast ratio
3. **Use gradients for decorative elements** - Headers, dividers, accent bars
4. **Orange is for emphasis** - Use sparingly for key CTAs and progress indicators
5. **Maintain 4.5:1 contrast ratio minimum** for body text (WCAG AA compliance)

---

## 4. Typography

### Font families

**Primary heading font:**
- **Libre Baskerville** - Serif typeface conveying editorial authority and trustworthiness
- Weights: Regular (400), Bold (700), Italic (400)
- Use for: Headlines, section titles, statistics, quotes

**Primary body font:**
- **Source Sans 3** - Clean sans-serif for readability
- Weights: Light (300), Regular (400), Medium (500), SemiBold (600), Bold (700)
- Use for: Body text, navigation, buttons, form elements

### Web-safe fallbacks

```css
/* Heading fallbacks */
font-family: 'Libre Baskerville', Georgia, 'Times New Roman', serif;

/* Body fallbacks */
font-family: 'Source Sans 3', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

### Type hierarchy

| Element | Font | Size | Weight | Line height | Letter spacing |
|---------|------|------|--------|-------------|----------------|
| H1 | Libre Baskerville | 2.5rem (40px) | 700 | 1.2 | -0.01em |
| H2 | Libre Baskerville | 1.875rem (30px) | 700 | 1.3 | -0.01em |
| H3 | Libre Baskerville | 1.5rem (24px) | 700 | 1.4 | -0.01em |
| H4 | Libre Baskerville | 1.25rem (20px) | 700 | 1.4 | -0.01em |
| H5 | Libre Baskerville | 1.125rem (18px) | 700 | 1.5 | -0.01em |
| H6 | Libre Baskerville | 1rem (16px) | 700 | 1.5 | -0.01em |
| Body | Source Sans 3 | 1rem (16px) | 400 | 1.5 | normal |
| Body large | Source Sans 3 | 1.125rem (18px) | 400 | 1.6 | normal |
| Small/Caption | Source Sans 3 | 0.875rem (14px) | 400 | 1.5 | normal |
| Label | Source Sans 3 | 0.6875rem (11px) | 700 | 1.5 | 0.1em |
| Metric numbers | Libre Baskerville | varies | 700 | 1 | -0.03em |

### Typography CSS

```css
:root {
    --font-family: 'Source Sans 3', system-ui, -apple-system, sans-serif;
    --font-heading: 'Libre Baskerville', Georgia, 'Times New Roman', serif;
}

h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-heading);
    font-weight: 700;
    letter-spacing: -0.01em;
}

body {
    font-family: var(--font-family);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Statistics and metrics */
.metric-number {
    font-family: var(--font-heading);
    font-variant-numeric: tabular-nums;
    font-weight: 700;
    letter-spacing: -0.03em;
}
```

---

## 5. Imagery

### Photography style

**Preferred subjects:**
- New Jersey communities and neighborhoods
- Local journalism in action
- Community gatherings and civic events
- Diverse representation of NJ residents
- Technology and media production

**Photo treatment:**
- Natural lighting preferred
- Authentic, documentary-style captures
- Avoid overly staged or stock-looking images
- Color-graded to complement the NJCIC palette when used as backgrounds

**Photo overlays:**
When using photos as backgrounds:
```css
/* Dark overlay for text readability */
background: linear-gradient(to bottom right,
    rgba(24, 54, 66, 0.85),
    rgba(43, 52, 54, 0.9)
), url('image.jpg');
```

### Illustration style

NJCIC uses minimal illustration, favoring:
- Clean, geometric iconography
- Data visualization and infographics
- Subtle pattern backgrounds (dot grids, topographic lines)

### Icon style

**Characteristics:**
- Stroke-based icons (2px stroke weight)
- Rounded line caps and joins
- Single color (adapts to context)
- 24x24px standard size
- Heroicons or similar minimal icon set

**Icon usage:**
```html
<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <!-- Icon path -->
</svg>
```

### Do's and don'ts

**Do:**
- Use high-resolution images (minimum 2x for retina)
- Ensure proper image alt text for accessibility
- Compress images appropriately for web
- Use images that represent New Jersey's diversity

**Don't:**
- Use low-quality or pixelated images
- Use generic stock photos that could be anywhere
- Use images without proper licensing
- Overlay text on busy image areas without sufficient contrast

---

## 6. UI components (for digital)

### Button styles

**Primary button:**
```css
.btn-primary {
    background: linear-gradient(135deg, #0e7c86 0%, #095057 100%);
    color: white;
    padding: 0.75rem 1.5rem;
    border-radius: 12px;
    font-weight: 600;
    box-shadow: 0 4px 14px rgba(14, 124, 134, 0.35);
}

.btn-primary:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 28px rgba(14, 124, 134, 0.45);
}
```

**Secondary button (orange):**
```css
.btn-secondary {
    background: linear-gradient(135deg, #c73610 0%, #a52a0c 100%);
    color: white;
    padding: 0.75rem 1.5rem;
    border-radius: 12px;
    font-weight: 600;
}
```

**Outline button:**
```css
.btn-outline {
    background: transparent;
    color: #0e7c86;
    border: 2px solid #0e7c86;
    padding: 0.75rem 1.5rem;
    border-radius: 12px;
}

.btn-outline:hover {
    background: #0e7c86;
    color: white;
}
```

**Ghost button:**
```css
.btn-ghost {
    background: transparent;
    color: #183642;
}

.btn-ghost:hover {
    background: rgba(45, 200, 210, 0.12);
    color: #0e7c86;
}
```

### Form elements

**Text inputs:**
```css
input, select, textarea {
    background: #ffffff;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    font-family: 'Source Sans 3', sans-serif;
    font-size: 0.875rem;
    transition: border-color 0.2s, box-shadow 0.2s;
}

input:focus, select:focus, textarea:focus {
    border-color: #2dc8d2;
    box-shadow: 0 0 0 4px rgba(45, 200, 210, 0.12);
    outline: none;
}
```

**Select dropdowns:**
- Custom arrow icon
- Same styling as text inputs
- Clear visual feedback on focus

### Cards

**Standard card:**
```css
.card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    box-shadow: 0 1px 3px rgba(24, 54, 66, 0.06);
    transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 24px rgba(24, 54, 66, 0.12);
    border-color: #2dc8d2;
}
```

**Card with gradient accent:**
Cards can feature a top gradient bar that animates on hover:
```css
.card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #2dc8d2 0%, #0e7c86 40%, #f34213 100%);
    transform: scaleX(0);
    transition: transform 0.5s ease;
}

.card:hover::before {
    transform: scaleX(1);
}
```

### Navigation patterns

**Primary navigation:**
- Dark background (#183642)
- White text links with 85% opacity
- Hover: Full opacity + subtle background
- Active: Teal background tint + gradient underline

```css
.nav-link {
    color: rgba(255, 255, 255, 0.85);
    padding: 0.5rem 0.875rem;
    border-radius: 0.375rem;
}

.nav-link:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.1);
}

.nav-link.active::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0.5rem;
    right: 0.5rem;
    height: 2px;
    background: linear-gradient(90deg, #2dc8d2, #f34213);
}
```

### Spacing system

Use an 8px base unit:

| Token | Value | Use case |
|-------|-------|----------|
| `--space-1` | 4px | Tight gaps |
| `--space-2` | 8px | Element padding |
| `--space-3` | 12px | Compact spacing |
| `--space-4` | 16px | Standard gaps |
| `--space-5` | 20px | Component padding |
| `--space-6` | 24px | Card padding |
| `--space-8` | 32px | Section gaps |
| `--space-10` | 40px | Large gaps |
| `--space-12` | 48px | Section padding |
| `--space-16` | 64px | Section margins |
| `--space-20` | 80px | Major separations |

### Shadow system

```css
:root {
    --shadow-xs: 0 1px 2px rgba(24, 54, 66, 0.04);
    --shadow-sm: 0 1px 3px rgba(24, 54, 66, 0.06), 0 1px 2px rgba(24, 54, 66, 0.04);
    --shadow-md: 0 4px 8px rgba(24, 54, 66, 0.08), 0 2px 4px rgba(24, 54, 66, 0.04);
    --shadow-lg: 0 12px 24px rgba(24, 54, 66, 0.12), 0 4px 8px rgba(24, 54, 66, 0.04);
    --shadow-xl: 0 24px 48px rgba(24, 54, 66, 0.16), 0 8px 16px rgba(24, 54, 66, 0.06);

    /* Colored shadows */
    --shadow-teal: 0 8px 24px rgba(45, 200, 210, 0.25);
    --shadow-orange: 0 8px 24px rgba(243, 66, 19, 0.2);
}
```

---

## 7. Voice and tone

### Writing style

**General principles:**
- Write in sentence case, not Title Case
- Use active voice
- Keep sentences concise
- Avoid jargon when possible
- Write for accessibility (clear, simple language)

**Tone adjustments by context:**

| Context | Tone |
|---------|------|
| Headlines | Bold, direct, impactful |
| Body copy | Informative, conversational |
| Grant announcements | Celebratory, specific |
| Data/research | Precise, objective |
| Community outreach | Warm, inclusive |

### Key messages

**Primary message:**
"Strengthening local news and civic engagement across New Jersey."

**Supporting messages:**
- "Investing in the future of community journalism"
- "Connecting New Jersey residents with trusted local information"
- "Supporting underserved communities through civic media"

### Words to use

- Community, residents, neighbors
- Local, civic, public interest
- Support, fund, invest
- Strengthen, enhance, improve
- Access, transparency, engagement
- Inform, connect, serve

### Words to avoid

- Leverage, synergy, ecosystem (corporate jargon)
- Revolutionary, groundbreaking (hyperbole)
- Simply, just, obviously (dismissive)
- Comprehensive, robust, holistic (overused filler)
- Cutting-edge, state-of-the-art (cliches)

---

## 8. Social media

### Profile standards

**Handle:** @NJCivicInfo (consistent across platforms)

**Bio elements:**
- Clear statement of purpose
- Location: New Jersey
- Link to njcivicinfo.org
- Founding year when space permits

**Profile image:**
- NJCIC circle logo
- Consistent across all platforms
- High resolution (minimum 400x400px)

**Cover/header images:**
- Feature the teal-to-dark gradient
- Include tagline or key message
- Update seasonally or for major initiatives

### Post templates

**Grant announcement:**
```
[Grantee Name] has received $[amount] from NJCIC to [brief description of project].

This project will [impact statement].

Learn more: [link]

#NJCivicInfo #LocalNews #NewJersey
```

**Event promotion:**
```
Join us for [Event Name]

[Date] | [Time]
[Location/Virtual]

[Brief description]

Register: [link]

#NJCivicInfo
```

**Impact statistic:**
```
By the numbers:

[Number] grants awarded
$[Amount] invested in NJ communities
[Number] organizations supported

That's the power of public investment in local news.

#NJCivicInfo #LocalJournalism
```

### Hashtags

**Primary:** #NJCivicInfo

**Secondary:**
- #LocalNews
- #NewJersey
- #CivicMedia
- #LocalJournalism
- #CommunityNews

**Campaign-specific:** Create unique hashtags for major initiatives

### Platform-specific notes

**X/Twitter:**
- Shorter updates, link to full content
- Engage with grantees and partners
- Thread longer stories

**LinkedIn:**
- Professional tone
- Industry insights
- Grant announcements
- Partner highlights

**Instagram:**
- Visual-first content
- Behind-the-scenes of grantee work
- Story highlights for each grantee cohort

**Facebook:**
- Community-focused content
- Event promotion
- Longer-form posts acceptable

---

## 9. Accessibility

### Contrast requirements

**WCAG AA compliance (minimum 4.5:1 for normal text):**

| Text type | Background | Compliant color |
|-----------|------------|-----------------|
| Body text | White | Slate 600 (#475569) or darker |
| Links | White | Teal Dark (#0e7c86) - 5.7:1 |
| Small text | White | Teal Darker (#095057) - 7.6:1 |
| Text on dark | Dark Navy | White or Slate 200 |

**Non-compliant (decorative only):**
- Bright teal (#2dc8d2) on white: 2.9:1 - FAILS

### Alt text guidelines

**Required for:**
- All informational images
- Charts and graphs (describe data)
- Icons that convey meaning

**Not required for:**
- Decorative images (use `alt=""`)
- Icons paired with visible text labels

**Best practices:**
- Be concise but descriptive
- Don't start with "Image of" or "Photo of"
- Include relevant context
- For complex charts, provide text alternative

**Examples:**
```html
<!-- Good -->
<img alt="Map showing 76 NJCIC grantee locations across New Jersey">

<!-- For decorative -->
<img alt="" role="presentation">
```

### Keyboard navigation

**Requirements:**
- All interactive elements focusable via Tab key
- Visible focus indicators
- Skip links for main content
- No keyboard traps
- Logical focus order

**Focus styles:**
```css
:focus-visible {
    outline: 2px solid #2dc8d2;
    outline-offset: 2px;
}

/* Skip link */
.skip-link {
    position: absolute;
    left: -9999px;
}

.skip-link:focus {
    position: fixed;
    top: 1rem;
    left: 1rem;
    z-index: 9999;
    background: white;
    padding: 0.5rem 1rem;
}
```

### Additional accessibility requirements

- **Headings:** Use proper hierarchy (H1 > H2 > H3)
- **Forms:** Label all inputs, provide error messages
- **Motion:** Respect `prefers-reduced-motion`
- **Color:** Never use color alone to convey information
- **Links:** Use descriptive link text (not "click here")
- **Tables:** Include proper headers and captions

```css
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
```

---

## Appendix A: CSS custom properties reference

```css
:root {
    /* NJCIC Official Brand Colors */
    --njcic-teal: #2dc8d2;
    --njcic-teal-dark: #0e7c86;
    --njcic-teal-darker: #095057;
    --njcic-orange: #f34213;
    --njcic-orange-dark: #c73610;
    --njcic-dark: #183642;
    --njcic-gray: #2b3436;
    --njcic-light: #e8f9fa;

    /* Semantic Colors */
    --color-primary: #0e7c86;
    --color-primary-light: #2dc8d2;
    --color-primary-dark: #095057;
    --color-accent: #f34213;
    --color-accent-dark: #c73610;
    --color-dark: #183642;
    --color-dark-800: #2b3436;

    /* Neutrals */
    --color-gray-600: #475569;
    --color-gray-500: #64748b;
    --color-gray-400: #94a3b8;
    --color-gray-300: #cbd5e1;
    --color-gray-200: #e2e8f0;
    --color-gray-100: #f1f5f9;
    --color-gray-50: #f8fafc;
    --color-white: #ffffff;

    /* Typography */
    --font-family: 'Source Sans 3', system-ui, sans-serif;
    --font-heading: 'Libre Baskerville', Georgia, serif;

    /* Animation */
    --transition-fast: 150ms;
    --transition-base: 250ms;
    --transition-slow: 400ms;
    --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
}
```

---

## Appendix B: Google Fonts implementation

```html
<!-- Preconnect for performance -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>

<!-- Font import -->
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
```

---

## Appendix C: Partner institutions

The NJCIC operates in collaboration with five member institutions:

- The College of New Jersey
- Montclair State University
- New Jersey Institute of Technology
- Rowan University
- Rutgers University

When co-branding with partner institutions, maintain NJCIC brand standards while respecting partner brand guidelines.

---

## Version history

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | January 2026 | Initial style guide creation |

---

*For questions about this style guide, contact the Center for Cooperative Media at Montclair State University.*
