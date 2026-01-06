Solvix AI Engine Specification
1. What Solvix Does
Solvix is a draft generation engine for B2B debt collection. It does not send communications autonomously.

The workflow:

AI Engine analyses case context
AI Engine decides whether a draft is warranted
AI Engine generates draft (tone, content, CTA, recommended sender)
Draft appears in finance team's Outlook
Human reviews, edits if needed, and decides to send or discard
If sent, delivery/response events flow back for the next cycle

Humans are always in the loop. The AI recommends; humans act.


2. Design Principles
Principle
Meaning
Draft, don't send
AI generates recommendations; humans make final decisions
Relationship preservation
B2B collections should not destroy customer relationships
Context over rules
LLM reasons about full context rather than rigid rules
Batch is acceptable
2-hour processing cycles are fine for B2B collections
Audit everything
Full history of drafts generated, sent, and responses received



3. Core Concepts
3.1 What is a Case?
A case is a collection effort for one customer who has an overdue balance.

Concept
Definition
Case
One customer with one or more overdue invoices
NOT a case
Individual invoices — we don't create separate cases per invoice


Example:

Customer "Acme Ltd" has 5 overdue invoices totalling £12,000
This is ONE case, not five
Communications reference all outstanding invoices together

Case creation criteria:

Customer has net_balance > minimum_threshold (configurable)
Customer has at least one invoice where due_date < TODAY - grace_days
3.2 What is an Obligation?
An obligation is a single outstanding invoice within a case.

From Sage:

document_outstanding_value = amount still unpaid on this invoice
due_date = when payment was due
Original value minus payments and credits = outstanding value

A case contains one or more obligations. Communications list all obligations but are sent as one consolidated message.
3.3 Relationship to Sage Data
Sage Entity
Solvix Concept
Customer
Party (potential debtor)
Sales Invoice with outstanding > 0
Obligation
Receipt
Payment (reduces obligation)
Credit Note
Credit (reduces obligation)
Customer.balance
Net amount owed (pre-calculated by Sage)



4. Case Lifecycle
4.1 States
State
Meaning
ACTIVE
Normal collection — drafts being generated
PAUSED
Temporarily halted (promise tracking, dispute pending client review, manual hold)
PIF
Paid in Full — closed successfully
PLAN
Payment plan agreed — monitoring instalments
LEGAL
Referred to legal/external collection — AI stops generating drafts
WO
Written off — closed


Note: There is no BLOCKED state. Cases that shouldn't exist are filtered at creation time by gates.
4.2 State Flow
Case Created (gates passed)

         │

         ▼

      ACTIVE ◀──────────────────────────────────────────────────┐

         │                                                       │

         ├── Promise detected ─────────▶ PAUSED (promise)       │

         │                                   │                   │

         │                                   ├── Promise kept ──▶ PIF

         │                                   └── Promise broken ─┘

         │                                                       │

         ├── Dispute raised ───────────▶ PAUSED (dispute)       │

         │                                   │                   │

         │                                   ├── Invalid ────────┘

         │                                   ├── Valid, adjust ──┘ (if balance remains)

         │                                   └── Valid, cancel ──▶ WO

         │                                                       │

         ├── Manual hold ──────────────▶ PAUSED (manual)        │

         │                                   │                   │

         │                                   └── Hold lifted ────┘

         │

         ├── Payment received (full) ──▶ PIF

         │

         ├── Plan agreed ──────────────▶ PLAN

         │                                   │

         │                                   ├── Plan completed ─▶ PIF

         │                                   └── Plan failed ────┘ (or LEGAL)

         │

         ├── Legal referral approved ──▶ LEGAL

         │

         └── Write-off approved ───────▶ WO
4.3 What Triggers a Pause?
Trigger
Pause Reason
Resume When
Promise to pay detected
Waiting for promise date
Promise kept (→ PIF) or broken (→ ACTIVE)
Dispute raised
Waiting for client to resolve
Client marks resolved
Manual hold by user
User decision
User lifts hold
Insolvency mentioned
Legal implications
Client review complete


