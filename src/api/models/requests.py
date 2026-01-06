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
