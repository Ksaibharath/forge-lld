# Forge

A practice bench for **low-level design** interviews — Parking Lot, Vending Machine, Elevator — with diagnostic feedback instead of a hidden unit-test suite.

This is a **monolith on purpose**. The interesting design is the domain (`Problem` → `Attempt` → `Submission` → `Evaluator`), not the number of processes.

```
Learner  →  notes / outline / optional Python
         →  SignalExtractor
         →  DeterministicEvaluator  (+ LLMEvaluator if a key exists)
         →  dimensional scores, findings, interviewer notes, history
```

Further write-up: [research](docs/RESEARCH.md) · [design note (5 questions)](docs/DESIGN.md)

---

## Run

```bash
cd forge
pip install -r requirements.txt
PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open the UI, pick a problem, write the talk track (and optional code), submit.

| Env | Effect |
|---|---|
| *(none)* | Mechanical rubric + interviewer-style notes. Product still works. |
| `OPENAI_API_KEY` | Qualitative critique merged 40/60 with the rules. |
| `OPENAI_MODEL` | Defaults to `gpt-4o-mini`. |

If AI is slow or missing: findings still land, banner says `skipped` / `failed`, **Retry critique** hits `POST /api/submissions/{id}/retry`. No queue.

```bash
PYTHONPATH=. pytest -q
```

---

## Architecture

Single FastAPI process serves the SPA and the JSON API. SQLite holds attempts. Evaluation runs **in-process** on submit.

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (frontend/)                                        │
│  hash router:  /  problems/:id  attempts/:id  history       │
└──────────────────────────┬──────────────────────────────────┘
                           │  REST
┌──────────────────────────▼──────────────────────────────────┐
│  backend/main.py          routes, no scoring logic          │
│  backend/service.py       attempt lifecycle                 │
│  backend/store.py         AttemptRepository (SQLite)        │
│  backend/catalog.py       ProblemSpec data                  │
│  backend/evaluators/      Evaluator interface               │
│  backend/signals.py       notes + AST → DesignSignals       │
└─────────────────────────────────────────────────────────────┘
                           │
                    data/forge.db
```

Layers do not skip. Routes never import a concrete evaluator. Evaluators never touch SQLite. Catalog is data, not code paths.

### Why this shape

| Temptation | What we did instead |
|---|---|
| Microservices / workers | One process. LLD of the *product* is the assignment, not k8s. |
| Grade by running hidden tests | LLD has many valid designs. Feedback is diagnostic. |
| LLM-only critique | Rules are explainable (“you never named Ticket”). LLM is optional taste. |
| Diagram editor in v1 | Diagrams are a format. The signal is types + APIs + trade-offs. |

---

## Domain

```
Problem 1──* Attempt 1──* Submission 1──0..1 Evaluation
                              ▲
                              │ produced by
                         Evaluator
                    ┌─────────┼─────────┐
                    │         │         │
              Deterministic  LLM    Composite
```

| Type | Responsibility |
|---|---|
| **Problem** | Statement, constraints, *considerations*, rubric signals. Adding a problem is a new `ProblemSpec`. |
| **Attempt** | One sitting. `in_progress` → `evaluating` → `evaluated` \| `evaluation_failed`. |
| **Submission** | `design_notes` + `class_outline` + `code`. Resubmit on the same attempt. |
| **Evaluation** | Overall score, 5 dimensions, findings, strengths, next moves, narrative, `ai_status`. |
| **Evaluator** | `evaluate(problem, submission) -> Evaluation`. |

Statuses are boring on purpose: if critique fails, the attempt is still saved.

---

## Request flow

```
POST /api/attempts                     { problem_id }
        │
        ▼
POST /api/attempts/{id}/submissions    { design_notes, class_outline, code }
        │
        ▼
ForgeService.submit
        │  status = evaluating
        ├─ CombinedExtractor  → DesignSignals
        ├─ DeterministicEvaluator   always
        ├─ LLMEvaluator             skip / timeout / fail isolated
        ├─ CompositeEvaluator       merge (rules 60% + LLM 40%)
        └─ persist Evaluation
        │  status = evaluated | evaluation_failed
        ▼
GET  /api/attempts/{id}
GET  /api/history
POST /api/submissions/{id}/retry       re-run critique only
```