Note: The following do NOT trigger automatic pause:

Out of Office (just context for human reviewing draft)
Hardship indication (agent adapts tone, continues)
Hostile response (agent adapts, flags for attention)


5. Gates
Gates determine whether to generate a draft for a case. They are checked every processing cycle, not just at case creation.
5.1 Case Creation Gates
These prevent a case from being created:

Gate
Check
Outcome if Fails
Minimum Balance
customer.balance > minimum_threshold
No case created
Has Overdue
At least one invoice past due date + grace
No case created
Statute Bar
Oldest invoice within limitation period
No case created

5.2 Draft Generation Gates
These are checked every cycle for existing cases:

Gate
Check
Outcome if Fails
Positive Balance
customer.balance > 0
Skip draft (may have been paid)
Touch Cap
touches < max_touches
Skip draft, flag for review
Not Paused
case.state = ACTIVE
Skip draft
No Manual Hold
case.manual_hold = FALSE
Skip draft
Valid Contact
Customer has valid email
Skip draft, flag for attention
Statute Bar
Still within limitation period
Skip draft (edge case)

5.3 Configuration
Statute Limits (by jurisdiction):

Country
Period
Reference
UK (England/Wales)
6 years
Limitation Act 1980
UK (Scotland)
5 years
Prescription and Limitation Act 1973
Ireland
6 years
Statute of Limitations 1957
Germany
3 years
BGB §195
France
5 years
Civil Code Art. 2224


Touch Limits (per tenant, configurable):

Parameter
Default
Description
Max per channel
5
Before channel exhausted
Max total
12
Across all channels
Period
90 days
Rolling window
Minimum balance
£50
Below this, no case created
Grace days
14
Days after due date before case created



6. Context Model
The AI Engine receives rich context about each case. The agent reasons holistically rather than following rigid rules.
6.1 Case Context
Data Point
Source
Use
Case ID
Internal
Reference
State
Case record
Determines if draft needed
Days in current state
Calculated
Urgency
Total outstanding
Sum of obligations
Communication content
Number of invoices
Count of obligations
Communication content
Oldest invoice date
Min due date
Days overdue
Days overdue
Calculated
Urgency, tone

6.2 Obligation Context (All Invoices in Case)
For each invoice:

Data Point
Source (Sage)
Use
Invoice number
transaction.reference
Communication content
Original amount
document_value
Context
Outstanding amount
document_outstanding_value
Communication content
Due date
due_date
Overdue calculation
Days overdue
Calculated
Prioritisation
Transaction type
trader_transaction_type
Classify (goods, services, etc.)

6.3 Customer Context
Data Point
Source
Use
Name
customer.name
Communication
Country
Customer record
Jurisdiction, statute limits
Net balance
customer.balance
Gate check, content
Credit limit
customer.credit_limit
Utilisation context
On hold in Sage
customer.on_hold
Warning flag
Primary email
Contact record
Delivery
Email valid
Bounce tracking
Gate check

6.4 Historical Behaviour (Derived from Sage)
Metric
Calculation
Use
Lifetime value
SUM of all historical invoice values
Relationship tier
Relationship length
Months since first invoice
Context
Total invoices paid
COUNT of fully paid invoices
Track record
Average days to pay
AVG(payment_date - due_date)
Behaviour prediction
On-time rate
% paid on or before due date
Anomaly detection
Partial payment tendency
% of invoices paid in multiple receipts
CTA framing
Credit note frequency
Credit notes / Invoices ratio
Dispute likelihood
Last payment date
Most recent receipt
Recency signal
Payment gap
Days since last payment vs normal frequency
Early warning

6.5 Derived Flags
Flag
Criteria
Effect on AI
Anomaly
On-time rate > 80% AND this is first late payment in 12+ months
Concerned inquiry tone
Deteriorating
Average days to pay increasing over last 6 months
More attention, earlier escalation
Reliable late
Always pays, but consistently 15-30 days late
Patient, know they'll pay
Disputer
Credit note frequency > 20%
Lead with evidence
New customer
Less than 3 invoices historically
Standard approach, no history to leverage

