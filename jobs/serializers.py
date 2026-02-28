from rest_framework import serializers
from .models import Job


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        # Explicit field contract for stable v1 responses.
        fields = (
            "id",
            "title",
            "company",
            "location",
            "url",
            "source",
            "posted_at",
            "created_at",
            "description",
            "skills",
            "seniority",
            "salary_min",
            "salary_max",
            "currency",
        )


class JobListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = JobSerializer(many=True)