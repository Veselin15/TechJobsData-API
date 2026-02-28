from rest_framework import generics, serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.permissions import IsAdminUser
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework_api_key.models import APIKey

# --- Postgres Search Imports ---
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import TextField
from django.db.models.functions import Cast
from django.contrib.auth import get_user_model

from .models import Job
from .serializers import JobSerializer, JobListResponseSerializer
from .tasks import run_scrapers
from .throttles import FreeTierThrottle, ProTierThrottle, BusinessTierThrottle, ScrapeTriggerThrottle
from .filters import JobFilter
from core.models import APIRequestLog

User = get_user_model()


# --- 1. The Job List API ---
def resolve_request_identity(request):
    user = request.user if request.user.is_authenticated else None
    api_key_prefix = ""
    plan_type = getattr(getattr(user, "subscription", None), "plan_type", "free")

    auth_header = request.META.get("HTTP_AUTHORIZATION")
    if auth_header and auth_header.startswith("Api-Key "):
        try:
            key_value = auth_header.split()[1]
            api_key = APIKey.objects.get_from_key(key_value)
            if api_key:
                api_key_prefix = api_key.prefix
                if not user:
                    user = User.objects.filter(email=api_key.name).first()
                plan_type = getattr(getattr(user, "subscription", None), "plan_type", "free")
        except Exception:
            pass

    return user, api_key_prefix, plan_type


def log_api_request(request, response):
    # We only log structured API traffic; HTML browsing is excluded.
    if request.accepted_renderer and request.accepted_renderer.format == "html":
        return

    if not request.path.startswith("/api/"):
        return

    user, api_key_prefix, plan_type = resolve_request_identity(request)
    if not user and not api_key_prefix:
        return

    APIRequestLog.objects.create(
        user=user,
        method=request.method,
        endpoint=request.path,
        status_code=response.status_code,
        plan_type=plan_type,
        api_key_prefix=api_key_prefix,
    )


class JobListAPI(generics.ListAPIView):
    serializer_class = JobSerializer
    # Filter Backend settings
    filter_backends = [DjangoFilterBackend]
    filterset_class = JobFilter

    # Allow both JSON (for API) and HTML (for Browser)
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    # Apply Throttles
    throttle_classes = [BusinessTierThrottle, ProTierThrottle, FreeTierThrottle]

    def get_queryset(self):
        """
        Uses Postgres Full-Text Search if the 'search' parameter is present.
        Otherwise, returns the standard list.
        """
        # Start with all jobs
        queryset = Job.objects.all().order_by('-posted_at')

        # Get the 'search' parameter from the URL (e.g., ?search=python developer)
        search_term = self.request.query_params.get('search', None)

        if search_term:
            # 1. Define where to search (Vector)
            # We use Cast for 'skills' to safely search inside the JSONField as text
            vector = SearchVector('title', weight='A') + \
                     SearchVector('company', weight='B') + \
                     SearchVector(Cast('skills', TextField()), weight='B')

            # 2. Process the query (Query)
            # SearchQuery automatically removes stop words (the, a, in) and performs stemming
            query = SearchQuery(search_term)

            # 3. Filter and sort by relevance (Rank)
            # We keep rank >= 0.1 to remove irrelevant results
            queryset = queryset.annotate(
                rank=SearchRank(vector, query)
            ).filter(rank__gte=0.1).order_by('-rank', '-posted_at')

        return queryset

    @extend_schema(
        summary="List jobs (stable v1 contract)",
        responses=JobListResponseSerializer,
    )
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # Handle Pagination Results
        current_results = response.data['results'] if isinstance(response.data, dict) else response.data

        # --- LOGIC: ZERO RESULTS AUTOMATIC SCRAPER ---
        if len(current_results) == 0:
            search_term = request.query_params.get('search')
            skills_term = request.query_params.get('skills')
            term_to_scrape = search_term or skills_term

            if term_to_scrape:
                # Create a lock key to prevent "Thundering Herd" (multiple scrapers for same term)
                lock_key = f"scrape_lock_{term_to_scrape.lower()}_Europe"
                is_already_scraping = cache.get(lock_key)

                if not is_already_scraping:
                    print(f"Triggering NEW scrape for '{term_to_scrape}'...")
                    cache.set(lock_key, "active", timeout=900)  # Lock for 15 mins
                    run_scrapers.delay(keyword=term_to_scrape, location="Europe")
                else:
                    print(f"Scrape ALREADY in progress for '{term_to_scrape}'. Skipping.")

        # --- LOGIC: CONTENT NEGOTIATION ---

        # 1. HTMX Request (Partial Update)
        # Returns only the job list part, not the whole page header/footer
        if request.headers.get('HX-Request') == 'true':
            htmx_response = Response(
                {'page_obj': current_results},
                template_name='core/partials/job_results.html'
            )
            return htmx_response

        # 2. Standard Browser Request (Full Page Load)
        # If the user visits /jobs/ directly in browser, render the full page
        if request.accepted_renderer.format == 'html':
            html_response = Response(
                {
                    'page_obj': current_results,
                    'query': request.query_params.get('search', ''),
                    'location': request.query_params.get('location', '')
                },
                template_name='core/job_list.html'
            )
            return html_response

        # 3. JSON API Request
        response["X-API-Version"] = "v1"
        log_api_request(request, response)
        return response


# --- 2. The Scraper Trigger (Manual Endpoint) ---

class ScrapeRequestSerializer(serializers.Serializer):
    keyword = serializers.CharField(default="Python", help_text="Job title or skill")
    location = serializers.CharField(default="Europe", help_text="Region or City")


class ScrapeTriggerAPI(APIView):
    # Restrict manual scrape trigger to admin users or requests with a valid API key.
    permission_classes = [IsAdminUser | HasAPIKey]
    throttle_classes = [ScrapeTriggerThrottle]

    @extend_schema(request=ScrapeRequestSerializer)
    def post(self, request):
        serializer = ScrapeRequestSerializer(data=request.data)
        if serializer.is_valid():
            keyword = serializer.validated_data['keyword']
            location = serializer.validated_data['location']

            run_scrapers.delay(keyword, location)

            response = Response({
                "message": "Scraper started successfully",
                "target": f"{keyword} jobs in {location}",
                "note": "Check back in 2-3 minutes for results."
            })
            response["X-API-Version"] = "v1"
            log_api_request(request, response)
            return response

        response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        response["X-API-Version"] = "v1"
        log_api_request(request, response)
        return response


class LegacyJobListAPI(JobListAPI):
    """
    Compatibility endpoint kept during v1 migration window.
    """

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response["Deprecation"] = "true"
        response["Sunset"] = "Wed, 31 Dec 2026 23:59:59 GMT"
        response["Link"] = '</api/v1/jobs/>; rel="successor-version"'
        return response


class LegacyScrapeTriggerAPI(ScrapeTriggerAPI):
    def post(self, request):
        response = super().post(request)
        response["Deprecation"] = "true"
        response["Sunset"] = "Wed, 31 Dec 2026 23:59:59 GMT"
        response["Link"] = '</api/v1/scrape/>; rel="successor-version"'
        return response