6.6 Customer Segments
Segment
Criteria
AI Approach
Strategic
Lifetime value > £50k, on-time rate > 80%
Careful, senior sender, preserve relationship
Problematic
Lifetime value > £50k, on-time rate < 50%
Attention needed, escalate early
Standard
Medium lifetime value
Normal process
Low priority
Lifetime value < £5k, poor history
Efficient, consider write-off threshold

6.7 Communication History
Data Point
Source
Use
Total touches
Event count
Gate check, escalation
Last touch date
Most recent outbound
Timing decision
Last touch channel
Event record
Channel rotation
Last sender level
Event record
Escalation decision
Last tone used
Event record
Progression
Response received?
Event record
Adjust approach
Last response classification
NLU result
Inform next draft

6.8 Dynamic State (from Previous Responses)
State
Source
Effect
Debtor stance
NLU classification
Tone adjustment
Promise details
Extracted from response
Tracking
Broken promises count
Historical
Escalation factor
Dispute details
Extracted from response
Pause, inform client
Hardship indicated
NLU classification
Tone adjustment, offer plan
Redirect contact
Extracted from response
Update recipient
Unsubscribe request
NLU classification
Must honour

6.9 Creditor Context (Client Configuration)
Setting
Use
Urgency flag on case
Prioritise, shorter intervals
Relationship notes
Context for tone
Collection preference
Aggressive / Balanced / Preserve relationship
Sender levels (L1-L4)
Names, titles, emails
Brand tone
Formal / Friendly-professional



7. AI Agent Decisions
The AI agent makes all decisions about draft content. No rigid rules — the agent reasons from context.
7.1 Primary Decisions
Decision
Options
Generate draft?
Yes / No (wait) / Flag for review
Tone
Friendly reminder, Professional follow-up, Firm but fair, Final notice, Concerned inquiry
Primary CTA
Request payment, Request timeline, Request call, Offer payment plan
Recommended sender level
L1 (AR Clerk) to L4 (MD)
Follow-up timing
Days until next draft if no response

7.2 Content Decisions
Decision
Description
Invoice prioritisation
Which invoices to emphasise (oldest? largest? best evidenced?)
Invoice listing
How to present multiple invoices (table, list, summary)
Evidence citation
Whether to reference PO numbers, delivery confirmations
History reference
Whether to mention previous communications, promises, partial payments
Credit mention
Whether to note pending credits on account
Consequence framing
Whether to mention potential consequences (relationship impact, service suspension)
Urgency framing
How urgent to make the request sound
Subject line
Appropriate email subject

7.3 Recommendation Decisions
Decision
When to Recommend
Legal referral
Touch cap reached, 3+ broken promises, hostile refusal
Write-off
Below threshold, valid dispute, uncollectable
Human attention needed
Unclear response, edge case, sensitive situation

7.4 Tone Definitions
Tone
When to Use
Character
Friendly reminder
First contact, good history
Warm, assumes oversight
Professional follow-up
Second contact, neutral history
Businesslike, clear ask
Firm but fair
Multiple non-responses, poor history
Direct, emphasises obligation
Final notice
Last attempt before legal recommendation
Serious, states consequences
Concerned inquiry
Anomaly — good customer, unusual behaviour
Relationship-first, asks if okay

7.5 Sender Levels
Level
Typical Title
When to Use
1
AR Clerk
Initial contact, routine follow-up
2
AR Manager
After non-response to L1, medium-value accounts
3
Finance Director
After non-response to L2, high-value, disputes
4
Managing Director
Final attempt, very high value, relationship requires


Progression factors:

Non-response after 2 touches at current level → consider escalation
High-value customer → may start at L2
Strategic segment → senior attention faster
Hostile response → escalate
7.6 CTA Options
CTA
When to Use
Request payment
Standard — ask for payment by specific date
Request timeline
Need to understand their situation
Request call
Complex situation, dispute, high-value relationship
Offer payment plan
Large amount, hardship indicated, long-overdue



