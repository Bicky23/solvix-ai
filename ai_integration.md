# AI Engine Repository: Setup & Integration

## Overview

Create the `solvix-ai-engine` repository — a FastAPI service that handles all LLM interactions for Solvix. Then integrate it with the Backend and ETL repositories.

---

## Architecture Summary

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Backend   │──HTTP──►│  AI Engine  │         │     ETL     │
│   (Django)  │◄────────│  (FastAPI)  │         │   (Tasks)   │
└──────┬──────┘         └─────────────┘         └──────┬──────┘
       │                       │                       │
       │                       │ No DB Access          │
       ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL                               │
│                   (Silver / Gold)                            │
└─────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- AI Engine is stateless — no database access
- Backend fetches context from Silver/Gold, sends to AI Engine
- AI Engine receives context, returns results
- Backend updates database with results, triggers ETL for Gold refresh

---

# PART 1: AI Engine Repository Structure

## 1.1 Create Repository

Create a new repository: `solvix-ai-engine`

```
solvix-ai-engine/
├── src/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entrypoint
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── classify.py         # POST /classify
│   │   │   ├── generate.py         # POST /generate-draft
│   │   │   ├── gates.py            # POST /evaluate-gates
│   │   │   └── health.py           # GET /health
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── requests.py         # Pydantic input models
│   │       └── responses.py        # Pydantic output models
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── classifier.py           # Email classification logic
│   │   ├── generator.py            # Draft generation logic
│   │   └── gate_evaluator.py       # Gate evaluation logic
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py               # OpenAI client wrapper
│   │   └── prompts.py              # Prompt templates
│   │
│   └── config/
│       ├── __init__.py
│       └── settings.py             # Pydantic settings
│
├── prompts/
│   ├── classification/
│   │   └── classify_email.txt
│   └── generation/
│       ├── friendly_reminder.txt
│       ├── professional.txt
│       ├── firm.txt
│       └── final_notice.txt
│
├── tests/
│   ├── __init__.py
│   ├── test_classifier.py
│   ├── test_generator.py
│   └── test_api.py
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 1.2 Dependencies

**File: `requirements.txt`**

```
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
openai>=1.12.0
tenacity>=8.2.0
python-dotenv>=1.0.0
httpx>=0.26.0
```

**File: `pyproject.toml`**

```toml
[project]
name = "solvix-ai-engine"
version = "0.1.0"
description = "AI Engine for Solvix debt collection platform"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

---

## 1.3 Configuration

**File: `src/config/settings.py`**

```python
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    debug: bool = False
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.3
    openai_max_tokens: int = 2000
    
    # Timeouts
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 3
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

**File: `.env.example`**

```
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=2000

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
DEBUG=false

# Timeouts
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=3

# Logging
LOG_LEVEL=INFO
```

---

## 1.4 Pydantic Models

**File: `src/api/models/requests.py`**

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class EmailContent(BaseModel):
    """Email content for classification."""
    subject: str
    body: str
    from_address: str
    from_name: Optional[str] = None
    received_at: Optional[datetime] = None


class PartyInfo(BaseModel):
    """Party (debtor) information."""
    party_id: str
    customer_code: str
    name: str
    country_code: Optional[str] = None
    currency: str = "GBP"
    credit_limit: Optional[float] = None
    on_hold: bool = False


class BehaviorInfo(BaseModel):
    """Historical payment behavior."""
    lifetime_value: Optional[float] = None
    avg_days_to_pay: Optional[float] = None
    on_time_rate: Optional[float] = None
    partial_payment_rate: Optional[float] = None
    segment: Optional[str] = None


class ObligationInfo(BaseModel):
    """Single invoice/obligation."""
    invoice_number: str
    original_amount: float
    amount_due: float
    due_date: str
    days_past_due: int
    state: str = "open"


class CommunicationInfo(BaseModel):
    """Communication history summary."""
    touch_count: int = 0
    last_touch_at: Optional[datetime] = None
    last_touch_channel: Optional[str] = None
    last_sender_level: Optional[int] = None
    last_tone_used: Optional[str] = None
    last_response_at: Optional[datetime] = None
    last_response_type: Optional[str] = None


class TouchHistory(BaseModel):
    """Single touch record."""
    sent_at: datetime
    tone: str
    sender_level: int
    had_response: bool


class PromiseHistory(BaseModel):
    """Single promise record."""
    promise_date: str
    promise_amount: Optional[float] = None
    outcome: str  # kept, broken, pending


class CaseContext(BaseModel):
    """Full case context for AI operations."""
    party: PartyInfo
    behavior: Optional[BehaviorInfo] = None
    obligations: List[ObligationInfo] = []
    communication: Optional[CommunicationInfo] = None
    recent_touches: List[TouchHistory] = []
    promises: List[PromiseHistory] = []
    
    # Case state
    case_state: Optional[str] = None
    days_in_state: Optional[int] = None
    broken_promises_count: int = 0
    active_dispute: bool = False
    hardship_indicated: bool = False
    
    # Tenant settings
    brand_tone: str = "professional"
    touch_cap: int = 10
    touch_interval_days: int = 3


class ClassifyRequest(BaseModel):
    """Request to classify an inbound email."""
    email: EmailContent
    context: CaseContext


class GenerateDraftRequest(BaseModel):
    """Request to generate a collection email draft."""
    context: CaseContext
    tone: str = "professional"  # friendly_reminder, professional, firm, final_notice
    objective: Optional[str] = None  # follow_up, promise_reminder, escalation
    custom_instructions: Optional[str] = None


class EvaluateGatesRequest(BaseModel):
    """Request to evaluate gates before taking action."""
    context: CaseContext
    proposed_action: str  # send_email, create_case, escalate, close_case
    proposed_tone: Optional[str] = None
```

