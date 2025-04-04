"""
Telegram Bridge Module

This module connects to the Telegram API using the Telethon library, enabling
interaction with Telegram chats and messages. It provides an HTTP server for
sending messages to Telegram users or groups, and stores message history in
a SQLite database.

Key Features:
- Connects to Telegram using API credentials.
- Stores chat and message data in a database.
- Provides an HTTP API for sending messages.
- Synchronizes message history and processes new messages.

Usage:
- Ensure TELEGRAM_API_ID and TELEGRAM_API_HASH are set in environment variables.
- Run the script to start the Telegram bridge and HTTP server.
- Use the '/api/send' endpoint to send messages via HTTP requests.
"""

import os
import sqlite3
import json
import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from dotenv import load_dotenv

from telethon import TelegramClient, events
from telethon.tl.types import (
    User,
    Chat,
    Channel,
    Message,
    Dialog,
)
from telethon.utils import get_display_name

# Global variable to store the main event loop
main_loop = None

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Directory for storing data
STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store")
os.makedirs(STORE_DIR, exist_ok=True)

# Database path
DB_PATH = os.path.join(STORE_DIR, "messages.db")

# API credentials from environment variables
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

if not API_ID or not API_HASH:
    logger.error(
        "TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables must be set"
    )
    logger.error("Get them from https://my.telegram.org/auth")
    sys.exit(1)

# Initialize the Telegram client
SESSION_FILE = os.path.join(STORE_DIR, "telegram_session")
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)


