"""
End-to-End Tests for TechCorp FTE System
Tests complete workflows and system integration
"""

import pytest
import asyncio
import json
import httpx
from unittest.mock import patch, AsyncMock
import sys
import os

# Add the production directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestHealthEndpoints:
    """Test health and readiness endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        """Test that health endpoint returns 200"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                response = await client.get("/health")
                
                # Accept both 200 and degraded status
                assert response.status_code in [200, 503]
                data = response.json()
                assert "status" in data
                assert "timestamp" in data
                assert "services" in data
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_ready_returns_200_or_503_depending_on_services(self):
        """Test that ready endpoint returns 200 or 503 based on services"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                response = await client.get("/ready")
                
                # Accept both ready and not ready status
                assert response.status_code in [200, 503]
                
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "ready"
                else:
                    data = response.json()
                    assert data["status"] == "not_ready"
            except httpx.ConnectError:
                pytest.skip("API server not running")

class TestWebFormFlow:
    """Test complete web form submission flow"""
    
    @pytest.mark.asyncio
    async def test_submit_valid_form(self):
        """Test submitting a valid web form"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                submission = {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "subject": "Login Issue",
                    "category": "technical",
                    "message": "I cannot log in to my account. The password reset link is not working."
                }
                
                response = await client.post("/api/support/submit", json=submission)
                
                assert response.status_code == 200
                data = response.json()
                assert "ticket_id" in data
                assert "message" in data
                assert "estimated_response_time" in data
                assert data["ticket_id"].startswith("TICKET-")
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_submit_invalid_form(self):
        """Test submitting invalid web form data"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                # Test with missing required fields
                invalid_submission = {
                    "name": "",  # Empty name
                    "email": "invalid-email",  # Invalid email
                    "subject": "A",  # Too short
                    "category": "general",
                    "message": "Hi"  # Too short
                }
                
                response = await client.post("/api/support/submit", json=invalid_submission)
                
                assert response.status_code == 422
                data = response.json()
                assert "detail" in data
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_get_ticket_status(self):
        """Test getting ticket status"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                # First submit a form to get a ticket
                submission = {
                    "name": "Jane Smith",
                    "email": "jane@example.com",
                    "subject": "API Question",
                    "category": "technical",
                    "message": "How do I integrate the API with my application?"
                }
                
                submit_response = await client.post("/api/support/submit", json=submission)
                assert submit_response.status_code == 200
                ticket_id = submit_response.json()["ticket_id"]
                
                # Now get the ticket status
                response = await client.get(f"/api/support/ticket/{ticket_id}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["ticket_id"] == ticket_id
                assert "status" in data
                assert "messages" in data
                assert "created_at" in data
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_ticket(self):
        """Test getting status for non-existent ticket"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                response = await client.get("/api/support/ticket/NONEXISTENT-TICKET")
                
                assert response.status_code == 404
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_get_form_config(self):
        """Test getting form configuration"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                response = await client.get("/api/support/form-config")
                
                assert response.status_code == 200
                data = response.json()
                assert "categories" in data
                assert "priorities" in data
                assert "max_message_length" in data
                
                # Verify expected categories
                categories = data["categories"]
                assert "general" in categories
                assert "technical" in categories
                assert "billing" in categories
                
                # Verify expected priorities
                priorities = data["priorities"]
                assert "low" in priorities
                assert "medium" in priorities
                assert "high" in priorities
            except httpx.ConnectError:
                pytest.skip("API server not running")

class TestWhatsAppWebhook:
    """Test WhatsApp webhook endpoints"""
    
    @pytest.mark.asyncio
    async def test_webhook_verification(self):
        """Test WhatsApp webhook verification"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                # Test webhook verification
                params = {
                    "hub.mode": "subscribe",
                    "hub.challenge": "test_challenge_123",
                    "hub.verify_token": "any_random_string_you_choose"
                }
                
                response = await client.get("/webhooks/whatsapp", params=params)
                
                # Should return the challenge as plain text
                assert response.status_code == 200
                assert response.text == "test_challenge_123"
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_webhook_invalid_token(self):
        """Test WhatsApp webhook with invalid token"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                params = {
                    "hub.mode": "subscribe",
                    "hub.challenge": "test_challenge_123",
                    "hub.verify_token": "wrong_token"
                }
                
                response = await client.get("/webhooks/whatsapp", params=params)
                
                assert response.status_code == 403
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_webhook_incoming_message(self):
        """Test WhatsApp webhook with incoming message"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                # Mock WhatsApp webhook payload
                payload = {
                    "entry": [{
                        "id": "webhook_id_123",
                        "changes": [{
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "923001234567"
                                },
                                "messages": [{
                                    "from": "923001234567",
                                    "id": "msg_id_123",
                                    "timestamp": "1709912345",
                                    "text": {
                                        "body": "Hello, I need help with my account"
                                    },
                                    "type": "text"
                                }]
                            }
                        }]
                    }]
                }
                
                response = await client.post("/webhooks/whatsapp", json=payload)
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "received"
            except httpx.ConnectError:
                pytest.skip("API server not running")

class TestMetrics:
    """Test metrics and monitoring endpoints"""
    
    @pytest.mark.asyncio
    async def test_channel_metrics_returns_dict(self):
        """Test channel metrics endpoint"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                response = await client.get("/api/metrics/channels")
                
                assert response.status_code == 200
                data = response.json()
                assert "metrics" in data
                assert "timeframe_hours" in data
                assert "generated_at" in data
                
                metrics = data["metrics"]
                # Should have metrics for each channel
                # Note: This might return empty if no data exists
                assert isinstance(metrics, dict)
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_daily_metrics_returns_data(self):
        """Test daily metrics endpoint"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                # Test with today's date
                from datetime import date
                today = date.today().strftime("%Y-%m-%d")
                
                response = await client.get(f"/api/metrics/daily/{today}")
                
                assert response.status_code == 200
                data = response.json()
                assert "date" in data
                assert "metrics" in data
                assert "source" in data  # "cached" or "generated"
                
                metrics = data["metrics"]
                # Should have daily metrics
                assert isinstance(metrics, dict)
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_admin_overview(self):
        """Test admin overview endpoint"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                response = await client.get("/api/admin/overview")
                
                assert response.status_code == 200
                data = response.json()
                assert "total_customers" in data
                assert "total_tickets_today" in data
                assert "tickets_by_status" in data
                assert "escalation_rate" in data
                assert "generated_at" in data
                
                # Verify data types
                assert isinstance(data["total_customers"], int)
                assert isinstance(data["total_tickets_today"], int)
                assert isinstance(data["tickets_by_status"], dict)
                assert isinstance(data["escalation_rate"], (int, float))
            except httpx.ConnectError:
                pytest.skip("API server not running")

