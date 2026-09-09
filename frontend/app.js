const view = document.getElementById("view");

const api = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};

function route() {
  const hash = location.hash.slice(1) || "/";
  const parts = hash.split("/").filter(Boolean);
  document.querySelectorAll("[data-nav]").forEach((a) => {
    const on =
      (a.dataset.nav === "home" && (parts.length === 0 || parts[0] === "problems")) ||
      (a.dataset.nav === "history" && parts[0] === "history");
    a.classList.toggle("active", on);
  });
  if (parts.length === 0) return renderHome();
  if (parts[0] === "problems" && parts[1]) return renderProblem(parts[1]);
  if (parts[0] === "attempts" && parts[1]) return renderAttempt(parts[1]);
  if (parts[0] === "history") return renderHistory();
  renderHome();
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function chip(diff) {
  return `<span class="chip ${escapeHtml(diff)}">${escapeHtml(diff)}</span>`;
}

async function renderHome() {
  view.innerHTML = `<p class="kicker">Practice bench</p>
    <h1>Design it. Hear it back.</h1>
    <p class="lede">Classic low-level design problems, scored like an interviewer — types, extension points, trade-offs — not a hidden unit-test suite. Pick a problem, write the talk track, optionally the code.</p>
    <div class="grid" id="cards"><p class="empty">Loading problems…</p></div>`;
  try {
    const problems = await api.get("/api/problems");
    document.getElementById("cards").innerHTML = problems
      .map(
        (p) => `<a class="card" href="#/problems/${p.id}">
          <div class="meta">${chip(p.difficulty)}<span class="chip">${p.minutes} min</span></div>
          <h2>${escapeHtml(p.title)}</h2>
          <p>${escapeHtml(p.summary)}</p>
          <div class="meta">${(p.expected_patterns || []).map((x) => `<span class="chip">${escapeHtml(x)}</span>`).join("")}</div>
        </a>`
      )
      .join("");
  } catch (err) {
    document.getElementById("cards").innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
  }
}

async function renderProblem(id) {
  view.innerHTML = `<p class="empty">Loading…</p>`;
  try {
    const p = await api.get(`/api/problems/${id}`);
    view.innerHTML = `<article class="brief" style="max-width:720px">
      <p class="kicker">Problem</p>
      <div class="meta">${chip(p.difficulty)}<span class="chip">${p.minutes} min</span></div>
      <h1>${escapeHtml(p.title)}</h1>
      <p class="statement">${escapeHtml(p.statement)}</p>
      <h3>Functional requirements</h3>
      <ul>${p.functional_requirements.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
      <h3>Constraints</h3>
      <ul>${p.constraints.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
      <h3>What a strong attempt usually shows</h3>
      <ul>${p.considerations_teaser.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
      <div class="actions">
        <button class="primary" id="start">Start attempt</button>
        <a class="ghost" href="#/" style="text-decoration:none;display:inline-flex;align-items:center">Back</a>
      </div>
    </article>`;
    document.getElementById("start").onclick = async () => {
      const btn = document.getElementById("start");
      btn.disabled = true;
      btn.textContent = "Opening bench…";
      const attempt = await api.post("/api/attempts", { problem_id: id });
      location.hash = `#/attempts/${attempt.id}`;
    };
  } catch (err) {
    view.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
  }
}

async function renderAttempt(id) {
  view.innerHTML = `<p class="empty">Loading attempt…</p>`;
  let attempt;
  try {
    attempt = await api.get(`/api/attempts/${id}`);
  } catch (err) {
    view.innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
    return;
  }
  const problem = await api.get(`/api/problems/${attempt.problem_id}`);
  const latest = attempt.submissions[attempt.submissions.length - 1];
  const notes0 = latest?.design_notes || "";
  const outline0 = latest?.class_outline || "";
  const code0 = latest?.code || "";

  view.innerHTML = `<div class="studio">
    <section class="brief">
      <p class="kicker">${escapeHtml(problem.title)}</p>
      <div class="meta">${chip(problem.difficulty)}<span class="chip">attempt ${escapeHtml(id.slice(-6))}</span>
        <span class="chip">${escapeHtml(attempt.status)}</span></div>
      <p class="statement">${escapeHtml(problem.statement)}</p>
      <h3>Requirements</h3>
      <ul>${problem.functional_requirements.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
      <h3>Constraints</h3>
      <ul>${problem.constraints.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
    </section>
    <section class="work">
      <div class="tabs">
        <button class="active" data-tab="notes">Design notes</button>
        <button data-tab="outline">Class outline</button>
        <button data-tab="code">Code</button>
      </div>
      <div data-pane="notes">
        <label class="hint">Assumptions, types, public APIs, one trade-off. This is the interview talk track.</label>
        <textarea id="notes">${escapeHtml(notes0)}</textarea>
      </div>
      <div data-pane="outline" hidden>
        <label class="hint">Optional. List classes and methods if you are not writing code yet.</label>
        <textarea id="outline" class="mono">${escapeHtml(outline0)}</textarea>
      </div>
      <div data-pane="code" hidden>
        <label class="hint">Optional Python. Parsed with AST — it does not need to run.</label>
        <textarea id="code" class="mono">${escapeHtml(code0)}</textarea>
      </div>
      <div class="actions">
        <button class="primary" id="submit">Submit for critique</button>
        <button class="ghost" id="sample">Fill a sample</button>
      </div>
      <p class="hint" id="status-line"></p>
      <div id="report"></div>
    </section>
  </div>`;

  view.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.onclick = () => {
      view.querySelectorAll("[data-tab]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      view.querySelectorAll("[data-pane]").forEach((p) => {
        p.hidden = p.dataset.pane !== btn.dataset.tab;
      });
    };
  });

  document.getElementById("sample").onclick = async () => {
    const sample = await api.get(`/api/problems/${attempt.problem_id}/sample`);
    document.getElementById("notes").value = sample.design_notes;
    document.getElementById("outline").value = sample.class_outline;
    document.getElementById("code").value = sample.code;
  };

  document.getElementById("submit").onclick = async () => {
    const btn = document.getElementById("submit");
    btn.disabled = true;
    document.getElementById("status-line").textContent = "Evaluating… mechanical checks first, then optional AI.";
    try {
      const updated = await api.post(`/api/attempts/${id}/submissions`, {
        design_notes: document.getElementById("notes").value,
        class_outline: document.getElementById("outline").value,
        code: document.getElementById("code").value,
      });
      paintReport(updated);
    } catch (err) {
      document.getElementById("status-line").innerHTML = `<span class="err">${escapeHtml(err.message)}</span>`;
    } finally {
      btn.disabled = false;
    }
  };

  if (latest?.evaluation) paintReport(attempt);
}

