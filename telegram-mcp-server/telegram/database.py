"""
Database operations for retrieving and managing Telegram data.
Uses SQLAlchemy ORM for database access instead of raw SQL.
"""

from sqlalchemy import create_engine, or_, and_, desc
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
from typing import Optional, List, Tuple

from . import MESSAGES_DB_PATH
from .models import Message, Chat, Contact, MessageContext

# Initialize SQLAlchemy engine and session
engine = create_engine(
    f"sqlite:///{MESSAGES_DB_PATH}",
    connect_args={"check_same_thread": False}  # Needed for SQLite
)
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)

# Import SQLAlchemy models from telegram-bridge
import sys
import os

# Add the parent directory to path to find telegram-bridge
bridge_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'telegram-bridge')
sys.path.append(bridge_path)

# Import models directly from telegram-bridge
from database.models import Chat as DBChat, Message as DBMessage

def search_contacts(query: str) -> List[Contact]:
    """Search contacts by name or username."""
    try:
        session = Session()
        
        # Search in chats where type is 'user'
        db_contacts = session.query(DBChat).filter(
            DBChat.type == 'user',
            or_(
                DBChat.title.ilike(f"%{query}%"),
                DBChat.username.ilike(f"%{query}%")
            )
        ).order_by(DBChat.title).limit(50).all()
        
        result = []
        for db_contact in db_contacts:
            contact = Contact(
                id=db_contact.id,
                username=db_contact.username,
                name=db_contact.title
            )
            result.append(contact)
            
        return result
        
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        session.close()

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
        session = Session()
        
        # Build base query with join
        db_query = session.query(DBMessage, DBChat).join(DBChat)
        
        # Add filters
        filters = []
        if date_range:
            filters.append(and_(
                DBMessage.timestamp >= date_range[0],
                DBMessage.timestamp <= date_range[1]
            ))
            
        if sender_id:
            filters.append(DBMessage.sender_id == sender_id)
            
        if chat_id:
            filters.append(DBMessage.chat_id == chat_id)
            
        if query:
            filters.append(DBMessage.content.ilike(f"%{query}%"))
            
        if filters:
            db_query = db_query.filter(and_(*filters))
            
        # Add pagination
        offset = page * limit
        db_query = db_query.order_by(desc(DBMessage.timestamp))
        db_query = db_query.limit(limit).offset(offset)
        
        # Execute query
        db_results = db_query.all()
        
        result = []
        for db_msg, db_chat in db_results:
            message = Message(
                id=db_msg.id,
                chat_id=db_msg.chat_id,
                chat_title=db_chat.title,
                sender_name=db_msg.sender_name,
                content=db_msg.content,
                timestamp=db_msg.timestamp,
                is_from_me=db_msg.is_from_me,
                sender_id=db_msg.sender_id
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
        
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        session.close()

def get_message_context(
    message_id: int,
    chat_id: int,
    before: int = 5,
    after: int = 5
) -> MessageContext:
    """Get context around a specific message."""
    try:
        session = Session()
        
        # Get the target message first
        result = session.query(DBMessage, DBChat) \
            .join(DBChat) \
            .filter(DBMessage.id == message_id, DBMessage.chat_id == chat_id) \
            .first()
        
        if not result:
            raise ValueError(f"Message with ID {message_id} in chat {chat_id} not found")
            
        db_msg, db_chat = result
        target_message = Message(
            id=db_msg.id,
            chat_id=db_msg.chat_id,
            chat_title=db_chat.title,
            sender_name=db_msg.sender_name,
            content=db_msg.content,
            timestamp=db_msg.timestamp,
            is_from_me=db_msg.is_from_me,
            sender_id=db_msg.sender_id
        )
        
        # Get messages before
        before_results = session.query(DBMessage, DBChat) \
            .join(DBChat) \
            .filter(
                DBMessage.chat_id == chat_id,
                DBMessage.timestamp < target_message.timestamp
            ) \
            .order_by(desc(DBMessage.timestamp)) \
            .limit(before) \
            .all()
        
        before_messages = []
        for db_msg, db_chat in before_results:
            before_messages.append(Message(
                id=db_msg.id,
                chat_id=db_msg.chat_id,
                chat_title=db_chat.title,
                sender_name=db_msg.sender_name,
                content=db_msg.content,
                timestamp=db_msg.timestamp,
                is_from_me=db_msg.is_from_me,
                sender_id=db_msg.sender_id
            ))
        
        # Get messages after
        after_results = session.query(DBMessage, DBChat) \
            .join(DBChat) \
            .filter(
                DBMessage.chat_id == chat_id,
                DBMessage.timestamp > target_message.timestamp
            ) \
            .order_by(DBMessage.timestamp) \
            .limit(after) \
            .all()
        
        after_messages = []
        for db_msg, db_chat in after_results:
            after_messages.append(Message(
                id=db_msg.id,
                chat_id=db_msg.chat_id,
                chat_title=db_chat.title,
                sender_name=db_msg.sender_name,
                content=db_msg.content,
                timestamp=db_msg.timestamp,
                is_from_me=db_msg.is_from_me,
                sender_id=db_msg.sender_id
            ))
        
        return MessageContext(
            message=target_message,
            before=before_messages,
            after=after_messages
        )
        
    except Exception as e:
        print(f"Database error: {e}")
        raise
    finally:
        session.close()

def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    chat_type: Optional[str] = None,
    sort_by: str = "last_active"
) -> List[Chat]:
    """Get chats matching the specified criteria."""
    try:
        session = Session()
        
        # Build base query
        db_query = session.query(DBChat)
        
        # Add filters
        filters = []
        
        if query:
            filters.append(or_(
                DBChat.title.ilike(f"%{query}%"),
                DBChat.username.ilike(f"%{query}%")
            ))
        
        if chat_type:
            filters.append(DBChat.type == chat_type)
            
        if filters:
            db_query = db_query.filter(and_(*filters))
            
        # Add sorting
        if sort_by == "last_active":
            db_query = db_query.order_by(desc(DBChat.last_message_time))
        else:
            db_query = db_query.order_by(DBChat.title)
        
        # Add pagination
        offset = page * limit
        db_query = db_query.limit(limit).offset(offset)
        
        # Execute query
        db_chats = db_query.all()
        
        result = []
        for db_chat in db_chats:
            chat = Chat(
                id=db_chat.id,
                title=db_chat.title,
                username=db_chat.username,
                type=db_chat.type,
                last_message_time=db_chat.last_message_time
            )
            result.append(chat)
            
        return result
        
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        session.close()