Empty body is `400`. Unknown ids are `404`. The UI polls nothing — submit is synchronous; retry is explicit.

---

## Evaluation pipeline

Submissions are **not** scored as raw strings. They are reduced to one DTO so a future PlantUML extractor does not rewrite graders.

```
Submission
    design_notes
    class_outline
    code
        │
        ▼
SignalExtractor          CombinedExtractor today
        │                (later: DiagramExtractor)
        ▼
DesignSignals
    class names, bases, methods
    ABC / Enum / abstractmethod
    exception types
    parse error?
    full text blob
        │
        ├──────────────► DeterministicEvaluator
        │                  entity hits, rubric keywords,
        │                  god-class heuristic, trade-off phrases
        │
        └──────────────► LLMEvaluator  (optional)
                           grounded in considerations + what they wrote
                           JSON dimensions / strengths / gaps
```

**Deterministic (always).** Did they model Ticket? Name an occupancy query? Extract pricing? Parse Python? Mention a trade-off? Findings are pass / warn / fail / info with a sentence an interviewer could say.

**LLM (optional).** Is Strategy *justified*, or cargo-cult? What breaks when a second floor appears? Prompt forbids inventing classes they never wrote and forbids binary right/wrong.

**Composite.** Mechanical findings always survive. If the model is down, `ai_status=failed` and Retry is enough.

Dimensions (0–10): requirements coverage · object modelling · SOLID / patterns · extensibility · trade-off awareness. Overall is not a LeetCode WA.

---

## Extensibility (open/closed line)

| Change | What you touch |
|---|---|
| New problem | Append a `ProblemSpec` in `backend/catalog.py`. |
| New evaluator (tests, embeddings, …) | Implement `Evaluator`, register on `CompositeEvaluator`. Routes stay put. |
| New submission format (diagrams) | New `SignalExtractor` → same `DesignSignals`. |
| New store | Implement the same methods as `AttemptRepository`. |

That is the whole plugin story. No framework.

---

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness |
| `GET` | `/api/problems` | Cards |
| `GET` | `/api/problems/{id}` | Statement — **no** gold solution |
| `GET` | `/api/problems/{id}/sample` | Weak starter text for demos |
| `POST` | `/api/attempts` | Start a sitting |
| `GET` | `/api/attempts/{id}` | Attempt + submissions + evaluations |
| `POST` | `/api/attempts/{id}/submissions` | Submit and evaluate |
| `POST` | `/api/submissions/{id}/retry` | Re-run critique |
| `GET` | `/api/history` | Past sittings |

One implicit local learner. Auth is out of scope.

---

## Layout

```
forge/
├── README.md
├── docs/
│   ├── RESEARCH.md          why LLD is hard to self-evaluate
│   └── DESIGN.md            five required questions
├── frontend/                vanilla SPA (no build)
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── backend/
│   ├── main.py              HTTP
│   ├── service.py           lifecycle
│   ├── store.py             SQLite
│   ├── models.py            domain dataclasses
│   ├── catalog.py           three ProblemSpecs
│   ├── signals.py           extractors
│   ├── evaluators/
│   │   ├── base.py          Protocol
│   │   ├── deterministic.py
│   │   ├── llm.py
│   │   └── composite.py
│   └── reference/           working Parking Lot & Vending Machine
├── tests/
└── data/forge.db            created at runtime
```

Frontend is hash-routed on purpose: FastAPI serves `/` and `/static/*`; the bench does not need a bundler.

---

## Out of scope (deliberate)

User accounts, diagram canvas, message queues, Kubernetes, sharding, running untrusted code in a sandbox. Those would raise implementation theatre and hide the domain model — the thing this assignment actually grades.
