from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from .models import (
    AlertEvent,
    AlertRule,
    CensorshipIncident,
    DarkWebCrawl,
    MonitoredTarget,
    OSINTScan,
    RelayAnomaly,
    Snapshot,
)
from .schedules import dispatch_monitored_target
from .serializers import (
    AlertEventSerializer,
    AlertRuleSerializer,
    CensorshipIncidentSerializer,
    DarkWebCrawlSerializer,
    MonitoredTargetSerializer,
    OSINTScanSerializer,
    RelayAnomalySerializer,
    SnapshotSerializer,
)
from .tasks import run_darkweb_crawl_task, run_osint_scan_task, run_relay_monitor_task


class OSINTScanViewSet(viewsets.ModelViewSet):
    queryset = OSINTScan.objects.all()
    serializer_class = OSINTScanSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        scan = OSINTScan.objects.create(
            target=serializer.validated_data["target"],
            scan_type=serializer.validated_data["scan_type"],
            status=OSINTScan.Status.QUEUED,
        )
        run_osint_scan_task.delay(scan.id)
        scan.refresh_from_db()
        return Response(self.get_serializer(scan).data, status=status.HTTP_201_CREATED)


class CensorshipIncidentListView(views.APIView):
    @extend_schema(responses=CensorshipIncidentSerializer(many=True))
    def get(self, request, *args, **kwargs):
        incidents = CensorshipIncident.objects.all()[:50]
        return Response(CensorshipIncidentSerializer(incidents, many=True).data)


class RelayAnomalyListView(views.APIView):
    """GET flagged relay anomalies; POST { search } to (re)run the monitor."""

    @extend_schema(responses=RelayAnomalySerializer(many=True))
    def get(self, request, *args, **kwargs):
        anomalies = RelayAnomaly.objects.all()[:100]
        return Response(RelayAnomalySerializer(anomalies, many=True).data)

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request, *args, **kwargs):
        search = request.data.get("search", "")
        summary = run_relay_monitor_task(search)
        anomalies = RelayAnomaly.objects.all()[:100]
        return Response(
            {"summary": summary, "anomalies": RelayAnomalySerializer(anomalies, many=True).data},
            status=status.HTTP_201_CREATED,
        )


class DarkWebCrawlViewSet(viewsets.ModelViewSet):
    queryset = DarkWebCrawl.objects.all()
    serializer_class = DarkWebCrawlSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = DarkWebCrawl.objects.create(
            url=serializer.validated_data["url"],
            keywords=serializer.validated_data.get("keywords", ""),
            status=DarkWebCrawl.Status.QUEUED,
        )
        run_darkweb_crawl_task.delay(record.id)
        record.refresh_from_db()
        return Response(self.get_serializer(record).data, status=status.HTTP_201_CREATED)


class MonitoredTargetViewSet(viewsets.ModelViewSet):
    queryset = MonitoredTarget.objects.all()
    serializer_class = MonitoredTargetSerializer

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, *args, **kwargs):
        target = self.get_object()
        result = dispatch_monitored_target(target)
        target.refresh_from_db()
        return Response(
            {"target": self.get_serializer(target).data, "dispatch": result},
            status=status.HTTP_202_ACCEPTED,
        )


class SnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Snapshot.objects.select_related("monitored_target").all()
    serializer_class = SnapshotSerializer


class AlertRuleViewSet(viewsets.ModelViewSet):
    queryset = AlertRule.objects.select_related("monitored_target").all()
    serializer_class = AlertRuleSerializer


class AlertEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AlertEvent.objects.select_related("rule", "monitored_target").all()
    serializer_class = AlertEventSerializer