class TestCrossChannel:
    """Test cross-channel customer continuity"""
    
    @pytest.mark.asyncio
    async def test_same_customer_multiple_channels(self):
        """Test same customer across multiple channels"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                customer_email = "crosschannel@example.com"
                
                # Submit web form ticket
                web_submission = {
                    "name": "Cross Channel User",
                    "email": customer_email,
                    "subject": "Multi-channel Test",
                    "category": "general",
                    "message": "Testing cross-channel continuity."
                }
                
                web_response = await client.post("/api/support/submit", json=web_submission)
                assert web_response.status_code == 200
                web_ticket_id = web_response.json()["ticket_id"]
                
                # Look up customer by email
                lookup_response = await client.get(f"/api/customers/lookup?email={customer_email}")
                assert lookup_response.status_code == 200
                
                customer_data = lookup_response.json()
                assert "customer" in customer_data
                assert customer_data["customer"]["email"] == customer_email
                assert "recent_conversations" in customer_data
                
                # Verify customer exists and has conversations
                conversations = customer_data["recent_conversations"]
                assert len(conversations) >= 1
                
                # Find the web form conversation
                web_conv = None
                for conv in conversations:
                    if conv["channel"] == "web_form":
                        web_conv = conv
                        break
                
                assert web_conv is not None
                assert web_conv["message_count"] >= 1
                
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_customer_lookup_by_phone(self):
        """Test customer lookup by phone number"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                # First create a customer via web form
                submission = {
                    "name": "Phone User",
                    "email": "phone@example.com",
                    "subject": "Phone Lookup Test",
                    "category": "general",
                    "message": "Testing phone number lookup."
                }
                
                submit_response = await client.post("/api/support/submit", json=submission)
                assert submit_response.status_code == 200
                
                # Try to lookup by phone (this might not work if phone is not stored)
                phone_lookup = await client.get("/api/customers/lookup?phone=1234567890")
                
                # Should return 404 if phone not found, or 200 if found
                assert phone_lookup.status_code in [200, 404]
                
                if phone_lookup.status_code == 200:
                    data = phone_lookup.json()
                    assert "customer" in data
            except httpx.ConnectError:
                pytest.skip("API server not running")

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_json_request(self):
        """Test handling of invalid JSON requests"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                # Send invalid JSON
                response = await client.post(
                    "/api/support/submit",
                    content="invalid json content",
                    headers={"Content-Type": "application/json"}
                )
                
                assert response.status_code == 422
            except httpx.ConnectError:
                pytest.skip("API server not running")
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test handling of requests with missing required fields"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            try:
                # Send request with missing required fields
                incomplete_submission = {
                    "name": "Test User"
                    # Missing email, subject, category, message
                }
                
                response = await client.post("/api/support/submit", json=incomplete_submission)
                
                assert response.status_code == 422
                data = response.json()
                assert "detail" in data
            except httpx.ConnectError:
                pytest.skip("API server not running")

# Test utilities and fixtures
@pytest.fixture
def api_client():
    """Create HTTP client for API testing"""
    return httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0)

@pytest.fixture
def sample_submission():
    """Sample valid submission data"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "subject": "Test Subject",
        "category": "general",
        "message": "This is a test message for the web form submission."
    }

# Pytest configuration
pytest_plugins = []

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__])
