"""
Data models for Telegram entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Message:
    """
    Represents a Telegram message with all its metadata.
    
    Attributes:
        id: Unique message identifier
        chat_id: ID of the chat the message belongs to
        chat_title: Title of the chat (user name, group name, etc.)
        sender_name: Name of the message sender
        content: Text content of the message
        timestamp: Date and time when the message was sent
        is_from_me: Boolean indicating if the message was sent by the user
        sender_id: ID of the message sender
    """
    id: int
    chat_id: int
    chat_title: str
    sender_name: str
    content: str
    timestamp: datetime
    is_from_me: bool
    sender_id: int

@dataclass
class Chat:
    """
    Represents a Telegram chat (direct message, group, channel, etc.).
    
    Attributes:
        id: Unique chat identifier
        title: Name of the chat (user name, group name, etc.)
        username: Optional Telegram username (without @)
        type: Type of chat ('user', 'group', 'channel', 'supergroup')
        last_message_time: Timestamp of the most recent message in the chat
    """
    id: int
    title: str
    username: Optional[str]
    type: str
    last_message_time: Optional[datetime]

@dataclass
class Contact:
    """
    Represents a Telegram contact.
    
    Attributes:
        id: Unique contact identifier
        username: Optional Telegram username (without @)
        name: Display name of the contact
    """
    id: int
    username: Optional[str]
    name: str

@dataclass
class MessageContext:
    """
    Provides context around a specific message.
    
    Attributes:
        message: The target message
        before: List of messages that came before the target message
        after: List of messages that came after the target message
    """
    message: Message
    before: List[Message]
    after: List[Message]