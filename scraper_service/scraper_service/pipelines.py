import logging

from django.db import close_old_connections
from twisted.internet import threads
from scrapy.exceptions import DropItem
from jobs.models import Job

from .utils import parse_salary, extract_skills, extract_seniority, clean_html_text

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
        url = item.get('url')
        if not url:
            return None

        title = (item.get('title') or "Unknown Title").strip()
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

        # Skills: union of source-provided tags and our own extraction,
        # deduped case-insensitively (our canonical capitalization wins)
        merged_skills = {
            s.strip().lower(): s.strip()
            for s in (item.get('skills') or [])
            if isinstance(s, str) and s.strip()
        }
        for s in extract_skills(text_to_scan):
            merged_skills[s.lower()] = s
        skills_found = sorted(merged_skills.values(), key=str.lower)

        # Seniority: source-provided value wins over heuristics
        seniority_level = item.get('seniority') or extract_seniority(title, description)

        job, created = Job.objects.update_or_create(
            url=url[:2000],
            defaults={
                'title': title[:500],
                'company': company[:500],
                'location': location[:500],
                'source': source[:50],
                'posted_at': item.get('posted_at'),
                'description': description,
                'skills': skills_found,
                'seniority': seniority_level[:50],
                'salary_min': int(min_sal) if min_sal is not None else None,
                'salary_max': int(max_sal) if max_sal is not None else None,
                'currency': curr,
            }
        )
        return job
