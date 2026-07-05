from collections import Counter

from rest_framework import generics, serializers, status
from rest_framework.filters import OrderingFilter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django.core.cache import cache
from django.db.models import Avg, Count, Max, Min
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .models import Job
from .serializers import JobSerializer
from .tasks import run_scrapers
from .throttles import FreeTierThrottle, ProTierThrottle, BusinessTierThrottle
from .filters import JobFilter


API_THROTTLES = [BusinessTierThrottle, ProTierThrottle, FreeTierThrottle]


# --- 1. The Job List API ---
@extend_schema(
    parameters=[
        OpenApiParameter(
            name='search',
            description="Full-text search across title, company, skills and "
                        "description. Supports quoted phrases and OR / - "
                        "operators (websearch syntax).",
            required=False, type=str,
        ),
        OpenApiParameter(
            name='ordering',
            description="Sort results. One of: posted_at, -posted_at, "
                        "salary_min, -salary_min, salary_max, -salary_max, "
                        "created_at, -created_at.",
            required=False, type=str,
        ),
    ]
)
class JobListAPI(generics.ListAPIView):
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = JobFilter
    ordering_fields = ['posted_at', 'salary_min', 'salary_max', 'created_at']

    # Allow both JSON (for API) and HTML (for Browser)
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    # We list all of them; the code inside them determines which one applies
    throttle_classes = API_THROTTLES

    def get_queryset(self):
        """
        Uses Postgres Full-Text Search if the 'search' parameter is present.
        Otherwise, returns the standard list.
        """
        queryset = Job.objects.all().order_by('-posted_at', '-id')

        search_term = self.request.query_params.get('search', None)

        if search_term:
            # Weight A: title (most important); B: company/skills; C: description
            vector = SearchVector('title', weight='A') + \
                     SearchVector('company', weight='B') + \
                     SearchVector('skills', weight='B') + \
                     SearchVector('description', weight='C')

            # 'websearch' understands quoted phrases, OR and -negation,
            # and still strips stop words / applies stemming.
            query = SearchQuery(search_term, search_type='websearch')

            queryset = queryset.annotate(
                rank=SearchRank(vector, query)
            ).filter(rank__gte=0.01).order_by('-rank', '-posted_at')

        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # Handle Pagination
        current_results = response.data['results'] if isinstance(response.data, dict) else response.data

        # --- LOGIC: ZERO RESULTS AUTOMATIC SCRAPER ---
        if len(current_results) == 0:
            search_term = request.query_params.get('search')
            skills_term = request.query_params.get('skills')
            term_to_scrape = search_term or skills_term

            if term_to_scrape:
                # Create a lock key to prevent "Thundering Herd"
                lock_key = f"scrape_lock_{term_to_scrape.lower()}_Europe"
                is_already_scraping = cache.get(lock_key)

                if not is_already_scraping:
                    cache.set(lock_key, "active", timeout=900)  # Lock for 15 mins
                    run_scrapers.delay(keyword=term_to_scrape, location="Europe")

        # --- LOGIC: CONTENT NEGOTIATION ---
        # If HTMX/Browser, return HTML
        if request.headers.get('HX-Request') == 'true':
            return Response(
                {'page_obj': current_results},
                template_name='core/partials/job_results.html'
            )

        return response


# --- 2. Single Job API ---
class JobDetailAPI(generics.RetrieveAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    throttle_classes = API_THROTTLES


# --- 3. Aggregated Stats API ---
class JobStatsAPI(APIView):
    """
    Lightweight analytics over the current job dataset:
    totals, breakdowns by source/seniority, top skills and salary aggregates.
    Cached for 15 minutes.
    """
    throttle_classes = API_THROTTLES

    CACHE_KEY = 'job_stats_v1'
    CACHE_TTL = 60 * 15

    @extend_schema(responses={200: dict})
    def get(self, request):
        data = cache.get(self.CACHE_KEY)
        if data is None:
            data = self.build_stats()
            cache.set(self.CACHE_KEY, data, timeout=self.CACHE_TTL)
        return Response(data)

    def build_stats(self):
        jobs = Job.objects.all()

        by_source = {
            row['source']: row['count']
            for row in jobs.values('source').annotate(count=Count('id')).order_by('-count')
        }
        by_seniority = {
            row['seniority']: row['count']
            for row in jobs.values('seniority').annotate(count=Count('id')).order_by('-count')
        }

        skill_counter = Counter()
        for skills in jobs.exclude(skills=[]).values_list('skills', flat=True):
            if isinstance(skills, list):
                skill_counter.update(skills)

        salary_stats = jobs.filter(salary_min__isnull=False).aggregate(
            avg_salary_min=Avg('salary_min'),
            avg_salary_max=Avg('salary_max'),
            min_salary=Min('salary_min'),
            max_salary=Max('salary_max'),
        )

        return {
            'total_jobs': jobs.count(),
            'jobs_with_salary': jobs.filter(salary_min__isnull=False).count(),
            'by_source': by_source,
            'by_seniority': by_seniority,
            'top_skills': [
                {'skill': skill, 'count': count}
                for skill, count in skill_counter.most_common(25)
            ],
            'salary': {
                'avg_min': round(salary_stats['avg_salary_min']) if salary_stats['avg_salary_min'] else None,
                'avg_max': round(salary_stats['avg_salary_max']) if salary_stats['avg_salary_max'] else None,
                'lowest': salary_stats['min_salary'],
                'highest': salary_stats['max_salary'],
            },
        }


# --- 4. The Scraper Trigger (Manual Endpoint) ---

class ScrapeRequestSerializer(serializers.Serializer):
    keyword = serializers.CharField(default="Python", help_text="Job title or skill")
    location = serializers.CharField(default="Europe", help_text="Region or City")


class ScrapeTriggerAPI(APIView):
    throttle_classes = API_THROTTLES

    @extend_schema(request=ScrapeRequestSerializer)
    def post(self, request):
        serializer = ScrapeRequestSerializer(data=request.data)
        if serializer.is_valid():
            keyword = serializer.validated_data['keyword']
            location = serializer.validated_data['location']

            run_scrapers.delay(keyword, location)

            return Response({
                "message": "Scraper started successfully",
                "target": f"{keyword} jobs in {location}",
                "note": "Check back in 2-3 minutes for results."
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
