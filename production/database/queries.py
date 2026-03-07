"""
TechCorp FTE Database Queries
All async database operations using AsyncPG
"""

import uuid
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import asyncpg
from .connection import get_connection

async def create_or_get_customer(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    whatsapp_id: Optional[str] = None,
    name: Optional[str] = None
) -> str:
    """
    Create or get customer by identifier. Returns customer UUID.
    Checks email first, then phone, then whatsapp_id.
    
    Args:
        email: Customer email address
        phone: Customer phone number
        whatsapp_id: WhatsApp identifier
        name: Customer name
        
    Returns:
        str: Customer UUID
        
    Raises:
        asyncpg.PostgresError: If database operation fails
    """
    async with get_connection() as conn:
        # Try to find existing customer by email, phone, or whatsapp_id
        customer_id = None
        
        if email:
            customer_id = await conn.fetchval(
                "SELECT id FROM customers WHERE email = $1", email
            )
        
        if not customer_id and phone:
            customer_id = await conn.fetchval(
                "SELECT id FROM customers WHERE phone = $1", phone
            )
        
        if not customer_id and whatsapp_id:
            customer_id = await conn.fetchval(
                "SELECT id FROM customers WHERE whatsapp_id = $1", whatsapp_id
            )
        
        if customer_id:
            # Update existing customer with new information
            update_fields = []
            update_values = []
            param_count = 1
            
            if name:
                update_fields.append(f"name = ${param_count}")
                update_values.append(name)
                param_count += 1
            
            if email and not await conn.fetchval("SELECT email FROM customers WHERE id = $1", customer_id):
                update_fields.append(f"email = ${param_count}")
                update_values.append(email)
                param_count += 1
            
            if phone and not await conn.fetchval("SELECT phone FROM customers WHERE id = $1", customer_id):
                update_fields.append(f"phone = ${param_count}")
                update_values.append(phone)
                param_count += 1
            
            if whatsapp_id and not await conn.fetchval("SELECT whatsapp_id FROM customers WHERE id = $1", customer_id):
                update_fields.append(f"whatsapp_id = ${param_count}")
                update_values.append(whatsapp_id)
                param_count += 1
            
            if update_fields:
                update_fields.append("updated_at = NOW()")
                update_values.append(customer_id)
                
                await conn.execute(
                    f"UPDATE customers SET {', '.join(update_fields)} WHERE id = ${param_count}",
                    *update_values
                )
            
            return str(customer_id)
        
        else:
            # Create new customer
            customer_id = await conn.fetchval(
                """
                INSERT INTO customers (email, phone, whatsapp_id, name)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                email, phone, whatsapp_id, name
            )
            
            # Create customer identifiers
            if email:
                await conn.execute(
                    "INSERT INTO customer_identifiers (customer_id, identifier_type, identifier_value) VALUES ($1, $2, $3)",
                    customer_id, 'email', email
                )
            
            if phone:
                await conn.execute(
                    "INSERT INTO customer_identifiers (customer_id, identifier_type, identifier_value) VALUES ($1, $2, $3)",
                    customer_id, 'phone', phone
                )
            
            if whatsapp_id:
                await conn.execute(
                    "INSERT INTO customer_identifiers (customer_id, identifier_type, identifier_value) VALUES ($1, $2, $3)",
                    customer_id, 'whatsapp', whatsapp_id
                )
            
            return str(customer_id)

async def create_conversation(customer_id: str, channel: str) -> str:
    """
    Insert new conversation and return conversation UUID.
    
    Args:
        customer_id: Customer UUID
        channel: Channel type (email, whatsapp, web_form)
        
    Returns:
        str: Conversation UUID
    """
    async with get_connection() as conn:
        conversation_id = await conn.fetchval(
            """
            INSERT INTO conversations (customer_id, initial_channel)
            VALUES ($1, $2)
            RETURNING id
            """,
            customer_id, channel
        )
        return str(conversation_id)

async def create_ticket(
    conversation_id: str,
    customer_id: str,
    channel: str,
    category: Optional[str] = None,
    priority: str = "medium",
    subject: Optional[str] = None
) -> str:
    """
    Insert ticket and return ticket UUID.
    
    Args:
        conversation_id: Conversation UUID
        customer_id: Customer UUID
        channel: Source channel
        category: Ticket category
        priority: Ticket priority (low, medium, high, critical)
        subject: Ticket subject
        
    Returns:
        str: Ticket UUID
    """
    async with get_connection() as conn:
        ticket_id = await conn.fetchval(
            """
            INSERT INTO tickets (conversation_id, customer_id, source_channel, category, priority, subject)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            conversation_id, customer_id, channel, category, priority, subject
        )
        return str(ticket_id)

