"""
Test suite for TechCorp FTE Channel Handlers
Tests Gmail, WhatsApp, and Web Form channel functionality
"""

import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os
import email
from email.message import Message

# Add the production directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from channels.gmail_handler import GmailHandler
from channels.whatsapp_handler import WhatsAppHandler
from channels.web_form_handler import router, SupportFormSubmission
from fastapi.testclient import TestClient

class TestGmailHandler:
    """Test Gmail channel handler functionality"""
    
    def test_gmail_extract_email(self):
        """Test email address extraction from various formats"""
        handler = GmailHandler()
        
        # Test standard format
        result = handler._parse_email_address("John Smith john@test.com")
        assert result == "john@test.com"
        
        # Test with angle brackets
        result = handler._parse_email_address("<john@test.com>")
        assert result == "john@test.com"
        
        # Test with quotes
        result = handler._parse_email_address('"John Smith" <john@test.com>')
        assert result == "john@test.com"
        
        # Test plain email
        result = handler._parse_email_address("john@test.com")
        assert result == "john@test.com"
    
    def test_gmail_extract_name(self):
        """Test sender name extraction from various formats"""
        handler = GmailHandler()
        
        # Test standard format
        result = handler._parse_sender_name("John Smith john@test.com")
        assert result == "John Smith"
        
        # Test with quotes
        result = handler._parse_sender_name('"John Smith" <john@test.com>')
        assert result == "John Smith"
        
        # Test with angle brackets only
        result = handler._parse_sender_name("<john@test.com>")
        assert result == ""
        
        # Test plain email
        result = handler._parse_sender_name("john@test.com")
        assert result == ""
    
    def test_gmail_extract_body_plain_text(self):
        """Test body extraction from plain text email"""
        handler = GmailHandler()
        
        # Create a plain text email message
        msg = Message()
        msg.set_content("This is a plain text email body.")
        
        result = handler._extract_body(msg)
        assert result == "This is a plain text email body."
    
    def test_gmail_extract_body_html(self):
        """Test body extraction from HTML email"""
        handler = GmailHandler()
        
        # Create an HTML email message
        msg = Message()
        msg.add_alternative("This is the plain text part.", "<html><body>This is <b>HTML</b> content.</body></html>")
        
        result = handler._extract_body(msg)
        assert "This is the plain text part." in result
    
    def test_gmail_decode_subject(self):
        """Test subject decoding"""
        handler = GmailHandler()
        
        # Test plain subject
        result = handler._decode_header("Test Subject")
        assert result == "Test Subject"
        
        # Test encoded subject (mock implementation)
        result = handler._decode_header("=?utf-8?B?VGVzdCBTdWJqZWN0?=")
        assert result == "Test Subject"  # This would work with proper decoding
    
    def test_gmail_parse_timestamp(self):
        """Test timestamp parsing"""
        handler = GmailHandler()
        
        # Test valid timestamp
        result = handler._parse_date("Mon, 7 Mar 2024 12:00:00 +0000 (UTC)")
        assert result is not None
        assert "T" in result  # ISO format check
        
        # Test invalid timestamp
        result = handler._parse_date("invalid-date")
        assert result is not None  # Falls back to current time
    
    @pytest.mark.asyncio
    async def test_gmail_send_reply(self):
        """Test sending email reply"""
        handler = GmailHandler()
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp_instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
            
            result = await handler.send_reply(
                to_email="test@example.com",
                subject="Test Subject",
                body="Test body"
            )
            
            assert result['delivery_status'] == 'sent'
            assert 'channel_message_id' in result
            assert mock_smtp_instance.send_message.called
    
    @pytest.mark.asyncio
    async def test_gmail_connection_test(self):
        """Test Gmail connection"""
        handler = GmailHandler()
        
        with patch('imaplib.IMAP4_SSL') as mock_imap, \
             patch('smtplib.SMTP') as mock_smtp:
            
            mock_imap_instance = MagicMock()
            mock_smtp_instance = MagicMock()
            mock_imap.return_value = mock_imap_instance
            mock_smtp.return_value = mock_smtp_instance
            
            result = await handler.test_connection()
            
            assert result is True

