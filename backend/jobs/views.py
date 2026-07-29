from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from .models import IngestionJob, JobTarget
from .serializers import IngestionJobSerializer, IngestRequestSerializer
from .tasks import run_ingestion_job


class JobListView(APIView):
    @extend_schema(operation_id="jobs_list", responses=IngestionJobSerializer(many=True))
    def get(self, request):
        jobs = IngestionJob.objects.prefetch_related("targets__document__source")[:50]
        return Response(IngestionJobSerializer(jobs, many=True).data)


class JobDetailView(APIView):
    @extend_schema(operation_id="jobs_retrieve", responses=IngestionJobSerializer)
    def get(self, request, pk):
        job = IngestionJob.objects.prefetch_related("targets__document__source").get(pk=pk)
        return Response(IngestionJobSerializer(job).data)


class IngestView(APIView):
    @extend_schema(
        operation_id="jobs_ingest",
        request=IngestRequestSerializer,
        responses={201: IngestionJobSerializer},
    )
    def post(self, request):
        serializer = IngestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        job = IngestionJob.objects.create(
            provider_preference=data.get("provider_preference", []),
            tags=data.get("tags", []),
            notification_settings={
                "notify": data.get("notify", True),
                "telegram_chat_id": data.get("telegram_chat_id", ""),
            },
        )
        for url in data["urls"]:
            JobTarget.objects.create(job=job, url=url)
        run_ingestion_job.delay(str(job.id))
        refreshed = IngestionJob.objects.prefetch_related("targets__document__source").get(pk=job.pk)
        return Response(IngestionJobSerializer(refreshed).data, status=status.HTTP_201_CREATED)
