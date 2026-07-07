from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CensorshipIncidentListView,
    DarkWebCrawlViewSet,
    OSINTScanViewSet,
    RelayAnomalyListView,
)

router = DefaultRouter()
router.register("scan", OSINTScanViewSet, basename="osint-scan")
router.register("crawl", DarkWebCrawlViewSet, basename="osint-crawl")

urlpatterns = [
    path("", include(router.urls)),
    path("censorship/", CensorshipIncidentListView.as_view(), name="censorship-list"),
    path("anomalies/", RelayAnomalyListView.as_view(), name="relay-anomalies"),
]
