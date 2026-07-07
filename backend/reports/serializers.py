from rest_framework import serializers

from .models import SummaryReport


class SummaryReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SummaryReport
        fields = ["id", "job", "document", "prompt", "summary", "model", "metadata", "created_at"]