async def store_message(
    conversation_id: str,
    channel: str,
    direction: str,
    role: str,
    content: str,
    tokens_used: Optional[int] = None,
    latency_ms: Optional[int] = None,
    tool_calls: Optional[List[Dict]] = None,
    channel_message_id: Optional[str] = None
) -> str:
    """
    Insert message and return message UUID.
    
    Args:
        conversation_id: Conversation UUID
        channel: Channel type
        direction: Message direction (inbound/outbound)
        role: Message role (customer/agent/system)
        content: Message content
        tokens_used: Number of tokens used
        latency_ms: Processing latency in milliseconds
        tool_calls: List of tool calls made
        channel_message_id: Original channel message ID
        
    Returns:
        str: Message UUID
    """
    async with get_connection() as conn:
        message_id = await conn.fetchval(
            """
            INSERT INTO messages (
                conversation_id, channel, direction, role, content,
                tokens_used, latency_ms, tool_calls, channel_message_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """,
            conversation_id, channel, direction, role, content,
            tokens_used, latency_ms, json.dumps(tool_calls) if tool_calls else None,
            channel_message_id
        )
        return str(message_id)

async def get_conversation_messages(conversation_id: str) -> List[Dict]:
    """
    Get all messages for a conversation ordered by created_at ASC.
    
    Args:
        conversation_id: Conversation UUID
        
    Returns:
        List[Dict]: List of message dictionaries
    """
    async with get_connection() as conn:
        messages = await conn.fetch(
            """
            SELECT id, channel, direction, role, content, created_at,
                   tokens_used, latency_ms, tool_calls, channel_message_id,
                   delivery_status
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
            """,
            conversation_id
        )
        
        return [dict(msg) for msg in messages]

async def get_customer_all_channels_history(
    customer_id: str,
    limit: int = 20
) -> List[Dict]:
    """
    Get last N messages across ALL conversations for this customer.
    
    Args:
        customer_id: Customer UUID
        limit: Maximum number of messages to return
        
    Returns:
        List[Dict]: List of message dictionaries
    """
    async with get_connection() as conn:
        messages = await conn.fetch(
            """
            SELECT m.id, m.conversation_id, m.channel, m.direction, m.role,
                   m.content, m.created_at, m.tokens_used, m.latency_ms,
                   m.tool_calls, m.channel_message_id, m.delivery_status,
                   c.initial_channel as conversation_channel
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.customer_id = $1
            ORDER BY m.created_at DESC
            LIMIT $2
            """,
            customer_id, limit
        )
        
        return [dict(msg) for msg in messages]

async def update_ticket_status(
    ticket_id: str,
    status: str,
    notes: Optional[str] = None
) -> None:
    """
    Update ticket status and optionally set resolution notes and resolved_at.
    
    Args:
        ticket_id: Ticket UUID
        status: New status
        notes: Resolution notes (optional)
    """
    async with get_connection() as conn:
        if status == 'resolved' and notes:
            await conn.execute(
                """
                UPDATE tickets 
                SET status = $1, updated_at = NOW(), resolved_at = NOW(), resolution_notes = $2
                WHERE id = $3
                """,
                status, notes, ticket_id
            )
        else:
            await conn.execute(
                """
                UPDATE tickets 
                SET status = $1, updated_at = NOW(), resolution_notes = $2
                WHERE id = $3
                """,
                status, notes, ticket_id
            )

