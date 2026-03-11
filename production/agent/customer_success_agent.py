"""
TechCorp FTE Customer Success Agent
Main agent implementation using Google ADK
"""

import os
import time
import asyncio
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from google.adk.agents import Agent as LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from .prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT
from .tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response,
    analyze_sentiment
)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create the customer success agent
customer_success_agent = LlmAgent(
    name="TechCorp_Customer_Success_FTE",
    model="gemini-2.0-flash",
    instruction=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
    tools=[
        search_knowledge_base,
        create_ticket,
        get_customer_history,
        escalate_to_human,
        send_response,
        analyze_sentiment
    ]
)

# Create the agent runner
_agent_runner = Runner(
    app="TechCorp_Customer_Success_FTE",
    agent=customer_success_agent,
    session_service=InMemorySessionService()
)

class CustomerSuccessAgentRunner:
    """Runner for the Customer Success Agent with enhanced tracking"""
    
    def __init__(self):
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=customer_success_agent,
            session_service=self.session_service
        )
    
    async def run_agent(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the customer success agent with enriched context
        
        Args:
            message: Customer message
            context: Context including customer_id, channel, etc.
            
        Returns:
            Dict: Agent response with metadata
        """
        start_time = time.time()
        
        try:
            # Build enriched message with context
            enriched_message = self._build_enriched_message(message, context)
            
            # Create or get session
            session_id = context.get('session_id', 'default')
            user_id = context.get('customer_id', 'anonymous')
            
            session = self.session_service.create_session(
                user_id=user_id,
                session_id=session_id
            )
            
            # Run the agent
            result = await self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                message=enriched_message
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract tool calls and escalation status
            tool_calls = self._extract_tool_calls(result)
            escalated = self._detect_escalation(tool_calls)
            
            # Store metrics
            await self._store_agent_metrics(
                context=context,
                latency_ms=latency_ms,
                escalated=escalated,
                tool_calls=tool_calls
            )
            
            return {
                'output': result.output,
                'tool_calls': tool_calls,
                'escalated': escalated,
                'latency_ms': latency_ms,
                'session_id': session_id,
                'success': True
            }
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log error metrics
            await self._store_error_metrics(context, str(e), latency_ms)
            
            return {
                'output': f"I apologize, but I encountered an error: {str(e)}",
                'tool_calls': [],
                'escalated': True,
                'latency_ms': latency_ms,
                'session_id': None,
                'success': False,
                'error': str(e)
            }
    
    def _build_enriched_message(self, message: str, context: Dict[str, Any]) -> str:
        """
        Build enriched message with context information
        
        Args:
            message: Original customer message
            context: Context information
            
        Returns:
            str: Enriched message
        """
        enriched_parts = []
        
        # Add channel information
        channel = context.get('channel', 'unknown')
        enriched_parts.append(f"Channel: {channel}")
        
        # Add customer information
        customer_id = context.get('customer_id', '')
        if customer_id:
            enriched_parts.append(f"Customer ID: {customer_id}")
        
        customer_name = context.get('customer_name', '')
        if customer_name:
            enriched_parts.append(f"Customer Name: {customer_name}")
        
        # Add conversation context
        conversation_id = context.get('conversation_id', '')
        if conversation_id:
            enriched_parts.append(f"Conversation ID: {conversation_id}")
        
        # Add subject if available
        subject = context.get('subject', '')
        if subject:
            enriched_parts.append(f"Subject: {subject}")
        
        # Add priority if available
        priority = context.get('priority', '')
        if priority:
            enriched_parts.append(f"Priority: {priority}")
        
        # Combine context with message
        context_section = "\n".join(enriched_parts)
        enriched_message = f"{context_section}\n\nCustomer Message:\n{message}"
        
        return enriched_message
    
    def _extract_tool_calls(self, result: Any) -> List[Dict[str, Any]]:
        """
        Extract tool calls from agent result
        
        Args:
            result: Agent result
            
        Returns:
            List[Dict]: Tool call information
        """
        tool_calls = []
        
        if hasattr(result, 'tool_calls') and result.tool_calls:
            for tool_call in result.tool_calls:
                tool_calls.append({
                    'tool_name': tool_call.get('name', 'unknown'),
                    'arguments': tool_call.get('arguments', {}),
                    'result': tool_call.get('result', ''),
                    'timestamp': time.time()
                })
        
        return tool_calls
    
    def _detect_escalation(self, tool_calls: List[Dict[str, Any]]) -> bool:
        """
        Detect if escalation was triggered
        
        Args:
            tool_calls: List of tool calls
            
        Returns:
            bool: True if escalation was triggered
        """
        for tool_call in tool_calls:
            if tool_call.get('tool_name') == 'escalate_to_human':
                return True
        return False
    
    async def _store_agent_metrics(
        self,
        context: Dict[str, Any],
        latency_ms: int,
        escalated: bool,
        tool_calls: List[Dict[str, Any]]
    ) -> None:
        """
        Store agent performance metrics
        
        Args:
            context: Interaction context
            latency_ms: Response latency
            escalated: Whether escalation occurred
            tool_calls: Tool calls made
        """
        try:
            from .tools import store_agent_metric
            
            # Store latency metric
            await store_agent_metric(
                metric_name="agent_response_latency_ms",
                metric_value=float(latency_ms),
                channel=context.get('channel'),
                dimensions={
                    'escalated': escalated,
                    'tool_count': len(tool_calls)
                }
            )
            
            # Store escalation rate
            await store_agent_metric(
                metric_name="agent_escalation_rate",
                metric_value=1.0 if escalated else 0.0,
                channel=context.get('channel')
            )
            
            # Store tool usage metrics
            for tool_call in tool_calls:
                await store_agent_metric(
                    metric_name=f"agent_tool_usage_{tool_call['tool_name']}",
                    metric_value=1.0,
                    channel=context.get('channel')
                )
            
        except Exception as e:
            # Don't fail the agent if metrics storage fails
            print(f"Warning: Failed to store metrics: {e}")
    
    async def _store_error_metrics(
        self,
        context: Dict[str, Any],
        error_message: str,
        latency_ms: int
    ) -> None:
        """
        Store error metrics
        
        Args:
            context: Interaction context
            error_message: Error description
            latency_ms: Response latency
        """
        try:
            from .tools import store_agent_metric
            
            # Store error rate
            await store_agent_metric(
                metric_name="agent_error_rate",
                metric_value=1.0,
                channel=context.get('channel'),
                dimensions={
                    'error_type': 'runtime_error',
                    'error_message': error_message[:100]
                }
            )
            
        except Exception as e:
            print(f"Warning: Failed to store error metrics: {e}")

# Global runner instance
_agent_runner = CustomerSuccessAgentRunner()

async def run_agent(message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to run the customer success agent
    
    Args:
        message: Customer message
        context: Context dictionary with:
            - customer_id: Customer UUID
            - channel: Channel type (email, whatsapp, web_form)
            - customer_name: Customer name (optional)
            - subject: Message subject (optional)
            - priority: Message priority (optional)
            - conversation_id: Existing conversation ID (optional)
            - session_id: Session ID for continuity (optional)
    
    Returns:
        Dict: Agent response with metadata:
            - output: Agent response text
            - tool_calls: List of tool calls made
            - escalated: Whether escalation was triggered
            - latency_ms: Response time in milliseconds
            - session_id: Session ID for continuity
            - success: Whether execution was successful
            - error: Error message if failed
    """
    return await _agent_runner.run_agent(message, context)

# Convenience functions for specific use cases

async def handle_email_message(
    customer_email: str,
    message: str,
    subject: str = "",
    customer_name: str = ""
) -> Dict[str, Any]:
    """
    Handle email message with automatic customer lookup
    
    Args:
        customer_email: Customer email address
        message: Email message content
        subject: Email subject
        customer_name: Customer name
        
    Returns:
        Dict: Agent response
    """
    from .tools import get_customer_by_identifier, create_or_get_customer
    
    # Find or create customer
    customer = await get_customer_by_identifier('email', customer_email)
    if customer:
        customer_id = customer['id']
        customer_name = customer_name or customer.get('name', '')
    else:
        customer_id = await create_or_get_customer(
            email=customer_email,
            name=customer_name
        )
    
    context = {
        'customer_id': customer_id,
        'channel': 'email',
        'customer_name': customer_name,
        'subject': subject
    }
    
    return await run_agent(message, context)

async def handle_whatsapp_message(
    phone_number: str,
    message: str,
    customer_name: str = ""
) -> Dict[str, Any]:
    """
    Handle WhatsApp message with automatic customer lookup
    
    Args:
        phone_number: Customer phone number
        message: WhatsApp message
        customer_name: Customer name
        
    Returns:
        Dict: Agent response
    """
    from .tools import get_customer_by_identifier, create_or_get_customer
    
    # Find or create customer
    customer = await get_customer_by_identifier('phone', phone_number)
    if customer:
        customer_id = customer['id']
        customer_name = customer_name or customer.get('name', '')
    else:
        customer_id = await create_or_get_customer(
            phone=phone_number,
            name=customer_name
        )
    
    context = {
        'customer_id': customer_id,
        'channel': 'whatsapp',
        'customer_name': customer_name
    }
    
    return await run_agent(message, context)

async def handle_web_form_message(
    email: str,
    message: str,
    customer_name: str = "",
    subject: str = ""
) -> Dict[str, Any]:
    """
    Handle web form message
    
    Args:
        email: Customer email
        message: Web form message
        customer_name: Customer name
        subject: Message subject
        
    Returns:
        Dict: Agent response
    """
    from .tools import get_customer_by_identifier, create_or_get_customer
    
    # Find or create customer
    customer = await get_customer_by_identifier('email', email)
    if customer:
        customer_id = customer['id']
        customer_name = customer_name or customer.get('name', '')
    else:
        customer_id = await create_or_get_customer(
            email=email,
            name=customer_name
        )
    
    context = {
        'customer_id': customer_id,
        'channel': 'web_form',
        'customer_name': customer_name,
        'subject': subject
    }
    
    return await run_agent(message, context)

# Health check function
async def agent_health_check() -> Dict[str, Any]:
    """
    Check agent health and configuration
    
    Returns:
        Dict: Health status
    """
    try:
        # Test basic functionality
        test_result = await run_agent(
            "Hello, this is a health check.",
            {
                'customer_id': 'health-check',
                'channel': 'web_form',
                'customer_name': 'Health Check'
            }
        )
        
        return {
            'status': 'healthy' if test_result['success'] else 'unhealthy',
            'agent_name': customer_success_agent.name,
            'model': customer_success_agent.model,
            'tool_count': len(customer_success_agent.tools),
            'last_check': test_result
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'agent_name': customer_success_agent.name,
            'model': customer_success_agent.model
        }

# Export main functions
__all__ = [
    'run_agent',
    'handle_email_message',
    'handle_whatsapp_message',
    'handle_web_form_message',
    'agent_health_check',
    'customer_success_agent'
]
