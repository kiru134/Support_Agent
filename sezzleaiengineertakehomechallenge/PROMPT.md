# Take-Home: Sezzle Support Agent

**Time budget: ~2 hours.** We respect your time — stop at the budget and write down
what you'd do next. An honest "unfinished" note is graded positively.

**AI tooling: expected.** Use Claude, Cursor, Copilot — whatever you like, including
for scaffolding. We deliberately give you **no starter code**: what you choose to
build, what you delegate to your AI, and what you ask it for are all part of what
we're evaluating. Log your prompts in `PROMPTS.md`.

## The problem

Sezzle shoppers contact support with questions like *"When is my next payment?"*,
*"Can I move my payment date?"*, and *"The merchant never shipped my order."* Build
an **LLM-powered assistant** that answers what it can, looks up what it must, and
escalates what it shouldn't touch.

## ⚠️ The LLM is the assignment

This challenge evaluates how you **engineer with a language model** — how you give
it capability, constrain it, keep it from inventing facts, and evaluate its
behavior. **A solution with no working LLM in the pipeline does not meet the brief**,
however clean the code. Deterministic logic *around* the model (pre-filters,
authorization, output validation) is welcome engineering; deterministic
routing-and-answering *instead of* the model is not.

Any provider works — Anthropic, OpenAI, or a local model via Ollama. `llm.py` in
this kit is an **optional** minimal client (chat + tool calling for all three); use
it, replace it, or ignore it. The whole eval costs cents on the cheapest paid tiers.
If you truly can't access any model, email the hiring manager before starting.

## What's provided (data only — the design is yours)

- `data/policies/` — 12 markdown docs of Sezzle shopper policy.
- `data/orders.json` — accounts + orders with installment schedules; the file's
  `today` field is the frozen "current date". (`data/mock_orders_api.py` serves the
  same data over HTTP if you'd rather integrate that way.)
- `cases/golden_visible.jsonl` — 10 labeled test cases: `question`, `user_id`,
  `expected_route` (`policy` | `tool` | `both` | `escalate`), and `must_include` /
  `must_not_include` regex checks. Use them however you see fit; we additionally
  grade against a **hidden set** in the same format, so build for the problem, not
  the ten cases.

## The one contract

So we can run our hidden set against your agent, include a `run_cases.py` that
reads a JSONL of `{id, question, user_id}` and writes `answers.jsonl` of
`{id, route, answer}`:

```
python3 run_cases.py <cases.jsonl> <answers.jsonl>
```

Everything else — architecture, files, harness, how routing works — is your call.
That's the point.

## Design constraint (address it in a decision record)

Assume production reality: **100k questions/day, an inference budget of ~$50/day,
p95 latency ≤ 3 seconds.** You won't hit these in a take-home — but your design
should have an answer, and at least one of your decision records (below) must state
what you'd trade to meet them.

## Deliverables

1. **Your code** + the `run_cases.py` contract above.
2. **`DECISIONS.md` — exactly 3 decision records**, each ≤ ~10 lines:
   *the decision · the options you considered · why this one · what evidence would
   change your mind.* Pick the three decisions you'd most want to defend in the
   follow-up interview (e.g., loop shape, where guardrails live, retrieval
   approach, how you handle model uncertainty, the cost/latency constraint).
3. **Iteration evidence**: your **first** full run over the visible cases and your
   **final** run (transcripts or answers files for both), plus a short note: what
   the first run got wrong, what you changed, and why. A submission with a single
   run and no measured iteration is missing its most important artifact — with AI
   tools writing the boilerplate, the iteration loop *is* the exercise.
4. **`PROMPTS.md`** — the prompts you used to build (including scaffolding asks)
   and the prompts inside your system.
5. **`README.md`** — half a page: how to run it, and what's honestly unfinished.

## Level expectations

- **AI Eng I:** working LLM pipeline, grounded answers on the common cases, one
  real iteration documented.
- **AI Eng II:** the above + guardrails that survive hostile input (order IDs that
  aren't yours or don't exist, fee-waiver demands, instructions to ignore its
  rules) + decision records that weigh real alternatives.
- **Senior:** the above + the cost/latency ADR reads like it's been lived, and the
  iteration note shows failure *taxonomy*, not just a fix.

## What we grade (in order of weight)

1. **Design decisions** — the quality of the options you considered and the
   honesty of "what would change my mind."
2. **The iteration loop** — measured behavior → diagnosis → change → delta.
3. **LLM engineering** — grounding, tool/prompt design, what the model is
   *structurally* prevented from doing vs. merely told not to.
4. Escalation & authorization judgment.
5. How you directed your AI tools.

We do **not** grade scaffolding quality, provider choice, or lines of code.
