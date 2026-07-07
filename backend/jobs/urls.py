from django.urls import path

from .views import IngestView, JobDetailView, JobListView

urlpatterns = [
    path("", JobListView.as_view(), name="job-list"),
    path("ingest", IngestView.as_view(), name="job-ingest"),
    path("<uuid:pk>", JobDetailView.as_view(), name="job-detail"),
]
