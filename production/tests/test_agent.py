"""
Test suite for TechCorp FTE Agent functionality
Tests agent tools, formatting, and core functionality
"""

import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock
import sys
import os

# Add the production directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.tools import (
    search_knowledge_base,
    create_ticket,
    escalate_to_human,
    analyze_sentiment,
    send_response
)
from agent.formatters import format_for_channel
from agent.customer_success_agent import run_agent

class TestAgentTools:
    """Test agent tool functions"""
    
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        """Test that search_knowledge_base returns results for valid queries"""
        # Mock the database queries and Gemini API
        with patch('agent.tools.queries.search_knowledge_by_vector') as mock_search:
            mock_search.return_value = [
                {
                    'title': 'Password Reset Guide',
                    'content': 'To reset your password, click "Forgot Password" on the login page.',
                    'similarity': 0.85
                }
            ]
            
            result = await search_knowledge_base("password reset")
            
            assert result is not None
            assert len(result) > 0
            assert "Password Reset Guide" in result
            assert "0.85" in result
    
    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """Test that search_knowledge_base handles no results gracefully"""
        with patch('agent.tools.queries.search_knowledge_by_vector') as mock_search:
            mock_search.return_value = []
            
            result = await search_knowledge_base("xyznonexistentquery999")
            
            assert result is not None
            assert "no" in result.lower() or "not found" in result.lower()
    
    @pytest.mark.asyncio
    async def test_create_ticket_returns_id(self):
        """Test that create_ticket returns a valid ticket ID"""
        with patch('agent.tools.queries.create_conversation') as mock_conv, \
             patch('agent.tools.queries.create_ticket') as mock_ticket:
            
            mock_conv.return_value = "conv-123"
            mock_ticket.return_value = "ticket-456"
            
            result = await create_ticket("user-123", "login issue", "medium", "email")
            
            assert result is not None
            assert result.startswith("Ticket")
    
    @pytest.mark.asyncio
    async def test_escalation_updates_status(self):
        """Test that escalate_to_human properly escalates a ticket"""
        with patch('agent.tools.queries.update_ticket_status') as mock_update, \
             patch('agent.tools.queries.log_escalation') as mock_log:
            
            mock_log.return_value = "escalation-789"
            
            result = await escalate_to_human("ticket-123", "customer angry", "high")
            
            assert result is not None
            assert "Escalated" in result
            assert "escalation-789" in result
    
    @pytest.mark.asyncio
    async def test_sentiment_detects_anger(self):
        """Test that analyze_sentiment detects negative sentiment"""
        with patch('agent.tools.genai.GenerativeModel') as mock_model:
            # Mock angry sentiment response
            mock_instance = AsyncMock()
            mock_instance.generate_content.return_value.text = json.dumps({
                'score': 0.2,
                'label': 'negative',
                'flags': ['angry', 'escalation_needed']
            })
            mock_model.return_value = mock_instance
            
            result = await analyze_sentiment("This is TERRIBLE, I'm furious!")
            
            assert result is not None
            sentiment_data = json.loads(result)
            assert sentiment_data['score'] < 0.4
            assert sentiment_data['label'] == 'negative'
            assert 'angry' in sentiment_data['flags']
    
    @pytest.mark.asyncio
    async def test_sentiment_detects_positive(self):
        """Test that analyze_sentiment detects positive sentiment"""
        with patch('agent.tools.genai.GenerativeModel') as mock_model:
            # Mock positive sentiment response
            mock_instance = AsyncMock()
            mock_instance.generate_content.return_value.text = json.dumps({
                'score': 0.8,
                'label': 'positive',
                'flags': ['satisfied']
            })
            mock_model.return_value = mock_instance
            
            result = await analyze_sentiment("Thank you so much, works great!")
            
            assert result is not None
            sentiment_data = json.loads(result)
            assert sentiment_data['score'] > 0.6
            assert sentiment_data['label'] == 'positive'
    
    @pytest.mark.asyncio
    async def test_sentiment_fallback_on_error(self):
        """Test that analyze_sentiment returns fallback on error"""
        with patch('agent.tools.genai.GenerativeModel') as mock_model:
            mock_model.side_effect = Exception("API error")
            
            result = await analyze_sentiment("Test message")
            
            assert result is not None
            sentiment_data = json.loads(result)
            assert sentiment_data['score'] == 0.5
            assert sentiment_data['label'] == 'neutral'
            assert sentiment_data['flags'] == []

