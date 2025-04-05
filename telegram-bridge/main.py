"""
Telegram Bridge main entry point.

This module initializes and runs the Telegram bridge application, connecting 
to the Telegram API and providing a REST API server for interaction.
"""

import asyncio
import logging
import sys
import uvicorn

from config import API_ID, API_HASH, SESSION_FILE, HTTP_PORT, HTTP_HOST
from database import init_db, ChatRepository, MessageRepository
from api import TelegramApiClient, TelegramMiddleware
from service import TelegramService
from server import app, get_telegram_service

# Initialize logger
logger = logging.getLogger(__name__)


# Global service instance
telegram_service = None


# Override the get_telegram_service function in the API app
def get_service_override():
    """Get the Telegram service singleton."""
    global telegram_service
    if telegram_service is None:
        raise RuntimeError("Telegram service not initialized")
    return telegram_service


# Initialize the application
async def init_app():
    """Initialize the application components."""
    global telegram_service
    
    # Initialize database
    init_db()
    
    # Create repositories
    chat_repo = ChatRepository()
    message_repo = MessageRepository()
    
    # Create API client
    client = TelegramApiClient(SESSION_FILE, API_ID, API_HASH)
    
    # Create middleware
    middleware = TelegramMiddleware(client)
    
    # Create service
    telegram_service = TelegramService(client, middleware, chat_repo, message_repo)
    
    # Override the service getter in the API app
    app.dependency_overrides[get_telegram_service] = get_service_override
    
    # Setup the service
    await telegram_service.setup()
    
    # Return the service for further use
    return telegram_service


async def login_flow():
    """Interactive login flow for Telegram."""
    global telegram_service
    
    if not await telegram_service.authorize():
        logger.info("Need to log in. Please enter your phone number:")
        phone = input("Phone number: ")
        
        # Send the code request
        await telegram_service.client.send_code_request(phone)
        
        logger.info("Code sent. Please enter the code you received:")
        code = input("Code: ")
        
        try:
            success = await telegram_service.login(phone, code)
            if not success:
                logger.error("Failed to log in with the provided code")
                return False
        except Exception as e:
            logger.error(f"Error signing in: {e}")
            logger.info(
                "If you have two-factor authentication enabled, please enter your password:"
            )
            password = input("Password: ")
            success = await telegram_service.login(phone, code, password)
            if not success:
                logger.error("Failed to log in with the provided password")
                return False
    
    logger.info("Successfully logged in to Telegram")
    return True


async def main():
    """Main application entry point."""
    try:
        # Initialize the application
        global telegram_service
        telegram_service = await init_app()
        
        # Login to Telegram if needed
        if not await login_flow():
            logger.error("Failed to authenticate with Telegram")
            return
        
        # Initial sync of message history
        await telegram_service.sync_all_dialogs()
        
        # Start the API server
        logger.info(f"Starting FastAPI server on {HTTP_HOST}:{HTTP_PORT}")
        config = uvicorn.Config(app=app, host=HTTP_HOST, port=HTTP_PORT, log_level="info")
        server = uvicorn.Server(config)
        
        # Keep the script running
        logger.info("Telegram bridge is running. Press Ctrl+C to exit.")
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("Shutting down Telegram bridge")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
