-- TechCorp FTE Database Schema
-- PostgreSQL 16 with pgvector extension

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Customers table - central customer records
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    name VARCHAR(255),
    whatsapp_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Customer identifiers - multiple ways to identify customers
CREATE TABLE customer_identifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type VARCHAR(50) NOT NULL, -- 'email', 'phone', 'whatsapp', 'web_form'
    identifier_value VARCHAR(255) NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(identifier_type, identifier_value)
);

-- Conversations - customer interaction sessions
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    initial_channel VARCHAR(50) NOT NULL, -- 'email', 'whatsapp', 'web_form'
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'resolved', 'escalated', 'closed')),
    sentiment_score DECIMAL(3,2) CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    resolution_type VARCHAR(100),
    escalated_to VARCHAR(255),
    metadata JSONB DEFAULT '{}'
);

-- Messages - individual messages within conversations
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL,
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    role VARCHAR(20) NOT NULL CHECK (role IN ('customer', 'agent', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    tokens_used INTEGER,
    latency_ms INTEGER,
    tool_calls JSONB DEFAULT '[]',
    channel_message_id VARCHAR(255),
    delivery_status VARCHAR(20) DEFAULT 'pending' CHECK (delivery_status IN ('pending', 'sent', 'delivered', 'failed', 'read'))
);

-- Tickets - support tickets for tracking
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    source_channel VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    status VARCHAR(30) DEFAULT 'open' CHECK (status IN ('open', 'processing', 'resolved', 'escalated', 'closed')),
    subject VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

-- Knowledge base - product documentation with vector embeddings
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    embedding VECTOR(768), -- Google text-embedding-004 = 768 dimensions
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Escalation log - track all escalations
CREATE TABLE escalation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    reason VARCHAR(200) NOT NULL,
    urgency VARCHAR(20) DEFAULT 'normal' CHECK (urgency IN ('critical', 'high', 'normal', 'low')),
    assigned_to VARCHAR(255),
    escalated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

-- Channel configurations - per-channel settings
CREATE TABLE channel_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel VARCHAR(50) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    max_response_length INTEGER DEFAULT 400,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent metrics - performance and usage metrics
CREATE TABLE agent_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    channel VARCHAR(50),
    dimensions JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily reports - aggregated daily statistics
CREATE TABLE daily_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date DATE UNIQUE NOT NULL,
    total_tickets INTEGER DEFAULT 0,
    resolved_tickets INTEGER DEFAULT 0,
    escalated_tickets INTEGER DEFAULT 0,
    avg_sentiment DECIMAL(3,2),
    avg_response_time_ms INTEGER,
    channel_breakdown JSONB DEFAULT '{}',
    top_categories JSONB DEFAULT '{}',
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance optimization

-- Customers indexes
CREATE INDEX idx_customers_email ON customers(email) WHERE email IS NOT NULL;
CREATE INDEX idx_customers_phone ON customers(phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_customers_created_at ON customers(created_at);

-- Customer identifiers indexes
CREATE INDEX idx_customer_identifiers_value ON customer_identifiers(identifier_value);
CREATE INDEX idx_customer_identifiers_type ON customer_identifiers(identifier_type);
CREATE INDEX idx_customer_identifiers_customer_id ON customer_identifiers(customer_id);

-- Conversations indexes
CREATE INDEX idx_conversations_customer_id ON conversations(customer_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_initial_channel ON conversations(initial_channel);
CREATE INDEX idx_conversations_started_at ON conversations(started_at DESC);
CREATE INDEX idx_conversations_active_recent ON conversations(customer_id, started_at DESC) 
    WHERE status = 'active' AND started_at > NOW() - INTERVAL '24 hours';

-- Messages indexes
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_channel ON messages(channel);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX idx_messages_direction ON messages(direction);
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at ASC);

-- Tickets indexes
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_source_channel ON tickets(source_channel);
CREATE INDEX idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX idx_tickets_created_at ON tickets(created_at DESC);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_category ON tickets(category);

-- Knowledge base indexes
CREATE INDEX idx_knowledge_base_category ON knowledge_base(category);
CREATE INDEX idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_knowledge_base_title_trgm ON knowledge_base USING gin (title gin_trgm_ops);
CREATE INDEX idx_knowledge_base_content_trgm ON knowledge_base USING gin (content gin_trgm_ops);

-- Escalation log indexes
CREATE INDEX idx_escalation_log_ticket_id ON escalation_log(ticket_id);
CREATE INDEX idx_escalation_log_escalated_at ON escalation_log(escalated_at DESC);
CREATE INDEX idx_escalation_log_urgency ON escalation_log(urgency);

-- Agent metrics indexes
CREATE INDEX idx_agent_metrics_name ON agent_metrics(metric_name);
CREATE INDEX idx_agent_metrics_channel ON agent_metrics(channel);
CREATE INDEX idx_agent_metrics_recorded_at ON agent_metrics(recorded_at DESC);
CREATE INDEX idx_agent_metrics_name_channel_time ON agent_metrics(metric_name, channel, recorded_at DESC);

-- Daily reports indexes
CREATE INDEX idx_daily_reports_date ON daily_reports(report_date);
CREATE INDEX idx_daily_reports_generated_at ON daily_reports(generated_at DESC);

-- Channel configs indexes
CREATE INDEX idx_channel_configs_channel ON channel_configs(channel);
CREATE INDEX idx_channel_configs_enabled ON channel_configs(enabled);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tickets_updated_at BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_channel_configs_updated_at BEFORE UPDATE ON channel_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default channel configurations
INSERT INTO channel_configs (channel, max_response_length, config) VALUES
('email', 400, '{"style": "formal", "requires_greeting": true, "requires_signoff": true}'),
('whatsapp', 300, '{"style": "casual", "requires_greeting": false, "max_chars": 300}'),
('web_form', 300, '{"style": "semi-formal", "requires_greeting": true, "structured": true}')
ON CONFLICT (channel) DO NOTHING;

-- Create view for active conversations with customer info
CREATE VIEW active_conversations AS
SELECT 
    c.id as conversation_id,
    c.customer_id,
    c.initial_channel,
    c.started_at,
    c.status,
    c.sentiment_score,
    cust.email,
    cust.phone,
    cust.whatsapp_id,
    cust.name,
    COUNT(m.id) as message_count,
    MAX(m.created_at) as last_message_at
FROM conversations c
JOIN customers cust ON c.customer_id = cust.id
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.status = 'active'
GROUP BY c.id, cust.id
ORDER BY c.started_at DESC;

-- Create view for ticket statistics
CREATE VIEW ticket_stats AS
SELECT 
    source_channel,
    category,
    priority,
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/60) as avg_resolution_minutes
FROM tickets
GROUP BY source_channel, category, priority, status
ORDER BY count DESC;
