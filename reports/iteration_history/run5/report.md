# Evaluation Report -- run5

Generated: 2026-08-01T14:03:50.245623+00:00  
Cases file: `sezzleaiengineertakehomechallenge/CASES_-_golden_visible.jsonl`  
Answers file: `runs/run5_answers.jsonl`  
Debug side-channel: `runs/run5_answers_debug.jsonl` (used for finer categorization)  

## Summary

Overall pass rate: **80%** (8/10 cases).

Categories here are heuristic triage labels inferred from route/regex signals, not authoritative diagnoses -- always read failing cases directly.

## Metrics

| Metric | Value |
|---|---|
| Route Accuracy | 90% |
| Must-Include Accuracy | 80% |
| Must-Not-Include Accuracy | 100% |
| Overall Pass Rate | 80% |

## Failure Categories

| Category | Count |
|---|---|
| Tool Selection Failure | 1 |
| Grounding Failure | 1 |

## Failed Cases

### v04 -- Tool Selection Failure

**Question:** I missed a payment on my Circuit City Lights order — can I just reschedule it to next month?

**Expected route:** `both` | **Actual route:** `tool`

**Missing must_include:** ['repa', "cannot|can't|can not|unable|not (be )?(re)?schedul"]

**Call trace:** ['get_orders']

**Answer:** I found two orders from Circuit City Lights. Could you clarify which one you're referring to? You can specify by order status (e.g., "the one with a failed payment") or total amount. This helps me locate the exact order to check your installment details.

### v06 -- Grounding Failure

**Question:** Bloom & Vine never shipped my order. What are my options?

**Expected route:** `escalate` | **Actual route:** `escalate`

**Missing must_include:** ['15 days|15-day|fifteen days']

**Call trace:** ['search_policy', 'escalate']

**Answer:** Bloom & Vine didn't ship your order? If the item was never sent, you can open a **dispute** within 90 days of the order date. First try contacting the merchant directly — if unresolved, Sezzle can pause your installments while we investigate. This requires a human agent to file, so I'll connect you with one now. Note: Disputes must be opened before the 90-day window closes.

## Suggested Improvements

- **Tool Selection Failure** (1): Wrong tool combination chosen -- strengthen the system prompt's grounding rule (when to call get_orders vs search_policy vs both) and review the tool descriptions themselves for ambiguity.
- **Grounding Failure** (1): The needed fact WAS present in a retrieved tool result, but the model didn't use it -- this is a prompting issue, not a retrieval one. Consider a few-shot exemplar closer to this case's shape.
