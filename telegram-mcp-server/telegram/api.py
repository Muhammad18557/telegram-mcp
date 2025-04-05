"""
API client for interacting with the Telegram Bridge API.
"""

import requests
import json
from typing import Tuple

from . import TELEGRAM_API_BASE_URL

def send_message(recipient: str, message: str) -> Tuple[bool, str]:
    """Send a Telegram message to the specified recipient.
    
    Args:
        recipient: The recipient - either a username (with or without @), 
                  or a chat ID as a string or integer
        message: The message text to send
        
    Returns:
        Tuple[bool, str]: A tuple containing success status and a status message
    """
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        url = f"{TELEGRAM_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "message": message
        }
        
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: Unknown"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"