function paintReport(attempt) {
  const latest = attempt.submissions[attempt.submissions.length - 1];
  const ev = latest?.evaluation;
  const el = document.getElementById("report");
  const status = document.getElementById("status-line");
  if (!el) return;
  if (!ev) {
    el.innerHTML = "";
    return;
  }
  status.textContent = `Submission ${latest.id.slice(-6)} · ${ev.evaluator_names.join(" + ")}`;
  const aiBanner =
    ev.ai_status === "complete"
      ? ""
      : `<div class="banner">AI critique is ${escapeHtml(ev.ai_status)}${
          ev.ai_error ? " — " + escapeHtml(ev.ai_error) : ""
        }. Mechanical findings still apply. <button class="ghost" id="retry">Retry critique</button></div>`;

  el.innerHTML = `<article class="report" style="margin-top:18px;padding:0;border:0;background:transparent">
    ${aiBanner}
    <div class="score-row">
      <div class="score">${ev.overall_score}</div>
      <div>
        <div class="chip">not a pass/fail</div>
        <p class="narrative">${escapeHtml(ev.narrative)}</p>
      </div>
    </div>
    ${(ev.dimensions || [])
      .map(
        (d) => `<div class="dim">
        <header><span>${escapeHtml(d.name)}</span><span>${d.score}/10</span></header>
        <div class="bar"><span style="width:${d.score * 10}%"></span></div>
      </div>`
      )
      .join("")}
    <div class="columns" style="margin-top:18px">
      <div>
        <h3>Strengths</h3>
        <ul>${(ev.strengths || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("") || "<li>—</li>"}</ul>
      </div>
      <div>
        <h3>Next moves</h3>
        <ul>${(ev.improvements || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("") || "<li>—</li>"}</ul>
      </div>
    </div>
    <ul class="findings">
      ${(ev.findings || [])
        .map(
          (f) => `<li><span class="tag ${escapeHtml(f.severity)}">${escapeHtml(f.severity)}</span>
            <span><strong>${escapeHtml(f.label)}.</strong> ${escapeHtml(f.message)}</span></li>`
        )
        .join("")}
    </ul>
  </article>`;

  const retry = document.getElementById("retry");
  if (retry) {
    retry.onclick = async () => {
      retry.disabled = true;
      retry.textContent = "Retrying…";
      const updated = await api.post(`/api/submissions/${latest.id}/retry`);
      paintReport(updated);
    };
  }
}

async function renderHistory() {
  view.innerHTML = `<p class="kicker">Log</p><h1>Attempts</h1>
    <p class="lede">Every sitting stays here so the second Parking Lot is allowed to be better than the first.</p>
    <div id="table"><p class="empty">Loading…</p></div>`;
  try {
    const rows = await api.get("/api/history");
    if (!rows.length) {
      document.getElementById("table").innerHTML = `<p class="empty">No attempts yet. Start from Problems.</p>`;
      return;
    }
    document.getElementById("table").innerHTML = `<table>
      <thead><tr><th>Problem</th><th>Status</th><th>Score</th><th>Subs</th><th>Updated</th></tr></thead>
      <tbody>
        ${rows
          .map(
            (r) => `<tr class="clickable" data-id="${escapeHtml(r.id)}">
              <td>${escapeHtml(r.problem_title)}</td>
              <td>${escapeHtml(r.status)}</td>
              <td>${r.latest_score ?? "—"}</td>
              <td>${r.submission_count}</td>
              <td>${escapeHtml((r.updated_at || "").replace("T", " ").replace("+00:00", " UTC"))}</td>
            </tr>`
          )
          .join("")}
      </tbody>
    </table>`;
    document.querySelectorAll("tr.clickable").forEach((tr) => {
      tr.onclick = () => {
        location.hash = `#/attempts/${tr.dataset.id}`;
      };
    });
  } catch (err) {
    document.getElementById("table").innerHTML = `<p class="err">${escapeHtml(err.message)}</p>`;
  }
}

window.addEventListener("hashchange", route);
route();
