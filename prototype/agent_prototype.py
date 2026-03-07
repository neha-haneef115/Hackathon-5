#!/usr/bin/env python3
"""
TechCorp FTE Agent Prototype - Phase 1
Exploratory code using Gemini 2.0 Flash API
"""

import os
import json
import re
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

class TechCorpAgent:
    def __init__(self):
        """Initialize the agent with context files and Gemini API"""
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Load context files
        self.product_docs = self._load_file('context/product-docs.md')
        self.escalation_rules = self._load_file('context/escalation-rules.md')
        self.brand_voice = self._load_file('context/brand-voice.md')
        
        # In-memory storage
        self.conversations: Dict[str, List[Dict]] = {}
        self.tickets: Dict[str, Dict] = {}
        
        # Escalation keywords
        self.escalation_keywords = [
            'refund', 'money back', 'chargeback', 'dispute',
            'lawyer', 'legal', 'sue', 'attorney', 'court action',
            'cancel my account', 'want to cancel',
            'human', 'agent', 'person', 'talk to a person', 'real agent',
            'data breach', 'my data was leaked', 'security incident',
            'GDPR', 'delete all my data', 'right to be forgotten'
        ]
        
        # Channel style instructions
        self.channel_styles = {
            'email': 'formal, max 400 words, include greeting and sign-off',
            'whatsapp': 'max 300 characters, casual, no greeting, end with "Reply \'human\' for live support 👤"',
            'web_form': 'semi-formal, max 300 words, friendly but structured'
        }
    
    def _load_file(self, filepath: str) -> str:
        """Load content from a file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: {filepath} not found")
            return ""
    
    def _search_product_docs(self, query: str) -> str:
        """Simple keyword search in product documentation"""
        query_lower = query.lower()
        docs_lower = self.product_docs.lower()
        
        # Split docs into sections
        sections = self.product_docs.split('\n## ')
        relevant_sections = []
        
        for section in sections:
            section_lower = section.lower()
            # Count keyword matches
            words = query_lower.split()
            matches = sum(1 for word in words if word in section_lower)
            if matches > 0:
                relevant_sections.append((matches, section))
        
        # Sort by relevance and return top 3
        relevant_sections.sort(key=lambda x: x[0], reverse=True)
        top_sections = [section for _, section in relevant_sections[:3]]
        
        return '\n\n'.join(top_sections)
    
    def _check_escalation(self, message: str) -> tuple[bool, str]:
        """Check if message contains escalation keywords"""
        message_lower = message.lower()
        
        for keyword in self.escalation_keywords:
            if keyword in message_lower:
                return True, keyword
        
        return False, ""
    
    def _generate_ticket_id(self) -> str:
        """Generate a ticket ID"""
        return f"T{str(uuid.uuid4())[:8].upper()}"
    
    def _get_or_create_conversation(self, customer_id: str) -> List[Dict]:
        """Get or create conversation history for customer"""
        if customer_id not in self.conversations:
            self.conversations[customer_id] = []
        return self.conversations[customer_id]
    
    def _build_gemini_prompt(self, customer_id: str, message: str, channel: str, 
                           relevant_docs: str, conversation_history: List[Dict]) -> str:
        """Build prompt for Gemini API"""
        channel_style = self.channel_styles.get(channel, 'professional and helpful')
        
        # Format conversation history
        history_text = ""
        for exchange in conversation_history[-5:]:  # Last 5 exchanges
            history_text += f"Customer: {exchange['customer_message']}\n"
            history_text += f"Agent: {exchange['agent_response']}\n\n"
        
        prompt = f"""
You are a customer support agent for TechCorp, a B2B project management SaaS company.

CONTEXT INFORMATION:
{relevant_docs}

BRAND VOICE GUIDELINES:
{self.brand_voice}

ESCALATION RULES:
{self.escalation_rules}

CONVERSATION HISTORY:
{history_text if history_text else "No previous conversation"}

CURRENT CUSTOMER MESSAGE:
{message}

CHANNEL STYLE: {channel_style}

RESPONSE REQUIREMENTS:
1. Answer the customer's question based on the provided context
2. Follow the brand voice guidelines for the specified channel
3. If you cannot find the answer in the context, be honest and suggest escalation
4. Keep responses concise and actionable
5. For WhatsApp: max 300 characters, casual, no greeting
6. For email: formal, max 400 words, include greeting and sign-off
7. For web form: semi-formal, max 300 words

