"""
Functions for displaying Telegram messages and chats in a formatted way.
"""

from typing import List
from .models import Message, Chat

def print_message(message: Message, show_chat_info: bool = True) -> None:
    """Print a single message with consistent formatting."""
    direction = "→" if message.is_from_me else "←"
    
    if show_chat_info:
        print(f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] {direction} Chat: {message.chat_title} (ID: {message.chat_id})")
    else:
        print(f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] {direction}")
        
    print(f"From: {'Me' if message.is_from_me else message.sender_name}")
    print(f"Message: {message.content}")
    print("-" * 100)

def print_messages_list(messages: List[Message], title: str = "", show_chat_info: bool = True) -> None:
    """Print a list of messages with a title and consistent formatting."""
    if not messages:
        print("No messages to display.")
        return
        
    if title:
        print(f"\n{title}")
        print("-" * 100)
    
    for message in messages:
        print_message(message, show_chat_info)

def print_chat(chat: Chat) -> None:
    """Print a single chat with consistent formatting."""
    print(f"Chat: {chat.title} (ID: {chat.id})")
    print(f"Type: {chat.type}")
    if chat.username:
        print(f"Username: @{chat.username}")
    if chat.last_message_time:
        print(f"Last active: {chat.last_message_time:%Y-%m-%d %H:%M:%S}")
    print("-" * 100)

def print_chats_list(chats: List[Chat], title: str = "") -> None:
    """Print a list of chats with a title and consistent formatting."""
    if not chats:
        print("No chats to display.")
        return
        
    if title:
        print(f"\n{title}")
        print("-" * 100)
    
    for chat in chats:
        print_chat(chat)