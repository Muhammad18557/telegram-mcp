"""
Telegram API client.

Handles communication with the Telegram API using the Telethon library.
"""

import os
import logging
import asyncio
from typing import Optional, List, Dict, Any, Callable, Tuple
from datetime import datetime

from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel, Message, Dialog
from telethon.utils import get_display_name

logger = logging.getLogger(__name__)


class TelegramApiClient:
    """Client for interacting with the Telegram API."""
    
    def __init__(self, session_file: str, api_id: str, api_hash: str):
        """Initialize the Telegram API client.
        
        Args:
            session_file: Path to the session file for authentication
            api_id: Telegram API ID
            api_hash: Telegram API hash
        """
        self.session_file = session_file
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = TelegramClient(session_file, api_id, api_hash)
        self._me = None
        
    async def connect(self) -> bool:
        """Connect to the Telegram API.
        
        Returns:
            bool: True if successfully connected, False otherwise
        """
        try:
            await self.client.connect()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False
    
    async def is_authorized(self) -> bool:
        """Check if the client is authorized.
        
        Returns:
            bool: True if authorized, False otherwise
        """
        return await self.client.is_user_authorized()
    
    async def send_code_request(self, phone: str) -> bool:
        """Send a code request to the given phone number.
        
        Args:
            phone: Phone number to send code to
            
        Returns:
            bool: True if code sent successfully, False otherwise
        """
        try:
            await self.client.send_code_request(phone)
            return True
        except Exception as e:
            logger.error(f"Failed to send code request: {e}")
            return False
    
    async def sign_in(self, phone: Optional[str] = None, code: Optional[str] = None, 
                      password: Optional[str] = None) -> bool:
        """Sign in to Telegram.
        
        Args:
            phone: Phone number (optional)
            code: Verification code (optional)
            password: Two-factor authentication password (optional)
            
        Returns:
            bool: True if signed in successfully, False otherwise
        """
        try:
            if password:
                await self.client.sign_in(password=password)
            else:
                await self.client.sign_in(phone, code)
            return True
        except Exception as e:
            logger.error(f"Failed to sign in: {e}")
            return False
    
    async def get_me(self) -> Optional[User]:
        """Get the current user.
        
        Returns:
            User: Current user object
        """
        if not self._me:
            self._me = await self.client.get_me()
        return self._me
    
    async def get_dialogs(self, limit: int = 100) -> List[Dialog]:
        """Get dialogs (chats) from Telegram.
        
        Args:
            limit: Maximum number of dialogs to retrieve
            
        Returns:
            List[Dialog]: List of dialogs
        """
        try:
            return await self.client.get_dialogs(limit=limit)
        except Exception as e:
            logger.error(f"Failed to get dialogs: {e}")
            return []
    
    async def get_entity(self, entity_id: Any) -> Optional[Any]:
        """Get an entity from Telegram.
        
        Args:
            entity_id: ID of the entity to retrieve
            
        Returns:
            Any: Entity object (User, Chat, or Channel)
        """
        try:
            return await self.client.get_entity(entity_id)
        except Exception as e:
            logger.error(f"Failed to get entity: {e}")
            return None
    
    async def get_messages(self, entity: Any, limit: int = 100) -> List[Message]:
        """Get messages from a chat.
        
        Args:
            entity: Chat entity
            limit: Maximum number of messages to retrieve
            
        Returns:
            List[Message]: List of messages
        """
        try:
            return await self.client.get_messages(entity, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    async def send_message(self, entity: Any, message: str) -> Optional[Message]:
        """Send a message to a chat.
        
        Args:
            entity: Chat entity
            message: Message text to send
            
        Returns:
            Message: Sent message object
        """
        try:
            return await self.client.send_message(entity, message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None
    
    def add_event_handler(self, callback: Callable, event: Any) -> None:
        """Add an event handler.
        
        Args:
            callback: Callback function to handle the event
            event: Event to handle
        """
        self.client.add_event_handler(callback, event)
        
    async def disconnect(self) -> None:
        """Disconnect from the Telegram API."""
        await self.client.disconnect()
        
    def __del__(self):
        """Cleanup when the client is deleted."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.disconnect())
            else:
                loop.run_until_complete(self.disconnect())
        except:
            pass