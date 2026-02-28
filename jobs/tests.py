from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory
from rest_framework import status
from rest_framework_api_key.models import APIKey
from unittest.mock import patch
from .models import Job
from .throttles import FreeTierThrottle


class JobSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create test data
        Job.objects.create(
            title="Senior Python Developer",
            company="Tech Corp",
            description="We need a backend expert.",
            skills=["Python", "Django"],
            url="http://example.com/1"
        )
        Job.objects.create(
            title="Java Engineer",
            company="Old School Inc",
            description="Enterprise java applications.",
            url="http://example.com/2"
        )
        Job.objects.create(
            title="Frontend React Dev",
            company="Tech Corp",
            description="React and Redux.",
            url="http://example.com/3"
        )

    def test_search_stemming(self):
        """
        Test if searching for 'developing' finds 'Developer' (stemming).
        This confirms that Postgres SearchVector is working, not just icontains.
        """
        url = reverse('job-list')  # Ensure name='job-list' is in urls.py
        response = self.client.get(url, {'search': 'developing'})  # Search for a related word

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data

        # Should find 'Senior Python Developer'
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Senior Python Developer")

    def test_search_company_weight(self):
        """
        Test searching by company name.
        """
        url = reverse('job-list')
        response = self.client.get(url, {'search': 'Tech Corp'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 2)


class ScrapeTriggerSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('job-scrape')

    @patch("jobs.views.run_scrapers.delay")
    def test_scrape_trigger_requires_auth(self, mock_delay):
        response = self.client.post(self.url, {"keyword": "Python", "location": "Europe"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_delay.assert_not_called()

    @patch("jobs.views.run_scrapers.delay")
    def test_scrape_trigger_accepts_valid_api_key(self, mock_delay):
        _, raw_key = APIKey.objects.create_key(name="test@example.com")
        response = self.client.post(
            self.url,
            {"keyword": "Python", "location": "Europe"},
            format="json",
            HTTP_AUTHORIZATION=f"Api-Key {raw_key}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_delay.assert_called_once_with("Python", "Europe")


class FreeTierThrottleTests(TestCase):
    def test_html_requests_are_not_exempt_from_free_throttle(self):
        request = APIRequestFactory().get("/api/jobs/", HTTP_ACCEPT="text/html")
        key = FreeTierThrottle().get_cache_key(request, view=None)
        self.assertIsNotNone(key)


class APIVersioningTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Job.objects.create(
            title="Backend Engineer",
            company="Versioned Inc",
            description="Contract test job",
            skills=["Python"],
            url="http://example.com/versioning-1",
            source="LinkedIn",
        )

    def test_v1_endpoint_is_available(self):
        response = self.client.get(reverse("job-list-v1"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["X-API-Version"], "v1")

    def test_legacy_endpoint_returns_deprecation_headers(self):
        response = self.client.get(reverse("job-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Deprecation"], "true")
        self.assertIn("/api/v1/jobs/", response["Link"])