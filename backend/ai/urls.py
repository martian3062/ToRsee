from django.urls import path

from .views import AIStatusView, SummarizeView

urlpatterns = [
    path("summarize", SummarizeView.as_view(), name="ai-summarize"),
    path("status", AIStatusView.as_view(), name="ai-status"),
]
