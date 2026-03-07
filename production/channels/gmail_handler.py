"""
TechCorp FTE Gmail Channel Handler
Free Gmail integration using IMAP/SMTP with app passwords
"""

import asyncio
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parseaddr, formataddr
from email.header import decode_header
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GmailHandler:
    """Gmail channel handler using IMAP/SMTP"""
    
    def __init__(self):
        """Initialize Gmail handler with credentials"""
        self.gmail_address = os.getenv('GMAIL_ADDRESS')
        self.gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
        
        if not self.gmail_address or not self.gmail_app_password:
            logger.error("❌ Gmail credentials not found in environment variables")
            raise ValueError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set")
        
        self.imap_server = "imap.gmail.com"
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
    
    async def poll_inbox(self) -> List[Dict[str, Any]]:
        """
        Poll Gmail inbox for new messages
        
        Returns:
            List[Dict]: List of normalized message dictionaries
        """
        try:
            loop = asyncio.get_event_loop()
            messages = await loop.run_in_executor(None, self._poll_inbox_sync)
            return messages
        except Exception as e:
            logger.error(f"❌ Error polling Gmail inbox: {e}")
            return []
    
    def _poll_inbox_sync(self) -> List[Dict[str, Any]]:
        """
        Synchronous Gmail inbox polling
        
        Returns:
            List[Dict]: List of normalized message dictionaries
        """
        messages = []
        
        try:
            # Connect to Gmail IMAP
            logger.info("📧 Connecting to Gmail IMAP...")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.gmail_address, self.gmail_app_password)
            mail.select('INBOX')
            
            # Search for unseen messages
            logger.info("🔍 Searching for unseen messages...")
            status, message_ids = mail.search(None, 'UNSEEN')
            
            if status != 'OK':
                logger.warning("⚠️ No unseen messages found")
                return messages
            
            # Process each message
            msg_id_list = message_ids[0].split()
            logger.info(f"📨 Found {len(msg_id_list)} unseen messages")
            
            for msg_id in msg_id_list:
                try:
                    # Fetch message content
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    # Parse message
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Extract message components
                    normalized_msg = self._normalize_message(msg, msg_id.decode())
                    if normalized_msg:
                        messages.append(normalized_msg)
                    
                    # Mark message as seen
                    mail.store(msg_id, '+FLAGS', '\\Seen')
                    
                except Exception as e:
                    logger.error(f"❌ Error processing message {msg_id}: {e}")
                    continue
            
            # Logout
            mail.logout()
            logger.info(f"✅ Processed {len(messages)} messages from Gmail")
            
        except Exception as e:
            logger.error(f"❌ Error in Gmail polling: {e}")
        
        return messages
    
    def _normalize_message(self, msg: email.message.Message, msg_id: str) -> Optional[Dict[str, Any]]:
        """
        Normalize email message to standard format
        
        Args:
            msg: Email message object
            msg_id: Message ID
            
        Returns:
            Optional[Dict]: Normalized message or None if invalid
        """
        try:
            # Extract headers
            from_header = msg.get('From', '')
            subject_header = msg.get('Subject', '')
            message_id = msg.get('Message-ID', '')
            date_header = msg.get('Date', '')
            
            # Parse sender information
            customer_email = self._parse_email_address(from_header)
            customer_name = self._parse_sender_name(from_header)
            
            if not customer_email:
                logger.warning(f"⚠️ No valid email address found in From header: {from_header}")
                return None
            
            # Decode subject
            subject = self._decode_header(subject_header)
            
            # Extract body
            body = self._extract_body(msg)
            
            # Parse received date
            received_at = self._parse_date(date_header)
            
            # Create normalized message
            normalized_msg = {
                'channel': 'email',
                'channel_message_id': message_id,
                'customer_email': customer_email,
                'customer_name': customer_name,
                'subject': subject,
                'content': body,
                'thread_id': message_id,  # Gmail uses Message-ID as thread
                'received_at': received_at,
                'metadata': {
                    'raw_from': from_header,
                    'raw_subject': subject_header,
                    'msg_id': msg_id,
                    'has_attachments': self._has_attachments(msg)
                }
            }
            
            return normalized_msg
            
        except Exception as e:
            logger.error(f"❌ Error normalizing message: {e}")
            return None
    
    def _extract_body(self, msg: email.message.Message) -> str:
        """
        Extract email body text
        
        Args:
            msg: Email message object
            
        Returns:
            str: Email body text
        """
        body = ""
        
        try:
            # Try text/plain first
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == 'text/plain':
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            body = payload.decode(charset, errors='ignore')
                            break
                    elif content_type == 'text/html' and not body:
                        # Fallback to HTML if no plain text found
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            html_body = payload.decode(charset, errors='ignore')
                            # Simple HTML to text conversion
                            body = re.sub(r'<[^>]+>', '', html_body)
            else:
                # Single part message
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='ignore')
            
        except Exception as e:
            logger.error(f"❌ Error extracting email body: {e}")
        
        return body.strip()
    
    def _decode_header(self, header: str) -> str:
        """
        Decode email header
        
        Args:
            header: Raw header string
            
        Returns:
            str: Decoded header
        """
        try:
            decoded_parts = decode_header(header)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding, errors='ignore')
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
            
            return decoded_string.strip()
            
        except Exception as e:
            logger.error(f"❌ Error decoding header: {e}")
            return header
    
    def _parse_email_address(self, from_header: str) -> str:
        """
        Extract email address from From header
        
        Args:
            from_header: From header string
            
        Returns:
            str: Email address
        """
        try:
            name, addr = parseaddr(from_header)
            return addr.lower().strip()
        except Exception:
            # Fallback to regex extraction
            email_match = re.search(r'<([^>]+)>', from_header)
            if email_match:
                return email_match.group(1).lower().strip()
            return from_header.strip()
    
    def _parse_sender_name(self, from_header: str) -> str:
        """
        Extract sender name from From header
        
        Args:
            from_header: From header string
            
        Returns:
            str: Sender name
        """
        try:
            name, addr = parseaddr(from_header)
            if name:
                # Remove quotes and clean up
                name = name.strip('"\'')
                return name
            return ""
        except Exception:
            return ""
    
    def _parse_date(self, date_header: str) -> str:
        """
        Parse email date header to ISO format
        
        Args:
            date_header: Date header string
            
        Returns:
            str: ISO formatted datetime
        """
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_header)
            if dt:
                # Convert to UTC and format
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt.isoformat()
        except Exception as e:
            logger.error(f"❌ Error parsing date: {e}")
        
        # Fallback to current time
        return datetime.now(timezone.utc).isoformat()
    
    def _has_attachments(self, msg: email.message.Message) -> bool:
        """
        Check if email has attachments
        
        Args:
            msg: Email message object
            
        Returns:
            bool: True if has attachments
        """
        try:
            for part in msg.walk():
                content_disposition = part.get('Content-Disposition', '')
                if 'attachment' in content_disposition:
                    return True
            return False
        except Exception:
            return False
    
    async def send_reply(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        thread_id: str = None
    ) -> Dict[str, Any]:
        """
        Send reply email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body
            thread_id: Thread ID for threading
            
        Returns:
            Dict: Send result
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._send_reply_sync, 
                to_email, 
                subject, 
                body, 
                thread_id
            )
            return result
        except Exception as e:
            logger.error(f"❌ Error sending Gmail reply: {e}")
            return {
                'delivery_status': 'failed',
                'error': str(e)
            }
    
    def _send_reply_sync(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        thread_id: str = None
    ) -> Dict[str, Any]:
        """
        Synchronous Gmail reply sending
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body
            thread_id: Thread ID for threading
            
        Returns:
            Dict: Send result
        """
        try:
            # Ensure subject starts with "Re: "
            if not subject.startswith('Re:'):
                subject = f"Re: {subject}"
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['To'] = to_email
            msg['From'] = self.gmail_address
            msg['Subject'] = subject
            
            # Add thread ID if provided
            if thread_id:
                msg['In-Reply-To'] = thread_id
                msg['References'] = thread_id
            
            # Add body
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Send email
            logger.info(f"📤 Sending email to {to_email}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_app_password)
                server.send_message(msg)
            
            channel_message_id = str(uuid.uuid4())
            logger.info(f"✅ Email sent successfully: {channel_message_id}")
            
            return {
                'delivery_status': 'sent',
                'channel_message_id': channel_message_id,
                'to': to_email,
                'subject': subject
            }
            
        except Exception as e:
            logger.error(f"❌ Error sending email: {e}")
            return {
                'delivery_status': 'failed',
                'error': str(e)
            }
    
    async def send_message(self, to_email: str, body: str) -> Dict[str, Any]:
        """
        Send message (convenience method)
        
        Args:
            to_email: Recipient email address
            body: Message body
            
        Returns:
            Dict: Send result
        """
        return await self.send_reply(
            to_email=to_email,
            subject="TechCorp Support Response",
            body=body
        )
    
    async def test_connection(self) -> bool:
        """
        Test Gmail connection
        
        Returns:
            bool: True if connection successful
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._test_connection_sync)
            return result
        except Exception as e:
            logger.error(f"❌ Gmail connection test failed: {e}")
            return False
    
    def _test_connection_sync(self) -> bool:
        """
        Synchronous Gmail connection test
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Test IMAP connection
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.gmail_address, self.gmail_app_password)
            mail.select('INBOX')
            mail.logout()
            
            # Test SMTP connection
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_app_password)
            
            logger.info("✅ Gmail connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Gmail connection test failed: {e}")
            return False

# Global handler instance
_gmail_handler: Optional[GmailHandler] = None

def get_gmail_handler() -> GmailHandler:
    """Get or create Gmail handler instance"""
    global _gmail_handler
    if _gmail_handler is None:
        _gmail_handler = GmailHandler()
    return _gmail_handler

# Example usage
if __name__ == "__main__":
    async def test_gmail():
        """Test Gmail handler"""
        try:
            handler = GmailHandler()
            
            # Test connection
            if await handler.test_connection():
                print("✅ Gmail connection successful")
                
                # Poll inbox
                messages = await handler.poll_inbox()
                print(f"📨 Found {len(messages)} messages")
                
                for msg in messages[:3]:  # Show first 3 messages
                    print(f"From: {msg['customer_email']}")
                    print(f"Subject: {msg['subject']}")
                    print(f"Content: {msg['content'][:100]}...")
                    print("---")
            else:
                print("❌ Gmail connection failed")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    asyncio.run(test_gmail())
