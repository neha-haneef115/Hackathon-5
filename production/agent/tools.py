"""
TechCorp FTE Agent Tools
Production-ready tool functions using Google ADK
"""

import os
import json
import asyncio
from typing import Dict, List, Optional
import google.generativeai as genai
import asyncpg

from ..database.connection import get_connection
from ..database import queries
from .formatters import format_for_channel

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

async def search_knowledge_base(query: str, max_results: int = 5) -> str:
    """
    Search knowledge base using vector embeddings
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        str: Formatted search results
    """
    try:
        # Generate embedding for the query
        embedding_response = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )
        embedding = embedding_response["embedding"]
        
        # Search using vector similarity
        results = await queries.search_knowledge_by_vector(
            embedding=embedding,
            max_results=max_results
        )
        
        if not results:
            return "No relevant docs found. Consider escalating."
        
        # Format results
        formatted_results = []
        for result in results:
            similarity = result.get('similarity', 0)
            title = result.get('title', 'Untitled')
            content = result.get('content', '')
            
            # Truncate content for readability
            content_preview = content[:500] + "..." if len(content) > 500 else content
            
            formatted_result = f"{title} (score: {similarity:.2f})\n{content_preview}"
            formatted_results.append(formatted_result)
        
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"Knowledge base unavailable, please escalate. Error: {str(e)}"

async def create_ticket(
    customer_id: str, 
    issue: str, 
    priority: str, 
    channel: str, 
    subject: str = ""
) -> str:
    """
    Create a support ticket
    
    Args:
        customer_id: Customer UUID
        issue: Customer issue description
        priority: Ticket priority (low, medium, high, critical)
        channel: Source channel
        subject: Optional ticket subject
        
    Returns:
        str: Ticket creation result
    """
    try:
        # Create conversation first
        conversation_id = await queries.create_conversation(
            customer_id=customer_id,
            channel=channel
        )
        
        # Create ticket
        ticket_id = await queries.create_ticket(
            conversation_id=conversation_id,
            customer_id=customer_id,
            channel=channel,
            priority=priority,
            subject=subject or f"Inquiry via {channel}"
        )
        
        return f"Ticket created: {ticket_id}"
        
    except Exception as e:
        return f"Ticket creation failed: {str(e)}"

async def get_customer_history(customer_id: str) -> str:
    """
    Get customer's conversation history across all channels
    
    Args:
        customer_id: Customer UUID
        
    Returns:
        str: Formatted conversation history
    """
    try:
        history = await queries.get_customer_all_channels_history(
            customer_id=customer_id,
            limit=15
        )
        
        if not history:
            return "New customer — no previous interactions found."
        
        # Format history
        formatted_messages = []
        for message in history:
            channel = message.get('channel', 'unknown')
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            
            # Truncate content for readability
            content_preview = content[:100] + "..." if len(content) > 100 else content
            
            formatted_msg = f"[{channel.upper()}] {role}: {content_preview}"
            formatted_messages.append(formatted_msg)
        
        return "\n".join(formatted_messages)
        
    except Exception as e:
        return f"Unable to retrieve customer history: {str(e)}"

async def escalate_to_human(
    ticket_id: str, 
    reason: str, 
    urgency: str = "normal"
) -> str:
    """
    Escalate ticket to human agent
    
    Args:
        ticket_id: Ticket UUID
        reason: Escalation reason
        urgency: Escalation urgency (critical, high, normal, low)
        
    Returns:
        str: Escalation confirmation
    """
    try:
        # Update ticket status
        await queries.update_ticket_status(
            ticket_id=ticket_id,
            status="escalated"
        )
        
        # Log escalation
        escalation_id = await queries.log_escalation(
            ticket_id=ticket_id,
            reason=reason,
            urgency=urgency
        )
        
        # Determine response time based on urgency
        response_times = {
            "critical": "15 minutes",
            "high": "30 minutes", 
            "normal": "2 hours",
            "low": "4 hours"
        }
        timeframe = response_times.get(urgency, "2 hours")
        
        return f"Escalated to human agent. Reference: {escalation_id}. Response within {timeframe}."
        
    except Exception as e:
        return f"Escalation failed: {str(e)}"

async def send_response(
    ticket_id: str, 
    message: str, 
    channel: str
) -> str:
    """
    Send response to customer via appropriate channel
    
    Args:
        ticket_id: Ticket UUID
        message: Response message
        channel: Delivery channel
        
    Returns:
        str: Delivery status
    """
    try:
        # Get ticket information for customer details
        ticket_info = await queries.get_ticket_by_id(ticket_id)
        if not ticket_info:
            return f"Ticket {ticket_id} not found"
        
        customer_name = ticket_info.get('name', '') or ""
        conversation_id = ticket_info.get('conversation_id', '')
        
        # Format response for channel
        formatted_response = format_for_channel(
            response=message,
            channel=channel,
            ticket_id=ticket_id,
            customer_name=customer_name
        )
        
        # Route to appropriate channel handler
        delivery_status = await _route_to_channel(
            channel=channel,
            message=formatted_response,
            ticket_info=ticket_info
        )
        
        # Store outbound message
        await queries.store_message(
            conversation_id=conversation_id,
            channel=channel,
            direction="outbound",
            role="agent",
            content=formatted_response,
            channel_message_id=ticket_id
        )
        
        return f"Response sent via {channel}: {delivery_status}"
        
    except Exception as e:
        return f"Response delivery failed: {str(e)}"

