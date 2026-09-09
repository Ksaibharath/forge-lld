# Design Note — Forge

A monolith for practising Low-Level Design. This note answers the five required questions and records the domain model. It is the design of **the practice product**, not of Parking Lot itself.

## Domain (the 25%)

```
Problem 1──* Attempt 1──* Submission 1──0..1 Evaluation
                              │
                              └── Evaluation is produced by an Evaluator
```

- **Problem** — identity, statement, constraints, *considerations* (what a strong answer discusses), and a **rubric** (checkable signals). Adding a problem is data, not a new code path.
- **Attempt** — one sitting on one problem. Status: `in_progress` → `evaluating` → `evaluated` | `evaluation_failed`.
- **Submission** — the learner artifact: `design_notes`, `class_outline`, `code`. An attempt may be resubmitted.
- **Evaluation** — dimensional scores, findings, strengths, improvements, narrative, plus which evaluator produced which part.
- **Evaluator** (interface) — `evaluate(problem, submission) -> Evaluation`.
  - `DeterministicEvaluator` — AST + keyword rubric. Always runs.
  - `LLMEvaluator` — qualitative critique. Optional; skipped if no API key.
  - `CompositeEvaluator` — deterministic first, critique second, merge.

Repositories sit behind a narrow interface (`AttemptRepository`) so SQLite can become something else later without touching routes.

---

## Q1. What does a learner need to give for a meaningful LLD attempt?

An LLD interview is not “paste a repo.” The useful minimum is the same things a human interviewer looks at:

| Artifact | Why it is required / optional |
|---|---|
| **Design notes** (required) | Assumptions, core types, relationships, public APIs, what you would say out loud. This is where trade-offs live. |
| **Class outline** (optional) | A compact list of classes and methods if they are not ready to write code. Lets us check modelling without a parser. |
| **Code** (optional) | Python that we can AST-parse. Proves the design is implementable. Not required for a first pass. |

We deliberately do **not** require diagrams in v1. Diagrams are a *format*, not a *signal*. The signal is types, responsibilities, and extension points — all of which can be written. A `SubmissionParser` protocol means a diagram format can be added later (see Q4).

What we do **not** ask for: scale numbers, Kafka, Kubernetes. Wrong interview.

---

## Q2. What makes feedback useful when many designs are valid?

Useful feedback is **diagnostic and conditional**, not a grade stamp.

- Talk about *what the design will struggle with* (“a new spot type requires editing `VEHICLE_TO_SPOT` and the fee `switch`”) rather than “wrong, here is the official class list.”
- Separate **coverage** (“you never mentioned a Ticket”) from **taste** (“Strategy for pricing is justified because rates change independently of allocation”).
- Always return **strengths**. A valid-but-simple design should not be punished for not being a pattern zoo.
- Score **dimensions** (requirements, modelling, SOLID/patterns, extensibility, trade-off awareness), not a single pass/fail.

The product copy in the UI says this out loud so learners do not treat 72/100 as “WA.”

---

## Q3. Deterministic vs LLM

| Deterministic (rules) | LLM / critique |
|---|---|
| Expected entities present in notes or AST | Whether responsibilities are in the right objects |
| `ABC` / Protocol / enum / custom errors exist | Whether a pattern is *justified* or cargo-culted |
| Named APIs (`check_in`, `insert_coin`) | Trade-off quality of the prose |
| God-class heuristic (method concentration) | What to try on the next iteration |
| Rubric keyword hits (ticket, occupancy, state) | Interviewer-style narrative |

Rules are cheap, explainable, and stable — they answer “did you even model X?” They cannot answer “is this a good place for State?” That is the LLM’s job, grounded in the problem’s `considerations` and the deterministic findings so it does not hallucinate classes the learner never wrote.

If no API key is configured, a **rubric-backed narrative builder** fills the critique slot so the product still works offline. Same interface, different implementation.

---

## Q4. How do we add a problem, an evaluator, or a new submission format?

- **New problem:** append a `ProblemSpec` in `catalog.py` (statement + considerations + rubric signals). No evaluator changes.
- **New evaluator:** implement `Evaluator.evaluate(...)`, register it in `CompositeEvaluator`. Routes never import a concrete class.
- **New submission format** (e.g. PlantUML, JSON class diagram): add a `SignalExtractor` that returns the same `DesignSignals` (class names, methods, interfaces, notes text). Evaluators consume signals, not raw strings.

```
Submission  →  SignalExtractor  →  DesignSignals  →  Evaluator
                  ├─ TextExtractor
                  ├─ PythonAstExtractor
                  └─ (later) DiagramExtractor
```

That is the open/closed line. We did not build a plugin framework; we built a small interface where it pays rent.

---

## Q5. What if AI evaluation is slow or fails?

Keep it boring.

1. Attempt status becomes `evaluating`.
2. Deterministic evaluation always runs in-process (milliseconds).
3. LLM is called with a short timeout. On missing key, timeout, or HTTP error: store what we have, set `ai_status = skipped | failed`, attempt status `evaluated` if rules succeeded or `evaluation_failed` if even rules blew up.
4. UI shows findings immediately, an honest “AI critique unavailable” banner, and **Retry critique**.
5. No message queue, no worker pool, no Kubernetes. Retry is `POST /submissions/{id}/retry`.

---

## API (enough to run the flow)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/problems` | List |
| GET | `/api/problems/{id}` | Statement + requirements (no reference solution) |
| POST | `/api/attempts` | Start an attempt |
| GET | `/api/attempts/{id}` | Attempt + submissions + evaluations |
| POST | `/api/attempts/{id}/submissions` | Submit notes/code, evaluate |
| POST | `/api/submissions/{id}/retry` | Re-run critique |
| GET | `/api/history` | Past attempts |

One implicit local learner. Auth is out of scope.

## What we refused to build

Multi-service split, diagram canvas, real-time collab, LLM streaming infra, user accounts. Those would raise implementation theatre and lower design clarity — the thing this assignment actually grades.
