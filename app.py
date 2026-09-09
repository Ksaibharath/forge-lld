from __future__ import annotations

import gradio as gr

from backend.catalog import get_problem, list_problems, problem_public
from backend.service import ForgeService
from backend.store import AttemptRepository

repo = AttemptRepository("data/forge.db")
service = ForgeService(repo)
PROBLEMS = list_problems()


def _brief(problem_id: str) -> str:
    p = problem_public(get_problem(problem_id))
    req = "\n".join(f"- {r}" for r in p["functional_requirements"])
    con = "\n".join(f"- {r}" for r in p["constraints"])
    return (
        f"### {p['title']}\n"
        f"*{p['difficulty']} · {p['minutes']} min*\n\n"
        f"{p['statement']}\n\n"
        f"**Requirements**\n{req}\n\n"
        f"**Constraints**\n{con}"
    )


def _sample(problem_id: str):
    p = get_problem(problem_id)
    return p.sample_notes, p.sample_outline, p.sample_code


def _submit(problem_id: str, notes: str, outline: str, code: str) -> str:
    if not (notes or "").strip() and not (outline or "").strip() and not (code or "").strip():
        return "Write design notes, an outline, or code before submitting."
    attempt = service.start_attempt(problem_id)
    attempt = service.submit(attempt.id, notes or "", outline or "", code or "")
    ev = attempt.submissions[-1].evaluation
    if ev is None:
        return "No evaluation stored."
    dims = "\n".join(f"- **{d.name}:** {d.score}/10 — {d.comment}" for d in ev.dimensions)
    strengths = "\n".join(f"- {s}" for s in ev.strengths) or "-"
    nexts = "\n".join(f"- {s}" for s in ev.improvements) or "-"
    findings = "\n".join(
        f"- `{f.severity.value}` **{f.label}** — {f.message}" for f in ev.findings
    )
    return (
        f"## Score {ev.overall_score} / 100\n"
        f"*Not pass/fail — diagnostic. AI critique: {ev.ai_status}*\n\n"
        f"{ev.narrative}\n\n"
        f"### Dimensions\n{dims}\n\n"
        f"### Strengths\n{strengths}\n\n"
        f"### Next moves\n{nexts}\n\n"
        f"### Findings\n{findings}"
    )


CHOICES = [(p.title, p.id) for p in PROBLEMS]
DEFAULT_ID = PROBLEMS[0].id

with gr.Blocks(title="Forge — LLD bench", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# Forge\n"
        "Low-level design practice. Feedback is diagnostic — many designs can be valid."
    )
    with gr.Row():
        picker = gr.Dropdown(choices=CHOICES, value=DEFAULT_ID, label="Problem")
        sample_btn = gr.Button("Fill a sample", variant="secondary")
    brief = gr.Markdown(_brief(DEFAULT_ID))
    notes = gr.Textbox(label="Design notes", lines=10)
    outline = gr.Textbox(label="Class outline (optional)", lines=6)
    code = gr.Textbox(label="Python (optional)", lines=12)
    go = gr.Button("Submit for critique", variant="primary")
    out = gr.Markdown()
    picker.change(fn=_brief, inputs=picker, outputs=brief)
    sample_btn.click(fn=_sample, inputs=picker, outputs=[notes, outline, code])
    go.click(fn=_submit, inputs=[picker, notes, outline, code], outputs=out)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)