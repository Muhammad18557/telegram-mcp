"""
Repository classes for database operations.

Provides abstraction for data access operations on Telegram chats and messages.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import desc, or_, and_

from database.base import get_session
from database.models import Chat, Message


class ChatRepository:
    """Repository for chat operations."""
    
    def store_chat(
        self,
        chat_id: int,
        title: str,
        username: Optional[str],
        chat_type: str,
        last_message_time: datetime,
    ) -> None:
        """Store a chat in the database."""
        session = get_session()
        try:
            chat = session.query(Chat).filter_by(id=chat_id).first()
            
            if chat:
                # Update existing chat
                chat.title = title
                chat.username = username
                chat.type = chat_type
                chat.last_message_time = last_message_time
            else:
                # Create new chat
                chat = Chat(
                    id=chat_id,
                    title=title,
                    username=username,
                    type=chat_type,
                    last_message_time=last_message_time
                )
                session.add(chat)
                
            session.commit()
        finally:
            session.close()
    
    def get_chats(
        self,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        chat_type: Optional[str] = None,
        sort_by: str = "last_message_time"
    ) -> List[Chat]:
        """Get chats from the database."""
        session = get_session()
        try:
            # Build query
            db_query = session.query(Chat)
            
            # Apply filters
            if query:
                db_query = db_query.filter(
                    or_(
                        Chat.title.ilike(f"%{query}%"),
                        Chat.username.ilike(f"%{query}%")
                    )
                )
            
            if chat_type:
                db_query = db_query.filter(Chat.type == chat_type)
                
            # Apply sorting
            if sort_by == "last_message_time":
                db_query = db_query.order_by(desc(Chat.last_message_time))
            else:
                db_query = db_query.order_by(Chat.title)
                
            # Apply pagination
            db_query = db_query.limit(limit).offset(offset)
            
            return db_query.all()
        finally:
            session.close()
    
    def get_chat_by_id(self, chat_id: int) -> Optional[Chat]:
        """Get a chat by its ID."""
        session = get_session()
        try:
            return session.query(Chat).filter_by(id=chat_id).first()
        finally:
            session.close()


class MessageRepository:
    """Repository for message operations."""
    
    def store_message(
        self,
        message_id: int,
        chat_id: int,
        sender_id: int,
        sender_name: str,
        content: str,
        timestamp: datetime,
        is_from_me: bool,
    ) -> None:
        """Store a message in the database."""
        if not content:  # Skip empty messages
            return
            
        session = get_session()
        try:
            message = session.query(Message).filter_by(
                id=message_id, chat_id=chat_id
            ).first()
            
            if message:
                # Update existing message
                message.sender_id = sender_id
                message.sender_name = sender_name
                message.content = content
                message.timestamp = timestamp
                message.is_from_me = is_from_me
            else:
                # Create new message
                message = Message(
                    id=message_id,
                    chat_id=chat_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    content=content,
                    timestamp=timestamp,
                    is_from_me=is_from_me
                )
                session.add(message)
                
            session.commit()
        finally:
            session.close()
    
    def get_messages(
        self,
        chat_id: Optional[int] = None,
        sender_id: Optional[int] = None,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        date_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> List[Message]:
        """Get messages from the database."""
        session = get_session()
        try:
            # Build query
            db_query = session.query(Message).join(Chat)
            
            # Apply filters
            filters = []
            
            if chat_id:
                filters.append(Message.chat_id == chat_id)
                
            if sender_id:
                filters.append(Message.sender_id == sender_id)
                
            if query:
                filters.append(Message.content.ilike(f"%{query}%"))
                
            if date_range:
                start_date, end_date = date_range
                filters.append(and_(
                    Message.timestamp >= start_date,
                    Message.timestamp <= end_date
                ))
                
            if filters:
                db_query = db_query.filter(and_(*filters))
                
            # Apply sorting and pagination
            db_query = db_query.order_by(desc(Message.timestamp))
            db_query = db_query.limit(limit).offset(offset)
            
            return db_query.all()
        finally:
            session.close()
    
    def get_message_context(
        self,
        message_id: int,
        chat_id: int,
        before: int = 5,
        after: int = 5
    ) -> Dict[str, Any]:
        """Get context around a specific message."""
        session = get_session()
        try:
            # Get the target message
            target_message = session.query(Message).filter_by(
                id=message_id, chat_id=chat_id
            ).first()
            
            if not target_message:
                raise ValueError(f"Message with ID {message_id} in chat {chat_id} not found")
                
            # Get messages before
            before_messages = session.query(Message).filter(
                Message.chat_id == chat_id,
                Message.timestamp < target_message.timestamp
            ).order_by(desc(Message.timestamp)).limit(before).all()
            
            # Get messages after
            after_messages = session.query(Message).filter(
                Message.chat_id == chat_id,
                Message.timestamp > target_message.timestamp
            ).order_by(Message.timestamp).limit(after).all()
            
            return {
                "message": target_message,
                "before": before_messages,
                "after": after_messages
            }
        finally:
            session.close()