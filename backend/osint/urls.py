from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AlertEventViewSet,
    AlertRuleViewSet,
    CensorshipIncidentListView,
    DarkWebCrawlViewSet,
    MonitoredTargetViewSet,
    OSINTScanViewSet,
    RelayAnomalyListView,
    SnapshotViewSet,
)

router = DefaultRouter()
router.register("scan", OSINTScanViewSet, basename="osint-scan")
router.register("crawl", DarkWebCrawlViewSet, basename="osint-crawl")
router.register("monitors", MonitoredTargetViewSet, basename="osint-monitor")
router.register("snapshots", SnapshotViewSet, basename="osint-snapshot")
router.register("alert-rules", AlertRuleViewSet, basename="osint-alert-rule")
router.register("alert-events", AlertEventViewSet, basename="osint-alert-event")

urlpatterns = [
    path("", include(router.urls)),
    path("censorship/", CensorshipIncidentListView.as_view(), name="censorship-list"),
    path("anomalies/", RelayAnomalyListView.as_view(), name="relay-anomalies"),
]