Provide a helpful, accurate response following these guidelines.
"""
        return prompt
    
    def run_agent(self, customer_id: str, message: str, channel: str) -> Dict[str, Any]:
        """Run the agent for a customer message"""
        try:
            # Check escalation keywords first
            escalated, escalation_reason = self._check_escalation(message)
            if escalated:
                # Create ticket for escalation
                ticket_id = self._generate_ticket_id()
                self.tickets[ticket_id] = {
                    'customer_id': customer_id,
                    'message': message,
                    'channel': channel,
                    'status': 'escalated',
                    'escalation_reason': escalation_reason,
                    'created_at': datetime.now().isoformat()
                }
                
                # Get conversation history
                conversation = self._get_or_create_conversation(customer_id)
                
                # Save exchange
                escalation_response = self._generate_escalation_response(escalation_reason, channel)
                conversation.append({
                    'customer_message': message,
                    'agent_response': escalation_response,
                    'timestamp': datetime.now().isoformat(),
                    'escalated': True
                })
                
                return {
                    'response': escalation_response,
                    'escalated': True,
                    'ticket_id': ticket_id,
                    'escalation_reason': escalation_reason
                }
            
            # Search product docs
            relevant_docs = self._search_product_docs(message)
            
            # Get conversation history
            conversation = self._get_or_create_conversation(customer_id)
            
            # Build Gemini prompt
            prompt = self._build_gemini_prompt(customer_id, message, channel, 
                                            relevant_docs, conversation)
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            agent_response = response.text.strip()
            
            # Create ticket if not exists
            ticket_id = self._generate_ticket_id()
            if customer_id not in [t.get('customer_id') for t in self.tickets.values()]:
                self.tickets[ticket_id] = {
                    'customer_id': customer_id,
                    'message': message,
                    'channel': channel,
                    'status': 'open',
                    'created_at': datetime.now().isoformat()
                }
            
            # Save exchange to conversation
            conversation.append({
                'customer_message': message,
                'agent_response': agent_response,
                'timestamp': datetime.now().isoformat(),
                'escalated': False
            })
            
            return {
                'response': agent_response,
                'escalated': False,
                'ticket_id': ticket_id,
                'escalation_reason': None
            }
            
        except Exception as e:
            error_response = f"I apologize, but I encountered an error: {str(e)}"
            return {
                'response': error_response,
                'escalated': True,
                'ticket_id': None,
                'escalation_reason': 'technical_error'
            }
    
    def _generate_escalation_response(self, reason: str, channel: str) -> str:
        """Generate appropriate escalation response based on channel"""
        if channel == 'whatsapp':
            return "I'm escalating this to our human team. Reply 'human' for live support 👤"
        elif channel == 'web_form':
            return "I'm escalating this to our specialist team for immediate attention. You'll hear back within 2 hours."
        else:  # email
            return "I'm escalating this to our specialist team for immediate attention. You'll hear back within 2 hours.\n\nBest regards,\nTechCorp Support Team"
    
    def load_test_cases(self, filepath: str) -> List[Dict]:
        """Load test cases from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tickets = json.load(f)
            
            # Select 6 diverse test cases
            test_cases = [
                tickets[0],   # Normal technical question (email)
                tickets[1],   # WhatsApp short message
                tickets[3],   # Refund request (escalation)
                tickets[6],   # Feature request (email)
                tickets[14],  # API question (web_form)
                tickets[25],  # Angry customer (escalation)
            ]
            
            return test_cases
            
        except FileNotFoundError:
            print(f"Test cases file {filepath} not found")
            return []
    
    def main(self):
        """Run test cases"""
        print("🤖 TechCorp FTE Agent Prototype - Test Run")
        print("=" * 50)
        
        # Load test cases
        test_cases = self.load_test_cases('context/sample-tickets.json')
        
        if not test_cases:
            print("❌ No test cases found")
            return
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test Case {i}: {test_case['channel'].upper()}")
            print(f"Customer: {test_case['customer_name']}")
            print(f"Message: {test_case['message'][:100]}...")
            
            # Run agent
            result = self.run_agent(
                customer_id=test_case['customer_email'] or test_case['customer_phone'],
                message=test_case['message'],
                channel=test_case['channel']
            )
            
            # Store result
            results.append({
                'test_case': test_case,
                'result': result
            })
            
            # Print result
            print(f"📝 Response: {result['response'][:150]}...")
            print(f"🚨 Escalated: {'Yes' if result['escalated'] else 'No'}")
            if result['escalated']:
                print(f"📋 Reason: {result['escalation_reason']}")
            print(f"🎫 Ticket: {result['ticket_id']}")
        
        # Print summary
        self._print_summary(results)
    
    def _print_summary(self, results: List[Dict]):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(results)
        escalated_tests = sum(1 for r in results if r['result']['escalated'])
        escalation_rate = (escalated_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"Total tests: {total_tests}")
        print(f"Escalated: {escalated_tests}")
        print(f"Escalation rate: {escalation_rate:.1f}%")
        
        print("\n📋 Detailed Results:")
        for i, result in enumerate(results, 1):
            test_case = result['test_case']
            agent_result = result['result']
            print(f"{i}. {test_case['channel']} - {'🚨' if agent_result['escalated'] else '✅'}")
        
        print(f"\n✅ Agent prototype testing complete!")

if __name__ == "__main__":
    agent = TechCorpAgent()
    agent.main()
