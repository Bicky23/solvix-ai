# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**solvix-ai** is the AI engine component of the Solvix AR Collections platform. It provides intelligent email classification, draft generation, and decision-making capabilities for automated debt collection workflows.

### Role in the Solvix Ecosystem

This repository is part of a three-component architecture:

- **Solvix (Django Backend)**: Manages authentication, organizations, Sage 200 integration, Microsoft 365 integration, Bronze layer data ingestion, and API endpoints
- **solvix-etl (ETL Pipeline)**: Transforms Bronze data into Silver layer PostgreSQL tables for business-ready analytics
- **solvix-ai (This Repo)**: AI engine for email classification, draft generation, and intelligent decision-making

### AI Engine Responsibilities

1. **Email Classification**: Analyze inbound emails from debtors and classify them into categories:
   - COOPERATIVE: Positive engagement, payment intent
   - PROMISE: Commitment to pay by specific date
   - DISPUTE: Questioning invoice validity or amounts
   - HOSTILE: Aggressive or threatening tone
   - ALREADY_PAID: Claims payment already made
   - INSOLVENCY: Indication of financial distress
   - OOO: Out of office notification
   - UNRELATED: Off-topic or spam

2. **Draft Generation**: Create personalized collection emails based on:
   - Debtor payment history and behavior metrics
   - Escalation level (1-4, increasing in firmness)
   - Case state and outstanding obligations
   - Previous communication history and responses
   - Tone requirements (professional, firm, urgent, legal-warning)

3. **Gate Evaluation**: Determine whether cases or drafts should be created based on business rules and thresholds

4. **Decision Support**: Provide recommendations for legal escalation, write-offs, or special attention cases

## Architecture

### Project Structure

```
solvix-ai/
├── src/
│   ├── api/              # FastAPI endpoints for classification and draft generation
│   ├── config/           # Configuration and settings
│   ├── engine/           # Core AI logic (classification, generation)
│   ├── llm/              # LLM client wrappers (OpenAI, Anthropic, etc.)
│   └── prompts/          # Prompt templates for different tasks
├── tests/                # Test suite
├── Dockerfile            # Container definition
└── pyproject.toml        # Dependencies and build configuration
```

### Expected API Endpoints

The AI engine should expose FastAPI endpoints that the Django backend calls:

#### POST /classify
**Purpose**: Classify an inbound email message

**Request Body**:
```json
{
  "tenant_id": "uuid",
  "message_id": "uuid",
  "from_address": "debtor@company.com",
  "subject": "Re: Invoice #12345",
  "body_content": "email body text...",
  "party_context": {
    "customer_code": "CUST001",
    "name": "Acme Corp",
    "outstanding_balance": 15000.00,
    "avg_days_to_pay": 45,
    "payment_history": "reliable_late",
    "broken_promises_count": 1
  }
}
```

**Response**:
```json
{
  "classification": "PROMISE",
  "confidence": 0.92,
  "reasoning": "Customer explicitly commits to payment by specific date",
  "extracted_data": {
    "promise_date": "2026-01-15",
    "promise_amount": 15000.00
  }
}
```

#### POST /generate-draft
**Purpose**: Generate a collection email draft

**Request Body**:
```json
{
  "tenant_id": "uuid",
  "party_id": "uuid",
  "escalation_level": 2,
  "party_context": {
    "customer_code": "CUST001",
    "name": "Acme Corp",
    "outstanding_balance": 15000.00,
    "overdue_invoices": [
      {"invoice_number": "INV-001", "amount": 10000.00, "days_overdue": 30},
      {"invoice_number": "INV-002", "amount": 5000.00, "days_overdue": 15}
    ],
    "payment_history": {...},
    "last_response_type": "COOPERATIVE",
    "touch_count": 1
  },
  "escalation_contact": {
    "name": "John Smith",
    "title": "AR Manager",
    "email": "john.smith@company.com"
  },
  "tone": "professional"
}
```

**Response**:
```json
{
  "subject": "Follow-up: Outstanding Invoices - Acme Corp",
  "body_html": "<p>Dear Acme Corp,</p>...",
  "body_text": "Dear Acme Corp...",
  "reasoning": "Level 2 escalation with firm but professional tone. References specific invoices and previous contact.",
  "suggested_send_date": "2026-01-06T09:00:00Z"
}
```

