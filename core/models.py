from django.db import models
from django.contrib.auth import get_user_model
from jobs.models import Job

User = get_user_model()

class JobAlert(models.Model):
    """
    Stores email subscriptions for specific search keywords.
    """
    email = models.EmailField()
    keyword = models.CharField(max_length=100)
    location = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(auto_now_add=True) # Tracks when we last emailed them
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.email} -> {self.keyword}"

class SavedJob(models.Model):
    """
    A 'Bookmark' connecting a User to a Job.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'job')  # Prevent saving the same job twice

    def __str__(self):
        return f"{self.user.email} saved {self.job.title}"


class APIRequestLog(models.Model):
    """
    Lightweight log for customer-facing API billing/usage visibility.
    """
    PLAN_CHOICES = [
        ("free", "Free"),
        ("pro", "Pro"),
        ("business", "Business"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="api_request_logs",
        null=True,
        blank=True,
    )
    method = models.CharField(max_length=10)
    endpoint = models.CharField(max_length=255)
    status_code = models.PositiveSmallIntegerField()
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")
    api_key_prefix = models.CharField(max_length=16, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["plan_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} -> {self.status_code}"