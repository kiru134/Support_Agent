# Evaluation Report -- run6

Generated: 2026-08-01T14:27:23.836926+00:00  
Cases file: `sezzleaiengineertakehomechallenge/CASES_-_golden_visible.jsonl`  
Answers file: `runs/run6_answers.jsonl`  
Debug side-channel: `runs/run6_answers_debug.jsonl` (used for finer categorization)  

## Summary

Overall pass rate: **80%** (8/10 cases).

Categories here are heuristic triage labels inferred from route/regex signals, not authoritative diagnoses -- always read failing cases directly.

## Metrics

| Metric | Value |
|---|---|
| Route Accuracy | 100% |
| Must-Include Accuracy | 80% |
| Must-Not-Include Accuracy | 100% |
| Overall Pass Rate | 80% |

## Failure Categories

| Category | Count |
|---|---|
| Grounding Failure | 2 |

## Failed Cases

### v03 -- Grounding Failure

**Question:** Can I push back the payment date on my Nordic Kicks order?

**Expected route:** `both` | **Actual route:** `both`

**Missing must_include:** ['2 weeks|two weeks|14 days|every two']

**Call trace:** ['get_orders', 'search_policy']

**Answer:** Your Nordic Kicks order (ord_3006) has 3 reschedules remaining. You can push back the July 11 installment date by requesting a reschedule at least 24 hours in advance — the first reschedule is free, but subsequent ones cost $5 each. Rescheduling only changes the due date, not the installment amount. Note that failed installments cannot be rescheduled, only repaid.

### v10 -- Grounding Failure

**Question:** Circuit City Lights approved my return on June 28 — where is my money?

**Expected route:** `both` | **Actual route:** `both`

**Missing must_include:** ['remaining|unpaid|outstanding|balance']

**Call trace:** ['get_orders', 'search_policy']

**Answer:** Your refund of $185.19 from Circuit City Lights was issued on June 28 and is now being processed. Since all 4 installments were already paid, the full refund is being returned to your original payment method (the one used for the purchase). Refunds typically take 3–10 business days to process. If it’s been over 10 days and the refund hasn’t appeared, please share this order ID (ord_3014) with a human agent for further assistance.

## Suggested Improvements

- **Grounding Failure** (2): The needed fact WAS present in a retrieved tool result, but the model didn't use it -- this is a prompting issue, not a retrieval one. Consider a few-shot exemplar closer to this case's shape.
