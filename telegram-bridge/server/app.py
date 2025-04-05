"""
FastAPI application for the Telegram bridge.

Provides HTTP API endpoints for interacting with Telegram.
"""

from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional

from api.models import (
    ChatModel,
    MessageModel,
    MessageContextModel,
    SendMessageRequest,
    SendMessageResponse
)
from service import TelegramService

# Create FastAPI app
app = FastAPI(
    title="Telegram Bridge API",
    description="API for interacting with Telegram",
    version="1.0.0"
)

# Service dependency
def get_telegram_service() -> TelegramService:
    """Get the Telegram service instance.
    
    This function should be replaced with a proper dependency injection
    mechanism to return the singleton instance of the TelegramService.
    """
    # This is a placeholder. In main.py, we'll set this to the actual service instance
    raise NotImplementedError("Telegram service not initialized")


@app.get("/api/chats", response_model=List[ChatModel])
async def list_chats(
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    chat_type: Optional[str] = None,
    sort_by: str = "last_message_time",
    service: TelegramService = Depends(get_telegram_service)
):
    """List chats."""
    chats = service.chat_repo.get_chats(
        query=query,
        limit=limit,
        offset=offset,
        chat_type=chat_type,
        sort_by=sort_by
    )
    return [
        ChatModel(
            id=chat.id,
            title=chat.title,
            username=chat.username,
            type=chat.type,
            last_message_time=chat.last_message_time
        ) for chat in chats
    ]


@app.get("/api/messages", response_model=List[MessageModel])
async def list_messages(
    chat_id: Optional[int] = None,
    sender_id: Optional[int] = None,
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    service: TelegramService = Depends(get_telegram_service)
):
    """List messages."""
    messages = service.message_repo.get_messages(
        chat_id=chat_id,
        sender_id=sender_id,
        query=query,
        limit=limit,
        offset=offset
    )
    return [
        MessageModel(
            id=msg.id,
            chat_id=msg.chat_id,
            chat_title=msg.chat.title,
            sender_id=msg.sender_id,
            sender_name=msg.sender_name,
            content=msg.content,
            timestamp=msg.timestamp,
            is_from_me=msg.is_from_me
        ) for msg in messages
    ]


@app.get("/api/messages/{chat_id}/{message_id}/context", response_model=MessageContextModel)
async def get_message_context(
    chat_id: int,
    message_id: int,
    before: int = 5,
    after: int = 5,
    service: TelegramService = Depends(get_telegram_service)
):
    """Get context around a message."""
    try:
        context = service.message_repo.get_message_context(
            message_id=message_id,
            chat_id=chat_id,
            before=before,
            after=after
        )
        
        # Convert to model
        target_message = MessageModel(
            id=context["message"].id,
            chat_id=context["message"].chat_id,
            chat_title=context["message"].chat.title,
            sender_id=context["message"].sender_id,
            sender_name=context["message"].sender_name,
            content=context["message"].content,
            timestamp=context["message"].timestamp,
            is_from_me=context["message"].is_from_me
        )
        
        before_messages = [
            MessageModel(
                id=msg.id,
                chat_id=msg.chat_id,
                chat_title=msg.chat.title,
                sender_id=msg.sender_id,
                sender_name=msg.sender_name,
                content=msg.content,
                timestamp=msg.timestamp,
                is_from_me=msg.is_from_me
            ) for msg in context["before"]
        ]
        
        after_messages = [
            MessageModel(
                id=msg.id,
                chat_id=msg.chat_id,
                chat_title=msg.chat.title,
                sender_id=msg.sender_id,
                sender_name=msg.sender_name,
                content=msg.content,
                timestamp=msg.timestamp,
                is_from_me=msg.is_from_me
            ) for msg in context["after"]
        ]
        
        return MessageContextModel(
            message=target_message,
            before=before_messages,
            after=after_messages
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    service: TelegramService = Depends(get_telegram_service)
):
    """Send a message to a Telegram recipient."""
    success, message = await service.send_message(
        recipient=request.recipient,
        message=request.message
    )
    return SendMessageResponse(success=success, message=message)