**File: `src/api/models/responses.py`**

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import date


class ExtractedData(BaseModel):
    """Data extracted from email by AI."""
    promise_date: Optional[date] = None
    promise_amount: Optional[float] = None
    dispute_type: Optional[str] = None
    dispute_reason: Optional[str] = None
    redirect_contact: Optional[str] = None
    redirect_email: Optional[str] = None


class ClassifyResponse(BaseModel):
    """Response from email classification."""
    classification: str  # COOPERATIVE, PROMISE, DISPUTE, HOSTILE, QUERY, OUT_OF_OFFICE, UNSUBSCRIBE, OTHER
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    extracted_data: Optional[ExtractedData] = None
    tokens_used: Optional[int] = None


class GenerateDraftResponse(BaseModel):
    """Response from draft generation."""
    subject: str
    body: str
    tone_used: str
    invoices_referenced: List[str] = []
    tokens_used: Optional[int] = None


class GateResult(BaseModel):
    """Result of a single gate evaluation."""
    passed: bool
    reason: str
    current_value: Optional[Any] = None
    threshold: Optional[Any] = None


class EvaluateGatesResponse(BaseModel):
    """Response from gate evaluation."""
    allowed: bool
    gate_results: Dict[str, GateResult]
    recommended_action: Optional[str] = None
    tokens_used: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    model: str
```

---

## 1.5 OpenAI Client

**File: `src/llm/client.py`**

```python
import json
import logging
from typing import Optional, Dict, Any

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for OpenAI API calls."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_response: bool = True
    ) -> Dict[str, Any]:
        """
        Make a completion request to OpenAI.
        
        Args:
            system_prompt: System message setting context
            user_prompt: User message with the actual request
            temperature: Override default temperature
            max_tokens: Override default max tokens
            json_response: If True, request JSON output
        
        Returns:
            Parsed response dict and token usage
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        
        if json_response:
            kwargs["response_format"] = {"type": "json_object"}
        
        logger.debug(f"Calling OpenAI: model={self.model}")
        
        response = self.client.chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else None
        
        logger.debug(f"OpenAI response: tokens={tokens_used}")
        
        if json_response:
            parsed = json.loads(content)
            parsed["_tokens_used"] = tokens_used
            return parsed
        
        return {"content": content, "_tokens_used": tokens_used}


# Singleton instance
llm_client = LLMClient()
```

---

## 1.6 Prompt Templates

**File: `src/llm/prompts.py`**

```python
CLASSIFY_EMAIL_SYSTEM = """You are an AI assistant for a B2B debt collection platform. Your task is to classify inbound emails from debtors.

Classifications:
- COOPERATIVE: Debtor is willing to work with us, acknowledges debt, positive tone
- PROMISE: Debtor commits to a specific payment date or amount
- DISPUTE: Debtor disputes the invoice, claims error, or refuses to pay due to issue
- HOSTILE: Aggressive, threatening, or abusive language
- QUERY: Asking questions about invoice, amount, or process
- OUT_OF_OFFICE: Auto-reply, vacation message
- UNSUBSCRIBE: Requesting to stop receiving emails
- REDIRECT: Asking to contact a different person or department
- OTHER: Doesn't fit other categories

If classification is PROMISE, extract:
- promise_date: The date they commit to pay (YYYY-MM-DD format)
- promise_amount: The amount they commit to pay (if specified)

If classification is DISPUTE, extract:
- dispute_type: goods_not_received, quality_issue, pricing_error, already_paid, wrong_customer, other
- dispute_reason: Brief description of their dispute

If classification is REDIRECT, extract:
- redirect_contact: Name of person to contact
- redirect_email: Email of person to contact

Respond in JSON format:
{
  "classification": "CLASSIFICATION",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation",
  "extracted_data": {
    "promise_date": null,
    "promise_amount": null,
    "dispute_type": null,
    "dispute_reason": null,
    "redirect_contact": null,
    "redirect_email": null
  }
}"""


CLASSIFY_EMAIL_USER = """Classify this email from a debtor.

**Debtor Context:**
- Company: {party_name}
- Total Outstanding: {currency} {total_outstanding:,.2f}
- Oldest Overdue: {days_overdue_max} days
- Previous Broken Promises: {broken_promises_count}
- Segment: {segment}

**Email:**
From: {from_name} <{from_address}>
Subject: {subject}

{body}

Classify this email and extract any relevant data."""


GENERATE_DRAFT_SYSTEM = """You are an AI assistant for a B2B debt collection platform. Your task is to generate professional collection emails.

Guidelines:
- Be professional and respectful at all times
- Reference specific invoice numbers and amounts
- Acknowledge any previous communication or promises
- Adjust tone based on the escalation level
- Include clear call-to-action
- Keep emails concise but complete
- Never be threatening or use language that could be seen as harassment
- For UK/EU debtors, be mindful of relevant regulations

Tones:
- friendly_reminder: Gentle first contact, assume oversight
- professional: Standard business tone, clear expectations
- firm: More serious, emphasize consequences, still respectful  
- final_notice: Last attempt before escalation, mention next steps

Respond in JSON format:
{
  "subject": "Email subject line",
  "body": "Full email body with proper greeting and signature placeholder"
}"""


GENERATE_DRAFT_USER = """Generate a collection email draft.

**Debtor:**
- Company: {party_name}
- Contact: {contact_name}
- Total Outstanding: {currency} {total_outstanding:,.2f}

**Overdue Invoices:**
{invoices_list}