class MessageStore:
    """Handles storage and retrieval of Telegram messages in SQLite."""

    def __init__(self, db_path: str):
        """Initialize the message store with the given database path."""
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the database with necessary tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables if they don't exist
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY,
            title TEXT,
            username TEXT,
            type TEXT,
            last_message_time TIMESTAMP
        )
        """
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER,
            chat_id INTEGER,
            sender_id INTEGER,
            sender_name TEXT,
            content TEXT,
            timestamp TIMESTAMP,
            is_from_me BOOLEAN,
            PRIMARY KEY (id, chat_id),
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
        """
        )

        # Create indexes for efficient queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_content ON messages(content)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages(sender_id)"
        )

        conn.commit()
        conn.close()

    def store_chat(
        self,
        chat_id: int,
        title: str,
        username: Optional[str],
        chat_type: str,
        last_message_time: datetime,
    ) -> None:
        """Store a chat in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR REPLACE INTO chats (id, title, username, type, last_message_time) VALUES (?, ?, ?, ?, ?)",
            (chat_id, title, username, chat_type, last_message_time.isoformat()),
        )

        conn.commit()
        conn.close()

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

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """INSERT OR REPLACE INTO messages 
               (id, chat_id, sender_id, sender_name, content, timestamp, is_from_me) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                message_id,
                chat_id,
                sender_id,
                sender_name,
                content,
                timestamp.isoformat(),
                is_from_me,
            ),
        )

        conn.commit()
        conn.close()

    def get_messages(
        self,
        chat_id: Optional[int] = None,
        limit: int = 50,
        query: Optional[str] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query_parts = [
            "SELECT m.id, m.chat_id, c.title, m.sender_name, m.content, m.timestamp, m.is_from_me, m.sender_id FROM messages m"
        ]
        query_parts.append("JOIN chats c ON m.chat_id = c.id")

        conditions = []
        params = []

        if chat_id:
            conditions.append("m.chat_id = ?")
            params.append(chat_id)

        if query:
            conditions.append("m.content LIKE ?")
            params.append(f"%{query}%")

        if conditions:
            query_parts.append("WHERE " + " AND ".join(conditions))

        query_parts.append("ORDER BY m.timestamp DESC")
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])

        cursor.execute(" ".join(query_parts), tuple(params))
        messages = cursor.fetchall()

        results = []
        for msg in messages:
            timestamp = datetime.fromisoformat(msg[5])
            results.append(
                {
                    "id": msg[0],
                    "chat_id": msg[1],
                    "chat_title": msg[2],
                    "sender_name": msg[3],
                    "content": msg[4],
                    "timestamp": timestamp,
                    "is_from_me": msg[6],
                    "sender_id": msg[7],
                }
            )

        conn.close()
        return results

    def get_chats(
        self, limit: int = 50, query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get chats from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query_parts = ["SELECT id, title, username, type, last_message_time FROM chats"]
        params = []

        if query:
            query_parts.append("WHERE title LIKE ? OR username LIKE ?")
            params.extend([f"%{query}%", f"%{query}%"])

        query_parts.append("ORDER BY last_message_time DESC")
        query_parts.append("LIMIT ?")
        params.append(limit)

        cursor.execute(" ".join(query_parts), tuple(params))
        chats = cursor.fetchall()

        results = []
        for chat in chats:
            last_message_time = datetime.fromisoformat(chat[4]) if chat[4] else None
            results.append(
                {
                    "id": chat[0],
                    "title": chat[1],
                    "username": chat[2],
                    "type": chat[3],
                    "last_message_time": last_message_time,
                }
            )

        conn.close()
        return results


# Create message store
message_store = MessageStore(DB_PATH)


async def process_message(message: Message) -> None:
    """Process and store a message."""
    if not message.text:
        return  # Skip non-text messages

    # Get the chat
    chat = message.chat
    if not chat:
        return

    chat_id = message.chat_id

    # Determine chat type and name
    if isinstance(chat, User):
        chat_type = "user"
        title = get_display_name(chat)
        username = chat.username
    elif isinstance(chat, Chat):
        chat_type = "group"
        title = chat.title
        username = None
    elif isinstance(chat, Channel):
        chat_type = "channel" if chat.broadcast else "supergroup"
        title = chat.title
        username = chat.username
    else:
        logger.warning(f"Unknown chat type: {type(chat)}")
        return

    # Store chat information
    message_store.store_chat(
        chat_id=chat_id,
        title=title,
        username=username,
        chat_type=chat_type,
        last_message_time=message.date,
    )

    # Get sender information
    sender = await message.get_sender()
    sender_id = sender.id if sender else 0
    sender_name = get_display_name(sender) if sender else "Unknown"

    # Check if the message is from the current user
    my_id = (await client.get_me()).id
    is_from_me = sender_id == my_id

    # Store the message
    message_store.store_message(
        message_id=message.id,
        chat_id=chat_id,
        sender_id=sender_id,
        sender_name=sender_name,
        content=message.text,
        timestamp=message.date,
        is_from_me=is_from_me,
    )

    logger.info(
        f"Stored message: [{message.date}] {sender_name} in {title}: {message.text[:30]}..."
    )


async def sync_dialog_history(dialog: Dialog, limit: int = 100) -> None:
    """Sync message history for a specific dialog."""
    chat_entity = dialog.entity

    # Extract chat info
    if isinstance(chat_entity, User):
        chat_type = "user"
        title = get_display_name(chat_entity)
        username = chat_entity.username
    elif isinstance(chat_entity, Chat):
        chat_type = "group"
        title = chat_entity.title
        username = None
    elif isinstance(chat_entity, Channel):
        chat_type = "channel" if chat_entity.broadcast else "supergroup"
        title = chat_entity.title
        username = chat_entity.username
    else:
        logger.warning(f"Unknown chat type: {type(chat_entity)}")
        return

    # Store chat info with last message time
    message_store.store_chat(
        chat_id=dialog.id,
        title=title,
        username=username,
        chat_type=chat_type,
        last_message_time=dialog.date,
    )

    # Get messages
    messages = await client.get_messages(dialog.entity, limit=limit)

    # Get current user ID
    my_id = (await client.get_me()).id

    # Process each message
    for message in messages:
        if not message.text:
            continue  # Skip non-text messages

        # Get sender information
        try:
            sender = await message.get_sender()
            sender_id = sender.id if sender else 0
            sender_name = get_display_name(sender) if sender else "Unknown"
        except Exception as e:
            logger.error(f"Error getting sender: {e}")
            sender_id = 0
            sender_name = "Unknown"

        is_from_me = sender_id == my_id

        # Store the message
        message_store.store_message(
            message_id=message.id,
            chat_id=dialog.id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=message.text,
            timestamp=message.date,
            is_from_me=is_from_me,
        )

    logger.info(f"Synced {len(messages)} messages from {title}")


async def sync_all_dialogs() -> None:
    """Sync message history for all dialogs."""
    logger.info("Starting synchronization of all dialogs")

    # Get all dialogs (chats)
    dialogs = await client.get_dialogs(limit=100)

    for dialog in dialogs:
        try:
            await sync_dialog_history(dialog)
        except Exception as e:
            logger.error(f"Error syncing dialog {dialog.name}: {e}")

    logger.info(f"Completed synchronization of {len(dialogs)} dialogs")


# HTTP server for API endpoints
class TelegramAPIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        request = json.loads(post_data.decode("utf-8"))

        if self.path == "/api/send":
            self._handle_send_message(request)
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_send_message(self, request):
        recipient = request.get("recipient")
        message_text = request.get("message")

        if not recipient or not message_text:
            self._send_json_response(
                400, {"success": False, "message": "Recipient and message are required"}
            )
            return

        try:
            # Instead of creating a new event loop, use a shared queue to communicate with the main thread
            # Create a Future to hold the result
            future = asyncio.run_coroutine_threadsafe(
                send_message(recipient, message_text), main_loop
            )

            # Wait for the result (with timeout)
            try:
                success, message = future.result(10)  # Wait up to 10 seconds
                self._send_json_response(
                    200 if success else 500, {"success": success, "message": message}
                )
            except asyncio.TimeoutError:
                self._send_json_response(
                    504,
                    {
                        "success": False,
                        "message": "Request timed out while sending message",
                    },
                )
            except Exception as inner_e:
                logger.error(f"Error in Future: {inner_e}")
                self._send_json_response(
                    500,
                    {"success": False, "message": f"Error in Future: {str(inner_e)}"},
                )

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self._send_json_response(
                500, {"success": False, "message": f"Error: {str(e)}"}
            )

    def _send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


async def send_message(recipient: str, message: str) -> Tuple[bool, str]:
    """Send a message to a Telegram recipient."""
    if not client.is_connected():
        return False, "Not connected to Telegram"

    try:
        # Try to parse recipient as an integer (chat ID)
        try:
            chat_id = int(recipient)
            entity = await client.get_entity(chat_id)
        except ValueError:
            # Not an integer, try as username
            if recipient.startswith("@"):
                recipient = recipient[1:]  # Remove @ if present
            try:
                entity = await client.get_entity(recipient)
            except Exception:
                # Try to find in database
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM chats WHERE title LIKE ? OR username = ?",
                    (f"%{recipient}%", recipient),
                )
                result = cursor.fetchone()
                conn.close()

                if result:
                    entity = await client.get_entity(result[0])
                else:
                    return False, f"Recipient not found: {recipient}"

        # Send the message
        await client.send_message(entity, message)
        return True, f"Message sent to {recipient}"

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False, f"Error sending message: {str(e)}"


