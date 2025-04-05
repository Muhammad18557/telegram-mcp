"""
Database module for the Telegram bridge.

Provides ORM models, connection management, and repositories for data access.
"""

from database.base import init_db, get_session
from database.models import Chat, Message
from database.repositories import ChatRepository, MessageRepository
