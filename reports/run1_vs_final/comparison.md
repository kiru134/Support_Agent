# Comparison -- run1 vs final

Generated: 2026-08-01T15:52:40.574803+00:00

## Metric Deltas

| Metric | run1 | final | Delta |
|---|---|---|---|
| route_accuracy | 80% | 90% | +10pp |
| must_include_accuracy | 70% | 90% | +20pp |
| must_not_include_accuracy | 100% | 100% | +0pp |
| overall_pass_rate | 70% | 80% | +10pp |

## Improvements (fail -> pass)

v03, v06, v10

## Regressions (pass -> fail)

v01, v04

## Still Failing (fail -> fail)

None.

## Failure Category Shifts

| Category | run1 | final |
|---|---|---|
| Grounding Failure | 1 | 1 |
| Tool Selection Failure | 2 | 1 |

