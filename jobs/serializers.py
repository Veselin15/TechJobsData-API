from django.utils import timezone
from rest_framework import serializers

from .models import Job


class JobSerializer(serializers.ModelSerializer):
    days_ago = serializers.SerializerMethodField(
        help_text="Days since the job was posted (null if unknown)."
    )
    salary_display = serializers.SerializerMethodField(
        help_text="Human-readable annual salary, e.g. 'USD 80,000 - 120,000'."
    )

    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'location', 'url', 'source',
            'posted_at', 'created_at', 'description', 'summary',
            'skills', 'seniority', 'category',
            'remote_type', 'employment_type', 'company_logo',
            'salary_min', 'salary_max', 'currency',
            'salary_min_usd', 'salary_max_usd',
            'quality_score', 'days_ago', 'salary_display',
        ]

    def get_days_ago(self, obj):
        if not obj.posted_at:
            return None
        return max((timezone.now().date() - obj.posted_at).days, 0)

    def get_salary_display(self, obj):
        if not obj.salary_min and not obj.salary_max:
            return None
        currency = obj.currency or 'USD'
        if obj.salary_min and obj.salary_max and obj.salary_min != obj.salary_max:
            return f"{currency} {obj.salary_min:,} - {obj.salary_max:,}"
        amount = obj.salary_min or obj.salary_max
        return f"{currency} {amount:,}"
