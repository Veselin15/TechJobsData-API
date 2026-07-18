from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from core.guides import GUIDES
from .models import Job


class StaticPagesSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    protocol = 'https'

    def items(self):
        return ['index', 'job_list', 'insights', 'developer_guide',
                'guide_list', 'about', 'contact', 'privacy', 'terms']

    def location(self, item):
        return reverse(item)


class GuideSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7
    protocol = 'https'

    def items(self):
        return GUIDES

    def lastmod(self, obj):
        return obj['published']

    def location(self, obj):
        return reverse('guide_detail', args=[obj['slug']])


class JobSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8
    protocol = 'https'

    def items(self):
        # Only substantial listings: pages with a real description and
        # enough structure to stand alone. Thin listings stay reachable
        # through the job board but are not pushed to Google — thousands
        # of near-empty pages in the sitemap is what "low value content"
        # reviews punish.
        return (
            Job.objects.exclude(description__isnull=True)
            .exclude(description='')
            .filter(quality_score__gte=35)
            .order_by('-posted_at')
        )

    def lastmod(self, obj):
        # Tells Google when the page was last updated
        return obj.posted_at

    def location(self, obj):
        # Returns the URL for each specific job
        return reverse('job_detail', args=[obj.pk])