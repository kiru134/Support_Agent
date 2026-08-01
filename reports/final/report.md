# Evaluation Report -- final

Generated: 2026-08-01T15:52:12.259223+00:00  
Cases file: `sezzleaiengineertakehomechallenge/CASES_-_golden_visible.jsonl`  
Answers file: `runs/final_answers.jsonl`  
Debug side-channel: `runs/final_answers_debug.jsonl` (used for finer categorization)  

## Summary

Overall pass rate: **80%** (8/10 cases).

Categories here are heuristic triage labels inferred from route/regex signals, not authoritative diagnoses -- always read failing cases directly.

## Metrics

| Metric | Value |
|---|---|
| Route Accuracy | 90% |
| Must-Include Accuracy | 90% |
| Must-Not-Include Accuracy | 100% |
| Overall Pass Rate | 80% |

## Failure Categories

| Category | Count |
|---|---|
| Tool Selection Failure | 1 |
| Grounding Failure | 1 |

## Failed Cases

### v01 -- Tool Selection Failure

**Question:** When is my next payment for my Nordic Kicks order and how much is it?

**Expected route:** `tool` | **Actual route:** `both`

**Call trace:** ['get_orders', 'search_policy']

**Answer:** Your next payment for the Nordic Kicks order is installment 4, which is due on July 11, 2026, and the amount is $118.36. This information is based on your order's record. If you need to reschedule this payment, you can do so up to 3 times, with no additional fees.

### v04 -- Grounding Failure

**Question:** I missed a payment on my Circuit City Lights order — can I just reschedule it to next month?

**Expected route:** `both` | **Actual route:** `both`

**Missing must_include:** ['repa', "cannot|can't|can not|unable|not (be )?(re)?schedul"]

**Call trace:** ['get_orders', 'search_policy']

**Answer:** I found two orders from Circuit City Lights. One has a failed payment (order ID: ord_3016, total: $182.63), and the other is active (order ID: ord_3018, total: $376.97). Please clarify which order you're referring to so I can provide accurate details about your installment and rescheduling options.

## Suggested Improvements

- **Tool Selection Failure** (1): Wrong tool combination chosen -- strengthen the system prompt's grounding rule (when to call get_orders vs search_policy vs both) and review the tool descriptions themselves for ambiguity.
- **Grounding Failure** (1): The needed fact WAS present in a retrieved tool result, but the model didn't use it -- this is a prompting issue, not a retrieval one. Consider a few-shot exemplar closer to this case's shape.
