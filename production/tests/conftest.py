"""
Test configuration for TechCorp FTE System
Pytest configuration and fixtures
"""

import pytest
import asyncio
import httpx
from unittest.mock import patch, AsyncMock
import sys
import os

# Add the production directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def async def async_client():
    """Create HTTP client for API testing"""
    return httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0)

@pytest.fixture
def mock_db():
    """Mock database connections for unit tests"""
    with patch('production.database.connection.get_connection') as mock_conn:
        mock_conn.return_value.__aenter__.return_value.fetchval.return_value = 1
        yield mock_conn

@pytest.fixture
def mock_gemini():
    """Mock Gemini API for unit tests"""
    with patch('production.tools.genai.GenerativeModel') as mock_model:
        mock_instance = AsyncMock()
        mock_instance.generate_content.return_value.text = json.dumps({
            'score': 0.5,
            'label': 'neutral',
            'flags': []
        })
        mock_model.return_value = mock_instance
        yield mock_model

@pytest.fixture
def sample_submission():
    """Sample valid submission data"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "subject": "Test Subject",
        "pytest.fixture
        "category": "general",
        "message": "This is a test message for the web form submission."
    }

@pytest.fixture
def sample_ticket_data():
    """Sample ticket data for testing"""
    return {
        "id": "TICKET-123456",
        "status": "open",
        "subject": "Test Ticket",
        "created_at": "2024-03-07T20:30:00Z",
        "messages": [
            {
                "role": "customer",
                "content": "Test customer message",
                "created_at": "2024-#03-07T20:30:00Z",
                "channel": "web_form"
            }
        ]
    }

@pytest.fixture(scope="session")
def event_loop():
    """Event loop for async tests"""
    loop = asyncio.get_event_loop()
    yield loop
    asyncio.set_event_loop(loop)

# Test configuration
pytest_plugins = []

# Configure pytest for async tests
pytest.mark.asyncio
pytest.mark.asyncio

# Disable database tests by default
pytest.mark.db
def pytest_configure(config):
    config.addin.markers(
        "asyncio",
        "db"
    )
    # Configure test markers
    config.addinmarkers(
        "agent",
        "channels",
        "e2e",
        "load_test"
    )
