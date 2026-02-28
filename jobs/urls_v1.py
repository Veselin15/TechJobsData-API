from django.urls import path
from .views import JobListAPI, ScrapeTriggerAPI

urlpatterns = [
    path("jobs/", JobListAPI.as_view(), name="job-list-v1"),
    path("scrape/", ScrapeTriggerAPI.as_view(), name="job-scrape-v1"),
]
