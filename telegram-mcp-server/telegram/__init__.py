"""
This module implements data models and functions for retrieving and sending
Telegram messages, managing chats, and working with contacts.

The module connects to a SQLite database that stores all Telegram messages and chat data,
which is maintained by the Telegram Bridge. It also provides an HTTP client for sending
messages via the Bridge's API endpoint.

Main features:
- Data models for messages, chats, contacts, and message context
- Database access functions for retrieving messages, chats, and contacts
- HTTP client for sending messages through the Telegram Bridge
- Helper functions for displaying formatted messages and chats
"""

import os.path

# Database path
MESSAGES_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'telegram-bridge', 'store', 'messages.db')
TELEGRAM_API_BASE_URL = "http://localhost:8081/api"

# Import all components to make them available at the module level
from .models import Message, Chat, Contact, MessageContext
from .display import print_message, print_messages_list, print_chat, print_chats_list
from .api import send_message
from .database import (
    search_contacts, list_messages, get_message_context, list_chats,
    get_chat, get_direct_chat_by_contact, get_contact_chats, get_last_interaction
)