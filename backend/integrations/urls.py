from django.urls import path

from .views import SearchView, TelegramWebhookView

urlpatterns = [
    path("search", SearchView.as_view(), name="search"),
    path("telegram/webhook", TelegramWebhookView.as_view(), name="telegram-webhook"),
]
