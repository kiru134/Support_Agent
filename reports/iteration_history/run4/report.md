# Evaluation Report -- run4

Generated: 2026-08-01T13:38:42.758853+00:00  
Cases file: `sezzleaiengineertakehomechallenge/CASES_-_golden_visible.jsonl`  
Answers file: `runs/run4_answers.jsonl`  
Debug side-channel: `runs/run4_answers_debug.jsonl` (used for finer categorization)  

## Summary

Overall pass rate: **60%** (6/10 cases).

Categories here are heuristic triage labels inferred from route/regex signals, not authoritative diagnoses -- always read failing cases directly.

## Metrics

| Metric | Value |
|---|---|
| Route Accuracy | 70% |
| Must-Include Accuracy | 70% |
| Must-Not-Include Accuracy | 100% |
| Overall Pass Rate | 60% |

## Failure Categories

| Category | Count |
|---|---|
| Tool Selection Failure | 3 |
| Grounding Failure | 1 |

## Failed Cases

### v03 -- Tool Selection Failure

**Question:** Can I push back the payment date on my Nordic Kicks order?

**Expected route:** `both` | **Actual route:** `tool`

**Missing must_include:** ['2 weeks|two weeks|14 days|every two']

**Call trace:** ['get_orders']

**Answer:** Your Nordic Kicks order (ord_3006) has 3 reschedules remaining. The upcoming 4th installment ($118.36) is due July 11, 2026. You can reschedule this installment to a future date within your available reschedules, but note:  
- Rescheduling only applies to **upcoming** installments (not past-due ones)  
- No fee applies for this reschedule  
- The new date will be set for the next available payment window  

Would you like to proceed with rescheduling this installment?

### v04 -- Tool Selection Failure

**Question:** I missed a payment on my Circuit City Lights order — can I just reschedule it to next month?

**Expected route:** `both` | **Actual route:** `tool`

**Call trace:** ['get_orders', 'get_orders']

**Answer:** I checked your orders and found a Circuit City Lights order (ord_3016) with a failed installment. Per our policy, failed installments must be repaid (not rescheduled) before you can adjust future payments. You have 3 reschedules remaining for this order, but they only apply to upcoming installments, not failed ones. 

To proceed:
1. Repay the failed installment ($136.97) plus any fees (none applied here)
2. Then, you can reschedule your next upcoming payment ($45.66 due July 24) using one of your 3 remaining reschedules

Would you like help with repayment options or connecting to a support agent for rescheduling?

### v06 -- Grounding Failure

**Question:** Bloom & Vine never shipped my order. What are my options?

**Expected route:** `escalate` | **Actual route:** `escalate`

**Missing must_include:** ['90 days|90-day|ninety days', '15 days|15-day|fifteen days']

**Call trace:** ['search_policy', 'escalate']

**Answer:** I'm connecting you with a human agent to file a dispute about Bloom & Vine's unshipped order. Per policy, disputes require direct handling by our team. While we investigate, your installments are paused. A ticket (esc_1785590818_2) has been created for your case.

### v10 -- Tool Selection Failure

**Question:** Circuit City Lights approved my return on June 28 — where is my money?

**Expected route:** `both` | **Actual route:** `tool`

**Missing must_include:** ['remaining|unpaid|outstanding|balance']

**Call trace:** ['get_orders']

**Answer:** The refund for your return with Circuit City Lights was issued on June 28 and is currently in **processing**. Since all 4 installments were fully paid by June 25, the refund amount of **$185.19** (half of the original $370.39 order) is being returned to your original payment method. Refunds typically take 3–10 business days to process, so your refund should appear within this window. If it’s delayed beyond 10 days, contact Circuit City Lights directly for merchant-side updates.

## Suggested Improvements

- **Tool Selection Failure** (3): Wrong tool combination chosen -- strengthen the system prompt's grounding rule (when to call get_orders vs search_policy vs both) and review the tool descriptions themselves for ambiguity.
- **Grounding Failure** (1): The needed fact WAS present in a retrieved tool result, but the model didn't use it -- this is a prompting issue, not a retrieval one. Consider a few-shot exemplar closer to this case's shape.
