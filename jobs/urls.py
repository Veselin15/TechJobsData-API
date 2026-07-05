from django.urls import path
from .views import JobListAPI, JobDetailAPI, JobStatsAPI, ScrapeTriggerAPI

urlpatterns = [
    # Map 'api/jobs/'
    path('jobs/', JobListAPI.as_view(), name='job-list'),

    # Map 'api/jobs/stats/' (must come before the <pk> route)
    path('jobs/stats/', JobStatsAPI.as_view(), name='job-stats'),

    # Map 'api/jobs/<id>/'
    path('jobs/<int:pk>/', JobDetailAPI.as_view(), name='job-detail-api'),

    # Map 'api/scrape/'
    path('scrape/', ScrapeTriggerAPI.as_view(), name='job-scrape'),
]
