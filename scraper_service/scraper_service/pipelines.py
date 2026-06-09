import logging

from django.db import close_old_connections
from jobs.models import Job

from .utils import parse_salary, extract_skills, extract_seniority

logger = logging.getLogger(__name__)


class ScraperServicePipeline:
    def process_item(self, item, spider=None):
        close_old_connections()
        try:
            return self.save_job(item)
        except Exception:
            logger.exception("Failed to save job from %s: %s", spider.name, item.get("url"))
            raise

    def save_job(self, item):
        url = item.get('url')
        if not url:
            return None

        title = item.get('title') or "Unknown Title"
        company = item.get('company') or "Unknown Company"
        description = item.get('description') or ""
        location = item.get('location') or "Remote"
        source = item.get('source') or "Unknown"

        text_to_scan = f"{title} {company} {description}"

        min_sal, max_sal, curr = parse_salary(text_to_scan)
        skills_found = extract_skills(text_to_scan)
        seniority_level = extract_seniority(title, description)

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
