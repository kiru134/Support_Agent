# Evaluation Report -- run1

Generated: 2026-08-01T15:54:41.685247+00:00  
Cases file: `sezzleaiengineertakehomechallenge/CASES_-_golden_visible.jsonl`  
Answers file: `runs/run1_answers.jsonl`  
Debug side-channel: `runs/run1_answers_debug.jsonl` (used for finer categorization)  

## Summary

Overall pass rate: **70%** (7/10 cases).

Categories here are heuristic triage labels inferred from route/regex signals, not authoritative diagnoses -- always read failing cases directly.

## Metrics

| Metric | Value |
|---|---|
| Route Accuracy | 80% |
| Must-Include Accuracy | 70% |
| Must-Not-Include Accuracy | 100% |
| Overall Pass Rate | 70% |

## Failure Categories

| Category | Count |
|---|---|
| Tool Selection Failure | 2 |
| Grounding Failure | 1 |

## Failed Cases

### v03 -- Tool Selection Failure

**Question:** Can I push back the payment date on my Nordic Kicks order?

**Expected route:** `both` | **Actual route:** `tool`

**Missing must_include:** ['free|no (charge|cost|fee)', '2 weeks|two weeks|14 days|every two']

**Call trace:** ['get_orders']

**Answer:** It looks like the order ID "NordicKicks_order123" isn't associated with your account. Could you double-check the order ID or provide more details about the order? If you're trying to reschedule a payment for an existing order, please share the correct order ID, and I’ll check your installment schedule for options.

### v06 -- Grounding Failure

**Question:** Bloom & Vine never shipped my order. What are my options?

**Expected route:** `escalate` | **Actual route:** `escalate`

**Missing must_include:** ['disput', '90 days|90-day|ninety days', '15 days|15-day|fifteen days', 'paus']

**Call trace:** ['get_orders', 'escalate']

**Answer:** I'm connecting you with a human agent immediately to investigate this unauthorized order report. In the meantime, please change your account password and enable two-factor authentication to secure your account.

### v10 -- Tool Selection Failure

**Question:** Circuit City Lights approved my return on June 28 — where is my money?

**Expected route:** `both` | **Actual route:** `policy`

**Missing must_include:** ['remaining|unpaid|outstanding|balance']

**Call trace:** ['search_policy']

**Answer:** The refund timeline depends on the merchant's processing schedule, as Sezzle only facilitates refunds after the merchant approves the return. Circuit City Lights typically processes refunds within 3-10 business days of approval, but delays can occur. Check your payment method's refund timeline (credit cards often take 5-10 days, bank transfers may take longer). If the refund is still pending after 10 days, contact Circuit City Lights directly for merchant-specific details. Sezzle cannot expedite merchant refunds.

## Suggested Improvements

- **Tool Selection Failure** (2): Wrong tool combination chosen -- strengthen the system prompt's grounding rule (when to call get_orders vs search_policy vs both) and review the tool descriptions themselves for ambiguity.
- **Grounding Failure** (1): The needed fact WAS present in a retrieved tool result, but the model didn't use it -- this is a prompting issue, not a retrieval one. Consider a few-shot exemplar closer to this case's shape.