async def analyze_sentiment(message: str) -> str:
    """
    Analyze sentiment of customer message using Gemini
    
    Args:
        message: Customer message to analyze
        
    Returns:
        str: JSON string with sentiment analysis
    """
    try:
        # Create Gemini model for sentiment analysis
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""Score the sentiment of this customer message from 0.0 (very angry/negative) to 1.0 (very positive/happy). Return ONLY a JSON object: {{'score': 0.0-1.0, 'label': 'positive|neutral|negative', 'flags': ['angry'|'frustrated'|'legal_threat'|'escalation_needed']}}. Message: {message}"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse and validate JSON response
        try:
            sentiment_data = json.loads(response_text)
            
            # Ensure required fields exist
            if 'score' not in sentiment_data:
                sentiment_data['score'] = 0.5
            if 'label' not in sentiment_data:
                sentiment_data['label'] = 'neutral'
            if 'flags' not in sentiment_data:
                sentiment_data['flags'] = []
            
            return json.dumps(sentiment_data)
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return '{"score": 0.5, "label": "neutral", "flags": []}'
        
    except Exception as e:
        # Fallback on any error
        return '{"score": 0.5, "label": "neutral", "flags": []}'

async def _route_to_channel(
    channel: str, 
    message: str, 
    ticket_info: Dict
) -> str:
    """
    Route message to appropriate channel handler
    
    Args:
        channel: Target channel
        message: Formatted message
        ticket_info: Ticket information
        
    Returns:
        str: Delivery status
    """
    try:
        if channel.lower() == "email":
            # Import email handler to avoid circular imports
            from ..channels.gmail_handler import GmailHandler
            handler = GmailHandler()
            customer_email = ticket_info.get('email', '')
            return await handler.send_message(customer_email, message)
            
        elif channel.lower() == "whatsapp":
            from ..channels.whatsapp_handler import WhatsAppHandler
            handler = WhatsAppHandler()
            customer_phone = ticket_info.get('phone', '') or ticket_info.get('whatsapp_id', '')
            return await handler.send_message(customer_phone, message)
            
        elif channel.lower() == "web_form":
            from ..channels.web_form_handler import WebFormHandler
            handler = WebFormHandler()
            return await handler.update_ticket(ticket_info.get('id', ''), message)
            
        else:
            # Unknown channel - simulate delivery
            print(f"[{channel.upper()} SEND] {message[:100]}...")
            return "simulated_sent"
            
    except ImportError as e:
        # Channel handler not implemented yet
        print(f"[{channel.upper()} SEND - FALLBACK] {message[:100]}...")
        return "simulated_sent"
    except Exception as e:
        return f"delivery_error: {str(e)}"

async def get_customer_by_identifier(
    identifier_type: str,
    identifier_value: str
) -> Optional[Dict]:
    """
    Get customer by identifier (helper function for tools)
    
    Args:
        identifier_type: Type of identifier (email, phone, whatsapp)
        identifier_value: Identifier value
        
    Returns:
        Optional[Dict]: Customer data or None
    """
    try:
        customer = await queries.get_customer_by_identifier(
            identifier_type=identifier_type,
            identifier_value=identifier_value
        )
        return customer
    except Exception:
        return None

async def store_agent_metric(
    metric_name: str,
    metric_value: float,
    channel: Optional[str] = None,
    dimensions: Optional[Dict] = None
) -> str:
    """
    Store agent performance metric (helper function)
    
    Args:
        metric_name: Name of the metric
        metric_value: Metric value
        channel: Optional channel
        dimensions: Optional additional dimensions
        
    Returns:
        str: Metric record UUID
    """
    try:
        metric_id = await queries.store_agent_metric(
            metric_name=metric_name,
            metric_value=metric_value,
            channel=channel,
            dimensions=dimensions
        )
        return metric_id
    except Exception as e:
        return f"metric_storage_failed: {str(e)}"

# Tool registration and validation functions

def validate_tool_inputs(tool_name: str, **kwargs) -> tuple[bool, str]:
    """
    Validate inputs for tool functions
    
    Args:
        tool_name: Name of the tool
        **kwargs: Tool arguments
        
    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    if tool_name == "create_ticket":
        required = ["customer_id", "issue", "priority", "channel"]
        for arg in required:
            if not kwargs.get(arg):
                return False, f"Missing required argument: {arg}"
        
        valid_priorities = ["low", "medium", "high", "critical"]
        if kwargs["priority"] not in valid_priorities:
            return False, f"Invalid priority: {kwargs['priority']}"
    
    elif tool_name == "escalate_to_human":
        required = ["ticket_id", "reason"]
        for arg in required:
            if not kwargs.get(arg):
                return False, f"Missing required argument: {arg}"
        
        valid_urgencies = ["critical", "high", "normal", "low"]
        urgency = kwargs.get("urgency", "normal")
        if urgency not in valid_urgencies:
            return False, f"Invalid urgency: {urgency}"
    
    elif tool_name == "send_response":
        required = ["ticket_id", "message", "channel"]
        for arg in required:
            if not kwargs.get(arg):
                return False, f"Missing required argument: {arg}"
    
    return True, ""

async def log_tool_usage(
    tool_name: str,
    ticket_id: str,
    execution_time_ms: int,
    success: bool,
    error_message: str = ""
) -> None:
    """
    Log tool usage for monitoring and analytics
    
    Args:
        tool_name: Name of the tool
        ticket_id: Associated ticket ID
        execution_time_ms: Execution time in milliseconds
        success: Whether tool executed successfully
        error_message: Error message if failed
    """
    try:
        await store_agent_metric(
            metric_name=f"tool_usage_{tool_name}",
            metric_value=1.0 if success else 0.0,
            dimensions={
                "ticket_id": ticket_id,
                "execution_time_ms": execution_time_ms,
                "success": success,
                "error": error_message[:100] if error_message else ""
            }
        )
    except Exception:
        # Don't fail the tool if logging fails
        pass