8. Communication Content
8.1 Structure of a Draft
A collection draft should include:

Always include:

Creditor company name
Clear statement of outstanding amount
List of overdue invoices with individual amounts
Specific payment request or CTA
Contact details for queries
Professional sign-off

Include when relevant:

"If you have recently made payment, please disregard" (configurable)
Reference to previous communication
Mention of unallocated credits
Evidence references (PO, delivery confirmation)
Promise reminder (if following up on broken promise)

Never include (unless Final Notice tone):

Threats of legal action
Interest or penalty charges (unless explicitly authorised)
Absolute claims about non-payment
8.2 Multiple Invoices
When a customer has multiple overdue invoices:

Example structure:

"Our records show the following outstanding invoices:

  Invoice #1001 (due 15 Oct) — £500.00 outstanding

  Invoice #1002 (due 30 Oct) — £1,200.00 outstanding

  Invoice #1003 (due 15 Nov) — £300.00 outstanding

  Total outstanding: £2,000.00

Please arrange payment of the total amount by [date]."

Key rules:

One communication per customer, not per invoice
Show document_outstanding_value (not original value)
Order by oldest first, or by amount, or by evidence strength (agent decides)
If many invoices, may summarise with "X invoices totalling £Y"
8.3 Credits and Partial Payments
If the customer has unallocated credits or has made partial payments:

"Note: We have a credit of £150.00 on your account which will be 

applied against these invoices, leaving a net balance of £1,850.00."

"Thank you for your recent payment of £400.00. The remaining 

balance of £600.00 on invoice #1001 is now overdue."
8.4 Language Guidelines
Do
Don't
"Our records show..."
"You haven't paid..."
"Please arrange payment"
"You must pay immediately"
"We'd welcome a call to discuss"
"Call us or face consequences"
"If you've recently paid, please disregard"
(omit this — absolute claim)



9. Response Classification
When a debtor responds, the AI classifies the response to update case state and inform the next draft.
9.1 Response Types
Type
Indicators
Action
COOPERATIVE
"I'll pay", "sorry for delay"
Note stance, soften next draft
PROMISE_TO_PAY
Specific date and/or amount
Pause case, track promise
DISPUTE
"incorrect", "never received", "wrong amount"
Pause case, notify client
HARDSHIP
"cash flow problems", "struggling"
Adapt tone, offer plan option
REDIRECT
"contact my accountant"
Update contact, continue
HOSTILE
Aggressive language, refusal
Flag for attention, adapt approach
ALREADY_PAID
"paid this already"
Urgent verification needed
REQUEST_INFO
"send invoice copy"
Queue fulfilment, continue
PLAN_REQUEST
"can we pay in instalments"
Notify client for approval
OUT_OF_OFFICE
Auto-reply
Note return date as context
UNSUBSCRIBE
"stop contacting me"
Pause, notify client (must honour)
INSOLVENCY
"in administration", "liquidation"
Pause, urgent client notification
UNCLEAR
Cannot confidently classify
Flag for human review

9.2 Multi-Intent Priority
When a response contains multiple intents:

