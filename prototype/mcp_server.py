#!/usr/bin/env python3
"""
TechCorp FTE MCP Server - Phase 1
MCP server exposing tools for customer support automation
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any
from mcp import Server, types
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

class TechCorpMCPServer:
    def __init__(self):
        """Initialize the MCP server with in-memory storage"""
        self.server = Server("techcorp-fte")
        
        # In-memory storage
        self._tickets: Dict[str, Dict] = {}
        self._conversations: Dict[str, List[Dict]] = {}
        self._escalations: Dict[str, Dict] = {}
        
        # Load product docs for search
        try:
            with open('context/product-docs.md', 'r', encoding='utf-8') as f:
                self.product_docs = f.read()
        except FileNotFoundError:
            self.product_docs = ""
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """Return list of available tools"""
            return [
                types.Tool(
                    name="search_knowledge_base",
                    description="Search TechCorp product documentation for relevant information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to find in documentation"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 3
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="create_ticket",
                    description="Create a new support ticket",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "customer_id": {
                                "type": "string",
                                "description": "Customer identifier (email or phone)"
                            },
                            "issue": {
                                "type": "string",
                                "description": "Description of the customer's issue"
                            },
                            "priority": {
                                "type": "string",
                                "description": "Ticket priority (low, medium, high)",
                                "enum": ["low", "medium", "high"]
                            },
                            "channel": {
                                "type": "string",
                                "description": "Support channel (email, whatsapp, web_form)",
                                "enum": ["email", "whatsapp", "web_form"]
                            }
                        },
                        "required": ["customer_id", "issue", "priority", "channel"]
                    }
                ),
                types.Tool(
                    name="get_customer_history",
                    description="Get conversation history for a customer",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "customer_id": {
                                "type": "string",
                                "description": "Customer identifier (email or phone)"
                            }
                        },
                        "required": ["customer_id"]
                    }
                ),
                types.Tool(
                    name="escalate_to_human",
                    description="Escalate a ticket to human agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "string",
                                "description": "Ticket ID to escalate"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for escalation"
                            },
                            "urgency": {
                                "type": "string",
                                "description": "Escalation urgency (low, normal, high, critical)",
                                "enum": ["low", "normal", "high", "critical"],
                                "default": "normal"
                            }
                        },
                        "required": ["ticket_id", "reason"]
                    }
                ),
                types.Tool(
                    name="send_response",
                    description="Send response to customer via specified channel",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "string",
                                "description": "Ticket ID for the response"
                            },
                            "message": {
                                "type": "string",
                                "description": "Response message to send"
                            },
                            "channel": {
                                "type": "string",
                                "description": "Channel to send response through",
                                "enum": ["email", "whatsapp", "web_form"]
                            }
                        },
                        "required": ["ticket_id", "message", "channel"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls"""
            
            if name == "search_knowledge_base":
                return await self._search_knowledge_base(arguments)
            elif name == "create_ticket":
                return await self._create_ticket(arguments)
            elif name == "get_customer_history":
                return await self._get_customer_history(arguments)
            elif name == "escalate_to_human":
                return await self._escalate_to_human(arguments)
            elif name == "send_response":
                return await self._send_response(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def _search_knowledge_base(self, args: Dict[str, Any]) -> List[types.TextContent]:
        """Search product documentation"""
        query = args.get("query", "")
        max_results = args.get("max_results", 3)
        
        if not self.product_docs:
            return [types.TextContent(type="text", text="Product documentation not available")]
        
        # Simple keyword search
        query_lower = query.lower()
        sections = self.product_docs.split('\n## ')
        relevant_sections = []
        
        for section in sections:
            section_lower = section.lower()
            words = query_lower.split()
            matches = sum(1 for word in words if word in section_lower)
            if matches > 0:
                relevant_sections.append((matches, section))
        
        # Sort by relevance and return top results
        relevant_sections.sort(key=lambda x: x[0], reverse=True)
        top_sections = [section for _, section in relevant_sections[:max_results]]
        
        if not top_sections:
            return [types.TextContent(type="text", text=f"No results found for query: {query}")]
        
        result_text = f"Found {len(top_sections)} relevant sections:\n\n"
        for i, section in enumerate(top_sections, 1):
            result_text += f"## Result {i}\n{section}\n\n"
        
        return [types.TextContent(type="text", text=result_text)]
    
    async def _create_ticket(self, args: Dict[str, Any]) -> List[types.TextContent]:
        """Create a new support ticket"""
        customer_id = args.get("customer_id", "")
        issue = args.get("issue", "")
        priority = args.get("priority", "medium")
        channel = args.get("channel", "email")
        
        # Generate ticket ID
        ticket_id = f"TICKET-{str(uuid.uuid4())[:8].upper()}"
        
        # Store ticket
        self._tickets[ticket_id] = {
            "customer_id": customer_id,
            "issue": issue,
            "priority": priority,
            "channel": channel,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        return [types.TextContent(type="text", text=f"Ticket created: {ticket_id}")]
    
    async def _get_customer_history(self, args: Dict[str, Any]) -> List[types.TextContent]:
        """Get customer conversation history"""
        customer_id = args.get("customer_id", "")
        
        if customer_id not in self._conversations:
            return [types.TextContent(type="text", text="No previous interactions. New customer.")]
        
        history = self._conversations[customer_id]
        last_10 = history[-10:] if len(history) > 10 else history
        
        if not last_10:
            return [types.TextContent(type="text", text="No previous interactions. New customer.")]
        
        history_text = f"Conversation history for {customer_id} (last {len(last_10)} messages):\n\n"
        
        for i, exchange in enumerate(last_10, 1):
            timestamp = exchange.get('timestamp', 'Unknown time')
            customer_msg = exchange.get('customer_message', '')
            agent_response = exchange.get('agent_response', '')
            
            history_text += f"{i}. [{timestamp}] Customer: {customer_msg[:100]}{'...' if len(customer_msg) > 100 else ''}\n"
            history_text += f"   Agent: {agent_response[:100]}{'...' if len(agent_response) > 100 else ''}\n\n"
        
        return [types.TextContent(type="text", text=history_text)]
    
    async def _escalate_to_human(self, args: Dict[str, Any]) -> List[types.TextContent]:
        """Escalate ticket to human agent"""
        ticket_id = args.get("ticket_id", "")
        reason = args.get("reason", "")
        urgency = args.get("urgency", "normal")
        
        if ticket_id not in self._tickets:
            return [types.TextContent(type="text", text=f"Ticket {ticket_id} not found")]
        
        # Update ticket status
        self._tickets[ticket_id]["status"] = "escalated"
        self._tickets[ticket_id]["updated_at"] = datetime.now().isoformat()
        
        # Create escalation record
        escalation_id = f"ESC-{str(uuid.uuid4())[:8].upper()}"
        self._escalations[escalation_id] = {
            "ticket_id": ticket_id,
            "reason": reason,
            "urgency": urgency,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # Set response time expectations based on urgency
        response_times = {
            "critical": "immediately",
            "high": "30 minutes",
            "normal": "2 hours",
            "low": "4 hours"
        }
        response_time = response_times.get(urgency, "2 hours")
        
        return [types.TextContent(type="text", text=f"Escalated successfully. Reference: {escalation_id}. Human agent will respond within {response_time}.")]
    
    async def _send_response(self, args: Dict[str, Any]) -> List[types.TextContent]:
        """Send response to customer via specified channel"""
        ticket_id = args.get("ticket_id", "")
        message = args.get("message", "")
        channel = args.get("channel", "email")
        
        # Apply channel-specific formatting
        if channel == "whatsapp" and len(message) > 300:
            message = message[:297] + "..."
        
        # Simulate sending response
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{channel.upper().ljust(8)} SEND] {message}")
        
        # Update ticket if exists
        if ticket_id in self._tickets:
            self._tickets[ticket_id]["updated_at"] = datetime.now().isoformat()
            if "responses" not in self._tickets[ticket_id]:
                self._tickets[ticket_id]["responses"] = []
            self._tickets[ticket_id]["responses"].append({
                "message": message,
                "channel": channel,
                "timestamp": datetime.now().isoformat()
            })
        
        return [types.TextContent(type="text", text=f"Response delivered via {channel}. Status: simulated_sent")]

def create_server() -> Server:
    """Create and return the MCP server instance"""
    mcp_server = TechCorpMCPServer()
    return mcp_server.server

if __name__ == "__main__":
    # Run the server
    server = create_server()
    
    # Print startup message
    print("🚀 TechCorp FTE MCP Server starting...")
    print("📋 Available tools:")
    print("   - search_knowledge_base")
    print("   - create_ticket") 
    print("   - get_customer_history")
    print("   - escalate_to_human")
    print("   - send_response")
    print("\n⏳ Server ready for connections...")
    
    # Run the server with stdio transport
    mcp.server.stdio.run(server)
