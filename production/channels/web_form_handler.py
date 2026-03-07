"""
TechCorp FTE Web Form Channel Handler
FastAPI router for web form submissions and ticket management
"""

import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from enum import Literal

from ..database import queries
from ..kafka_client import publish_event, TOPICS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class SupportFormSubmission(BaseModel):
    """Web form submission model"""
    name: str
    email: EmailStr
    subject: str
    category: Literal["general", "technical", "billing", "feedback", "bug_report"]
    message: str
    priority: Literal["low", "medium", "high"] = "medium"
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "subject": "Login Issue",
                "category": "technical",
                "message": "I cannot log in to my account. It says invalid password.",
                "priority": "medium"
            }
        }

class SupportFormResponse(BaseModel):
    """Web form submission response model"""
    ticket_id: str
    message: str
    estimated_response_time: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TICKET-12345678",
                "message": "Your request was received. AI will respond within 5 minutes.",
                "estimated_response_time": "~5 minutes"
            }
        }

class TicketResponse(BaseModel):
    """Ticket information response model"""
    ticket_id: str
    status: str
    subject: str
    created_at: str
    messages: List[Dict[str, Any]]
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TICKET-12345678",
                "status": "open",
                "subject": "Login Issue",
                "created_at": "2024-03-07T20:30:00Z",
                "messages": [
                    {
                        "role": "customer",
                        "content": "I cannot log in to my account.",
                        "created_at": "2024-03-07T20:30:00Z",
                        "channel": "web_form"
                    }
                ]
            }
        }

class FormConfig(BaseModel):
    """Form configuration model"""
    categories: List[str]
    priorities: List[str]
    max_message_length: int
    estimated_response_times: Dict[str, str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "categories": ["general", "technical", "billing", "feedback", "bug_report"],
                "priorities": ["low", "medium", "high"],
                "max_message_length": 1000,
                "estimated_response_times": {
                    "low": "~2 hours",
                    "medium": "~30 minutes",
                    "high": "~5 minutes"
                }
            }
        }

# Create router
router = APIRouter(prefix="/support", tags=["support"])

@router.post("/submit", response_model=SupportFormResponse)
async def submit_support_form(submission: SupportFormSubmission) -> SupportFormResponse:
    """
    Submit a support request via web form
    
    Args:
        submission: Support form submission data
        
    Returns:
        SupportFormResponse: Submission confirmation with ticket ID
    """
    try:
        # Generate ticket ID
        ticket_id = f"TICKET-{str(uuid.uuid4())[:8].upper()}"
        
        # Create normalized message for Kafka
        normalized_message = {
            'channel': 'web_form',
            'channel_message_id': ticket_id,
            'customer_email': submission.email,
            'customer_name': submission.name,
            'subject': submission.subject,
            'content': submission.message,
            'category': submission.category,
            'priority': submission.priority,
            'received_at': datetime.now(timezone.utc).isoformat(),
            'metadata': {
                'source': 'web_form',
                'form_version': '1.0'
            }
        }
        
        # Create or get customer
        customer_id = await queries.create_or_get_customer(
            email=submission.email,
            name=submission.name
        )
        
        # Create conversation
        conversation_id = await queries.create_conversation(
            customer_id=customer_id,
            channel='web_form'
        )
        
        # Create ticket
        await queries.create_ticket(
            conversation_id=conversation_id,
            customer_id=customer_id,
            channel='web_form',
            category=submission.category,
            priority=submission.priority,
            subject=submission.subject
        )
        
        # Store incoming message
        await queries.store_message(
            conversation_id=conversation_id,
            channel='web_form',
            direction='inbound',
            role='customer',
            content=submission.message,
            channel_message_id=ticket_id
        )
        
        # Publish to Kafka for processing
        await publish_event(
            topic=TOPICS['tickets_incoming'],
            event=normalized_message,
            key=ticket_id
        )
        
        # Determine estimated response time based on priority
        response_times = {
            'low': '~2 hours',
            'medium': '~30 minutes',
            'high': '~5 minutes'
        }
        estimated_time = response_times.get(submission.priority, '~30 minutes')
        
        logger.info(f"✅ Support form submitted: {ticket_id} - {submission.email}")
        
        return SupportFormResponse(
            ticket_id=ticket_id,
            message="Your request was received. AI will respond within 5 minutes.",
            estimated_response_time=estimated_time
        )
        
    except Exception as e:
        logger.error(f"❌ Error submitting support form: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process support request. Please try again."
        )

