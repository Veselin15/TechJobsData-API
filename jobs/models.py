from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField


class Job(models.Model):
    title = models.CharField(max_length=500)
    company = models.CharField(max_length=500, db_index=True)
    location = models.CharField(max_length=500, default="Remote")
    url = models.URLField(unique=True, max_length=2048)
    source = models.CharField(max_length=50, db_index=True)
    posted_at = models.DateField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    seniority = models.CharField(max_length=50, default="Not Specified")
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)

    # --- Enrichment fields (computed by the scraper pipeline) ---
    company_logo = models.URLField(max_length=2048, blank=True, default="")
    remote_type = models.CharField(max_length=20, default="Not Specified", db_index=True)
    employment_type = models.CharField(max_length=20, blank=True, default="")
    category = models.CharField(max_length=40, blank=True, default="", db_index=True)
    summary = models.CharField(max_length=300, blank=True, default="")
    quality_score = models.PositiveSmallIntegerField(default=0)
    # Annual salary converted to USD at fixed reference rates, for
    # cross-currency sorting and analytics
    salary_min_usd = models.IntegerField(null=True, blank=True)
    salary_max_usd = models.IntegerField(null=True, blank=True)

    # Weighted full-text document (title=A, company/skills=B, description=C).
    # Maintained by a Postgres trigger (migration 0007), NOT by Django —
    # never assign to it in application code.
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        indexes = [
            models.Index(fields=['-posted_at', 'title']),
            models.Index(fields=['-quality_score', '-posted_at']),
            GinIndex(fields=['search_vector'], name='jobs_search_vector_gin'),
        ]

    def __str__(self):
        return f"{self.title} at {self.company}"