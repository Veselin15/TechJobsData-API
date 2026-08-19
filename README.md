# TechJobsData API

🌐 **Live Website:** [https://techjobsdata.com](https://techjobsdata.com)

**TechJobsData API** is a high-performance, real-time job aggregation engine built for developers. It scrapes, normalizes, and serves tech job listings from major platforms like **LinkedIn, Glassdoor, Indeed, RemoteOK, and WeWorkRemotely** via a clean REST API.

Built with **Django**, **Scrapy**, and **Celery**, it features a sophisticated scraping pipeline that handles anti-bot measures, cleans data, and provides a tiered access system (Free/Pro/Business) with Stripe integration.

## 🚀 Features

* **Real-Time Scraping**: On-demand and scheduled scraping using **Scrapy** and **Celery**.
* **Multi-Source Aggregation**: Supports **LinkedIn, Glassdoor, Indeed, RemoteOK, WeWorkRemotely, Remotive, Arbeitnow, The Muse, and PyJobs**.
* **Smart Search Engine**: Postgres full-text search over a stored, weighted `tsvector` (title > company/skills > description), kept in sync by a database trigger and served from a GIN index. On top of that:
  * **Tech synonyms** — `js` finds JavaScript jobs, `k8s` finds Kubernetes, `golang` finds Go.
  * **Typo correction** — `pyton` → *python*, with a "Showing results for…" notice.
  * **Prefix completion** — `javasc` already matches JavaScript listings (powers search-as-you-type).
  * **Ambiguity handling** — searching `go` matches the Go language in titles/skills, not the English verb in every description.
  * **Trigram fuzzy fallback** (pg_trgm) for misspelled companies and out-of-vocabulary terms.
  * **Relevance ranking** with match highlighting and "why this matched" description snippets.
* **REST API**: Fully documented API using **Django REST Framework** and **OpenAPI (Swagger)** — the same layered search via `?search=`, rich filters (salary range, seniority, skills, posting date, remote-only), ordering, `?page_size=` (max 50), single-job detail (`/api/v1/jobs/{id}/`) and aggregated stats (`/api/v1/jobs/stats/`).
* **Job Board UI**: Live search-as-you-type with autocomplete (skills, categories, companies), faceted filter counts that update with every query, keyboard shortcuts (`/` to search, arrows + Enter in suggestions) — built with **Django Templates, TailwindCSS, and HTMX**.
* **Smart Throttling**: 3-Tier rate limiting system based on API Keys:
  * **Free**: 20 requests/day
  * **Pro**: 1,000 requests/day
  * **Business**: 10,000 requests/day
* **Stripe Integration**: Full subscription handling (Checkout, Webhooks, Portal) for monetizing API access.
* **Data Normalization**: Automatically extracts skills (with negation and ambiguity guards), parses salaries (converting currencies and periods), detects seniority/remote type/employment type, and scores listing quality.

---

## 🛠 Tech Stack

* **Core**: Python 3.11+, Django 5/6
* **API**: Django REST Framework, DRF API Key
* **Scraping**: Scrapy, Scrapy-Impersonate
* **Async/Tasks**: Celery 5, Redis (Broker)
* **Database**: PostgreSQL 15 (full-text search + pg_trgm)
* **Frontend**: TailwindCSS, Flowbite, HTMX
* **Infrastructure**: Docker, Docker Compose, Gunicorn

---

## ⚡ Getting Started

### 1. Prerequisites

* Docker & Docker Compose installed on your machine.
* Stripe Account (for payments; optional for local development).

### 2. Installation

```bash
git clone https://github.com/veselin15/techjobsdata-api.git
cd techjobsdata-api
```

Create a `.env` file in the project root:

```env
POSTGRES_DB=remotejobs
POSTGRES_USER=user
POSTGRES_PASSWORD=change-me
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
```

Start the stack and run migrations:

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
```

The site is served on <http://localhost:8002>, the API docs on `/api/docs/`.

### 3. Local development without Docker (optional)

The database connection is configurable via environment variables, so you can
run Django on the host against a containerized Postgres:

```bash
python -m venv .venv && .venv/Scripts/activate   # or source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d db
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5433 python manage.py migrate
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5433 python manage.py runserver
```

### 4. Populating data

Trigger the API-based spiders directly (fast, no browser automation):

```bash
cd scraper_service
scrapy crawl remoteok      # also: wwr, remotive, arbeitnow, jobicy, themuse, pyjobs
```

Or let Celery Beat run the scheduled bulk scrapes (08:00 and 18:00 UTC).

After changing the enrichment logic, re-apply it to existing rows with:

```bash
python manage.py reprocess_jobs
```

### 5. Tests

```bash
python manage.py test jobs
```

---

## 📚 API quick reference

| Endpoint | Description |
| --- | --- |
| `GET /api/v1/jobs/?search=senior+python` | Layered full-text search (synonyms, typo fixes, ranking) |
| `GET /api/v1/jobs/?skills=Python,Docker&remote=true` | Exact skill AND-filtering + remote flag |
| `GET /api/v1/jobs/?salary_min_usd=100000&posted_within=7` | USD-normalized salary floor, freshness window |
| `GET /api/v1/jobs/{id}/` | Single listing |
| `GET /api/v1/jobs/stats/` | Aggregated dataset stats (sources, skills, salaries) |
| `POST /api/v1/scrape/` | Trigger an on-demand scrape |

Authenticate with `Authorization: Api-Key <your-key>` — get a key from the dashboard.