async def log_escalation(
    ticket_id: str,
    reason: str,
    urgency: str = "normal"
) -> str:
    """
    Insert into escalation_log and return escalation UUID.
    
    Args:
        ticket_id: Ticket UUID
        reason: Escalation reason
        urgency: Escalation urgency (critical, high, normal, low)
        
    Returns:
        str: Escalation UUID
    """
    async with get_connection() as conn:
        escalation_id = await conn.fetchval(
            """
            INSERT INTO escalation_log (ticket_id, reason, urgency)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            ticket_id, reason, urgency
        )
        return str(escalation_id)

async def search_knowledge_by_vector(
    embedding: List[float],
    max_results: int = 5,
    category: Optional[str] = None
) -> List[Dict]:
    """
    Use pgvector cosine similarity to search knowledge base.
    
    Args:
        embedding: Query embedding vector
        max_results: Maximum number of results to return
        category: Optional category filter
        
    Returns:
        List[Dict]: List of knowledge entries with similarity scores
    """
    async with get_connection() as conn:
        if category:
            results = await conn.fetch(
                """
                SELECT id, title, content, category,
                       1 - (embedding <=> $1::vector) as similarity
                FROM knowledge_base
                WHERE category = $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                embedding, category, max_results
            )
        else:
            results = await conn.fetch(
                """
                SELECT id, title, content, category,
                       1 - (embedding <=> $1::vector) as similarity
                FROM knowledge_base
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                embedding, max_results
            )
        
        return [dict(result) for result in results]

async def get_channel_metrics(hours: int = 24) -> Dict:
    """
    Get metrics grouped by channel.
    
    Args:
        hours: Number of hours to look back
        
    Returns:
        Dict: Channel metrics
    """
    async with get_connection() as conn:
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = await conn.fetch(
            """
            SELECT 
                t.source_channel as channel,
                COUNT(*) as total,
                COUNT(CASE WHEN t.status = 'resolved' THEN 1 END) as resolved,
                COUNT(CASE WHEN t.status = 'escalated' THEN 1 END) as escalated,
                AVG(c.sentiment_score) as avg_sentiment,
                AVG(m.latency_ms) as avg_response_time
            FROM tickets t
            JOIN conversations c ON t.conversation_id = c.id
            LEFT JOIN messages m ON c.id = m.conversation_id AND m.role = 'agent'
            WHERE t.created_at >= $1
            GROUP BY t.source_channel
            """,
            since_time
        )
        
        return {metric['channel']: dict(metric) for metric in metrics}

async def get_ticket_by_id(ticket_id: str) -> Optional[Dict]:
    """
    Get full ticket with customer email/phone/whatsapp_id joined from customers table.
    
    Args:
        ticket_id: Ticket UUID
        
    Returns:
        Optional[Dict]: Ticket data or None if not found
    """
    async with get_connection() as conn:
        ticket = await conn.fetchrow(
            """
            SELECT 
                t.id, t.conversation_id, t.customer_id, t.source_channel,
                t.category, t.priority, t.status, t.subject,
                t.created_at, t.updated_at, t.resolved_at, t.resolution_notes,
                c.email, c.phone, c.whatsapp_id, c.name,
                conv.initial_channel, conv.started_at, conv.status as conversation_status
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            JOIN conversations conv ON t.conversation_id = conv.id
            WHERE t.id = $1
            """,
            ticket_id
        )
        
        return dict(ticket) if ticket else None

async def get_active_conversation(
    customer_id: str,
    hours: int = 24
) -> Optional[str]:
    """
    Get active conversation ID if exists within last N hours, else None.
    
    Args:
        customer_id: Customer UUID
        hours: Number of hours to look back
        
    Returns:
        Optional[str]: Conversation UUID or None
    """
    async with get_connection() as conn:
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        conversation_id = await conn.fetchval(
            """
            SELECT id
            FROM conversations
            WHERE customer_id = $1 AND status = 'active' AND started_at >= $2
            ORDER BY started_at DESC
            LIMIT 1
            """,
            customer_id, since_time
        )
        
        return str(conversation_id) if conversation_id else None

async def insert_knowledge_entry(
    title: str,
    content: str,
    category: str,
    embedding: List[float]
) -> str:
    """
    Insert into knowledge_base and return UUID.
    
    Args:
        title: Knowledge entry title
        content: Knowledge entry content
        category: Knowledge entry category
        embedding: Vector embedding
        
    Returns:
        str: Knowledge entry UUID
    """
    async with get_connection() as conn:
        entry_id = await conn.fetchval(
            """
            INSERT INTO knowledge_base (title, content, category, embedding)
            VALUES ($1, $2, $3, $4::vector)
            RETURNING id
            """,
            title, content, category, embedding
        )
        return str(entry_id)

async def get_daily_metrics(date: Optional[datetime] = None) -> Dict:
    """
    Get daily metrics for a specific date.
    
    Args:
        date: Date to get metrics for (defaults to today)
        
    Returns:
        Dict: Daily metrics
    """
    if date is None:
        date = datetime.utcnow().date()
    
    async with get_connection() as conn:
        metrics = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) as total_tickets,
                COUNT(CASE WHEN t.status = 'resolved' THEN 1 END) as resolved_tickets,
                COUNT(CASE WHEN t.status = 'escalated' THEN 1 END) as escalated_tickets,
                AVG(c.sentiment_score) as avg_sentiment,
                AVG(m.latency_ms) as avg_response_time_ms
            FROM tickets t
            JOIN conversations c ON t.conversation_id = c.id
            LEFT JOIN messages m ON c.id = m.conversation_id AND m.role = 'agent'
            WHERE DATE(t.created_at) = $1
            """,
            date
        )
        
        # Channel breakdown
        channel_breakdown = await conn.fetch(
            """
            SELECT source_channel, COUNT(*) as count
            FROM tickets
            WHERE DATE(created_at) = $1
            GROUP BY source_channel
            """,
            date
        )
        
        # Top categories
        top_categories = await conn.fetch(
            """
            SELECT category, COUNT(*) as count
            FROM tickets
            WHERE DATE(created_at) = $1 AND category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
            LIMIT 10
            """,
            date
        )
        
        return {
            'date': date.isoformat(),
            'total_tickets': metrics['total_tickets'] or 0,
            'resolved_tickets': metrics['resolved_tickets'] or 0,
            'escalated_tickets': metrics['escalated_tickets'] or 0,
            'avg_sentiment': float(metrics['avg_sentiment'] or 0),
            'avg_response_time_ms': int(metrics['avg_response_time_ms'] or 0),
            'channel_breakdown': {row['source_channel']: row['count'] for row in channel_breakdown},
            'top_categories': {row['category']: row['count'] for row in top_categories}
        }

