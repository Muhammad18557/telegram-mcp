"""
Telegram MCP Server

The server uses FastMCP to expose Telegram functionality in a standardized way,
with each tool implemented as a decorated function. This allows Claude to:
1. Search contacts and chats
2. Retrieve message history with optional context
3. Send messages to individuals or groups

The server connects to the local SQLite database maintained by the Telegram Bridge,
and also communicates with the Bridge's HTTP API for sending messages.
"""

from typing import List, Dict, Any, Optional, Tuple
from mcp.server.fastmcp import FastMCP
from datetime import datetime
from telegram import (
    search_contacts as telegram_search_contacts,
    list_messages as telegram_list_messages,
    list_chats as telegram_list_chats,
    get_chat as telegram_get_chat,
    get_direct_chat_by_contact as telegram_get_direct_chat_by_contact,
    get_contact_chats as telegram_get_contact_chats,
    get_last_interaction as telegram_get_last_interaction,
    get_message_context as telegram_get_message_context,
    send_message as telegram_send_message
)

# Initialize FastMCP server
mcp = FastMCP("telegram")

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search Telegram contacts by name or username.
    
    Args:
        query: Search term to match against contact names or usernames
    """
    contacts = telegram_search_contacts(query)
    return contacts

@mcp.tool()
def list_messages(
    date_range: Optional[Tuple[datetime, datetime]] = None,
    sender_id: Optional[int] = None,
    chat_id: Optional[int] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get Telegram messages matching specified criteria with optional context.
    
    Args:
        date_range: Optional tuple of (start_date, end_date) to filter messages by date
        sender_id: Optional sender ID to filter messages by sender
        chat_id: Optional chat ID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    messages = telegram_list_messages(
        date_range=date_range,
        sender_id=sender_id,
        chat_id=chat_id,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )
    return messages

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    chat_type: Optional[str] = None,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get Telegram chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or username
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        chat_type: Optional chat type filter ("user", "group", "channel", or "supergroup")
        sort_by: Field to sort results by, either "last_active" or "title" (default "last_active")
    """
    chats = telegram_list_chats(
        query=query,
        limit=limit,
        page=page,
        chat_type=chat_type,
        sort_by=sort_by
    )
    return chats

@mcp.tool()
def get_chat(chat_id: int) -> Dict[str, Any]:
    """Get Telegram chat metadata by ID.
    
    Args:
        chat_id: The ID of the chat to retrieve
    """
    chat = telegram_get_chat(chat_id)
    return chat

@mcp.tool()
def get_direct_chat_by_contact(contact_id: int) -> Dict[str, Any]:
    """Get Telegram chat metadata by contact ID.
    
    Args:
        contact_id: The contact ID to search for
    """
    chat = telegram_get_direct_chat_by_contact(contact_id)
    return chat

@mcp.tool()
def get_contact_chats(contact_id: int, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all Telegram chats involving the contact.
    
    Args:
        contact_id: The contact's ID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = telegram_get_contact_chats(contact_id, limit, page)
    return chats

@mcp.tool()
def get_last_interaction(contact_id: int) -> Dict[str, Any]:
    """Get most recent Telegram message involving the contact.
    
    Args:
        contact_id: The ID of the contact to search for
    """
    message = telegram_get_last_interaction(contact_id)
    return message

@mcp.tool()
def get_message_context(
    message_id: int,
    chat_id: int,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific Telegram message.
    
    Args:
        message_id: The ID of the message to get context for
        chat_id: The ID of the chat containing the message
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = telegram_get_message_context(message_id, chat_id, before, after)
    return context

@mcp.tool()
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a Telegram message to a person or group.

    Args:
        recipient: The recipient - either a username (with or without @) or a chat ID
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    # Call the telegram_send_message function
    success, status_message = telegram_send_message(recipient, message)
    return {
        "success": success,
        "message": status_message
    }

if __name__ == "__main__":
    # Redirect stdout/stderr to suppress initial output that might confuse Claude
    import sys
    import os
    
    # Create logs directory
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs'), exist_ok=True)
    
    # Redirect stderr to log file
    sys.stderr = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'mcp_error.log'), 'w')
    
    # Initialize and run the server
    mcp.run(transport='stdio')