def get_chat(chat_id: int) -> Optional[Chat]:
    """Get chat metadata by ID."""
    try:
        session = Session()
        
        db_chat = session.query(DBChat).filter(DBChat.id == chat_id).first()
        
        if not db_chat:
            return None
            
        return Chat(
            id=db_chat.id,
            title=db_chat.title,
            username=db_chat.username,
            type=db_chat.type,
            last_message_time=db_chat.last_message_time
        )
        
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        session.close()

def get_direct_chat_by_contact(contact_id: int) -> Optional[Chat]:
    """Get direct chat metadata by contact ID."""
    try:
        session = Session()
        
        db_chat = session.query(DBChat).filter(
            DBChat.id == contact_id,
            DBChat.type == 'user'
        ).first()
        
        if not db_chat:
            return None
            
        return Chat(
            id=db_chat.id,
            title=db_chat.title,
            username=db_chat.username,
            type=db_chat.type,
            last_message_time=db_chat.last_message_time
        )
        
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        session.close()

def get_contact_chats(contact_id: int, limit: int = 20, page: int = 0) -> List[Chat]:
    """Get all chats involving the contact.
    
    Args:
        contact_id: The contact's ID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    try:
        session = Session()
        
        # Using a subquery to get distinct chats for the contact
        db_chats = session.query(DBChat).join(DBMessage, DBChat.id == DBMessage.chat_id).filter(
            or_(
                DBMessage.sender_id == contact_id,
                DBChat.id == contact_id
            )
        ).distinct().order_by(desc(DBChat.last_message_time)).limit(limit).offset(page * limit).all()
        
        result = []
        for db_chat in db_chats:
            chat = Chat(
                id=db_chat.id,
                title=db_chat.title,
                username=db_chat.username,
                type=db_chat.type,
                last_message_time=db_chat.last_message_time
            )
            result.append(chat)
            
        return result
        
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        session.close()

def get_last_interaction(contact_id: int) -> Optional[Message]:
    """Get most recent message involving the contact."""
    try:
        session = Session()
        
        result = session.query(DBMessage, DBChat).join(DBChat).filter(
            or_(
                DBMessage.sender_id == contact_id,
                DBChat.id == contact_id
            )
        ).order_by(desc(DBMessage.timestamp)).first()
        
        if not result:
            return None
            
        db_msg, db_chat = result
        return Message(
            id=db_msg.id,
            chat_id=db_msg.chat_id,
            chat_title=db_chat.title,
            sender_name=db_msg.sender_name,
            content=db_msg.content,
            timestamp=db_msg.timestamp,
            is_from_me=db_msg.is_from_me,
            sender_id=db_msg.sender_id
        )
        
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        session.close()