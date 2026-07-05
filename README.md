# TechJobsData API

**TechJobsData API** is a high-performance, real-time job aggregation engine built for developers. It scrapes, normalizes, and serves tech job listings from major platforms like **LinkedIn, Glassdoor, Indeed, RemoteOK, and WeWorkRemotely** via a clean REST API.

Built with **Django**, **Scrapy**, and **Celery**, it features a sophisticated scraping pipeline that handles anti-bot measures, cleans data, and provides a tiered access system (Free/Pro/Business) with Stripe integration.

## 🚀 Features

* **Real-Time Scraping**: On-demand and scheduled scraping using **Scrapy** and **Celery**.
* **Multi-Source Aggregation**: Supports **LinkedIn, Glassdoor, Indeed, RemoteOK, WeWorkRemotely, Remotive, Arbeitnow, The Muse, and PyJobs**.
* **REST API**: Fully documented API using **Django REST Framework** and **OpenAPI (Swagger)** — full-text search (websearch syntax), rich filters (salary range, seniority, skills, posting date, remote-only), ordering, single-job detail (`/api/v1/jobs/{id}/`) and aggregated stats (`/api/v1/jobs/stats/`).
* **Smart Throttling**: 3-Tier rate limiting system based on API Keys:
  * **Free**: 20 requests/day
  * **Pro**: 1,000 requests/day
  * **Business**: 10,000 requests/day
* **Stripe Integration**: Full subscription handling (Checkout, Webhooks, Portal) for monetizing API access.
* **User Dashboard**: A modern frontend built with **Django Templates, TailwindCSS, and HTMX** for managing keys and subscriptions.
* **Data Normalization**: Automatically extracts skills, parses salaries (converting currencies and periods), and detects seniority levels.

---

## 🛠 Tech Stack

* **Core**: Python 3.11, Django 5.0+
* **API**: Django REST Framework, DRF API Key
* **Scraping**: Scrapy, Scrapy-Impersonate
* **Async/Tasks**: Celery 5, Redis (Broker)
* **Database**: PostgreSQL 15
* **Frontend**: TailwindCSS, Flowbite, HTMX
* **Infrastructure**: Docker, Docker Compose, Gunicorn

---

## ⚡ Getting Started

### 1. Prerequisites
* Docker & Docker Compose installed on your machine.
* Stripe Account (for payments).

### 2. Installation

Clone the repository:
```bash
git clone [https://github.com/veselin15/techjobsdata-api.git](https://github.com/veselin15/techjobsdata-api.git)
cd techjobsdata-api
