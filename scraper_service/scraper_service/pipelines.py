import logging

from django.db import close_old_connections
from twisted.internet import threads
from scrapy.exceptions import DropItem
from jobs.models import Job

from .utils import (
    parse_salary, extract_skills, extract_seniority, clean_html_text,
    clean_title, canonicalize_url, normalize_skills, detect_remote_type,
    detect_employment_type, classify_role, to_usd, make_summary,
    compute_quality_score,
)

logger = logging.getLogger(__name__)


class ScraperServicePipeline:
    def process_item(self, item, spider=None):
        return threads.deferToThread(self._process_in_thread, item, spider)

    def _process_in_thread(self, item, spider):
        close_old_connections()
        try:
            result = self.save_job(item)
            if result is None:
                raise DropItem(f"Missing URL: {item.get('title')}")
            return item
        except DropItem:
            raise
        except Exception:
            spider_name = spider.name if spider else "unknown"
            logger.exception("Failed to save job from %s: %s", spider_name, item.get("url"))
            raise

    def save_job(self, item):
        url = canonicalize_url(item.get('url'))
        if not url:
            return None

        title = clean_title(item.get('title')) or "Unknown Title"
        company = (item.get('company') or "Unknown Company").strip()
        location = (item.get('location') or "Remote").strip()
        source = item.get('source') or "Unknown"

        # Normalize HTML descriptions to plain text (RemoteOK/Remotive/
        # Glassdoor/Indeed hand us raw HTML fragments)
        description = item.get('description') or ""
        if '<' in description and '>' in description:
            description = clean_html_text(description)

        text_to_scan = f"{title} {company} {description}"

        # Salary: trust structured data from the source; parse text otherwise
        min_sal = item.get('salary_min')
        max_sal = item.get('salary_max')
        curr = item.get('currency')
        if min_sal is None and max_sal is None:
            min_sal, max_sal, curr = parse_salary(text_to_scan)
        elif not curr:
            curr = "USD"
        if min_sal is not None and max_sal is not None and min_sal > max_sal:
            min_sal, max_sal = max_sal, min_sal

        # Skills: source tags + our own extraction, aliased to canonical
        # names, noise-filtered and deduplicated
        skills_found = normalize_skills(
            item.get('skills') or [],
            extract_skills(text_to_scan),
        )

        # Seniority: source-provided value wins over heuristics
        seniority_level = item.get('seniority') or extract_seniority(title, description)

        # --- Enrichment: structure the source usually doesn't provide ---
        remote_type = item.get('remote_type') or detect_remote_type(title, location, description)
        employment_type = item.get('employment_type') or detect_employment_type(title, description)
        category = classify_role(title, skills_found)
        summary = make_summary(description)
        company_logo = (item.get('company_logo') or "").strip()

        posted_at = item.get('posted_at')
        quality_score = compute_quality_score(
            description=description,
            skills=skills_found,
            salary_min=min_sal,
            salary_max=max_sal,
            seniority=seniority_level,
            remote_type=remote_type,
            employment_type=employment_type,
            company_logo=company_logo,
            posted_at=posted_at,
        )

        job, created = Job.objects.update_or_create(
            url=url[:2000],
            defaults={
                'title': title[:500],
                'company': company[:500],
                'location': location[:500],
                'source': source[:50],
                'posted_at': posted_at,
                'description': description,
                'skills': skills_found,
                'seniority': seniority_level[:50],
                'salary_min': int(min_sal) if min_sal is not None else None,
                'salary_max': int(max_sal) if max_sal is not None else None,
                'currency': curr,
                'company_logo': company_logo[:2000],
                'remote_type': remote_type[:20],
                'employment_type': employment_type[:20],
                'category': category[:40],
                'summary': summary[:300],
                'quality_score': quality_score,
                'salary_min_usd': to_usd(min_sal, curr),
                'salary_max_usd': to_usd(max_sal, curr),
            }
        )
        return job
