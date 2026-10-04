"""Shared OpenAPI annotations so /api/docs/ documents auth + payment flows."""

from drf_spectacular.utils import OpenApiResponse, inline_serializer
from rest_framework import serializers


def msg(description="OK"):
    return inline_serializer(name="MessageResponse",
                             fields={"detail": serializers.CharField()}, many=False)


def err(description="Error"):
    return {400: OpenApiResponse(description=description)}
