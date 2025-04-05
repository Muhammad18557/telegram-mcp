"""
Service layer for the Telegram bridge.

Connects the API middleware with database repositories to provide 
high-level operations for the application.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from telethon import events

from api import TelegramApiClient, TelegramMiddleware
from database import ChatRepository, MessageRepository

logger = logging.getLogger(__name__)


class TelegramService:
    """Service for Telegram operations."""
    
    def __init__(
        self,
        telegram_client: TelegramApiClient,
        middleware: TelegramMiddleware,
        chat_repo: ChatRepository,
        message_repo: MessageRepository
    ):
        """Initialize the service.
        
        Args:
            telegram_client: Telegram API client
            middleware: Telegram middleware
            chat_repo: Chat repository
            message_repo: Message repository
        """
        self.client = telegram_client
        self.middleware = middleware
        self.chat_repo = chat_repo
        self.message_repo = message_repo
        
    async def setup(self) -> None:
        """Set up the service, connect to Telegram, and register handlers."""
        # Connect to Telegram
        await self.client.connect()
        
        # Register event handlers
        self.client.add_event_handler(self._handle_new_message, events.NewMessage)
        
    async def authorize(self) -> bool:
        """Authorize with Telegram if needed."""
        if await self.client.is_authorized():
            logger.info("Already authorized with Telegram")
            return True
            
        logger.info("Not authorized with Telegram. Interactive login required.")
        return False
        
    async def login(self, phone: str, code: str, password: Optional[str] = None) -> bool:
        """Login to Telegram.
        
        Args:
            phone: Phone number
            code: Verification code
            password: Two-factor authentication password (optional)
            
        Returns:
            bool: True if login successful, False otherwise
        """
        if password:
            return await self.client.sign_in(phone=phone, code=code, password=password)
        else:
            # First send code request
            await self.client.send_code_request(phone)
            # Then sign in with the code
            return await self.client.sign_in(phone=phone, code=code)
            
    async def sync_all_dialogs(self, limit: int = 100) -> None:
        """Sync all dialogs (chats) from Telegram.
        
        Args:
            limit: Maximum number of dialogs to retrieve
        """
        logger.info("Starting synchronization of all dialogs")
        
        # Get all dialogs (chats)
        dialogs = await self.client.get_dialogs(limit=limit)
        
        for dialog in dialogs:
            try:
                await self.sync_dialog_history(dialog)
            except Exception as e:
                logger.error(f"Error syncing dialog {dialog.name}: {e}")
                
        logger.info(f"Completed synchronization of {len(dialogs)} dialogs")
        
    async def sync_dialog_history(self, dialog, limit: int = 100) -> None:
        """Sync message history for a specific dialog.
        
        Args:
            dialog: Dialog to sync
            limit: Maximum number of messages to retrieve
        """
        # Process dialog entity
        chat_info = await self.middleware.process_dialog(dialog)
        
        if not chat_info:
            logger.warning(f"Could not process dialog: {dialog}")
            return
            
        # Store chat information
        self.chat_repo.store_chat(
            chat_id=chat_info["id"],
            title=chat_info["title"],
            username=chat_info.get("username"),
            chat_type=chat_info["type"],
            last_message_time=chat_info["last_message_time"]
        )
        
        # Get messages
        messages = await self.client.get_messages(dialog.entity, limit=limit)
        
        # Process each message
        for message in messages:
            msg_info = await self.middleware.process_message(message)
            if msg_info:
                self.message_repo.store_message(
                    message_id=msg_info["id"],
                    chat_id=msg_info["chat_id"],
                    sender_id=msg_info["sender_id"],
                    sender_name=msg_info["sender_name"],
                    content=msg_info["content"],
                    timestamp=msg_info["timestamp"],
                    is_from_me=msg_info["is_from_me"]
                )
                
        logger.info(f"Synced {len(messages)} messages from {chat_info['title']}")
        
    async def send_message(self, recipient: str, message: str) -> Tuple[bool, str]:
        """Send a message to a Telegram recipient.
        
        Args:
            recipient: Recipient identifier (ID, username, or title)
            message: Message text to send
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        if not self.client.client.is_connected():
            return False, "Not connected to Telegram"
            
        entity = await self.middleware.find_entity_by_name_or_id(recipient)
        
        if not entity:
            # Try to find in database
            try:
                # Try to parse as integer
                chat_id = int(recipient)
                chat = self.chat_repo.get_chat_by_id(chat_id)
                if chat:
                    entity = await self.client.get_entity(chat_id)
            except ValueError:
                # Not an integer, try to find by name
                chats = self.chat_repo.get_chats(query=recipient, limit=1)
                if chats:
                    entity = await self.client.get_entity(chats[0].id)
                    
        if not entity:
            return False, f"Recipient not found: {recipient}"
            
        # Send the message
        sent_message = await self.client.send_message(entity, message)
        
        if sent_message:
            # Process and store the sent message
            msg_info = await self.middleware.process_message(sent_message)
            if msg_info:
                self.message_repo.store_message(
                    message_id=msg_info["id"],
                    chat_id=msg_info["chat_id"],
                    sender_id=msg_info["sender_id"],
                    sender_name=msg_info["sender_name"],
                    content=msg_info["content"],
                    timestamp=msg_info["timestamp"],
                    is_from_me=msg_info["is_from_me"]
                )
            return True, f"Message sent to {recipient}"
        else:
            return False, f"Failed to send message to {recipient}"
            
    async def _handle_new_message(self, event) -> None:
        """Handle a new message event from Telegram."""
        message = event.message
        msg_info = await self.middleware.process_message(message)
        
        if msg_info:
            # Process and store chat information
            chat_entity = message.chat
            if chat_entity:
                chat_info = await self.middleware.process_chat_entity(chat_entity)
                self.chat_repo.store_chat(
                    chat_id=chat_info["id"],
                    title=chat_info["title"],
                    username=chat_info.get("username"),
                    chat_type=chat_info["type"],
                    last_message_time=message.date
                )
                
            # Store the message
            self.message_repo.store_message(
                message_id=msg_info["id"],
                chat_id=msg_info["chat_id"],
                sender_id=msg_info["sender_id"],
                sender_name=msg_info["sender_name"],
                content=msg_info["content"],
                timestamp=msg_info["timestamp"],
                is_from_me=msg_info["is_from_me"]
            )
            
            logger.info(
                f"Stored message: [{msg_info['timestamp']}] {msg_info['sender_name']} "
                f"in {msg_info['chat_title']}: {msg_info['content'][:30]}..."
            )