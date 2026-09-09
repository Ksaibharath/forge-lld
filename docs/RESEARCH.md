# Research Note — Why LLD is hard to self-evaluate, and the gap Forge fills

**Product:** Forge — a practice bench for Low-Level Design interviews
**Scope:** 1–2 pages. Sources reviewed: Educative / Design Gurus “Grokking” OOD courses, ByteByteGo OOD, GitHub LLD primers, LeetCode-style discussion, Codemia / LLD Mastery.

## 1. Why LLD is hard to self-evaluate

DSA has an oracle: the test case. LLD does not. “Design a parking lot” admits many valid shapes — a Strategy for pricing, a State machine for gates, a simple map of spots. Interviewers are not scoring a golden class diagram. They are scoring *how you think*:

- Did you clarify scope, or invent a distributed system?
- Are responsibilities in the right objects, or is there a god `ParkingLotManager`?
- Can the design absorb a new vehicle type or a surge-pricing rule without a rewrite?
- Can you defend a trade-off out loud?

That is why self-study fails so often. Reading a finished Parking Lot solution on GitHub produces *recognition*, not *skill*. You nod at the State pattern and still freeze when the interviewer asks “why not a flag?” There is no compiler for “this abstraction will hurt in six months,” and no unit test for “you never mentioned what happens when the lot is full.”

Three properties make LLD uniquely awkward to grade alone:

1. **Multiple valid designs.** Binary right/wrong feedback is actively misleading.
2. **The artifact is incomplete.** Interviews produce talk + a sketch + a few methods, not a repo. If a tool only accepts running code, it trains the wrong muscle.
3. **Quality lives in extension points.** The interesting signal is what happens when requirements change — something a static “solution PDF” never probes.

## 2. What existing tools actually do

| Approach | Example | What it is good at | Where it stops |
|---|---|---|---|
| Walkthrough courses | Educative / Design Gurus *Grokking the OOD Interview* | Repeatable method, UML, 20+ case studies, mock-interview scripts | You mostly *read* a solution. Assessments lean MCQ, not “critique *my* classes.” |
| Visual explainers | ByteByteGo OOD (e.g. Parking Lot) | Seeing components and HLD↔LLD connection | Passive. Weak at “now write yours and get notes.” |
| Code dumps | GitHub LLD primers, `tssovi/grokking-the-object-oriented-design-interview` | Full implementations to study after you have tried | No feedback loop. Easy to copy structure and believe you can produce it. |
| Peer threads | LeetCode Discuss, Reddit | Anecdotes, alternative designs | Unstructured, uneven, no rubric, no history of *your* attempts. |
| Practice-first HLD/OOD platforms | Codemia, LLD Mastery | Active practice, sometimes AI comments, in-browser coding | Heavier products; feedback is often generic (“add SOLID”) or solution-reveal. Costly. Hard to see *why* a check fired. |

The pattern: **content is abundant, a tight attempt → critique → retry loop is not.** Courses optimise for “here is a good design.” Platforms that auto-grade tend to either (a) treat LLD like DSA (hidden tests on running code) or (b) dump an LLM essay that cannot tell a missing interface from a missing `import`.

## 3. The gap

A learner who wants to get better this week needs:

1. A **small set of classic problems** with explicit requirements and *considerations* (not a spoiler class diagram).
2. A way to submit the **same artifacts an interview produces**: assumptions, types, public APIs, optional code.
3. Feedback that is **useful rather than correct/incorrect** — strengths, missing considerations, what would break if requirement X showed up.
4. A split between **mechanical checks** (did you introduce a type for Spot? an interface for pricing?) and **qualitative critique** (is Strategy justified here?).
5. **History**, so they can see whether the second Parking Lot attempt actually improved.

That loop is what Forge is for. It is not a course, not a UML drawing tool, and not a Kubernetes exercise. It is a bench: pick a problem, design it, get a structured critique, try again.

## 4. Product direction (MVP)

- **In:** 3 problems (Parking Lot, Vending Machine, Elevator). Submission = design notes + class outline + optional Python.
- **Evaluate:** a `Evaluator` interface with a deterministic pass (AST + rubric keywords) and a pluggable LLM/critique pass. Composite results. If AI is slow or missing, the mechanical report still lands; status is `pending` / `failed` with retry — no queue infrastructure.
- **Out:** dimensional scores, pass/fail findings, interviewer-style notes, attempt history.
- **Explicitly out of scope:** auth, multi-tenant scale, diagram editors, microservices.

The bet: a candidate who iterates twice on Parking Lot with *specific* feedback (“pricing is a switch on vehicle type — that is the extension point”) learns more than one who reads five GitHub solutions.

## Sources

- Educative, *Grokking the Low-Level Design Interview Using OOD Principles*
- Design Gurus, *Grokking the Object Oriented Design Interview*
- ByteByteGo OOD / Parking Lot material
- Hello Interview, “How to Prepare for a Low-Level Design Interview”
- GitHub: Low-Level-Design-Primer; community Grokking OOD ports
- Codemia.io, LLD Mastery — practice-first system/OOD tools
- Practitioner write-ups on why LLD prep-by-reading fails (DEV, r/leetcode)
