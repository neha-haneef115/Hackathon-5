# TechCorp Escalation Rules

## ALWAYS ESCALATE when customer message contains:

### Financial/Legal Keywords
- **"refund", "money back", "chargeback", "dispute"** → reason: `billing_request`
- **"cancel my account", "want to cancel"** → reason: `cancellation_request`
- **"lawyer", "legal", "sue", "attorney", "court action"** → reason: `legal_threat`

### Security/Data Privacy
- **"data breach", "my data was leaked", "security incident"** → reason: `security_concern`
- **"GDPR", "delete all my data", "right to be forgotten"** → reason: `data_privacy_request`

### Customer Sentiment
- **Profanity or aggressive language** → reason: `negative_sentiment`
- **"talk to a person", "real agent", "human please", "speak to someone"** → reason: `human_requested`

### WhatsApp-Specific Escalations
- Customer sends just: **"human", "agent", "help", "person"** → reason: `human_requested`

### Knowledge Gaps
- **Cannot find answer after 2 knowledge base searches** → reason: `knowledge_gap`

### Pricing Issues
- **Pricing negotiation beyond listed prices** → reason: `pricing_negotiation`

## ESCALATION URGENCY LEVELS

### CRITICAL - Respond Immediately
- **Legal threats**: Any mention of lawyers, lawsuits, or legal action
- **Security/Data breach**: Customer reports data compromise or security incidents
- **GDPR compliance**: Data deletion requests under privacy regulations

### HIGH - Respond Within 30 Minutes
- **Refunds/Chargebacks**: Customer demanding money back or threatening chargebacks
- **Angry customers**: Aggressive language, profanity, or clearly frustrated tone
- **Cancellations**: Immediate account cancellation requests
- **Data privacy**: Any request for data deletion or privacy concerns

### NORMAL - Respond Within 2 Hours
- **Human requested**: Customer specifically asks for human agent
- **Pricing questions**: Questions about custom pricing or discounts
- **Complex technical issues**: Problems requiring engineering investigation

## DO NOT ESCALATE for:

### Self-Service Issues
- **General how-to questions**: Answer from product documentation
- **Password resets**: Guide through standard password reset process
- **Basic troubleshooting**: Browser issues, cache clearing, etc.
- **Feature questions**: Explain existing functionality from docs

### Standard Support
- **Technical troubleshooting**: Provide step-by-step solutions from knowledge base
- **API and integration questions**: Answer using API documentation
- **Account management**: Role changes, invitations, workspace settings
- **Billing inquiries**: Standard questions about plans, billing dates, invoices

## ESCALATION PROCESS

### Immediate Escalations (CRITICAL/HIGH)
1. **Tag ticket** with appropriate escalation reason
2. **Notify** relevant team via Slack/Teams channel:
   - `#legal-alerts` for legal threats
   - `#security-incidents` for data breaches
   - `#billing-urgent` for refund/chargeback threats
   - `#customer-escalations` for angry customers
3. **Document** all customer interactions in ticket notes
4. **Set expectation** with customer: "I'm escalating this to our specialist team who will respond within [timeframe]"

### Standard Escalations (NORMAL)
1. **Tag ticket** with escalation reason
2. **Route** to appropriate department:
   - `billing-team` for pricing questions
   - `human-support` for human agent requests
   - `engineering` for complex technical issues
3. **Provide ETA** to customer: "A specialist will review this and respond within 2 hours"

## ESCALATION TRIGGERS - AUTOMATIC DETECTION

### Keyword-Based Triggers
The system should automatically flag tickets containing:
- Any financial/legal keywords listed above
- Profanity detection (using standard profanity lists)
- Multiple exclamation points or all-caps messages
- Security-related terminology

### Sentiment Analysis
- **Negative sentiment score** below -0.5 → escalate
- **Frustration indicators**: "unacceptable", "ridiculous", "terrible", "worst"
- **Urgency markers**: "immediately", "urgent", "asap", "right now"

### Pattern Recognition
- **Repeat contacts**: Same customer contacting 3+ times about same issue
- **Failed self-service**: Customer tried multiple solutions without success
- **Account value**: High-value customers ($500+/month) get faster escalation

## QUALITY ASSURANCE

### Escalation Review
- **Daily review** of all escalated tickets
- **False positive analysis**: Were escalations appropriate?
- **Response time tracking**: Did teams meet SLA requirements?
- **Customer satisfaction**: Follow-up survey after escalation resolution

### Continuous Improvement
- **Monthly escalation report** with trends and patterns
- **Knowledge base updates** based on common escalation reasons
- **Agent training** for better first-contact resolution
- **Process refinement** to reduce unnecessary escalations

## SPECIAL HANDLING INSTRUCTIONS

### Enterprise Customers
- **Immediate escalation** for any Enterprise customer issues
- **Dedicated account manager** notification
- **24/7 on-call engineer** for critical issues

### Regulatory Compliance
- **GDPR requests**: 30-day response deadline required by law
- **Data breaches**: Follow incident response protocol
- **Legal matters**: Do not admit fault, forward to legal team immediately

### Communication Guidelines
- **Never promise** specific outcomes or timelines you can't guarantee
- **Always document** escalation reasons and customer statements
- **Maintain professional tone** even with angry customers
- **Set clear expectations** about next steps and response times

## ESCALATION METRICS TO TRACK

### Volume Metrics
- **Total escalations per day/week/month**
- **Escalation rate** (percentage of total tickets)
- **Reason distribution** (most common escalation reasons)

### Performance Metrics
- **Time to escalate** (from ticket creation to escalation)
- **Time to resolve** (from escalation to resolution)
- **Customer satisfaction** after escalation
- **First-contact resolution rate**

### Quality Metrics
- **False positive rate** (unnecessary escalations)
- **Repeat escalation rate** (same customer escalating multiple times)
- **Agent escalation accuracy** (correct vs. incorrect escalation decisions)