## Data Integration

### Reading from Silver Layer

The AI engine needs read-only access to Silver layer PostgreSQL tables created by solvix-etl:

**Key Tables**:
- `parties`: Debtor master data with behavior metrics and case state
- `obligations`: Outstanding invoices
- `evidence`: Payment history
- `thread_messages`: Email communication history with classifications
- `promise_history`: Previous payment promises and outcomes
- `dispute_history`: Dispute records
- `escalation_hierarchy`: Configured escalation levels per tenant

**Database Connection**:
```python
# Use DATABASE_URL from environment
# Format: postgresql://user:password@host:port/database
# In local dev: postgresql://solvix:localdev@localhost:5433/solvix
```

### Writing Classification Results

After classifying an email, update the `thread_messages` table:

```python
UPDATE thread_messages
SET 
    classification = 'PROMISE',
    classification_confidence = 0.92,
    classified_at = NOW(),
    processing_status = 'processed',
    processed_at = NOW()
WHERE tenant_id = %s AND message_id = %s
```

**Side Effects**: Based on classification, insert into audit tables:
- `PROMISE` → Insert into `promise_history`
- `DISPUTE` → Insert into `dispute_history`
- `INSOLVENCY` → Insert into `insolvency_history`
- `ALREADY_PAID` → Insert into `payment_verifications`

### Draft Storage

Generated drafts are stored in the `drafts` table:

```sql
INSERT INTO drafts (
    tenant_id, party_id, escalation_level,
    subject, body_html, body_text,
    ai_reasoning, status, created_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
```

## Development Workflow

### Setting Up Local Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (once pyproject.toml is configured)
pip install -e ".[dev]"

# Set environment variables
export DATABASE_URL="postgresql://solvix:localdev@localhost:5433/solvix"
export OPENAI_API_KEY="your-api-key"  # or ANTHROPIC_API_KEY
export REDIS_URL="redis://localhost:6379/0"

# Run the API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8001
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_classification.py

# Run with verbose output
pytest tests/ -v
```

### Linting and Formatting

The project should follow the same standards as the main Solvix backend:

```bash
# Check code style
ruff check src/ tests/

# Auto-format code
ruff format src/ tests/
```

## Prompt Engineering Guidelines

### Classification Prompts

Store prompts in `src/prompts/classification.py` as versioned templates. Include:

1. **Clear Task Definition**: "You are an AI assistant analyzing debtor email responses..."
2. **Classification Categories**: Provide examples for each category
3. **Context Fields**: List all available party context fields
4. **Output Format**: Specify exact JSON structure expected
5. **Edge Cases**: Handle ambiguous or multi-intent emails

### Draft Generation Prompts

Store in `src/prompts/drafts.py`:

1. **Escalation Level Guidelines**: Define tone for levels 1-4
2. **Personalization**: Use customer name, specific invoice numbers, overdue amounts
3. **Payment History Integration**: Reference past behavior (e.g., "typically pays 15 days late")
4. **Call-to-Action**: Clear next steps (e.g., "pay by date X" or "contact us to discuss")
5. **Compliance**: Avoid threatening language, maintain professional tone

## Key Architectural Decisions

### Stateless API Design

The AI engine should be stateless - all required context is passed in API requests or fetched from Silver layer. Do not maintain session state.

### Idempotency

Classification and draft generation should be idempotent:
- Same input → same classification (within confidence threshold)
- Use deterministic LLM parameters when possible (temperature = 0 for classification)

### Error Handling

- Network failures: Retry with exponential backoff
- LLM API rate limits: Queue requests if needed
- Database connection issues: Graceful degradation, log errors
- Invalid input: Return 400 with clear error message

### Observability

Log all AI decisions for audit and improvement:
- Input context (sanitize sensitive data)
- LLM prompt and response
- Classification result and confidence
- Processing time

## Integration with Backend (Solvix)

### Triggering Classification

The Django backend calls the AI engine via HTTP after emails arrive in Bronze layer:

```python
# In Solvix backend (organizations/tasks.py or similar)
import httpx

