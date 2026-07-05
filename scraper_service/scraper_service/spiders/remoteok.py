import json
import scrapy
from datetime import datetime
from ..items import JobItem


class RemoteOKSpider(scrapy.Spider):
    """
    Uses RemoteOK's official JSON API (https://remoteok.com/api) instead of
    the RSS feed: it exposes structured salary_min/salary_max, tags (skills),
    company and full descriptions.
    """
    name = "remoteok"
    allowed_domains = ["remoteok.com"]

    async def start(self):
        yield scrapy.Request(
            "https://remoteok.com/api",
            callback=self.parse,
            meta={'impersonate': 'chrome110'}
        )

    def parse(self, response):
        if response.status == 403:
            self.logger.warning("RemoteOK returned 403 — site is blocking scrapers")
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("RemoteOK API returned invalid JSON")
            return

        for entry in data:
            # The first element is a legal notice, real jobs have an 'id'
            if not isinstance(entry, dict) or not entry.get('id'):
                continue

            url = entry.get('url') or entry.get('apply_url')
            title = entry.get('position') or entry.get('title')
            if not url or not title:
                continue

            posted_at = None
            date_str = entry.get('date')
            if date_str:
                try:
                    posted_at = datetime.fromisoformat(date_str).date()
                except ValueError:
                    pass
            if posted_at is None:
                posted_at = datetime.today().date()

            salary_min = entry.get('salary_min') or None
            salary_max = entry.get('salary_max') or None

            yield JobItem(
                title=title,
                company=entry.get('company') or "RemoteOK",
                location=entry.get('location') or "Remote",
                url=url,
                posted_at=posted_at,
                description=entry.get('description') or "",
                source="RemoteOK",
                skills=[t for t in (entry.get('tags') or []) if isinstance(t, str)],
                salary_min=salary_min,
                salary_max=salary_max,
                currency="USD" if (salary_min or salary_max) else None,
            )
