from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer

from ai.providers import GroqSummarizer, SarvamSpeechService, TabPFNService
from reports.models import SummaryReport
from sources.models import Document


class SummarizeRequestSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True)
    document_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    prompt = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if not attrs.get("text") and not attrs.get("document_ids"):
            raise serializers.ValidationError("Provide text or document_ids.")
        return attrs


class SummarizeView(APIView):
    @extend_schema(
        request=SummarizeRequestSerializer,
        responses=inline_serializer(
            name="SummarizeResponse",
            fields={
                "summary": serializers.CharField(),
                "provider": serializers.CharField(),
                "model": serializers.CharField(),
                "metadata": serializers.DictField(),
            },
        ),
    )
    def post(self, request):
        serializer = SummarizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        text = data.get("text", "")
        documents = []
        if data.get("document_ids"):
            documents = list(Document.objects.filter(pk__in=data["document_ids"]))
            text = "\n\n".join([doc.content_markdown for doc in documents]) + "\n\n" + text
        result = GroqSummarizer().summarize(text, prompt=data.get("prompt", ""))
        if documents:
            first_document = documents[0]
            first_target = first_document.job_targets.select_related("job").first()
            if first_target:
                SummaryReport.objects.create(
                    job=first_target.job,
                    document=first_document,
                    prompt=data.get("prompt", ""),
                    summary=result.text,
                    model=result.model,
                    metadata={"provider": result.provider, **result.metadata},
                )
        return Response(
            {
                "summary": result.text,
                "provider": result.provider,
                "model": result.model,
                "metadata": result.metadata,
            },
            status=status.HTTP_200_OK,
        )


class AIStatusView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(
            {
                "sarvam": SarvamSpeechService().status(),
                "tabpfn": TabPFNService().status(),
            }
        )
