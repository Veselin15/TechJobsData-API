import django_filters
import re
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Job


class JobFilter(django_filters.FilterSet):
    # Standard text searches
    title = django_filters.CharFilter(lookup_expr='icontains')
    company = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.CharFilter(lookup_expr='icontains')
    seniority = django_filters.CharFilter(lookup_expr='icontains')
    source = django_filters.CharFilter(lookup_expr='icontains')
    currency = django_filters.CharFilter(lookup_expr='iexact')

    # Salary filters (annualized values)
    salary_min = django_filters.NumberFilter(field_name='salary_min', lookup_expr='gte')
    salary_max = django_filters.NumberFilter(field_name='salary_max', lookup_expr='lte')
    has_salary = django_filters.BooleanFilter(method='filter_has_salary')

    # Date filters
    posted_after = django_filters.DateFilter(field_name='posted_at', lookup_expr='gte')
    posted_before = django_filters.DateFilter(field_name='posted_at', lookup_expr='lte')
    posted_within = django_filters.NumberFilter(method='filter_posted_within')

    # Remote-only convenience flag
    remote = django_filters.BooleanFilter(method='filter_remote')

    # Custom Skills Filter (search inside JSON list, comma-separated = AND)
    skills = django_filters.CharFilter(method='filter_skills')

    class Meta:
        model = Job
        fields = [
            'title', 'company', 'location', 'skills', 'seniority',
            'salary_min', 'salary_max', 'has_salary', 'source', 'currency',
            'posted_after', 'posted_before', 'posted_within', 'remote',
        ]

    def filter_skills(self, queryset, name, value):
        """
        Searches for specific skills inside the JSONField list.
        Comma-separated values are ANDed: ?skills=Python,Docker matches jobs
        that list BOTH. Matching is exact per skill (quoted inside the JSON),
        so 'Java' matches ["Java"] but NOT ["JavaScript"].
        """
        if not value:
            return queryset

        for skill in [s.strip() for s in value.split(',') if s.strip()]:
            queryset = queryset.filter(skills__iregex=f'"{re.escape(skill)}"')
        return queryset

    def filter_posted_within(self, queryset, name, value):
        """?posted_within=7 -> jobs posted in the last 7 days."""
        try:
            days = int(value)
        except (TypeError, ValueError):
            return queryset
        if days <= 0:
            return queryset
        cutoff = timezone.now().date() - timedelta(days=days)
        return queryset.filter(posted_at__gte=cutoff)

    def filter_remote(self, queryset, name, value):
        if value is True:
            return queryset.filter(location__icontains='remote')
        if value is False:
            return queryset.exclude(location__icontains='remote')
        return queryset

    def filter_has_salary(self, queryset, name, value):
        salary_q = Q(salary_min__isnull=False) | Q(salary_max__isnull=False)
        if value is True:
            return queryset.filter(salary_q)
        if value is False:
            return queryset.exclude(salary_q)
        return queryset
