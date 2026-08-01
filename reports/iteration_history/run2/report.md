# Evaluation Report -- run2

Generated: 2026-08-01T13:32:21.366954+00:00  
Cases file: `sezzleaiengineertakehomechallenge/CASES_-_golden_visible.jsonl`  
Answers file: `runs/run2_answers.jsonl`  
Debug side-channel: `runs/run2_answers_debug.jsonl` (used for finer categorization)  

## Summary

Overall pass rate: **60%** (6/10 cases).

Categories here are heuristic triage labels inferred from route/regex signals, not authoritative diagnoses -- always read failing cases directly.

## Metrics

| Metric | Value |
|---|---|
| Route Accuracy | 70% |
| Must-Include Accuracy | 60% |
| Must-Not-Include Accuracy | 100% |
| Overall Pass Rate | 60% |

## Failure Categories

| Category | Count |
|---|---|
| Tool Selection Failure | 3 |
| Retrieval Failure | 1 |

## Failed Cases

### v03 -- Tool Selection Failure

**Question:** Can I push back the payment date on my Nordic Kicks order?

**Expected route:** `both` | **Actual route:** `tool`

**Missing must_include:** ['2 weeks|two weeks|14 days|every two']

**Call trace:** ['get_orders', 'get_orders']

**Answer:** Your Nordic Kicks order (ord_3006) has an upcoming installment due on July 11, 2026. Since this is an upcoming payment, you can reschedule it using one of your 3 remaining reschedules. Rescheduling this installment would push the new due date to the next available window (typically 1-2 business days later). There is no fee for rescheduling. Would you like to proceed with rescheduling this payment?

### v04 -- Tool Selection Failure

**Question:** I missed a payment on my Circuit City Lights order — can I just reschedule it to next month?

**Expected route:** `both` | **Actual route:** `tool`

**Missing must_include:** ["cannot|can't|can not|unable|not (be )?(re)?schedul"]

**Call trace:** ['get_orders', 'get_orders']

**Answer:** I checked your orders and found a Circuit City Lights order (ord_3016) with a failed installment. Per our policy, failed installments must be repaid rather than rescheduled. You'll need to repay the $136.97 unpaid balance for installment 2 immediately. 

The next upcoming installment (installment 3, due July 24) can be rescheduled using one of your 3 remaining reschedule slots. Rescheduling this installment would push it to the next month, but you'll still need to repay the full $45.66 amount. 

Would you like help rescheduling the next installment?

### v06 -- Retrieval Failure

**Question:** Bloom & Vine never shipped my order. What are my options?

**Expected route:** `escalate` | **Actual route:** `escalate`

**Missing must_include:** ['90 days|90-day|ninety days', '15 days|15-day|fifteen days']

**Call trace:** ['search_policy', 'escalate']

**Answer:** I'm connecting you with a human agent to file a dispute for the unshipped order from Bloom & Vine. Per our policy, disputes for "item not received" must be handled directly by our team to initiate the merchant review process. Your installments will be paused during this investigation, and you'll need to provide order details to proceed.

### v10 -- Tool Selection Failure

**Question:** Circuit City Lights approved my return on June 28 — where is my money?

**Expected route:** `both` | **Actual route:** `tool`

**Missing must_include:** ['remaining|unpaid|outstanding|balance', '3', '\\b10 business days|3.10 business|\\b10 days']

**Call trace:** ['get_orders']

**Answer:** I cannot locate an order with the name "Circuit City Lights" in your account. Could you please share the exact order number from your confirmation email or account dashboard? This will help me check the status of your return and refund processing.

## Suggested Improvements

- **Tool Selection Failure** (3): Wrong tool combination chosen -- strengthen the system prompt's grounding rule (when to call get_orders vs search_policy vs both) and review the tool descriptions themselves for ambiguity.
- **Retrieval Failure** (1): The needed fact exists in some chunk of the corpus but wasn't retrieved for this query -- check retrieval.py's synonym map for a lexical gap between the question's phrasing and the policy doc's wording, or inspect hybrid search's fused ranking for this query.