@router.get("/ticket/{ticket_id}", response_model=TicketResponse)
async def get_ticket_status(ticket_id: str) -> TicketResponse:
    """
    Get ticket status and conversation history
    
    Args:
        ticket_id: Ticket ID
        
    Returns:
        TicketResponse: Ticket information and messages
    """
    try:
        # Get ticket information
        ticket = await queries.get_ticket_by_id(ticket_id)
        
        if not ticket:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found"
            )
        
        # Get conversation messages
        messages = await queries.get_conversation_messages(ticket['conversation_id'])
        
        # Format messages for response
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                'role': msg['role'],
                'content': msg['content'],
                'created_at': msg['created_at'],
                'channel': msg['channel']
            }
            formatted_messages.append(formatted_msg)
        
        logger.info(f"📋 Retrieved ticket: {ticket_id}")
        
        return TicketResponse(
            ticket_id=ticket_id,
            status=ticket['status'],
            subject=ticket['subject'],
            created_at=ticket['created_at'],
            messages=formatted_messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve ticket information"
        )

@router.get("/form-config", response_model=FormConfig)
async def get_form_config() -> FormConfig:
    """
    Get form configuration for the React form
    
    Returns:
        FormConfig: Form configuration data
    """
    try:
        config = FormConfig(
            categories=["general", "technical", "billing", "feedback", "bug_report"],
            priorities=["low", "medium", "high"],
            max_message_length=1000,
            estimated_response_times={
                "low": "~2 hours",
                "medium": "~30 minutes",
                "high": "~5 minutes"
            }
        )
        
        logger.info("📋 Form configuration retrieved")
        return config
        
    except Exception as e:
        logger.error(f"❌ Error getting form config: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve form configuration"
        )

@router.get("/tickets")
async def get_customer_tickets(
    email: EmailStr = Query(..., description="Customer email address"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of tickets to return")
) -> List[Dict[str, Any]]:
    """
    Get customer's recent tickets
    
    Args:
        email: Customer email address
        limit: Maximum number of tickets to return
        
    Returns:
        List[Dict]: List of ticket information
    """
    try:
        # Get customer by email
        customer = await queries.get_customer_by_identifier('email', email)
        
        if not customer:
            raise HTTPException(
                status_code=404,
                detail="Customer not found"
            )
        
        # Get customer's conversation history
        history = await queries.get_customer_all_channels_history(
            customer_id=customer['id'],
            limit=limit
        )
        
        # Group messages by conversation/ticket
        tickets = {}
        for msg in history:
            conv_id = msg['conversation_id']
            if conv_id not in tickets:
                tickets[conv_id] = {
                    'conversation_id': conv_id,
                    'channel': msg['conversation_channel'],
                    'last_message': msg['content'][:100] + '...' if len(msg['content']) > 100 else msg['content'],
                    'last_message_at': msg['created_at'],
                    'message_count': 0
                }
            
            tickets[conv_id]['message_count'] += 1
        
        # Convert to list and sort by last message time
        ticket_list = list(tickets.values())
        ticket_list.sort(key=lambda x: x['last_message_at'], reverse=True)
        
        logger.info(f"📋 Retrieved {len(ticket_list)} tickets for {email}")
        
        return ticket_list[:limit]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting tickets for {email}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve customer tickets"
        )

@router.post("/ticket/{ticket_id}/close")
async def close_ticket(ticket_id: str) -> Dict[str, str]:
    """
    Close a ticket
    
    Args:
        ticket_id: Ticket ID to close
        
    Returns:
        Dict: Closure confirmation
    """
    try:
        # Update ticket status
        await queries.update_ticket_status(
            ticket_id=ticket_id,
            status='closed',
            notes='Closed by customer request'
        )
        
        logger.info(f"🔒 Ticket closed: {ticket_id}")
        
        return {
            'message': 'Ticket closed successfully',
            'ticket_id': ticket_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error closing ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to close ticket"
        )

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint
    
    Returns:
        Dict: Health status
    """
    try:
        # Test database connection
        from ..database.connection import db_manager
        db_health = await db_manager.health_check()
        
        # Test Kafka connection
        from ..kafka_client import get_producer
        producer = await get_producer()
        kafka_health = await producer.health_check()
        
        return {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': db_health,
            'kafka': kafka_health
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e)
        }

# Utility functions
async def validate_form_submission(submission: SupportFormSubmission) -> bool:
    """
    Validate form submission
    
    Args:
        submission: Form submission to validate
        
    Returns:
        bool: True if valid
    """
    # Check message length
    if len(submission.message) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Message too long. Maximum 1000 characters allowed."
        )
    
    # Check name length
    if len(submission.name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Name must be at least 2 characters long."
        )
    
    # Check subject length
    if len(submission.subject) < 5:
        raise HTTPException(
            status_code=400,
            detail="Subject must be at least 5 characters long."
        )
    
    return True

async def log_form_metrics(submission: SupportFormSubmission, ticket_id: str) -> None:
    """
    Log form submission metrics
    
    Args:
        submission: Form submission data
        ticket_id: Generated ticket ID
    """
    try:
        await queries.store_agent_metric(
            metric_name="web_form_submissions",
            metric_value=1.0,
            channel='web_form',
            dimensions={
                'category': submission.category,
                'priority': submission.priority,
                'message_length': len(submission.message)
            }
        )
    except Exception as e:
        logger.error(f"❌ Failed to log form metrics: {e}")

# Export router
__all__ = ['router']
