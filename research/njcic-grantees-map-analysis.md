# NJCIC Grantees Map - Technical Analysis

## Project Overview

**NJCIC Grantees Map** is an interactive web-based mapping application that visualizes grantees of the New Jersey Civic Information Consortium across New Jersey.

- **Live Site:** https://njcivicinfo.org/map/
- **Repository:** https://github.com/jamditis/njcic-grantees-map
- **Creator:** Joe Amditis (Center for Cooperative Media at Montclair State University)

### Key Statistics
- 76+ grantee organizations
- $10.8+ million in funding
- Grant years: 2021-2025

---

## Tech Stack

| Category | Technologies |
|----------|--------------|
| **Frontend** | Vanilla JavaScript |
| **Mapping** | Leaflet.js v1.9.4 + MarkerCluster |
| **Map Tiles** | CARTO Voyager |
| **Styling** | Tailwind CSS + Custom CSS |
| **Data Source** | Airtable API |
| **Backend Sync** | PHP (server) + Node.js (local) |
| **CI/CD** | GitHub Actions |
| **Hosting** | Nestify (Apache/PHP) |

---

## Key Features

### Map Display
- Interactive Leaflet.js map centered on New Jersey
- Custom markers with organization initials
- Marker clustering with hover-to-expand
- Mobile touch zoom support

### Filtering System
- Year filter (2021-2025)
- County filter (21 NJ counties + regional)
- Focus area filter
- Status filter (Active/Completed)

### Grantee Information
- Marker tooltips with name, location, funding
- Detail modals with full grant information
- Multi-grant consolidation
- Social sharing (Twitter, Facebook, LinkedIn, Email)

### Data Flow
```
Airtable Database
    ↓ (7am ET daily)
GitHub Actions → sync.php
    ↓
grantees.json
    ↓
Client-side app.js
    ↓
Rendered map
```

---

## Project Structure

```
njcic-grantees-map/
├── index.html              # Main entry (1,037 lines)
├── js/app.js              # Application logic (910 lines)
├── styles/main.css        # Custom styles (356 lines)
├── data/grantees.json     # Grantee data (1,839 lines)
├── scripts/               # Sync utilities
├── .github/workflows/     # CI/CD automation
├── .claude/skills/        # AI domain expertise
├── docs/                  # Documentation
└── sw.js                  # Service Worker
```

---

## Key Files

### `/js/app.js` (910 lines)
- Map initialization and configuration
- Filtering logic
- Marker management
- Modal display
- Social sharing functions
- Navigation controls

### `/data/grantees.json`
```json
{
  "grantees": [{
    "name": "Organization Name",
    "county": "County",
    "city": "City",
    "years": ["2024"],
    "amount": 50000,
    "lat": 40.1234,
    "lng": -74.5678,
    "status": "active",
    "website": "https://...",
    "focusArea": "Category",
    "description": "...",
    "grants": [...]
  }]
}
```

---

## Configuration

### Environment Variables
```
AIRTABLE_PAT=personal_access_token
AIRTABLE_BASE_ID=appryDZWgPpP0GmZw
AIRTABLE_TABLE_ID=tblFADXYCq495smGH
AIRTABLE_VIEW_ID=viwjXro41ehrvxTfs
```

### Brand Colors
- Primary teal: `#2dc8d2`
- Primary dark: `#183642`
- New org orange: `#f34213`

---

## Deployment

### Development
```bash
npm install
npm start  # http://localhost:8080
```

### Automatic Sync
- GitHub Actions triggers daily at 7am ET
- Calls sync.php on Nestify server
- Updates grantees.json from Airtable

---

*Analysis Date: January 7, 2026*
