# newsR0 — Intelligent News Aggregator & Web Scraper

newsR0 pulls real-time news from 20+ sources, categorises articles into structured sectors and sub-sectors, and surfaces them through a fast, filterable dashboard with direct links to source articles.

## Features

- **Multi-source scraping** — RSS feeds (primary) + HTML scraping (Phase 4)
- **Auto-tagging** — keyword-based sector/sub-sector classification
- **Deduplication** — exact URL + fuzzy title matching (90% threshold)
- **Scheduled refresh** — every 15 minutes via APScheduler
- **FastAPI backend** — filterable REST API
- **Vanilla JS frontend** — no build step, works out of the box
- **Fully config-driven** — sources, sectors, and keywords are YAML files

## Project Structure

```
newsR0/
├── scraper/
│   ├── engine.py          # Main scraper orchestrator
│   ├── rss_parser.py      # RSS feed handler
│   ├── html_parser.py     # BeautifulSoup / Playwright handler
│   ├── deduplicator.py    # Fuzzy match dedup logic
│   ├── tagger.py          # Keyword-to-sector auto-tagger
│   └── scheduler.py       # APScheduler job runner
├── db/
│   ├── models.py          # SQLAlchemy models
│   ├── database.py        # DB connection & session
│   └── newsR0.db          # SQLite database (gitignored)
├── api/
│   ├── main.py            # FastAPI app
│   └── routes/
│       ├── articles.py    # GET /api/articles, POST /api/refresh
│       └── sectors.py     # GET /api/sectors, GET /api/sources
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── config/
│   ├── sources.yaml       # Source list
│   ├── sectors.yaml       # Sector taxonomy
│   └── keywords.yaml      # Keyword → sector mapping
├── logs/
│   └── scraper.log
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the API server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The frontend is served at **http://localhost:8000**.

### 3. Run the scraper (standalone)

```bash
python -m scraper.scheduler
```

Or trigger a one-off run:

```bash
python -c "from scraper.engine import run_scraper; run_scraper()"
```

## Configuration

### Adding a new source (`config/sources.yaml`)

```yaml
- name: My Source
  url: https://example.com/rss.xml
  type: rss            # rss | html
  default_sector: Macroeconomic
  enabled: true
```

### Adding keywords (`config/keywords.yaml`)

```yaml
sector_keywords:
  Geopolitical:
    - my_keyword
  Commodities.Metals.Precious:
    - new_metal_term
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `NEWSR0_DB_PATH` | `db/newsR0.db` | SQLite database path |
| `NEWSR0_SOURCES_PATH` | `config/sources.yaml` | Sources config |
| `NEWSR0_SECTORS_PATH` | `config/sectors.yaml` | Sectors config |
| `NEWSR0_KEYWORDS_PATH` | `config/keywords.yaml` | Keywords config |
| `NEWSR0_REFRESH_MINUTES` | `15` | Scraper interval |

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/articles` | List articles with filters |
| `GET` | `/api/sectors` | Full sector taxonomy |
| `GET` | `/api/sources` | Source list with run status |
| `POST` | `/api/refresh` | Trigger immediate scraper run |
| `GET` | `/api/runs/{id}` | Get scraper run status |

### `GET /api/articles` query parameters

| Param | Type | Description |
|---|---|---|
| `q` | string | Keyword search in title + excerpt |
| `sector` | string | Comma-separated sector names |
| `sub_sector` | string | Comma-separated sub-sector names |
| `source` | string | Comma-separated source names |
| `from_date` | ISO8601 | Start date filter |
| `to_date` | ISO8601 | End date filter |
| `limit` | int | Results per page (default 50) |
| `offset` | int | Pagination offset |
| `include_archived` | bool | Include articles older than 7 days |

## Development Phases

| Phase | Scope | Status |
|---|---|---|
| Phase 1 | Core scraper, RSS parser, auto-tagger, SQLite, scheduler | ✅ Scaffolded |
| Phase 2 | FastAPI backend, full filter API | ✅ Scaffolded |
| Phase 3 | Frontend dashboard | ✅ Scaffolded |
| Phase 4 | HTML/Playwright scraper, dedup, full source list | 🔲 Pending |

## Legal & Ethics

- Respects `robots.txt` for all HTML-scraped sources
- Minimum 1-second crawl delay per domain (2 seconds for HTML scraping)
- Only scrapes publicly available, non-paywalled content
- User-Agent clearly identifies the bot

## Roadmap (v1)

- Sentiment scoring (VADER / distilBERT)
- Email digest
- Keyword watchlist + desktop alerts
- Telegram / Slack bot integration
- Export to CSV / JSON
- Historical article volume charts
