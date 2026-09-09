from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from backend.models import Attempt, AttemptStatus, Evaluation, Submission, new_id, now_iso


class AttemptRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY,
                    problem_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL,
                    design_notes TEXT NOT NULL,
                    class_outline TEXT NOT NULL,
                    code TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    FOREIGN KEY (attempt_id) REFERENCES attempts(id)
                );
                CREATE TABLE IF NOT EXISTS evaluations (
                    id TEXT PRIMARY KEY,
                    submission_id TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (submission_id) REFERENCES submissions(id)
                );
                """
            )

    def create_attempt(self, problem_id: str) -> Attempt:
        attempt = Attempt(
            id=new_id("att"),
            problem_id=problem_id,
            status=AttemptStatus.IN_PROGRESS,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO attempts (id, problem_id, status, created_at, updated_at) VALUES (?,?,?,?,?)",
                (attempt.id, attempt.problem_id, attempt.status.value, attempt.created_at, attempt.updated_at),
            )
        return attempt

    def get_attempt(self, attempt_id: str) -> Optional[Attempt]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
            if not row:
                return None
            attempt = Attempt(
                id=row["id"],
                problem_id=row["problem_id"],
                status=AttemptStatus(row["status"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            subs = conn.execute(
                "SELECT * FROM submissions WHERE attempt_id = ? ORDER BY submitted_at ASC",
                (attempt_id,),
            ).fetchall()
            for s in subs:
                sub = Submission(
                    id=s["id"],
                    attempt_id=s["attempt_id"],
                    design_notes=s["design_notes"],
                    class_outline=s["class_outline"],
                    code=s["code"],
                    submitted_at=s["submitted_at"],
                )
                ev = conn.execute(
                    "SELECT payload FROM evaluations WHERE submission_id = ?",
                    (sub.id,),
                ).fetchone()
                if ev:
                    sub.evaluation = Evaluation.from_dict(json.loads(ev["payload"]))
                attempt.submissions.append(sub)
        return attempt

    def set_status(self, attempt_id: str, status: AttemptStatus) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE attempts SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now_iso(), attempt_id),
            )

    def add_submission(self, attempt_id: str, design_notes: str, class_outline: str, code: str) -> Submission:
        sub = Submission(
            id=new_id("sub"),
            attempt_id=attempt_id,
            design_notes=design_notes,
            class_outline=class_outline,
            code=code,
            submitted_at=now_iso(),
        )
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO submissions
                   (id, attempt_id, design_notes, class_outline, code, submitted_at)
                   VALUES (?,?,?,?,?,?)""",
                (sub.id, sub.attempt_id, sub.design_notes, sub.class_outline, sub.code, sub.submitted_at),
            )
            conn.execute(
                "UPDATE attempts SET updated_at = ? WHERE id = ?",
                (now_iso(), attempt_id),
            )
        return sub

    def save_evaluation(self, evaluation: Evaluation) -> None:
        payload = json.dumps(evaluation.to_dict())
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO evaluations (id, submission_id, payload, created_at)
                   VALUES (?,?,?,?)
                   ON CONFLICT(submission_id) DO UPDATE SET
                     payload = excluded.payload,
                     created_at = excluded.created_at""",
                (evaluation.id, evaluation.submission_id, payload, evaluation.created_at),
            )

    def get_submission(self, submission_id: str) -> Optional[Submission]:
        with self._connect() as conn:
            s = conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
            if not s:
                return None
            sub = Submission(
                id=s["id"],
                attempt_id=s["attempt_id"],
                design_notes=s["design_notes"],
                class_outline=s["class_outline"],
                code=s["code"],
                submitted_at=s["submitted_at"],
            )
            ev = conn.execute(
                "SELECT payload FROM evaluations WHERE submission_id = ?",
                (sub.id,),
            ).fetchone()
            if ev:
                sub.evaluation = Evaluation.from_dict(json.loads(ev["payload"]))
            return sub

    def history(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT a.id, a.problem_id, a.status, a.created_at, a.updated_at,
                       (SELECT COUNT(*) FROM submissions s WHERE s.attempt_id = a.id) AS n_sub
                FROM attempts a
                ORDER BY a.updated_at DESC
                """
            ).fetchall()
            out = []
            for r in rows:
                latest = conn.execute(
                    """
                    SELECT e.payload FROM evaluations e
                    JOIN submissions s ON s.id = e.submission_id
                    WHERE s.attempt_id = ?
                    ORDER BY s.submitted_at DESC LIMIT 1
                    """,
                    (r["id"],),
                ).fetchone()
                score = None
                if latest:
                    score = json.loads(latest["payload"]).get("overall_score")
                out.append(
                    {
                        "id": r["id"],
                        "problem_id": r["problem_id"],
                        "status": r["status"],
                        "created_at": r["created_at"],
                        "updated_at": r["updated_at"],
                        "submission_count": r["n_sub"],
                        "latest_score": score,
                    }
                )
            return out
