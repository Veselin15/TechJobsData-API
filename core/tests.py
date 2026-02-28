from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import APIRequestLog
from payments.models import UserSubscription

User = get_user_model()


class SubscriptionTemplateSafetyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="nosubuser",
            email="nosub@example.com",
            password="safe-pass-123",
        )
        # If a signal created a subscription, remove it to validate the no-subscription edge case.
        subscription = getattr(self.user, "subscription", None)
        if subscription:
            subscription.delete()

    def test_dashboard_renders_without_subscription(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_developer_guide_renders_without_subscription(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("developer_guide"))
        self.assertEqual(response.status_code, 200)


class DashboardUsageVisibilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="usageuser",
            email="usage@example.com",
            password="safe-pass-123",
        )
        UserSubscription.objects.update_or_create(
            user=self.user,
            defaults={"plan_type": "pro"},
        )

    def test_dashboard_includes_usage_context(self):
        APIRequestLog.objects.create(
            user=self.user,
            method="GET",
            endpoint="/api/v1/jobs/",
            status_code=200,
            plan_type="pro",
            api_key_prefix="abcd1234",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("today_usage", response.context)
        self.assertIn("remaining_quota", response.context)