class TestWhatsAppHandler:
    """Test WhatsApp channel handler functionality"""
    
    def test_whatsapp_format_phone(self):
        """Test phone number formatting for WhatsApp API"""
        handler = WhatsAppHandler()
        
        # Test that + is removed for API
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "messages": [{"id": "msg_123"}]
            }
            mock_client.return_value.post.return_value = mock_response
            
            asyncio.run(handler.send_message("+923001234567", "Test message"))
            
            # Check that the call was made without the +
            call_args = mock_client.return_value.post.call_args
            request_data = json.loads(call_args[1]['json'])
            assert request_data['to'] == "923001234567"  # No +
    
    def test_whatsapp_long_message(self):
        """Test long message handling"""
        handler = WhatsAppHandler()
        
        # Test message splitting
        long_message = "x" * 2000
        chunks = handler.split_for_whatsapp(long_message)
        
        # All chunks should be under 1600 characters
        for chunk in chunks:
            assert len(chunk) <= 1600
        
        # Should have multiple chunks for very long message
        assert len(chunks) > 1
    
    def test_whatsapp_webhook_verification(self):
        """Test webhook verification"""
        handler = WhatsAppHandler()
        
        # Test valid verification
        result = handler.verify_webhook(
            mode="subscribe",
            token=handler.verify_token,
            challenge="test_challenge"
        )
        
        assert result == "test_challenge"
        
        # Test invalid verification
        result = handler.verify_webhook(
            mode="subscribe",
            token="wrong_token",
            challenge="test_challenge"
        )
        
        assert result is None
    
    def test_whatsapp_process_webhook(self):
        """Test webhook message processing"""
        handler = WhatsAppHandler()
        
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg_123",
                            "from": "923001234567",
                            "text": {"body": "Hello"}
                        }]
                    }
                }]
            }]
        }
        
        messages = handler.process_webhook(payload)
        
        assert len(messages) == 1
        assert messages[0]['channel'] == 'whatsapp'
        assert messages[0]['customer_phone'] == '923001234567'
        assert messages[0]['content'] == 'Hello'
    
    def test_whatsapp_process_webhook_empty(self):
        """Test webhook processing with no messages"""
        handler = WhatsAppHandler()
        
        payload = {
            "entry": [{
                "changes": [{
                    "value": {}
                }]
            }]
        }
        
        messages = handler.process_webhook(payload)
        
        assert len(messages) == 0
    
    @pytest.mark.asyncio
    async def test_whatsapp_send_message(self):
        """Test sending WhatsApp message"""
        handler = WhatsAppHandler()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "messages": [{"id": "msg_sent_123"}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.post.return_value = mock_response
            
            result = await handler.send_message("923001234567", "Test message")
            
            assert result['delivery_status'] == 'sent'
            assert result['channel_message_id'] == 'msg_sent_123'
    
    @pytest.mark.asyncio
    async def test_whatsapp_send_template_message(self):
        """Test sending WhatsApp template message"""
        handler = WhatsAppHandler()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "messages": [{"id": "template_sent_123"}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.post.return_value = mock_response
            
            result = await handler.send_template_message(
                to_phone="923001234567",
                template_name="welcome_message"
            )
            
            assert result['delivery_status'] == 'sent'
            assert result['template_name'] == 'welcome_message'
    
    @pytest.mark.asyncio
    async def test_whatsapp_get_business_profile(self):
        """Test getting business profile"""
        handler = WhatsAppHandler()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "name": "TechCorp Support",
                "about": "We help with your TechCorp account"
            }
            mock_client.return_value.get.return_value = mock_response
            
            result = await handler.get_business_profile()
            
            assert result['name'] == 'TechCorp Support'
            assert 'about' in result

class TestWebFormHandler:
    """Test Web Form channel handler functionality"""
    
    def setup_method(self):
        """Setup FastAPI test client"""
        self.client = TestClient(router)
    
    def test_webform_validation_rejects_short_name(self):
        """Test validation rejects short name"""
        submission = {
            "name": "A",
            "email": "test@example.com",
            "subject": "Test subject",
            "category": "general",
            "message": "This is a valid message length for testing purposes"
        }
        
        response = self.client.post("/support/submit", json=submission)
        
        assert response.status_code == 422
        assert "name" in response.json()["detail"]
    
    def test_webform_validation_rejects_short_message(self):
        """Test validation rejects short message"""
        submission = {
            "name": "John Doe",
            "email": "test@example.com",
            "subject": "Test subject",
            "category": "general",
            "message": "Hi"
        }
        
        response = self.client.post("/support/submit", json=submission)
        
        assert response.status_code == 422
        assert "message" in response.json()["detail"]
    
    def test_webform_validation_rejects_invalid_email(self):
        """Test validation rejects invalid email"""
        submission = {
            "name": "John Doe",
            "email": "invalid-email",
            "subject": "Test subject",
            "category": "general",
            "message": "This is a valid message length for testing purposes"
        }
        
        response = self.client.post("/support/submit", json=submission)
        
        assert response.status_code == 422
    
    def test_webform_validation_rejects_invalid_category(self):
        """Test validation rejects invalid category"""
        submission = {
            "name": "John Doe",
            "email": "test@example.com",
            "subject": "Test subject",
            "category": "invalid_category",
            "message": "This is a valid message length for testing purposes"
        }
        
        response = self.client.post("/support/submit", json=submission)
        
        assert response.status_code == 422
    
    def test_webform_validation_rejects_long_message(self):
        """Test validation rejects message that's too long"""
        submission = {
            "name": "John Doe",
            "email": "test@example.com",
            "subject": "Test subject",
            "category": "general",
            "message": "x" * 1001  # Over 1000 character limit
        }
        
        response = self.client.post("/support/submit", json=submission)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    def test_webform_returns_ticket_id(self):
        """Test valid form submission returns ticket ID"""
        with patch('production.web_form_handler.queries.create_or_get_customer') as mock_customer, \
             patch('production.web_form_handler.queries.create_conversation') as mock_conv, \
             patch('production.web_form_handler.queries.create_ticket') as mock_ticket, \
             patch('production.web_form_handler.queries.store_message') as mock_store, \
             patch('production.web_form_handler.publish_event') as mock_publish:
            
            # Setup mocks
            mock_customer.return_value = "customer-123"
            mock_conv.return_value = "conv-123"
            mock_ticket.return_value = "ticket-456"
            mock_store.return_value = "msg-123"
            mock_publish.return_value = AsyncMock()
            
            submission = {
                "name": "John Doe",
                "email": "john@example.com",
                "subject": "Login issue",
                "category": "technical",
                "message": "I cannot log in to my account. Please help."
            }
            
            response = self.client.post("/support/submit", json=submission)
            
            assert response.status_code == 200
            data = response.json()
            assert "ticket_id" in data
            assert data["ticket_id"] is not None
    
    def test_webform_get_form_config(self):
        """Test getting form configuration"""
        response = self.client.get("/support/form-config")
        
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "priorities" in data
        assert "max_message_length" in data
        assert len(data["categories"]) > 0
        assert len(data["priorities"]) > 0
    
    @pytest.mark.asyncio
    def test_webform_get_ticket_status(self):
        """Test getting ticket status"""
        with patch('production.web_form_handler.queries.get_ticket_by_id') as mock_ticket, \
             patch('production.web_form_handler.queries.get_conversation_messages') as mock_messages:
            
            # Setup mocks
            mock_ticket.return_value = {
                "id": "ticket-123",
                "status": "open",
                "subject": "Login issue",
                "created_at": "2024-03-07T20:30:00Z",
                "conversation_id": "conv-123"
            }
            mock_messages.return_value = [
                {
                    "role": "customer",
                    "content": "I cannot log in",
                    "created_at": "2024-03-07T20:30:00Z",
                    "channel": "web_form"
                }
            ]
            
            response = self.client.get("/support/ticket/ticket-123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ticket_id"] == "ticket-123"
            assert data["status"] == "open"
            assert "messages" in data
    
    def test_webform_get_nonexistent_ticket(self):
        """Test getting non-existent ticket returns 404"""
        with patch('production.web_form_handler.queries.get_ticket_by_id') as mock_ticket:
            mock_ticket.return_value = None
            
            response = self.client.get("/support/ticket/nonexistent")
            
            assert response.status_code == 404
    
    def test_webform_health_check(self):
        """Test health check endpoint"""
        response = self.client.get("/support/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

# Test fixtures
@pytest.fixture
def mock_gmail_handler():
    """Mock Gmail handler"""
    with patch('channels.gmail_handler.os.getenv') as mock_env:
        mock_env.side_effect = lambda key, default=None: {
            'GMAIL_ADDRESS': 'test@example.com',
            'GMAIL_APP_PASSWORD': 'test_password'
        }.get(key, default)
        yield GmailHandler()

@pytest.fixture
def mock_whatsapp_handler():
    """Mock WhatsApp handler"""
    with patch('channels.whatsapp_handler.os.getenv') as mock_env:
        mock_env.side_effect = lambda key, default=None: {
            'WHATSAPP_TOKEN': 'test_token',
            'WHATSAPP_PHONE_NUMBER_ID': 'test_phone_id',
            'WHATSAPP_VERIFY_TOKEN': 'test_verify_token'
        }.get(key, default)
        yield WhatsAppHandler()

# Pytest configuration
pytest_plugins = []

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__])
