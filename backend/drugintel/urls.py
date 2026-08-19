from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CorrelationFindingViewSet,
    DrugSignalViewSet,
    EntityViewSet,
    EvidenceItemViewSet,
    IntelligenceSourceViewSet,
    InvestigationViewSet,
)

router = DefaultRouter()
router.register("investigations", InvestigationViewSet, basename="intel-investigation")
router.register("sources", IntelligenceSourceViewSet, basename="intel-source")
router.register("evidence", EvidenceItemViewSet, basename="intel-evidence")
router.register("signals", DrugSignalViewSet, basename="intel-signal")
router.register("entities", EntityViewSet, basename="intel-entity")
router.register("correlations", CorrelationFindingViewSet, basename="intel-correlation")

urlpatterns = [path("", include(router.urls))]
