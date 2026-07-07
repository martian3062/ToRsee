from rest_framework import status, views, viewsets
from rest_framework.response import Response

from .models import CensorshipIncident, DarkWebCrawl, OSINTScan, RelayAnomaly
from .serializers import (
    CensorshipIncidentSerializer,
    DarkWebCrawlSerializer,
    OSINTScanSerializer,
    RelayAnomalySerializer,
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
    def get(self, request, *args, **kwargs):
        incidents = CensorshipIncident.objects.all()[:50]
        return Response(CensorshipIncidentSerializer(incidents, many=True).data)


class RelayAnomalyListView(views.APIView):
    """GET flagged relay anomalies; POST { search } to (re)run the monitor."""

    def get(self, request, *args, **kwargs):
        anomalies = RelayAnomaly.objects.all()[:100]
        return Response(RelayAnomalySerializer(anomalies, many=True).data)

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
