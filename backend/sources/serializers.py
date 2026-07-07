from rest_framework import serializers

from .models import Document, Source


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = ["id", "kind", "value", "tags", "metadata", "created_at"]


class DocumentSerializer(serializers.ModelSerializer):
    source = SourceSerializer(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "source",
            "url",
            "title",
            "content_markdown",
            "metadata",
            "embedding_id",
            "created_at",
        ]