class TestAgentFormatting:
    """Test agent response formatting"""
    
    def test_format_email_has_greeting(self):
        """Test that email formatting includes proper greeting"""
        result = format_for_channel("Test response", "email", "TICKET-001", "Sarah")
        
        assert "Hi Sarah" in result
        assert "TechCorp Support Team" in result
        assert "TICKET-001" in result
    
    def test_format_email_has_no_name(self):
        """Test that email formatting handles missing name"""
        result = format_for_channel("Test response", "email", "TICKET-001", "")
        
        assert "Hi there" in result
        assert "TechCorp Support Team" in result
    
    def test_format_whatsapp_is_short(self):
        """Test that WhatsApp formatting keeps messages short"""
        long_message = "A" * 500
        result = format_for_channel(long_message, "whatsapp", "T001", "")
        
        assert len(result) < 400
        assert "Reply 'human'" in result
    
    def test_format_whatsapp_has_human_support(self):
        """Test that WhatsApp formatting includes human support option"""
        result = format_for_channel("Test response", "whatsapp", "T001", "John")
        
        assert "Reply 'human'" in result
        assert "👤" in result
    
    def test_format_web_has_ticket_ref(self):
        """Test that web form formatting includes ticket reference"""
        result = format_for_channel("Test", "web_form", "TICKET-123", "")
        
        assert "TICKET-123" in result
        assert "TechCorp Support" in result
    
    def test_format_web_has_name(self):
        """Test that web form formatting includes customer name"""
        result = format_for_channel("Test", "web_form", "TICKET-123", "Alice")
        
        assert "Hi Alice" in result
        assert "TechCorp Support" in result

class TestAgentIntegration:
    """Test agent integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_run_agent_with_simple_question(self):
        """Test agent with a simple question"""
        with patch('agent.customer_success_agent.get_producer') as mock_producer, \
             patch('agent.customer_success_agent.queries.create_or_get_customer') as mock_customer, \
             patch('agent.customer_success_agent.queries.create_conversation') as mock_conv, \
             patch('agent.customer_success_agent.queries.create_ticket') as mock_ticket, \
             patch('agent.customer_success_agent.queries.store_message') as mock_store, \
             patch('agent.customer_success_agent.LlmAgent') as mock_agent:
            
            # Setup mocks
            mock_producer.return_value.publish_event = AsyncMock()
            mock_customer.return_value = "customer-123"
            mock_conv.return_value = "conv-123"
            mock_ticket.return_value = "ticket-123"
            mock_store.return_value = "msg-123"
            
            # Mock agent response
            mock_instance = AsyncMock()
            mock_instance.run_async.return_value.output = "Here's how to reset your password"
            mock_instance.run_async.return_value.tool_calls = []
            mock_instance.run_async.return_value.escalated = False
            mock_instance.run_async.return_value.latency_ms = 1500
            mock_agent.return_value = mock_instance
            
            context = {
                'customer_id': 'customer-123',
                'channel': 'web_form',
                'conversation_id': 'conv-123'
            }
            
            result = await run_agent("How do I reset my password?", context)
            
            assert result is not None
            assert result['success'] is True
            assert result['escalated'] is False
            assert result['latency_ms'] > 0
    
    @pytest.mark.asyncio
    async def test_run_agent_with_escalation_trigger(self):
        """Test agent with escalation trigger"""
        with patch('agent.customer_success_agent.get_producer') as mock_producer, \
             patch('agent.customer_success_agent.queries.create_or_get_customer') as mock_customer, \
             patch('agent.customer_success_agent.queries.create_conversation') as mock_conv, \
             patch('agent.customer_success_agent.queries.create_ticket') as mock_ticket, \
             patch('agent.customer_success_agent.queries.store_message') as mock_store, \
             patch('agent.customer_success_agent.LlmAgent') as mock_agent:
            
            # Setup mocks
            mock_producer.return_value.publish_event = AsyncMock()
            mock_customer.return_value = "customer-123"
            mock_conv.return_value = "conv-123"
            mock_ticket.return_value = "ticket-123"
            mock_store.return_value = "msg-123"
            
            # Mock agent response with escalation
            mock_instance = AsyncMock()
            mock_instance.run_async.return_value.output = "I'm escalating this to our human team."
            mock_instance.run_async.return_value.tool_calls = [
                {'tool_name': 'escalate_to_human', 'arguments': {'ticket_id': 'ticket-123', 'reason': 'refund_request'}}
            ]
            mock_instance.run_async.return_value.escalated = True
            mock_instance.run_async.return_value.latency_ms = 2000
            mock_agent.return_value = mock_instance
            
            context = {
                'customer_id': 'customer-123',
                'channel': 'email',
                'conversation_id': 'conv-123'
            }
            
            result = await run_agent("I want a refund for my subscription", context)
            
            assert result is not None
            assert result['success'] is True
            assert result['escalated'] is True
            assert result['latency_ms'] > 0

# Test fixtures and utilities
@pytest.fixture
def mock_database():
    """Mock database connections"""
    with patch('agent.tools.get_connection') as mock_conn:
        mock_conn.return_value.__aenter__.return_value.fetchval.return_value = 1
        yield mock_conn

@pytest.fixture
def mock_gemini():
    """Mock Gemini API"""
    with patch('agent.tools.genai.GenerativeModel') as mock_model:
        mock_instance = AsyncMock()
        mock_instance.generate_content.return_value.text = json.dumps({
            'score': 0.5,
            'label': 'neutral',
            'flags': []
        })
        mock_model.return_value = mock_instance
        yield mock_model

# Pytest configuration
pytest_plugins = []

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__])