async def classify_email(message_id: str):
    context = get_party_context(message_id)
    response = await httpx.post(
        "http://ai-engine:8001/classify",
        json={"message_id": message_id, "party_context": context}
    )
    update_classification(message_id, response.json())
```

### Triggering Draft Generation

Called when a case enters ACTIVE state and passes gate evaluation:

```python
# In Solvix backend
def generate_draft_for_case(party_id: str, escalation_level: int):
    context = get_party_full_context(party_id)
    response = httpx.post(
        "http://ai-engine:8001/generate-draft",
        json={"party_id": party_id, "escalation_level": escalation_level, "party_context": context}
    )
    save_draft_to_silver(party_id, response.json())
```

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://solvix:localdev@localhost:5433/solvix

# LLM Provider
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Redis (for caching/queueing if needed)
REDIS_URL=redis://localhost:6379/0

# API Configuration
AI_ENGINE_PORT=8001
LOG_LEVEL=INFO

# Model Configuration
CLASSIFICATION_MODEL=gpt-4o-mini  # or claude-3-5-sonnet-20241022
GENERATION_MODEL=gpt-4o  # or claude-3-5-sonnet-20241022
CLASSIFICATION_TEMPERATURE=0.0
GENERATION_TEMPERATURE=0.7
```

## Docker Deployment

The AI engine should be containerized for deployment alongside other services:

```dockerfile
# Expected Dockerfile structure
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e ".[prod]"

COPY src/ ./src/

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

Run with docker-compose in the Solvix backend:

```yaml
# In Solvix/docker-compose.yml
services:
  ai-engine:
    build: ../solvix-ai
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://solvix:localdev@postgres:5432/solvix
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
```

## Testing Strategy

### Unit Tests

Test individual components in isolation:
- Prompt template rendering
- Response parsing
- Classification logic
- Draft formatting

### Integration Tests

Test with real LLM APIs (use test fixtures to avoid excessive API calls):
- End-to-end classification flow
- Draft generation with various party contexts
- Database read/write operations

### Mock Data

Use realistic test fixtures based on Silver layer schema:
```python
# tests/fixtures/party_context.py
SAMPLE_PARTY = {
    "customer_code": "TEST001",
    "name": "Test Customer Ltd",
    "outstanding_balance": 25000.00,
    "avg_days_to_pay": 35,
    "on_time_rate": 0.65,
    "broken_promises_count": 0,
    "segment": "medium_risk"
}
```

## Related Documentation

- **Backend Repository**: `/Users/bijitdeka23/Downloads/Solvix/README.md` - Django API, authentication, integrations
- **ETL Repository**: `/Users/bijitdeka23/Downloads/solvix-etl/README.md` - Data transformations, Silver layer schema
- **Frontend Repository**: `/Users/bijitdeka23/Downloads/solvix_frontend/README.md` - React dashboard UI
- **Silver Layer Spec**: `/Users/bijitdeka23/Downloads/Solvix/silver_layer.md` - Complete database schema
- **Email Pipeline**: `/Users/bijitdeka23/Downloads/Solvix/email_ingestion_pipeline.md` - Email ingestion workflow

## Common Tasks

### Add a New Classification Category

1. Update classification enum in `src/engine/classifier.py`
2. Add examples to `src/prompts/classification.py`
3. Update Silver layer `thread_messages` table if needed (in solvix-etl)
4. Add test cases in `tests/test_classification.py`
5. Update API documentation

### Improve Draft Quality

1. Collect feedback from users (stored in draft_events table)
2. Analyze low-confidence drafts
3. Refine prompts in `src/prompts/drafts.py`
4. A/B test different prompt versions
5. Monitor send rates and response rates

### Debug Classification Issues

1. Check logs for input context and LLM response
2. Query Silver layer for party behavior metrics
3. Test prompt in LLM playground with same context
4. Review similar historical classifications in `thread_messages`
5. Adjust confidence thresholds if needed

### Add Support for New LLM Provider

1. Create provider client in `src/llm/`
2. Implement common interface (completion, streaming, embeddings)
3. Add provider-specific configuration
4. Update environment variable docs
5. Add integration tests with mock responses