INSOLVENCY — Legal implications, immediate pause
DISPUTE — Pause, investigate
ALREADY_PAID — Urgent verification
UNSUBSCRIBE — Must honour
HOSTILE — Flag, but may continue carefully
PROMISE_TO_PAY — Track
HARDSHIP — Adapt approach (don't auto-pause)
PLAN_REQUEST — Route for approval
REDIRECT — Update contact
REQUEST_INFO — Fulfil
OUT_OF_OFFICE — Note as context
COOPERATIVE — Positive signal
9.3 Hardship Handling
When hardship is detected, the agent:

Adjusts tone to empathetic
Makes "offer payment plan" a primary CTA option
Extends follow-up intervals
Avoids pressure language
Does NOT automatically pause

Only pause for hardship if:

Debtor explicitly mentions insolvency/administration (legal implications)
Agent is genuinely uncertain how to proceed
9.4 Out of Office Handling
OOO is not an automatic pause trigger.

When OOO detected:

Extract return date if present
Include in case context
Human reviewing draft can see "Debtor OOO until [date]"
Human decides whether to send now or wait


10. Promise Tracking
10.1 Promise Detection
When a response contains a promise to pay:

Field
Required?
Notes
Promise amount
No
Default to full if unspecified
Promise date
Yes
Must be specific
Method
No
BACS, cheque, etc.


Vague promises ("soon", "ASAP") → Generate draft requesting specific date.
10.2 Promise Lifecycle
Specific promise detected

         │

         ▼

    Case → PAUSED

    Promise date recorded

         │

         │ Check daily after promise_date

         │

         ├── Payment ≥ promised ────▶ PIF (or continue if balance remains)

         │

         ├── Payment < promised ────▶ Generate "partial received" draft

         │

         └── No payment (+2 days) ──▶ Case → ACTIVE, "promise broken" draft
10.3 Broken Promise Escalation
Broken Promises
Next Draft Approach
1st
Disappointed but understanding, request new commitment
2nd
Firm, require concrete plan
3rd+
Final notice tone, legal referral recommended



11. Dispute Handling
11.1 Dispute Types
Type
Description
GOODS_NOT_RECEIVED
Claims non-delivery
GOODS_DEFECTIVE
Quality issue
WRONG_AMOUNT
Invoice amount incorrect
WRONG_INVOICE
Not their invoice
ALREADY_PAID
Claims payment made
CONTRACTUAL
Terms dispute
OTHER
Unclassified

11.2 Dispute Flow
Dispute detected

      │

      ▼

 Case → PAUSED

 Client notified (type, details, debtor quote)

      │

      │ Client investigates

      │

      ├── "Invalid" ─────────▶ Case → ACTIVE

      │                        Next draft reasserts with evidence

      │

      ├── "Valid, adjust" ───▶ Amount reduced

      │                        Case → ACTIVE if balance > 0, else WO

      │

      └── "Valid, cancel" ───▶ Case → WO

Client decides validity. Solvix notifies and waits.


12. Payment Plans
12.1 Plan Creation
Debtor requests plan (detected) OR client initiates
Client approves plan terms
Case → PLAN state
AI generates reminder drafts before instalments
12.2 Plan Monitoring
Event
AI Action
3 days before instalment
Generate reminder draft
Paid on time
Generate thank you, confirm next date
2 days overdue
Generate "missed payment" draft
7+ days overdue
Generate "plan at risk" draft
14+ days overdue
Plan failed

12.3 Plan Outcomes
All instalments paid → PIF
Plan failed → Client decides: resume ACTIVE or LEGAL


13. Flags and Recommendations
The AI sets flags that surface in the dashboard for human action.
13.1 Flag Types
Flag
Meaning
Triggered By
LEGAL_RECOMMENDED
AI suggests legal referral
Touch cap, 3+ broken promises, hostile refusal
WRITE_OFF_RECOMMENDED
AI suggests write-off
Below threshold, valid dispute
URGENT_VERIFICATION
Payment claim needs checking
ALREADY_PAID response
DISPUTE_PENDING
Awaiting client decision
DISPUTE response
INSOLVENCY_DETECTED
Legal review needed
Insolvency mentioned
NO_VALID_CONTACT
Cannot reach debtor
All emails bounced
ATTENTION_NEEDED
Human should review
Hostile, unclear, edge case

13.2 User Actions Flow
When a user acts on a recommendation:

Dashboard shows flag (e.g., LEGAL_RECOMMENDED)

         │

         ▼

User clicks "Approve Legal Referral"

         │

         ▼

Event written to Bronze: {

  action: "legal_referral_approved",

  case_id: "...",

  user_id: "...",

  timestamp: "..."

}

         │

         ▼

Next ETL cycle: Bronze → Silver

Case state updated to LEGAL

         │

         ▼

RDS cache refreshed (daily)

Dashboard reflects new state

For immediate feedback: UI can optimistically update while event processes.


14. Terminal States
14.1 Paid in Full (PIF)
Triggered when:

Payment clears outstanding balance
Client marks as paid

Action:

Case closed
Optional: Generate thank you draft (if configured)
14.2 Legal Referral (LEGAL)
Triggered when:

User approves LEGAL_RECOMMENDED flag
User manually refers case

Action:

AI stops generating drafts
Case data exportable for external collection
14.3 Write-Off (WO)
Triggered when:

User approves WRITE_OFF_RECOMMENDED flag
Valid dispute cancels debt
User manually writes off

Action:

Case closed
Client notified if system-initiated


15. Special Scenarios
15.1 Payment Race Condition
Problem: Debtor pays but Sage sync hasn't captured it. Draft references unpaid debt.

Mitigations:

Phrasing: "Our records as of [date] show..." not "You haven't paid"
Include: "If you have recently made payment, please disregard"
ALREADY_PAID response triggers urgent verification
15.2 Contact Redirect
Debtor says "speak to my accountant at X."

Action:

Add new contact to case
Next draft goes to new contact
Original may be CC'd (client preference)
15.3 Bounced Emails
Bounce does NOT count as touch
Email marked invalid
Client notified to provide alternative
Case flagged if no valid contact
15.4 Already Paid Response
High priority — relationship risk.

Pause draft generation immediately
Notify client urgently
If confirmed: Generate apology draft
If not found: Polite request for payment reference


16. Metrics
16.1 Operational
Metric
Measures
Drafts generated per cycle
AI throughput
Drafts sent vs discarded
Human acceptance
Gate block rate
Data quality
Classification confidence
NLU quality

16.2 Collection Performance
Metric
Measures
Collection rate
£ collected / £ outstanding
Days to resolution
Case creation → terminal state
Touch efficiency
Cases resolved / touches
Promise fulfilment rate
Kept / made

16.3 Quality
Metric
Concern Threshold
Hostile response rate
> 5%
Dispute rate
> 10%
False positive rate (already paid)
> 2%
Unsubscribe rate
> 1%



17. Configuration (Per Tenant)
Setting
Description
Example
Minimum collection amount
Below this, no case created
£50
Grace days
Days after due date before case created
14
Statute bar country
Which limitation period
GB
Touch limits
Max per channel, max total, period
5 / 12 / 90 days
Sender levels
Names, titles, emails for L1-L4
—
Legal threshold
Minimum for legal referral
£1,000
Write-off threshold
Maximum for write-off recommendation
£50
Include "if paid ignore"
Whether to include disclaimer
Yes/No
Thank you on payment
Generate thank you draft
Yes/No
Brand tone
Communication style
Formal / Friendly-professional
Collection preference
Approach
Aggressive / Balanced / Preserve relationship



18. What Solvix Does NOT Do
Not Solvix's Job
Why
Send emails automatically
Human always reviews and sends
Approve payment plans
Client decision
Decide dispute validity
Client decision
Decide write-off
Client decision (on recommendation)
Decide legal referral
Client decision (on recommendation)
Access external credit data
Future enhancement
Check Companies House
Future enhancement (MVP: reactive via responses)



19. Summary
The AI Agent's Role:

Monitor all active cases every processing cycle
Check gates to determine which cases can have drafts generated
Analyse full context including history and behaviour patterns
Decide whether to generate a draft, and if so:
Tone, CTA, sender level
Invoice prioritisation and presentation
Evidence and history references
Subject line and framing
Follow-up timing
Generate the draft email content
Push drafts to Outlook for human review
Process responses to update case state
Flag cases needing human decisions

The Human Finance Team's Role:

Review drafts in Outlook
Edit if needed
Send or discard
Resolve disputes (valid/invalid)
Approve payment plans
Approve/dismiss legal referral recommendations
Approve/dismiss write-off recommendations

Division of Labour:

AI Decides
Human Decides
What to say
Whether to send
How to say it
Dispute outcomes
When to follow up
Plan approval
When to recommend escalation
Actual escalation
Tone and framing
Final content (can edit)


This keeps humans in control while automating the cognitive load of crafting appropriate, context-aware collection communications.



