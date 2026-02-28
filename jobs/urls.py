from django.urls import path
from .views import LegacyJobListAPI, LegacyScrapeTriggerAPI

urlpatterns = [
    # Legacy endpoints kept for backward compatibility.
    path('jobs/', LegacyJobListAPI.as_view(), name='job-list'),

    path('scrape/', LegacyScrapeTriggerAPI.as_view(), name='job-scrape'),
]