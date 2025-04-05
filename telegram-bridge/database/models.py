"""
Database models for the Telegram bridge.

This module defines SQLAlchemy ORM models for storing Telegram chats and messages.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Index, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Chat(Base):
    """Represents a Telegram chat (direct message, group, channel, etc.)."""
    
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    username = Column(String)
    type = Column(String, nullable=False)
    last_message_time = Column(DateTime)
    
    # Relationship with messages
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chat(id={self.id}, title='{self.title}', type='{self.type}')>"


class Message(Base):
    """Represents a Telegram message with all its metadata."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), primary_key=True)
    sender_id = Column(Integer)
    sender_name = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    is_from_me = Column(Boolean, default=False)
    
    # Relationship with chat
    chat = relationship("Chat", back_populates="messages")
    
    # Indexes for improved query performance
    __table_args__ = (
        Index("idx_messages_chat_id", "chat_id"),
        Index("idx_messages_timestamp", "timestamp"),
        Index("idx_messages_content", "content"),
        Index("idx_messages_sender_id", "sender_id"),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, chat_id={self.chat_id}, sender='{self.sender_name}')>"