async def update_conversation_status(
    conversation_id: str,
    status: str,
    sentiment_score: Optional[float] = None,
    resolution_type: Optional[str] = None
) -> None:
    """
    Update conversation status and optionally sentiment score and resolution type.
    
    Args:
        conversation_id: Conversation UUID
        status: New status
        sentiment_score: Optional sentiment score
        resolution_type: Optional resolution type
    """
    async with get_connection() as conn:
        update_fields = ["status = $1", "updated_at = NOW()"]
        params = [status, conversation_id]
        param_idx = 2
        
        if sentiment_score is not None:
            update_fields.append(f"sentiment_score = ${param_idx}")
            params.insert(param_idx, sentiment_score)
            param_idx += 1
        
        if resolution_type is not None:
            update_fields.append(f"resolution_type = ${param_idx}")
            params.insert(param_idx, resolution_type)
            param_idx += 1
        
        if status in ['resolved', 'closed']:
            update_fields.append("ended_at = NOW()")
        
        await conn.execute(
            f"UPDATE conversations SET {', '.join(update_fields)} WHERE id = ${param_idx}",
            *params
        )

async def get_customer_by_identifier(
    identifier_type: str,
    identifier_value: str
) -> Optional[Dict]:
    """
    Get customer by identifier type and value.
    
    Args:
        identifier_type: Type of identifier (email, phone, whatsapp)
        identifier_value: Identifier value
        
    Returns:
        Optional[Dict]: Customer data or None
    """
    async with get_connection() as conn:
        customer = await conn.fetchrow(
            """
            SELECT c.*
            FROM customers c
            JOIN customer_identifiers ci ON c.id = ci.customer_id
            WHERE ci.identifier_type = $1 AND ci.identifier_value = $2
            """,
            identifier_type, identifier_value
        )
        
        return dict(customer) if customer else None

async def store_agent_metric(
    metric_name: str,
    metric_value: float,
    channel: Optional[str] = None,
    dimensions: Optional[Dict] = None
) -> str:
    """
    Store agent performance metric.
    
    Args:
        metric_name: Name of the metric
        metric_value: Metric value
        channel: Optional channel
        dimensions: Optional additional dimensions
        
    Returns:
        str: Metric record UUID
    """
    async with get_connection() as conn:
        metric_id = await conn.fetchval(
            """
            INSERT INTO agent_metrics (metric_name, metric_value, channel, dimensions)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            metric_name, metric_value, channel, json.dumps(dimensions) if dimensions else None
        )
        return str(metric_id)
