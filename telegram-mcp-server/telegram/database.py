"""
Database operations for retrieving and managing Telegram data.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple

from . import MESSAGES_DB_PATH
from .models import Message, Chat, Contact, MessageContext

def search_contacts(query: str) -> List[Contact]:
    """Search contacts by name or username."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Search in chats where type is 'user'
        cursor.execute("""
            SELECT id, username, title
            FROM chats
            WHERE type = 'user' AND (title LIKE ? OR username LIKE ?)
            ORDER BY title
            LIMIT 50
        """, (f"%{query}%", f"%{query}%"))
        
        contacts = cursor.fetchall()
        
        result = []
        for contact_data in contacts:
            contact = Contact(
                id=contact_data[0],
                username=contact_data[1],
                name=contact_data[2]
            )
            result.append(contact)
            
        return result
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

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
) -> List[Message]:
    """Get messages matching the specified criteria with optional context."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Build base query
        query_parts = ["""
            SELECT 
                m.id, 
                m.chat_id, 
                c.title, 
                m.sender_name, 
                m.content, 
                m.timestamp, 
                m.is_from_me, 
                m.sender_id
            FROM messages m
        """]
        query_parts.append("JOIN chats c ON m.chat_id = c.id")
        where_clauses = []
        params = []
        
        # Add filters
        if date_range:
            where_clauses.append("m.timestamp BETWEEN ? AND ?")
            params.extend([date_range[0].isoformat(), date_range[1].isoformat()])
            
        if sender_id:
            where_clauses.append("m.sender_id = ?")
            params.append(sender_id)
            
        if chat_id:
            where_clauses.append("m.chat_id = ?")
            params.append(chat_id)
            
        if query:
            where_clauses.append("LOWER(m.content) LIKE LOWER(?)")
            params.append(f"%{query}%")
            
        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
            
        # Add pagination
        offset = page * limit
        query_parts.append("ORDER BY m.timestamp DESC")
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])
        
        cursor.execute(" ".join(query_parts), tuple(params))
        messages = cursor.fetchall()
        
        result = []
        for msg in messages:
            message = Message(
                id=msg[0],
                chat_id=msg[1],
                chat_title=msg[2],
                sender_name=msg[3],
                content=msg[4],
                timestamp=datetime.fromisoformat(msg[5]),
                is_from_me=bool(msg[6]),
                sender_id=msg[7]
            )
            result.append(message)
            
        if include_context and result:
            # Add context for each message
            messages_with_context = []
            for msg in result:
                context = get_message_context(msg.id, msg.chat_id, context_before, context_after)
                messages_with_context.extend(context.before)
                messages_with_context.append(context.message)
                messages_with_context.extend(context.after)
            return messages_with_context
            
        return result
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_message_context(
    message_id: int,
    chat_id: int,
    before: int = 5,
    after: int = 5
) -> MessageContext:
    """Get context around a specific message."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Get the target message first
        cursor.execute("""
            SELECT m.id, m.chat_id, c.title, m.sender_name, m.content, m.timestamp, m.is_from_me, m.sender_id
            FROM messages m
            JOIN chats c ON m.chat_id = c.id
            WHERE m.id = ? AND m.chat_id = ?
        """, (message_id, chat_id))
        msg_data = cursor.fetchone()
        
        if not msg_data:
            raise ValueError(f"Message with ID {message_id} in chat {chat_id} not found")
            
        target_message = Message(
            id=msg_data[0],
            chat_id=msg_data[1],
            chat_title=msg_data[2],
            sender_name=msg_data[3],
            content=msg_data[4],
            timestamp=datetime.fromisoformat(msg_data[5]),
            is_from_me=bool(msg_data[6]),
            sender_id=msg_data[7]
        )
        
        # Get messages before
        cursor.execute("""
            SELECT m.id, m.chat_id, c.title, m.sender_name, m.content, m.timestamp, m.is_from_me, m.sender_id
            FROM messages m
            JOIN chats c ON m.chat_id = c.id
            WHERE m.chat_id = ? AND m.timestamp < ?
            ORDER BY m.timestamp DESC
            LIMIT ?
        """, (chat_id, target_message.timestamp.isoformat(), before))
        
        before_messages = []
        for msg in cursor.fetchall():
            before_messages.append(Message(
                id=msg[0],
                chat_id=msg[1],
                chat_title=msg[2],
                sender_name=msg[3],
                content=msg[4],
                timestamp=datetime.fromisoformat(msg[5]),
                is_from_me=bool(msg[6]),
                sender_id=msg[7]
            ))
        
        # Get messages after
        cursor.execute("""
            SELECT m.id, m.chat_id, c.title, m.sender_name, m.content, m.timestamp, m.is_from_me, m.sender_id
            FROM messages m
            JOIN chats c ON m.chat_id = c.id
            WHERE m.chat_id = ? AND m.timestamp > ?
            ORDER BY m.timestamp ASC
            LIMIT ?
        """, (chat_id, target_message.timestamp.isoformat(), after))
        
        after_messages = []
        for msg in cursor.fetchall():
            after_messages.append(Message(
                id=msg[0],
                chat_id=msg[1],
                chat_title=msg[2],
                sender_name=msg[3],
                content=msg[4],
                timestamp=datetime.fromisoformat(msg[5]),
                is_from_me=bool(msg[6]),
                sender_id=msg[7]
            ))
        
        return MessageContext(
            message=target_message,
            before=before_messages,
            after=after_messages
        )
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    chat_type: Optional[str] = None,
    sort_by: str = "last_active"
) -> List[Chat]:
    """Get chats matching the specified criteria."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Build base query
        query_parts = ["SELECT id, title, username, type, last_message_time FROM chats"]
        
        where_clauses = []
        params = []
        
        if query:
            where_clauses.append("(LOWER(title) LIKE LOWER(?) OR LOWER(username) LIKE LOWER(?))")
            params.extend([f"%{query}%", f"%{query}%"])
        
        if chat_type:
            where_clauses.append("type = ?")
            params.append(chat_type)
            
        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
            
        # Add sorting
        order_by = "last_message_time DESC" if sort_by == "last_active" else "title"
        query_parts.append(f"ORDER BY {order_by}")
        
        # Add pagination
        offset = (page) * limit
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])
        
        cursor.execute(" ".join(query_parts), tuple(params))
        chats = cursor.fetchall()
        
        result = []
        for chat_data in chats:
            last_message_time = datetime.fromisoformat(chat_data[4]) if chat_data[4] else None
            chat = Chat(
                id=chat_data[0],
                title=chat_data[1],
                username=chat_data[2],
                type=chat_data[3],
                last_message_time=last_message_time
            )
            result.append(chat)
            
        return result
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_chat(chat_id: int) -> Optional[Chat]:
    """Get chat metadata by ID."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, username, type, last_message_time
            FROM chats
            WHERE id = ?
        """, (chat_id,))
        
        chat_data = cursor.fetchone()
        
        if not chat_data:
            return None
            
        last_message_time = datetime.fromisoformat(chat_data[4]) if chat_data[4] else None
        return Chat(
            id=chat_data[0],
            title=chat_data[1],
            username=chat_data[2],
            type=chat_data[3],
            last_message_time=last_message_time
        )
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def get_direct_chat_by_contact(contact_id: int) -> Optional[Chat]:
    """Get direct chat metadata by contact ID."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, username, type, last_message_time
            FROM chats
            WHERE id = ? AND type = 'user'
        """, (contact_id,))
        
        chat_data = cursor.fetchone()
        
        if not chat_data:
            return None
            
        last_message_time = datetime.fromisoformat(chat_data[4]) if chat_data[4] else None
        return Chat(
            id=chat_data[0],
            title=chat_data[1],
            username=chat_data[2],
            type=chat_data[3],
            last_message_time=last_message_time
        )
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def get_contact_chats(contact_id: int, limit: int = 20, page: int = 0) -> List[Chat]:
    """Get all chats involving the contact.
    
    Args:
        contact_id: The contact's ID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT
                c.id, c.title, c.username, c.type, c.last_message_time
            FROM chats c
            JOIN messages m ON c.id = m.chat_id
            WHERE m.sender_id = ? OR c.id = ?
            ORDER BY c.last_message_time DESC
            LIMIT ? OFFSET ?
        """, (contact_id, contact_id, limit, page * limit))
        
        chats = cursor.fetchall()
        
        result = []
        for chat_data in chats:
            last_message_time = datetime.fromisoformat(chat_data[4]) if chat_data[4] else None
            chat = Chat(
                id=chat_data[0],
                title=chat_data[1],
                username=chat_data[2],
                type=chat_data[3],
                last_message_time=last_message_time
            )
            result.append(chat)
            
        return result
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_last_interaction(contact_id: int) -> Optional[Message]:
    """Get most recent message involving the contact."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                m.id, m.chat_id, c.title, m.sender_name, m.content, m.timestamp, m.is_from_me, m.sender_id
            FROM messages m
            JOIN chats c ON m.chat_id = c.id
            WHERE m.sender_id = ? OR c.id = ?
            ORDER BY m.timestamp DESC
            LIMIT 1
        """, (contact_id, contact_id))
        
        msg_data = cursor.fetchone()
        
        if not msg_data:
            return None
            
        return Message(
            id=msg_data[0],
            chat_id=msg_data[1],
            chat_title=msg_data[2],
            sender_name=msg_data[3],
            content=msg_data[4],
            timestamp=datetime.fromisoformat(msg_data[5]),
            is_from_me=bool(msg_data[6]),
            sender_id=msg_data[7]
        )
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()