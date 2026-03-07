"""
TechCorp FTE WhatsApp Channel Handler
Meta WhatsApp Cloud API integration (FREE tier)
"""

import asyncio
import httpx
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppHandler:
    """WhatsApp channel handler using Meta Cloud API"""
    
    def __init__(self):
        """Initialize WhatsApp handler with credentials"""
        self.whatsapp_token = os.getenv('WHATSAPP_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN')
        
        if not all([self.whatsapp_token, self.phone_number_id, self.verify_token]):
            logger.error("❌ WhatsApp credentials not found in environment variables")
            raise ValueError("WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, and WHATSAPP_VERIFY_TOKEN must be set")
        
        self.api_base_url = "https://graph.facebook.com/v18.0"
        self.timeout = 30
    
    def verify_webhook(
        self, 
        mode: str, 
        token: str, 
        challenge: str
    ) -> Optional[str]:
        """
        Verify webhook for WhatsApp setup
        
        Args:
            mode: Webhook mode
            token: Verification token
            challenge: Challenge string
            
        Returns:
            Optional[str]: Challenge string if verified, None otherwise
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("✅ WhatsApp webhook verified")
            return challenge
        else:
            logger.warning("⚠️ WhatsApp webhook verification failed")
            return None
    
    def process_webhook(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process Meta WhatsApp webhook payload
        
        Args:
            payload: Webhook payload from Meta
            
        Returns:
            List[Dict]: List of normalized message dictionaries
        """
        messages = []
        
        try:
            # Extract messages from webhook payload
            entries = payload.get('entry', [])
            
            for entry in entries:
                changes = entry.get('changes', [])
                
                for change in changes:
                    value = change.get('value', {})
                    
                    # Check if this is a message
                    if 'messages' not in value:
                        continue
                    
                    webhook_messages = value.get('messages', [])
                    contacts = value.get('contacts', [])
                    
                    # Create contact lookup
                    contacts_map = {}
                    for contact in contacts:
                        wa_id = contact.get('wa_id', '')
                        contacts_map[wa_id] = contact
                    
                    # Process each message
                    for msg in webhook_messages:
                        try:
                            normalized_msg = self._normalize_message(msg, contacts_map)
                            if normalized_msg:
                                messages.append(normalized_msg)
                        except Exception as e:
                            logger.error(f"❌ Error processing WhatsApp message: {e}")
                            continue
            
            logger.info(f"📨 Processed {len(messages)} WhatsApp messages")
            
        except Exception as e:
            logger.error(f"❌ Error processing WhatsApp webhook: {e}")
        
        return messages
    
    def _normalize_message(
        self, 
        msg: Dict[str, Any], 
        contacts_map: Dict[str, Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize WhatsApp message to standard format
        
        Args:
            msg: WhatsApp message object
            contacts_map: Contact information lookup
            
        Returns:
            Optional[Dict]: Normalized message or None if invalid
        """
        try:
            # Extract basic message info
            message_id = msg.get('id', '')
            from_phone = msg.get('from', '')
            timestamp = msg.get('timestamp', '')
            message_type = msg.get('type', '')
            
            if not message_id or not from_phone:
                logger.warning("⚠️ Missing required fields in WhatsApp message")
                return None
            
            # Get contact information
            wa_id = from_phone.split('@')[0]  # Remove @c.us suffix
            contact_info = contacts_map.get(wa_id, {})
            profile_name = contact_info.get('profile', {}).get('name', '')
            
            # Extract content based on message type
            content = ""
            if message_type == 'text':
                content = msg.get('text', {}).get('body', '')
            elif message_type == 'interactive':
                # Handle interactive messages
                interactive = msg.get('interactive', {})
                if interactive.get('type') == 'button_reply':
                    content = f"Button: {interactive.get('button_reply', {}).get('title', '')}"
                elif interactive.get('type') == 'list_reply':
                    content = f"List selection: {interactive.get('list_reply', {}).get('title', '')}"
            elif message_type == 'location':
                location = msg.get('location', {})
                content = f"Location: {location.get('latitude', '')}, {location.get('longitude', '')}"
            elif message_type == 'image':
                content = "[Image message]"
            elif message_type == 'document':
                content = "[Document message]"
            elif message_type == 'audio':
                content = "[Audio message]"
            elif message_type == 'video':
                content = "[Video message]"
            else:
                content = f"[{message_type} message]"
            
            # Parse timestamp
            received_at = self._parse_timestamp(timestamp)
            
            # Create normalized message
            normalized_msg = {
                'channel': 'whatsapp',
                'channel_message_id': message_id,
                'customer_phone': from_phone,
                'customer_name': profile_name,
                'subject': '',  # WhatsApp doesn't have subjects
                'content': content,
                'thread_id': message_id,  # Use message ID as thread
                'received_at': received_at,
                'metadata': {
                    'message_type': message_type,
                    'profile_name': profile_name,
                    'wa_id': wa_id,
                    'raw_message': msg
                }
            }
            
            return normalized_msg
            
        except Exception as e:
            logger.error(f"❌ Error normalizing WhatsApp message: {e}")
            return None
    
    def _parse_timestamp(self, timestamp: str) -> str:
        """
        Parse WhatsApp timestamp to ISO format
        
        Args:
            timestamp: Unix timestamp string
            
        Returns:
            str: ISO formatted datetime
        """
        try:
            ts_int = int(timestamp)
            dt = datetime.fromtimestamp(ts_int, tz=timezone.utc)
            return dt.isoformat()
        except Exception as e:
            logger.error(f"❌ Error parsing timestamp: {e}")
            return datetime.now(timezone.utc).isoformat()
    
    async def send_message(self, to_phone: str, body: str) -> Dict[str, Any]:
        """
        Send WhatsApp message
        
        Args:
            to_phone: Recipient phone number
            body: Message content
            
        Returns:
            Dict: Send result
        """
        try:
            # Prepare request payload
            payload = {
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "text",
                "text": {
                    "body": body
                }
            }
            
            # Send request
            url = f"{self.api_base_url}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.whatsapp_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                messages = result.get('messages', [])
                
                if messages:
                    message_id = messages[0].get('id', '')
                    logger.info(f"✅ WhatsApp message sent: {message_id}")
                    
                    return {
                        'delivery_status': 'sent',
                        'channel_message_id': message_id,
                        'to': to_phone,
                        'message_length': len(body)
                    }
                else:
                    logger.error("❌ No message ID in WhatsApp response")
                    return {
                        'delivery_status': 'failed',
                        'error': 'No message ID in response'
                    }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ WhatsApp API error: {e.response.status_code} - {e.response.text}")
            return {
                'delivery_status': 'failed',
                'error': f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp message: {e}")
            return {
                'delivery_status': 'failed',
                'error': str(e)
            }
    
    async def send_template_message(
        self, 
        to_phone: str, 
        template_name: str, 
        components: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Send WhatsApp template message
        
        Args:
            to_phone: Recipient phone number
            template_name: Template name
            components: Template components
            
        Returns:
            Dict: Send result
        """
        try:
            # Prepare request payload
            payload = {
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": "en_US"
                    }
                }
            }
            
            # Add components if provided
            if components:
                payload["template"]["components"] = components
            
            # Send request
            url = f"{self.api_base_url}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.whatsapp_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                messages = result.get('messages', [])
                
                if messages:
                    message_id = messages[0].get('id', '')
                    logger.info(f"✅ WhatsApp template sent: {message_id}")
                    
                    return {
                        'delivery_status': 'sent',
                        'channel_message_id': message_id,
                        'to': to_phone,
                        'template_name': template_name
                    }
                else:
                    logger.error("❌ No message ID in WhatsApp template response")
                    return {
                        'delivery_status': 'failed',
                        'error': 'No message ID in response'
                    }
        
        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp template: {e}")
            return {
                'delivery_status': 'failed',
                'error': str(e)
            }
    
    async def mark_message_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark WhatsApp message as read
        
        Args:
            message_id: Message ID to mark as read
            
        Returns:
            Dict: Result
        """
        try:
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            
            url = f"{self.api_base_url}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.whatsapp_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                logger.info(f"✅ WhatsApp message marked as read: {message_id}")
                return {
                    'success': True,
                    'message_id': message_id
                }
        
        except Exception as e:
            logger.error(f"❌ Error marking WhatsApp message as read: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_business_profile(self) -> Dict[str, Any]:
        """
        Get WhatsApp business profile information
        
        Returns:
            Dict: Business profile data
        """
        try:
            url = f"{self.api_base_url}/{self.phone_number_id}"
            headers = {
                "Authorization": f"Bearer {self.whatsapp_token}"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                return result
        
        except Exception as e:
            logger.error(f"❌ Error getting WhatsApp business profile: {e}")
            return {}
    
    async def test_connection(self) -> bool:
        """
        Test WhatsApp API connection
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Try to get business profile
            profile = await self.get_business_profile()
            if profile:
                logger.info("✅ WhatsApp API connection successful")
                return True
            else:
                logger.error("❌ WhatsApp API connection failed: No profile data")
                return False
        
        except Exception as e:
            logger.error(f"❌ WhatsApp connection test failed: {e}")
            return False

# Global handler instance
_whatsapp_handler: Optional[WhatsAppHandler] = None

def get_whatsapp_handler() -> WhatsAppHandler:
    """Get or create WhatsApp handler instance"""
    global _whatsapp_handler
    if _whatsapp_handler is None:
        _whatsapp_handler = WhatsAppHandler()
    return _whatsapp_handler

# Example usage
if __name__ == "__main__":
    async def test_whatsapp():
        """Test WhatsApp handler"""
        try:
            handler = WhatsAppHandler()
            
            # Test webhook verification
            challenge = handler.verify_webhook(
                mode="subscribe",
                token=handler.verify_token,
                challenge="test_challenge"
            )
            print(f"Webhook verification: {challenge}")
            
            # Test connection
            if await handler.test_connection():
                print("✅ WhatsApp connection successful")
                
                # Test sending message
                result = await handler.send_message(
                    to_phone="1234567890",  # Replace with actual number
                    body="Test message from TechCorp FTE"
                )
                print(f"Send result: {result}")
            else:
                print("❌ WhatsApp connection failed")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    asyncio.run(test_whatsapp())
