from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CorrelationFinding, DrugSignal, Entity, EvidenceItem, IntelligenceSource, Investigation
from .permissions import IntelligenceOperatorPermission
from .serializers import (
    CorrelationFindingSerializer,
    DrugSignalSerializer,
    EntitySerializer,
    EvidenceItemSerializer,
    IntelligenceSourceSerializer,
    InvestigationSerializer,
    SignalReviewSerializer,
)
from .services import refresh_correlations
from .tasks import run_intelligence_source


class GovernedViewSet(viewsets.ModelViewSet):
    permission_classes = [IntelligenceOperatorPermission]


class InvestigationViewSet(GovernedViewSet):
    serializer_class = InvestigationSerializer

    def get_queryset(self):
        return Investigation.objects.annotate(
            source_count=Count("sources", distinct=True),
            signal_count=Count("signals", distinct=True),
        )

    @action(detail=True, methods=["post"], url_path="correlate")
    def correlate(self, request, *args, **kwargs):
        investigation = self.get_object()
        findings = refresh_correlations(investigation.id)
        return Response(CorrelationFindingSerializer(findings, many=True).data)


class IntelligenceSourceViewSet(GovernedViewSet):
    serializer_class = IntelligenceSourceSerializer

    def get_queryset(self):
        return IntelligenceSource.objects.select_related("investigation").annotate(
            evidence_count=Count("evidence", distinct=True)
        )

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, *args, **kwargs):
        source = self.get_object()
        result = run_intelligence_source.delay(source.id)
        return Response(
            {"source": self.get_serializer(source).data, "task_id": result.id},
            status=status.HTTP_202_ACCEPTED,
        )


class EvidenceItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EvidenceItemSerializer
    permission_classes = [IntelligenceOperatorPermission]

    def get_queryset(self):
        queryset = EvidenceItem.objects.select_related("source", "investigation").annotate(
            signal_count=Count("signals", distinct=True)
        )
        investigation = self.request.query_params.get("investigation")
        source = self.request.query_params.get("source")
        if investigation:
            queryset = queryset.filter(investigation_id=investigation)
        if source:
            queryset = queryset.filter(source_id=source)
        return queryset


class DrugSignalViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DrugSignalSerializer
    permission_classes = [IntelligenceOperatorPermission]

    def get_queryset(self):
        queryset = DrugSignal.objects.select_related("evidence__source", "investigation")
        investigation = self.request.query_params.get("investigation")
        review_status = self.request.query_params.get("review_status")
        if investigation:
            queryset = queryset.filter(investigation_id=investigation)
        if review_status:
            queryset = queryset.filter(review_status=review_status)
        return queryset

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, *args, **kwargs):
        signal = self.get_object()
        serializer = SignalReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.apply(signal)
        return Response(self.get_serializer(signal).data)


class EntityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EntitySerializer
    permission_classes = [IntelligenceOperatorPermission]

    def get_queryset(self):
        return Entity.objects.annotate(evidence_count=Count("evidence_links", distinct=True))


class CorrelationFindingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CorrelationFindingSerializer
    permission_classes = [IntelligenceOperatorPermission]

    def get_queryset(self):
        queryset = CorrelationFinding.objects.select_related("investigation")
        investigation = self.request.query_params.get("investigation")
        if investigation:
            queryset = queryset.filter(investigation_id=investigation)
        return queryset