**Communication History:**
- Previous Touches: {touch_count}
- Last Contact: {last_touch_at}
- Last Tone: {last_tone_used}
- Last Response: {last_response_type}

**Current State:**
- Days Since Last Touch: {days_since_last_touch}
- Broken Promises: {broken_promises_count}
- Active Dispute: {active_dispute}

**Instructions:**
- Tone: {tone}
- Objective: {objective}
{custom_instructions}

Generate the email draft."""


EVALUATE_GATES_SYSTEM = """You are an AI assistant evaluating whether a proposed collection action should proceed.

Evaluate these gates:
1. touch_cap: Has the maximum number of touches been reached?
2. cooling_off: Has enough time passed since last contact?
3. dispute_active: Is there an unresolved dispute?
4. hardship: Has the debtor indicated financial hardship?
5. unsubscribe: Has the debtor requested no contact?
6. escalation_appropriate: Is the proposed tone/action appropriate given history?

For each gate, determine if it passes (action allowed) or fails (action blocked).

Respond in JSON format:
{
  "allowed": true/false,
  "gate_results": {
    "gate_name": {
      "passed": true/false,
      "reason": "explanation",
      "current_value": value,
      "threshold": threshold
    }
  },
  "recommended_action": "alternative action if blocked"
}"""


EVALUATE_GATES_USER = """Evaluate whether this action should proceed.

**Proposed Action:** {proposed_action}
**Proposed Tone:** {proposed_tone}

**Case State:**
- Total Touches: {touch_count}
- Touch Cap: {touch_cap}
- Days Since Last Touch: {days_since_last_touch}
- Required Interval: {touch_interval_days} days
- Active Dispute: {active_dispute}
- Hardship Indicated: {hardship_indicated}
- Unsubscribe Requested: {unsubscribe_requested}
- Broken Promises: {broken_promises_count}
- Last Tone Used: {last_tone_used}

