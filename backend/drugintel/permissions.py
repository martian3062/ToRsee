import hmac

from django.conf import settings
from rest_framework.permissions import BasePermission


class IntelligenceOperatorPermission(BasePermission):
    """Require an operator key for live intelligence operations.

    Mock mode intentionally remains frictionless for local demonstrations and tests.
    """

    message = "A valid ToRsy operator key is required for live intelligence operations."

    def has_permission(self, request, view) -> bool:
        if settings.PROVIDER_MOCK_MODE:
            return True
        configured = settings.INTELLIGENCE_OPERATOR_KEY
        supplied = request.headers.get("X-ToRsy-Operator-Key", "")
        return bool(
            settings.INTELLIGENCE_LIVE_ENABLED
            and configured
            and supplied
            and hmac.compare_digest(configured, supplied)
        )
