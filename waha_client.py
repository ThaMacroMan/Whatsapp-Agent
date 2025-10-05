import os
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from logging_config import get_logger

logger = get_logger(__name__)

class WAHAClient:
    """Client for interacting with WAHA (WhatsApp HTTP API)"""
    
    def __init__(self):
        self.base_url = os.getenv("WAHA_BASE_URL", "http://localhost:3000")
        self.session_name = os.getenv("WAHA_SESSION_NAME", "default")
        self.api_key = os.getenv("WAHA_API_KEY")  # Optional for authentication
        
        # Headers for API requests
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        logger.info(f"WAHA client initialized with base URL: {self.base_url}")
        logger.info(f"Using session: {self.session_name}")
    
    async def start_session(self) -> Dict[str, Any]:
        """
        Start a new WAHA session
        
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/api/sessions/start"
        
        payload = {
            "name": self.session_name,
            "config": {
                "webhooks": [
                    {
                        "url": os.getenv("WEBHOOK_URL", "http://localhost:8000/webhook"),
                        "events": ["message"]
                    }
                ]
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Session {self.session_name} started successfully")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to start session: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error starting WAHA session: {str(e)}")
            raise
    
    async def get_session_status(self) -> Dict[str, Any]:
        """
        Get the current status of the session
        
        Returns:
            Session status dictionary
        """
        url = f"{self.base_url}/api/sessions/{self.session_name}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                return result
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            raise
    
    async def get_qr_code(self) -> str:
        """
        Get QR code for WhatsApp authentication
        
        Returns:
            QR code data URL
        """
        url = f"{self.base_url}/api/sessions/{self.session_name}/auth/qr"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                return result.get("qr", "")
        except Exception as e:
            logger.error(f"Error getting QR code: {str(e)}")
            raise
    
    async def send_text_message(
        self, 
        to: str, 
        message: str,
        reply_to_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a text message to a WhatsApp user or group
        
        Args:
            to: Phone number in international format (e.g., "1234567890@c.us") or group ID
            message: Text message to send
            reply_to_message_id: Optional message ID to reply to
        
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/api/sendText"
        
        payload = {
            "session": self.session_name,
            "chatId": to,
            "text": message
        }
        
        # Add reply context if provided
        if reply_to_message_id:
            payload["quotedMsgId"] = reply_to_message_id
        
        try:
            logger.info(f"🚀 WAHA Client: Sending message to {to}")
            logger.info(f"🚀 WAHA Client: Payload: {payload}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                logger.info(f"🚀 WAHA Client: Response status: {response.status_code}")
                logger.info(f"🚀 WAHA Client: Response text: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                logger.info(f"✅ WAHA Client: Message sent successfully to {to}")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to send message: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            raise
    
    async def send_reaction(
        self,
        to: str,
        message_id: str,
        emoji: str
    ) -> Dict[str, Any]:
        """
        Send a reaction to a message
        
        Args:
            to: Phone number or group ID
            message_id: ID of the message to react to
            emoji: Emoji to react with (e.g., "👍", "❤️")
        
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/api/reaction"
        
        payload = {
            "session": self.session_name,
            "chatId": to,
            "msgId": message_id,
            "reaction": emoji
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Reaction sent successfully: {emoji}")
                return result
        except Exception as e:
            logger.error(f"Error sending reaction: {str(e)}")
            raise
    
    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read
        
        Args:
            message_id: ID of the message to mark as read
        
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/api/sendSeen"
        
        payload = {
            "session": self.session_name,
            "msgId": message_id,
            "chatId": "13065505040@c.us"  # Default chat ID, will be overridden by actual chat
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Message marked as read: {message_id}")
                return result
        except Exception as e:
            logger.error(f"Error marking message as read: {str(e)}")
            raise
    
    async def get_chats(self) -> List[Dict[str, Any]]:
        """
        Get list of chats (individual and groups)
        
        Returns:
            List of chat dictionaries
        """
        url = f"{self.base_url}/api/chats"
        
        params = {
            "session": self.session_name
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                return result
        except Exception as e:
            logger.error(f"Error getting chats: {str(e)}")
            raise
    
    async def get_groups(self) -> List[Dict[str, Any]]:
        """
        Get list of groups
        
        Returns:
            List of group dictionaries
        """
        url = f"{self.base_url}/api/groups"
        
        params = {
            "session": self.session_name
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                return result
        except Exception as e:
            logger.error(f"Error getting groups: {str(e)}")
            raise
    
    async def join_group(self, group_id: str) -> Dict[str, Any]:
        """
        Join a WhatsApp group using invite link
        
        Args:
            group_id: Group invite link or group ID
        
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/api/groups/join"
        
        payload = {
            "session": self.session_name,
            "inviteCode": group_id
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Successfully joined group: {group_id}")
                return result
        except Exception as e:
            logger.error(f"Error joining group: {str(e)}")
            raise
    
    async def leave_group(self, group_id: str) -> Dict[str, Any]:
        """
        Leave a WhatsApp group
        
        Args:
            group_id: Group ID
        
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/api/groups/leave"
        
        payload = {
            "session": self.session_name,
            "groupId": group_id
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Successfully left group: {group_id}")
                return result
        except Exception as e:
            logger.error(f"Error leaving group: {str(e)}")
            raise
    
    async def get_group_info(self, group_id: str) -> Dict[str, Any]:
        """
        Get information about a specific group
        
        Args:
            group_id: Group ID
        
        Returns:
            Group information dictionary
        """
        url = f"{self.base_url}/api/groups/{group_id}"
        
        params = {
            "session": self.session_name
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                result = response.json()
                return result
        except Exception as e:
            logger.error(f"Error getting group info: {str(e)}")
            raise
    
    async def is_session_ready(self) -> bool:
        """
        Check if the session is ready to send messages
        
        Returns:
            True if session is ready, False otherwise
        """
        try:
            status = await self.get_session_status()
            return status.get("status") == "WORKING"
        except Exception as e:
            logger.error(f"Error checking session status: {str(e)}")
            return False