Evaluate all gates and determine if the action should proceed."""
```

---

## 1.7 Engine Logic

**File: `src/engine/classifier.py`**

```python
import logging
from typing import Dict, Any

from src.api.models.requests import ClassifyRequest
from src.api.models.responses import ClassifyResponse, ExtractedData
from src.llm.client import llm_client
from src.llm.prompts import CLASSIFY_EMAIL_SYSTEM, CLASSIFY_EMAIL_USER

logger = logging.getLogger(__name__)


class EmailClassifier:
    """Classifies inbound emails from debtors."""
    
    def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        """
        Classify an inbound email.
        
        Args:
            request: Classification request with email and context
        
        Returns:
            Classification result with confidence and extracted data
        """
        # Build user prompt with context
        user_prompt = CLASSIFY_EMAIL_USER.format(
            party_name=request.context.party.name,
            currency=request.context.party.currency,
            total_outstanding=sum(o.amount_due for o in request.context.obligations),
            days_overdue_max=max((o.days_past_due for o in request.context.obligations), default=0),
            broken_promises_count=request.context.broken_promises_count,
            segment=request.context.behavior.segment if request.context.behavior else "unknown",
            from_name=request.email.from_name or "Unknown",
            from_address=request.email.from_address,
            subject=request.email.subject,
            body=request.email.body
        )
        
        # Call LLM
        result = llm_client.complete(
            system_prompt=CLASSIFY_EMAIL_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.2  # Lower temperature for classification
        )
        
        # Parse extracted data
        extracted = None
        if result.get("extracted_data"):
            extracted = ExtractedData(**result["extracted_data"])
        
        return ClassifyResponse(
            classification=result["classification"],
            confidence=result["confidence"],
            reasoning=result.get("reasoning"),
            extracted_data=extracted,
            tokens_used=result.get("_tokens_used")
        )


classifier = EmailClassifier()
```

**File: `src/engine/generator.py`**

```python
import logging
from typing import Dict, Any

from src.api.models.requests import GenerateDraftRequest
from src.api.models.responses import GenerateDraftResponse
from src.llm.client import llm_client
from src.llm.prompts import GENERATE_DRAFT_SYSTEM, GENERATE_DRAFT_USER

logger = logging.getLogger(__name__)


class DraftGenerator:
    """Generates collection email drafts."""
    
    def generate(self, request: GenerateDraftRequest) -> GenerateDraftResponse:
        """
        Generate a collection email draft.
        
        Args:
            request: Generation request with context and parameters
        
        Returns:
            Generated draft with subject and body
        """
        # Build invoices list
        invoices_list = "\n".join([
            f"- {o.invoice_number}: {request.context.party.currency} {o.amount_due:,.2f} ({o.days_past_due} days overdue)"
            for o in request.context.obligations[:10]  # Limit to top 10
        ])
        
        # Get communication info
        comm = request.context.communication
        
        # Build user prompt
        user_prompt = GENERATE_DRAFT_USER.format(
            party_name=request.context.party.name,
            contact_name=request.context.party.name,  # Use party name as fallback
            currency=request.context.party.currency,
            total_outstanding=sum(o.amount_due for o in request.context.obligations),
            invoices_list=invoices_list or "No specific invoices provided",
            touch_count=comm.touch_count if comm else 0,
            last_touch_at=comm.last_touch_at.strftime("%Y-%m-%d") if comm and comm.last_touch_at else "Never",
            last_tone_used=comm.last_tone_used if comm else "None",
            last_response_type=comm.last_response_type if comm else "No response",
            days_since_last_touch=request.context.days_in_state or 0,
            broken_promises_count=request.context.broken_promises_count,
            active_dispute=request.context.active_dispute,
            tone=request.tone,
            objective=request.objective or "collect payment",
            custom_instructions=f"\nAdditional: {request.custom_instructions}" if request.custom_instructions else ""
        )
        
        # Call LLM
        result = llm_client.complete(
            system_prompt=GENERATE_DRAFT_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.7  # Slightly higher for creative generation
        )
        
        # Extract referenced invoices
        invoices_referenced = [
            o.invoice_number for o in request.context.obligations
            if o.invoice_number in result.get("body", "")
        ]
        
        return GenerateDraftResponse(
            subject=result["subject"],
            body=result["body"],
            tone_used=request.tone,
            invoices_referenced=invoices_referenced,
            tokens_used=result.get("_tokens_used")
        )


generator = DraftGenerator()
```

**File: `src/engine/gate_evaluator.py`**

```python
import logging
from typing import Dict, Any

from src.api.models.requests import EvaluateGatesRequest
from src.api.models.responses import EvaluateGatesResponse, GateResult
from src.llm.client import llm_client
from src.llm.prompts import EVALUATE_GATES_SYSTEM, EVALUATE_GATES_USER

logger = logging.getLogger(__name__)


class GateEvaluator:
    """Evaluates gates before allowing collection actions."""
    
    def evaluate(self, request: EvaluateGatesRequest) -> EvaluateGatesResponse:
        """
        Evaluate gates for a proposed action.
        
        Args:
            request: Gate evaluation request with context and proposed action
        
        Returns:
            Gate evaluation results
        """
        comm = request.context.communication
        
        # Calculate days since last touch
        days_since_last_touch = 999  # Default to large number if never contacted
        if comm and comm.last_touch_at:
            from datetime import datetime, timezone
            delta = datetime.now(timezone.utc) - comm.last_touch_at
            days_since_last_touch = delta.days
        
        # Build user prompt
        user_prompt = EVALUATE_GATES_USER.format(
            proposed_action=request.proposed_action,
            proposed_tone=request.proposed_tone or "not specified",
            touch_count=comm.touch_count if comm else 0,
            touch_cap=request.context.touch_cap,
            days_since_last_touch=days_since_last_touch,
            touch_interval_days=request.context.touch_interval_days,
            active_dispute=request.context.active_dispute,
            hardship_indicated=request.context.hardship_indicated,
            unsubscribe_requested=False,  # TODO: Add to context
            broken_promises_count=request.context.broken_promises_count,
            last_tone_used=comm.last_tone_used if comm else "None"
        )
        
        # Call LLM
        result = llm_client.complete(
            system_prompt=EVALUATE_GATES_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.1  # Very low temperature for consistent evaluation
        )
        
        # Parse gate results
        gate_results = {}
        for gate_name, gate_data in result.get("gate_results", {}).items():
            gate_results[gate_name] = GateResult(
                passed=gate_data["passed"],
                reason=gate_data["reason"],
                current_value=gate_data.get("current_value"),
                threshold=gate_data.get("threshold")
            )
        
        return EvaluateGatesResponse(
            allowed=result["allowed"],
            gate_results=gate_results,
            recommended_action=result.get("recommended_action"),
            tokens_used=result.get("_tokens_used")
        )


gate_evaluator = GateEvaluator()
```

---

## 1.8 API Routes

**File: `src/api/routes/classify.py`**

```python
import logging
from fastapi import APIRouter, HTTPException

from src.api.models.requests import ClassifyRequest
from src.api.models.responses import ClassifyResponse
from src.engine.classifier import classifier

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/classify", response_model=ClassifyResponse)
async def classify_email(request: ClassifyRequest) -> ClassifyResponse:
    """
    Classify an inbound email from a debtor.
    
    Returns classification (COOPERATIVE, PROMISE, DISPUTE, etc.),
    confidence score, and any extracted data.
    """
    try:
        logger.info(f"Classifying email for party: {request.context.party.party_id}")
        result = classifier.classify(request)
        logger.info(f"Classification: {result.classification} ({result.confidence:.2f})")
        return result
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**File: `src/api/routes/generate.py`**

```python
import logging
from fastapi import APIRouter, HTTPException

from src.api.models.requests import GenerateDraftRequest
from src.api.models.responses import GenerateDraftResponse
from src.engine.generator import generator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate-draft", response_model=GenerateDraftResponse)
async def generate_draft(request: GenerateDraftRequest) -> GenerateDraftResponse:
    """
    Generate a collection email draft.
    
    Returns subject, body, and metadata about the generated draft.
    """
    try:
        logger.info(f"Generating draft for party: {request.context.party.party_id}")
        result = generator.generate(request)
        logger.info(f"Generated draft with tone: {result.tone_used}")
        return result
    except Exception as e:
        logger.error(f"Draft generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**File: `src/api/routes/gates.py`**

```python
import logging
from fastapi import APIRouter, HTTPException

from src.api.models.requests import EvaluateGatesRequest
from src.api.models.responses import EvaluateGatesResponse
from src.engine.gate_evaluator import gate_evaluator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/evaluate-gates", response_model=EvaluateGatesResponse)
async def evaluate_gates(request: EvaluateGatesRequest) -> EvaluateGatesResponse:
    """
    Evaluate gates before allowing a collection action.
    
    Returns whether action is allowed and individual gate results.
    """
    try:
        logger.info(f"Evaluating gates for action: {request.proposed_action}")
        result = gate_evaluator.evaluate(request)
        logger.info(f"Gates evaluation: allowed={result.allowed}")
        return result
    except Exception as e:
        logger.error(f"Gate evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**File: `src/api/routes/health.py`**

```python
from fastapi import APIRouter

from src.api.models.responses import HealthResponse
from src.config.settings import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        model=settings.openai_model
    )
```

---

## 1.9 Main Application

**File: `src/main.py`**

```python
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.api.routes import classify, generate, gates, health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create app
app = FastAPI(
    title="Solvix AI Engine",
    description="AI-powered email classification and draft generation for debt collection",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(classify.router, tags=["Classification"])
app.include_router(generate.router, tags=["Generation"])
app.include_router(gates.router, tags=["Gates"])


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting Solvix AI Engine")
    logger.info(f"Model: {settings.openai_model}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
```

---

## 1.10 Docker Configuration

**File: `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ src/
COPY prompts/ prompts/

# Expose port
EXPOSE 8001

# Run
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**File: `docker-compose.yml`**

```yaml
version: '3.8'

services:
  ai-engine:
    build: .
    ports:
      - "8001:8001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    restart: unless-stopped
```

---

# PART 2: Backend Integration

## 2.1 AI Engine Client Service

Add a service in Backend to call the AI Engine.

**File: `services/ai_engine.py`** (in Backend repo)

```python
import logging
from typing import Optional, Dict, Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class AIEngineClient:
    """Client for calling the AI Engine service."""
    
    def __init__(self):
        self.base_url = settings.AI_ENGINE_URL.rstrip("/")
        self.timeout = settings.AI_ENGINE_TIMEOUT
    
    async def classify_email(
        self,
        email: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify an inbound email.
        
        Args:
            email: Email content (subject, body, from_address, from_name)
            context: Case context from Gold layer
        
        Returns:
            Classification result
        """
        payload = {
            "email": email,
            "context": context
        }
        
        return await self._post("/classify", payload)
    
    async def generate_draft(
        self,
        context: Dict[str, Any],
        tone: str = "professional",
        objective: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a collection email draft.
        
        Args:
            context: Case context from Gold layer
            tone: Email tone (friendly_reminder, professional, firm, final_notice)
            objective: Specific objective for the email
            custom_instructions: Additional instructions
        
        Returns:
            Generated draft with subject and body
        """
        payload = {
            "context": context,
            "tone": tone,
            "objective": objective,
            "custom_instructions": custom_instructions
        }
        
        return await self._post("/generate-draft", payload)
    
    async def evaluate_gates(
        self,
        context: Dict[str, Any],
        proposed_action: str,
        proposed_tone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate gates before taking an action.
        
        Args:
            context: Case context from Gold layer
            proposed_action: Action to evaluate
            proposed_tone: Proposed tone for email actions
        
        Returns:
            Gate evaluation results
        """
        payload = {
            "context": context,
            "proposed_action": proposed_action,
            "proposed_tone": proposed_tone
        }
        
        return await self._post("/evaluate-gates", payload)
    
    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to AI Engine."""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Calling AI Engine: {endpoint}")
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                logger.info(f"AI Engine response received")
                return result
            except httpx.TimeoutException:
                logger.error(f"AI Engine timeout: {endpoint}")
                raise
            except httpx.HTTPStatusError as e:
                logger.error(f"AI Engine error: {e.response.status_code}")
                raise
            except Exception as e:
                logger.error(f"AI Engine call failed: {e}")
                raise


# Singleton instance
ai_engine = AIEngineClient()
```

## 2.2 Backend Settings

**Add to `config/settings.py`:**

```python
# AI Engine Configuration
AI_ENGINE_URL = os.getenv('AI_ENGINE_URL', 'http://localhost:8001')
AI_ENGINE_TIMEOUT = int(os.getenv('AI_ENGINE_TIMEOUT', '30'))
```

**Add to `.env`:**

```
AI_ENGINE_URL=http://localhost:8001
AI_ENGINE_TIMEOUT=30
```

## 2.3 Email Classification Task

Update the email processing to call AI Engine after Silver insertion.

**File: `tasks/email_tasks.py`** (update existing)

```python
import logging
from celery import shared_task
from asgiref.sync import async_to_sync

from services.ai_engine import ai_engine
from models import ThreadMessage  # Adjust import

logger = logging.getLogger(__name__)


@shared_task
def classify_pending_emails(tenant_id: str):
    """
    Classify all pending emails for a tenant.
    
    Finds emails in thread_messages with processing_status='pending'
    and party_id IS NOT NULL, calls AI Engine for classification.
    """
    from gold.models import GoldAICaseContext  # Adjust import
    
    # Get pending emails with linked parties
    pending_emails = ThreadMessage.objects.filter(
        tenant_id=tenant_id,
        processing_status='pending',
        party_id__isnull=False,
        is_inbound=True
    ).select_related('party')[:50]  # Batch of 50
    
    logger.info(f"Found {len(pending_emails)} pending emails to classify")
    
    for email in pending_emails:
        try:
            # Get context from Gold layer
            try:
                context_record = GoldAICaseContext.objects.get(
                    party_id=email.party_id,
                    is_valid=True
                )
                context = context_record.context_json
            except GoldAICaseContext.DoesNotExist:
                # Build minimal context if Gold not available
                context = build_minimal_context(email.party)
            
            # Build email dict
            email_data = {
                "subject": email.subject,
                "body": email.body_content,
                "from_address": email.from_address,
                "from_name": email.from_name
            }
            
            # Call AI Engine
            result = async_to_sync(ai_engine.classify_email)(
                email=email_data,
                context=context
            )
            
            # Update thread_message with classification
            email.classification = result["classification"]
            email.classification_confidence = result["confidence"]
            email.processing_status = "processed"
            email.classified_at = timezone.now()
            email.save()
            
            # Handle classification result
            handle_classification_result(email, result)
            
            logger.info(f"Classified email {email.id}: {result['classification']}")
            
        except Exception as e:
            logger.error(f"Failed to classify email {email.id}: {e}")
            email.processing_status = "failed"
            email.processing_error = str(e)
            email.save()


def handle_classification_result(email, result):
    """
    Handle the classification result — update case state, create records.
    """
    classification = result["classification"]
    extracted = result.get("extracted_data", {})
    
    if classification == "PROMISE":
        # Create promise record
        from models import PromiseHistory
        PromiseHistory.objects.create(
            tenant_id=email.tenant_id,
            party_id=email.party_id,
            promise_date=extracted.get("promise_date"),
            promise_amount=extracted.get("promise_amount"),
            source="email",
            source_message_id=email.id
        )
        # Update party state
        update_party_state(email.party_id, promise_detected=True)
    
    elif classification == "DISPUTE":
        # Create dispute record
        from models import DisputeHistory
        DisputeHistory.objects.create(
            tenant_id=email.tenant_id,
            party_id=email.party_id,
            dispute_type=extracted.get("dispute_type"),
            dispute_reason=extracted.get("dispute_reason"),
            source_message_id=email.id
        )
        # Pause the case
        update_party_state(email.party_id, active_dispute=True)
    
    elif classification == "HOSTILE":
        # Flag for review, potentially pause
        update_party_state(email.party_id, hostile_response=True)
    
    elif classification == "UNSUBSCRIBE":
        # Mark party as unsubscribed
        update_party_state(email.party_id, unsubscribe_requested=True)
    
    # Trigger Gold refresh
    from tasks.gold_tasks import refresh_gold_for_party
    refresh_gold_for_party.delay(str(email.party_id))


def build_minimal_context(party):
    """Build minimal context when Gold record not available."""
    return {
        "party": {
            "party_id": str(party.party_id),
            "customer_code": party.customer_code,
            "name": party.name,
            "currency": party.currency or "GBP"
        },
        "behavior": {
            "segment": party.segment
        },
        "obligations": [],
        "communication": None,
        "broken_promises_count": 0,
        "active_dispute": False
    }


def update_party_state(party_id, **kwargs):
    """Update party state flags."""
    from models import Party
    Party.objects.filter(party_id=party_id).update(**kwargs)
```

## 2.4 Draft Generation Endpoint

Add API endpoint for frontend to request draft generation.

**File: `views/draft_views.py`** (in Backend)

```python
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from asgiref.sync import async_to_sync

from services.ai_engine import ai_engine
from gold.models import GoldAICaseContext
from models import Draft, Party

logger = logging.getLogger(__name__)


class GenerateDraftView(APIView):
    """Generate a collection email draft for a case."""
    
    def post(self, request, party_id):
        """
        Generate draft for a party/case.
        
        Request body:
        {
            "tone": "professional",
            "objective": "follow_up",
            "custom_instructions": "Mention the upcoming deadline"
        }
        """
        try:
            # Get party
            party = Party.objects.get(party_id=party_id)
            
            # Get context from Gold
            try:
                context_record = GoldAICaseContext.objects.get(
                    party_id=party_id,
                    is_valid=True
                )
                context = context_record.context_json
            except GoldAICaseContext.DoesNotExist:
                return Response(
                    {"error": "Case context not available"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get parameters
            tone = request.data.get("tone", "professional")
            objective = request.data.get("objective")
            custom_instructions = request.data.get("custom_instructions")
            
            # Call AI Engine
            result = async_to_sync(ai_engine.generate_draft)(
                context=context,
                tone=tone,
                objective=objective,
                custom_instructions=custom_instructions
            )
            
            # Create draft record
            draft = Draft.objects.create(
                tenant_id=party.tenant_id,
                party_id=party_id,
                subject=result["subject"],
                body=result["body"],
                tone=result["tone_used"],
                status="pending_review",
                generated_by="ai"
            )
            
            return Response({
                "draft_id": str(draft.id),
                "subject": result["subject"],
                "body": result["body"],
                "tone": result["tone_used"],
                "invoices_referenced": result.get("invoices_referenced", [])
            })
            
        except Party.DoesNotExist:
            return Response(
                {"error": "Party not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Draft generation failed: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

---

# PART 3: ETL Integration

## 3.1 Gold Context Builder

Add a transformer to build `gold_ai_case_context` from Silver tables.

**File: `etl/transformers/gold_context_transformer.py`**

```python
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class GoldContextTransformer:
    """Build gold_ai_case_context JSON from Silver tables."""
    
    def __init__(self, tenant_id: str, db_connection):
        self.tenant_id = tenant_id
        self.db = db_connection
    
    def build_context(self, party_id: str) -> Dict[str, Any]:
        """
        Build complete AI context for a party.
        
        Fetches from:
        - parties
        - obligations
        - touches
        - thread_messages
        - promise_history
        - dispute_history
        - tenant_config
        """
        context = {
            "party": self._get_party_info(party_id),
            "behavior": self._get_behavior_info(party_id),
            "obligations": self._get_obligations(party_id),
            "communication": self._get_communication_summary(party_id),
            "recent_touches": self._get_recent_touches(party_id),
            "recent_responses": self._get_recent_responses(party_id),
            "promises": self._get_promises(party_id),
            "disputes": self._get_disputes(party_id),
            "case_state": None,
            "days_in_state": 0,
            "broken_promises_count": 0,
            "active_dispute": False,
            "hardship_indicated": False,
            "brand_tone": "professional",
            "touch_cap": 10,
            "touch_interval_days": 3
        }
        
        # Add case state from party
        party = context["party"]
        if party:
            context["case_state"] = party.get("case_state")
            context["broken_promises_count"] = party.get("broken_promises_count", 0)
            context["active_dispute"] = party.get("active_dispute", False)
            context["hardship_indicated"] = party.get("hardship_indicated", False)
        
        # Add tenant settings
        settings = self._get_tenant_settings()
        if settings:
            context["brand_tone"] = settings.get("brand_tone", "professional")
            context["touch_cap"] = settings.get("touch_cap", 10)
            context["touch_interval_days"] = settings.get("touch_interval_days", 3)
        
        return context
    
    def _get_party_info(self, party_id: str) -> Optional[Dict]:
        query = """
            SELECT 
                party_id, customer_code, name, country_code, currency,
                credit_limit, on_hold, case_state, broken_promises_count,
                active_dispute, hardship_indicated, segment
            FROM parties
            WHERE party_id = %s AND tenant_id = %s
        """
        result = self.db.execute(query, [party_id, self.tenant_id])
        if result:
            row = result[0]
            return {
                "party_id": str(row[0]),
                "customer_code": row[1],
                "name": row[2],
                "country_code": row[3],
                "currency": row[4] or "GBP",
                "credit_limit": float(row[5]) if row[5] else None,
                "on_hold": row[6],
                "case_state": row[7],
                "broken_promises_count": row[8] or 0,
                "active_dispute": row[9] or False,
                "hardship_indicated": row[10] or False,
                "segment": row[11]
            }
        return None
    
    def _get_behavior_info(self, party_id: str) -> Optional[Dict]:
        query = """
            SELECT 
                lifetime_value, avg_days_to_pay, on_time_rate,
                partial_payment_rate, segment
            FROM parties
            WHERE party_id = %s AND tenant_id = %s
        """
        result = self.db.execute(query, [party_id, self.tenant_id])
        if result:
            row = result[0]
            return {
                "lifetime_value": float(row[0]) if row[0] else None,
                "avg_days_to_pay": float(row[1]) if row[1] else None,
                "on_time_rate": float(row[2]) if row[2] else None,
                "partial_payment_rate": float(row[3]) if row[3] else None,
                "segment": row[4]
            }
        return None
    
    def _get_obligations(self, party_id: str, limit: int = 20) -> list:
        query = """
            SELECT 
                invoice_number, original_amount, amount_due,
                due_date, days_past_due, state
            FROM obligations
            WHERE party_id = %s AND tenant_id = %s AND state = 'open'
            ORDER BY days_past_due DESC
            LIMIT %s
        """
        results = self.db.execute(query, [party_id, self.tenant_id, limit])
        return [
            {
                "invoice_number": row[0],
                "original_amount": float(row[1]),
                "amount_due": float(row[2]),
                "due_date": row[3].isoformat() if row[3] else None,
                "days_past_due": row[4] or 0,
                "state": row[5]
            }
            for row in results
        ]
    
    def _get_communication_summary(self, party_id: str) -> Optional[Dict]:
        query = """
            SELECT 
                COUNT(*) as touch_count,
                MAX(sent_at) as last_touch_at,
                (SELECT channel FROM touches WHERE party_id = %s ORDER BY sent_at DESC LIMIT 1) as last_channel,
                (SELECT sender_level FROM touches WHERE party_id = %s ORDER BY sent_at DESC LIMIT 1) as last_level,
                (SELECT tone FROM touches WHERE party_id = %s ORDER BY sent_at DESC LIMIT 1) as last_tone
            FROM touches
            WHERE party_id = %s AND tenant_id = %s
        """
        result = self.db.execute(query, [party_id, party_id, party_id, party_id, self.tenant_id])
        if result:
            row = result[0]
            # Get last response
            response_query = """
                SELECT received_at, classification
                FROM thread_messages
                WHERE party_id = %s AND tenant_id = %s AND is_inbound = TRUE
                ORDER BY received_at DESC LIMIT 1
            """
            response = self.db.execute(response_query, [party_id, self.tenant_id])
            
            return {
                "touch_count": row[0] or 0,
                "last_touch_at": row[1].isoformat() if row[1] else None,
                "last_touch_channel": row[2],
                "last_sender_level": row[3],
                "last_tone_used": row[4],
                "last_response_at": response[0][0].isoformat() if response else None,
                "last_response_type": response[0][1] if response else None
            }
        return None
    
    def _get_recent_touches(self, party_id: str, limit: int = 5) -> list:
        query = """
            SELECT sent_at, tone, sender_level,
                   EXISTS(SELECT 1 FROM thread_messages WHERE party_id = t.party_id AND is_inbound = TRUE AND received_at > t.sent_at) as had_response
            FROM touches t
            WHERE party_id = %s AND tenant_id = %s
            ORDER BY sent_at DESC
            LIMIT %s
        """
        results = self.db.execute(query, [party_id, self.tenant_id, limit])
        return [
            {
                "sent_at": row[0].isoformat(),
                "tone": row[1],
                "sender_level": row[2],
                "had_response": row[3]
            }
            for row in results
        ]
    
    def _get_recent_responses(self, party_id: str, limit: int = 5) -> list:
        query = """
            SELECT received_at, classification, classification_confidence
            FROM thread_messages
            WHERE party_id = %s AND tenant_id = %s AND is_inbound = TRUE AND classification IS NOT NULL
            ORDER BY received_at DESC
            LIMIT %s
        """
        results = self.db.execute(query, [party_id, self.tenant_id, limit])
        return [
            {
                "received_at": row[0].isoformat(),
                "classification": row[1],
                "confidence": float(row[2]) if row[2] else None
            }
            for row in results
        ]
    
    def _get_promises(self, party_id: str) -> list:
        query = """
            SELECT promise_date, promise_amount, outcome
            FROM promise_history
            WHERE party_id = %s AND tenant_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """
        results = self.db.execute(query, [party_id, self.tenant_id])
        return [
            {
                "promise_date": row[0].isoformat() if row[0] else None,
                "promise_amount": float(row[1]) if row[1] else None,
                "outcome": row[2]
            }
            for row in results
        ]
    
    def _get_disputes(self, party_id: str) -> list:
        query = """
            SELECT dispute_type, dispute_reason, status, created_at
            FROM dispute_history
            WHERE party_id = %s AND tenant_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        """
        results = self.db.execute(query, [party_id, self.tenant_id])
        return [
            {
                "dispute_type": row[0],
                "dispute_reason": row[1],
                "status": row[2],
                "created_at": row[3].isoformat()
            }
            for row in results
        ]
    
    def _get_tenant_settings(self) -> Optional[Dict]:
        query = """
            SELECT brand_tone, touch_cap, touch_interval_days
            FROM tenant_config
            WHERE tenant_id = %s
        """
        result = self.db.execute(query, [self.tenant_id])
        if result:
            row = result[0]
            return {
                "brand_tone": row[0] or "professional",
                "touch_cap": row[1] or 10,
                "touch_interval_days": row[2] or 3
            }
        return None
    
    def refresh_context(self, party_id: str) -> bool:
        """Refresh gold_ai_case_context for a single party."""
        try:
            context = self.build_context(party_id)
            
            query = """
                INSERT INTO gold_ai_case_context (party_id, tenant_id, context_json, computed_at, is_valid)
                VALUES (%s, %s, %s, NOW(), TRUE)
                ON CONFLICT (party_id) DO UPDATE SET
                    context_json = EXCLUDED.context_json,
                    context_version = gold_ai_case_context.context_version + 1,
                    computed_at = NOW(),
                    is_valid = TRUE
            """
            self.db.execute(query, [party_id, self.tenant_id, json.dumps(context)])
            return True
        except Exception as e:
            logger.error(f"Failed to refresh context for {party_id}: {e}")
            return False
    
    def refresh_all_contexts(self) -> Dict[str, int]:
        """Refresh contexts for all parties in tenant."""
        query = "SELECT party_id FROM parties WHERE tenant_id = %s"
        results = self.db.execute(query, [self.tenant_id])
        
        stats = {"success": 0, "failed": 0}
        for row in results:
            if self.refresh_context(str(row[0])):
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        return stats
```

## 3.2 Gold Refresh Task

**File: `tasks/gold_tasks.py`** (in Backend or ETL)

```python
from celery import shared_task
from django.db import connection

from etl.transformers.gold_context_transformer import GoldContextTransformer


@shared_task
def refresh_gold_for_party(party_id: str):
    """Refresh Gold layer for a single party."""
    from models import Party
    
    party = Party.objects.get(party_id=party_id)
    tenant_id = str(party.tenant_id)
    
    transformer = GoldContextTransformer(tenant_id, connection)
    transformer.refresh_context(party_id)
    
    # Also refresh gold_case_summary and gold_activity_feed here
    # (implementation depends on your Gold layer structure)


@shared_task
def refresh_all_gold_contexts(tenant_id: str):
    """Refresh all Gold AI contexts for a tenant."""
    transformer = GoldContextTransformer(tenant_id, connection)
    stats = transformer.refresh_all_contexts()
    return stats
```

---

# PART 4: Testing

## 4.1 Test AI Engine Locally

```bash
# Terminal 1: Start AI Engine
cd solvix-ai-engine
cp .env.example .env
# Add your OPENAI_API_KEY to .env
python -m src.main

# Terminal 2: Test endpoints
curl -X POST http://localhost:8001/classify \
  -H "Content-Type: application/json" \
  -d '{
    "email": {
      "subject": "RE: Invoice 1234",
      "body": "I will pay this by Friday",
      "from_address": "john@acme.com"
    },
    "context": {
      "party": {
        "party_id": "123",
        "customer_code": "ACME001",
        "name": "Acme Ltd",
        "currency": "GBP"
      },
      "obligations": [
        {"invoice_number": "INV-1234", "amount_due": 5000, "days_past_due": 30, "original_amount": 5000, "due_date": "2024-12-01", "state": "open"}
      ],
      "broken_promises_count": 0,
      "active_dispute": false
    }
  }'
```

## 4.2 Test Full Integration

1. Start all services:
   - AI Engine: `python -m src.main` (port 8001)
   - Django: `python manage.py runserver` (port 8000)
   - Celery: `celery -A config worker -l info`
   - ngrok: `ngrok http 8000`

2. Send email to shared mailbox

3. Verify flow:
   - Email stored in Bronze
   - Email transformed to Silver thread_messages
   - AI Engine called for classification
   - thread_messages updated with classification
   - Gold layer refreshed

---

# Summary

## Repositories

| Repo | Port | Purpose |
|------|------|---------|
| solvix-ai-engine | 8001 | LLM operations |
| solvix-backend | 8000 | API, orchestration |
| solvix-etl | N/A | Celery workers |

## Data Flow

```
Email → Webhook → Bronze → Silver → AI Engine → Silver (updated) → Gold
```

## Key Files Created

**AI Engine:**
- `src/main.py` — FastAPI app
- `src/api/models/` — Pydantic models
- `src/engine/` — Classification, generation, gates
- `src/llm/client.py` — OpenAI wrapper

**Backend:**
- `services/ai_engine.py` — AI Engine client
- `tasks/email_tasks.py` — Classification task
- `views/draft_views.py` — Draft generation API

**ETL:**
- `transformers/gold_context_transformer.py` — Build Gold context
- `tasks/gold_tasks.py` — Gold refresh tasks