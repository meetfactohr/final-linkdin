# Corporate Contact Finder

## Overview
A full-stack web application that searches for corporate contacts by finding LinkedIn profiles using Google Custom Search, scraping profile data with Playwright, and verifying email addresses using Apollo API and Hunter.io.

**Current State:** Enhanced MVP with Playwright scraping, Apollo API integration, custom role input, and CSV export capabilities.

**Last Updated:** October 30, 2025

## Recent Changes
- **October 30, 2025**: Major enhancement with Playwright and Apollo integration
  - Added custom role input field (user can specify their own roles)
  - Integrated Playwright for direct LinkedIn profile scraping (extracts name, title, company, location)
  - Integrated Apollo API for email finding (with Hunter.io as fallback)
  - Changed workflow: Google Search → Playwright Scraping → Apollo/Hunter Email Finding
  - Updated frontend to handle domain-role pairs (N domains × M roles combinations)
  - Real-time progress now shows both domain and role being processed
- **October 29, 2025**: Implemented EventSource-based real-time progress tracking
  - Split search into POST /search (initialize) and GET /search/stream/<session_id> (stream)
  - Frontend uses native EventSource API for reliable SSE consumption
  - Real-time progress bar, log updates, and incremental result display
  - Functional stop button that halts server-side processing mid-run
- Initial project setup with Flask backend and vanilla JavaScript frontend
- Implemented API key rotation system for Google Custom Search API
- Built responsive UI with Tailwind CSS
- Added CSV export functionality

## Project Architecture

### Backend (Flask)
- **app.py** - Main Flask application with:
  - API key rotation logic for rate limit handling
  - LinkedIn URL search via Google Custom Search API
  - Domain-role pair processing with SSE streaming
  - CSV export endpoint
- **linkedin_scraper.py** - Playwright-based LinkedIn scraper
  - Launches headless Chromium browser
  - Extracts name, title, company, location from LinkedIn profiles
  - Handles timeouts and errors gracefully
- **apollo_api.py** - Apollo API integration
  - Finds emails using Apollo's people search API
  - Supports filtering by domain, name, and title
  - Validates email results

### Frontend
- **templates/index.html** - Main UI with Tailwind CSS
  - Multi-domain input textarea
  - Multi-role input textarea (NEW)
  - Real-time progress tracking
  - Dynamic results table
  - Search log display
- **static/script.js** - Frontend logic
  - EventSource for SSE streaming
  - Sends domain-role pairs to backend
  - Progress updates showing domain and role
  - CSV download functionality
- **static/style.css** - Custom styling and animations

### Configuration
- **.gitignore** - Python/Flask specific ignores
- **pyproject.toml** - Python dependencies managed by uv

## Environment Variables
Required secrets (configured via Replit Secrets):
- `GOOGLE_API_KEYS` - Comma-separated list of Google Custom Search API keys for LinkedIn profile search
- `GOOGLE_CX_ID` - Google Custom Search Engine ID
- `APOLLO_API_KEY` - Apollo API key for email finding (primary method)
- `HUNTER_API_KEY` - Hunter.io API key for email verification (fallback)
- `SESSION_SECRET` - Flask session secret (auto-configured)

## Search Workflow
1. **User Input**: User provides domains and roles (custom input, not hardcoded)
2. **Google Search**: Find LinkedIn profile URL for each domain-role combination
3. **Playwright Scraping**: Visit LinkedIn profile and extract name, title, company, location
4. **Email Finding**: Use Apollo API to find email (with Hunter.io as fallback)
5. **Results**: Display all findings in real-time with CSV export option

## Features
- Custom role input (user defines roles instead of hardcoded hierarchy)
- Multi-domain × Multi-role batch processing
- Direct LinkedIn profile scraping with Playwright
- Apollo API email finding with Hunter.io fallback
- Automatic API key rotation to handle rate limits
- Real-time progress tracking with Server-Sent Events
- Search log with timestamps showing domain and role
- Results table with LinkedIn profile links
- CSV export with all results
- Error handling and validation
- Responsive design for mobile/desktop

## User Preferences
- None specified yet

## Technical Notes
- Playwright runs in headless Chromium mode with anti-detection headers
- Google Custom Search API query format: `site:linkedin.com/in ("{ROLE}") "{DOMAIN}"`
- Apollo API searches by domain, name, and title for better accuracy
- Hunter.io Email Finder API as fallback when Apollo doesn't find email
- Server binds to 0.0.0.0:5000 for Replit compatibility
- System dependencies installed: Chromium browser, X11 libraries for Playwright
