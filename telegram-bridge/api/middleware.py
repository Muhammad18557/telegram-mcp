"""
Telegram API middleware.

Handles common operations between the application and Telegram API such as
authentication, error handling, and entity type conversion.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List, Callable
from datetime import datetime
from functools import wraps

from telethon.tl.types import User, Chat, Channel, Message, Dialog
from telethon.utils import get_display_name

from api.client import TelegramApiClient

logger = logging.getLogger(__name__)


def handle_telegram_errors(func):
    """Decorator to handle Telegram API errors."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Telegram API error in {func.__name__}: {e}")
            return None
    return wrapper


class TelegramMiddleware:
    """Middleware for Telegram API operations."""
    
    def __init__(self, client: TelegramApiClient):
        """Initialize the middleware with a Telegram client.
        
        Args:
            client: Initialized Telegram API client
        """
        self.client = client
        
    async def process_chat_entity(self, entity: Any) -> Dict[str, Any]:
        """Process a chat entity and convert it to a dictionary.
        
        Args:
            entity: Chat entity from Telegram API
            
        Returns:
            Dict: Standardized chat representation
        """
        if isinstance(entity, User):
            chat_type = "user"
            title = get_display_name(entity)
            username = entity.username
        elif isinstance(entity, Chat):
            chat_type = "group"
            title = entity.title
            username = None
        elif isinstance(entity, Channel):
            chat_type = "channel" if entity.broadcast else "supergroup"
            title = entity.title
            username = entity.username
        else:
            logger.warning(f"Unknown chat type: {type(entity)}")
            return {}
            
        return {
            "id": entity.id,
            "title": title,
            "username": username,
            "type": chat_type
        }
        
    @handle_telegram_errors
    async def process_dialog(self, dialog: Dialog) -> Dict[str, Any]:
        """Process a dialog and convert it to a dictionary.
        
        Args:
            dialog: Dialog from Telegram API
            
        Returns:
            Dict: Standardized dialog representation
        """
        chat_info = await self.process_chat_entity(dialog.entity)
        chat_info["last_message_time"] = dialog.date
        return chat_info
        
    @handle_telegram_errors
    async def process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """Process a message and convert it to a dictionary.
        
        Args:
            message: Message from Telegram API
            
        Returns:
            Dict: Standardized message representation
        """
        if not message.text:
            return None  # Skip non-text messages
            
        # Get the chat
        chat = message.chat
        if not chat:
            return None
            
        chat_info = await self.process_chat_entity(chat)
        
        # Get sender information
        sender = await message.get_sender()
        sender_id = sender.id if sender else 0
        sender_name = get_display_name(sender) if sender else "Unknown"
        
        # Check if the message is from the current user
        my_id = (await self.client.get_me()).id
        is_from_me = sender_id == my_id
        
        return {
            "id": message.id,
            "chat_id": chat_info["id"],
            "chat_title": chat_info["title"],
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": message.text,
            "timestamp": message.date,
            "is_from_me": is_from_me
        }
        
    @handle_telegram_errors
    async def find_entity_by_name_or_id(self, recipient: str) -> Optional[Any]:
        """Find an entity by name or ID.
        
        Args:
            recipient: Recipient identifier (ID, username, or title)
            
        Returns:
            Any: Found entity or None
        """
        # Try to parse as an integer (chat ID)
        try:
            chat_id = int(recipient)
            return await self.client.get_entity(chat_id)
        except ValueError:
            pass
            
        # Not an integer, try as username
        if recipient.startswith("@"):
            recipient = recipient[1:]  # Remove @ if present
            
        try:
            return await self.client.get_entity(recipient)
        except Exception:
            logger.error(f"Could not find entity: {recipient}")
            return None