"""
API module for Telegram interaction.

Provides client, middleware, and models for interacting with the Telegram API.
"""

from api.client import TelegramApiClient
from api.middleware import TelegramMiddleware, handle_telegram_errors
from api.models import (
    ChatModel,
    MessageModel,
    MessageContextModel,
    SendMessageRequest,
    SendMessageResponse
)