# Start HTTP server in a separate thread
def start_http_server(port: int = 8081):
    server_address = ("", port)
    httpd = HTTPServer(server_address, TelegramAPIHandler)
    logger.info(f"Starting HTTP server on port {port}")
    httpd.serve_forever()


async def main():
    global main_loop

    # Store the current event loop
    main_loop = asyncio.get_event_loop()

    logger.info("Starting Telegram bridge")

    # Connect to Telegram
    await client.connect()

    # Check if we're already authorized
    if not await client.is_user_authorized():
        logger.info("Need to log in. Please enter your phone number:")
        phone = input("Phone number: ")
        await client.send_code_request(phone)
        logger.info("Code sent. Please enter the code you received:")
        code = input("Code: ")
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            logger.error(f"Error signing in: {e}")
            logger.info(
                "If you have two-factor authentication enabled, please enter your password:"
            )
            password = input("Password: ")
            await client.sign_in(password=password)

    logger.info("Successfully logged in to Telegram")

    # Start HTTP server in a separate thread
    server_thread = threading.Thread(target=start_http_server)
    server_thread.daemon = True
    server_thread.start()

    # Register event handler for new messages
    @client.on(events.NewMessage)
    async def handle_new_message(event):
        await process_message(event.message)

    # Initial sync of message history
    await sync_all_dialogs()

    # Keep the script running
    logger.info("Telegram bridge is running. Press Ctrl+C to exit.")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    # Run the main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Telegram bridge")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
