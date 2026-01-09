# CCM repository - Technical analysis

## Project overview

**Center for Cooperative Media (CCM)** - A collection of free tools and resources for journalists, created by the Center for Cooperative Media at Montclair State University.

- **Repository:** https://github.com/jamditis/ccm
- **Organization:** Center for Cooperative Media at Montclair State University
- **Founded:** 2012

### Mission
- Coordinate statewide reporting through NJ News Commons (300+ local news providers)
- Provide training and support to local journalists
- Research collaborative journalism
- Develop innovative tools for newsrooms

---

## Repository contents

### Public Tools (9)

| Tool | Purpose | Tech |
|------|---------|------|
| **LLM Advisor** | AI tool recommendation quiz | React + Vite |
| **Invoicer** | Invoice generation | HTML + React CDN |
| **Sponsorship Generator** | Sponsorship proposals | HTML + React CDN |
| **Event Budget Calculator** | Event finance planning | HTML + React CDN |
| **Chart Maker** | Flowchart/diagram creation | HTML + React CDN |
| **Media Kit Builder** | Media kit generation | HTML + React CDN |
| **Freelancer Rate Calculator** | Project rate calculation | HTML + React CDN |
| **Grant Proposal Generator** | Grant proposal templates | HTML + React CDN |
| **Collaboration Agreement Generator** | Partnership MOUs | HTML + React CDN |

### Internal research

**NJ Influencer Social Media Scraper**
- Multi-platform scraping (TikTok, Instagram, YouTube)
- AI-powered content analysis
- Semantic and sentiment analysis
- Interactive web reports

---

## Tech stack

### Frontend
- **HTML Tools:** HTML5 + Vanilla JS + Tailwind CSS + React (CDN)
- **React App:** React 18 + Vite 5 + Tailwind CSS

### Backend (Social Scraper)
- **Language:** Python 3.11+
- **Scraping:** yt-dlp, instaloader
- **Analysis:** pandas, matplotlib, seaborn
- **AI:** OpenAI, Anthropic, Google Gemini APIs

### DevOps
- **Deployment:** Netlify (PR previews)
- **CI/CD:** GitHub Actions
- **Testing:** pytest, Vitest

---

## Project structure

```
ccm/
├── tools/                     # Public tools
│   ├── llm-advisor/          # React app
│   ├── invoicer/             # Invoice tool
│   ├── sponsorship-generator/
│   ├── event-budget-calculator/
│   ├── chart-maker/
│   ├── media-kit-builder/
│   ├── freelancer-rate-calculator/
│   ├── grant-proposal-generator/
│   └── collaboration-agreement-generator/
├── social-scraper/           # Research project
│   ├── scrapers/            # Platform scrapers
│   ├── analysis/            # Data analysis
│   └── tests/               # Unit tests
├── docs/                     # Documentation
├── reports/                  # Research reports
└── .github/workflows/        # CI/CD
```

---

## LLM Advisor (React App)

### Components
- `App.jsx` - Main application with useReducer
- `QuestionView.jsx` - Interactive quiz questions
- `RecommendationView.jsx` - AI tool recommendations
- `Header.jsx` - Navigation and progress
- `ToolCard.jsx` - Individual tool display

### Data
- `decisionTree.js` - Question/answer logic
- Recommendations for Claude, ChatGPT, Gemini, Perplexity

### Commands
```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # Production build
npm test         # Run tests
```

---

## Social scraper

### Platform support
- TikTok (via yt-dlp)
- Instagram (via instaloader)
- YouTube (via yt-dlp)

### Analysis capabilities

**Semantic Analysis:**
- Topic classification
- NJ relevance scoring
- Entity recognition
- Production quality assessment

**Sentiment Analysis:**
- Sentiment score (-1 to +1)
- Emotion detection
- Authenticity scoring
- Controversy potential

### AI providers
- Anthropic Claude (primary)
- Google Gemini (fast/cheap)
- OpenAI GPT (balanced)

### Commands
```bash
python main.py --test              # Test first influencer
python main.py --start 0 --end 5   # Batch scrape
python run_ai_analysis.py          # AI analysis
```

---

## CI/CD Pipeline

1. **HTML Linting** - Validates all HTML files
2. **LLM Advisor Tests** - ESLint + Vitest + Coverage
3. **Social Scraper Tests** - pytest + Coverage
4. **Security Scanning** - Trivy + TruffleHog
5. **Netlify Preview** - PR deployments

---

## Key features

### Browser-based tools
- Zero installation required
- Work directly in browser
- Local storage for persistence
- PDF export capability

### Internationalization
- English and Spanish support
- Translation files in `tools/shared/locales/`

### Security
- All data stays local (no server storage)
- Environment variables for API keys
- Security scanning in CI/CD

---

*Analysis Date: January 7, 2026*
