(() => {
  "use strict";

  const DATA = window.DBMS_DATA || { questions: [], categories: [], lessons: [], seedProgress: {} };
  const STORE_KEY = "dbms_quest_progress_v1";
  const SQL_STORE_PREFIX = "dbms_quest_sql_";
  const view = document.getElementById("view");
  const titleScreen = document.getElementById("title");
  const hud = document.getElementById("hud");

  // ---------- state ----------
  const state = {
    progress: loadProgress(),
    filter: "all",
    catFilter: "all",
  };

  // ---------- sql.js lazy loader ----------
  let sqlPromise = null;
  function getSql() {
    if (!sqlPromise) {
      sqlPromise = window.initSqlJs({ locateFile: f => "vendor/" + f })
        .then(SQL => { beep("nav"); return SQL; });
    }
    return sqlPromise;
  }

  function loadProgress() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) return new Set(JSON.parse(raw));
    } catch (e) { /* ignore */ }
    return new Set(Object.keys(DATA.seedProgress || {}));
  }

  function saveProgress() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify([...state.progress])); } catch (e) {}
  }

  function isDone(id) { return state.progress.has(String(id)); }
  function toggleDone(id) {
    const key = String(id);
    if (state.progress.has(key)) { state.progress.delete(key); beep("down"); }
    else { state.progress.add(key); beep("up"); }
    saveProgress();
    renderHud();
  }

  // ---------- sound (Web Audio beeps) ----------
  let actx = null;
  function beep(kind) {
    try {
      actx = actx || new (window.AudioContext || window.webkitAudioContext)();
      const o = actx.createOscillator();
      const g = actx.createGain();
      o.connect(g); g.connect(actx.destination);
      o.type = "square";
      const t = actx.currentTime;
      const notes = {
        up:   [[660, 0.06], [990, 0.09]],
        down: [[440, 0.06], [220, 0.09]],
        nav:  [[880, 0.04]],
        err:  [[180, 0.12]],
      }[kind] || [[660, 0.05]];
      notes.forEach((n, i) => {
        o.frequency.setValueAtTime(n[0], t + i * 0.05);
        g.gain.setValueAtTime(0.07, t + i * 0.05);
        g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.05 + n[1]);
      });
      o.start(t); o.stop(t + notes.length * 0.05 + 0.1);
    } catch (e) { /* no audio, no problem */ }
  }

  // ---------- routing ----------
  function go(target, payload) {
    if (target === "title") {
      titleScreen.classList.add("active");
      hud.classList.add("hidden");
      view.innerHTML = "";
      beep("nav");
      return;
    }
    titleScreen.classList.remove("active");
    hud.classList.remove("hidden");
    beep("nav");
    if (target === "quests") renderQuests();
    else if (target === "quest") renderQuest(payload);
    else if (target === "lessons") renderLessons();
    else if (target === "lesson") renderLesson(payload);
    else if (target === "progress") renderProgress();
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function tpl(id) { return document.getElementById(id).content.cloneNode(true); }

  // ---------- HUD ----------
  function renderHud() {
    const total = DATA.questions.length;
    const done = DATA.questions.filter(q => isDone(q.id)).length;
    document.getElementById("hudLevel").textContent = Math.max(1, Math.floor(done / 5) + 1);
    document.getElementById("hudXp").textContent = `${done}/${total}`;
    document.getElementById("hudClear").textContent = `${done}/${total}`;
  }

  // ---------- quests list ----------
  function renderQuests() {
    const node = tpl("tpl-quests");
    view.replaceChildren(node);

    const catSel = document.getElementById("catFilter");
    DATA.categories.forEach(c => {
      const o = document.createElement("option");
      o.value = c.name; o.textContent = c.name.toUpperCase();
      catSel.appendChild(o);
    });
    catSel.value = state.catFilter;

    view.querySelectorAll(".filter").forEach(b => {
      b.classList.toggle("active", b.dataset.filter === state.filter);
      b.addEventListener("click", () => {
        state.filter = b.dataset.filter;
        view.querySelectorAll(".filter").forEach(x => x.classList.toggle("active", x === b));
        drawQuestList();
      });
    });
    catSel.addEventListener("change", () => { state.catFilter = catSel.value; drawQuestList(); });
    drawQuestList();
  }

  function drawQuestList() {
    const list = document.getElementById("questList");
    list.innerHTML = "";
    const items = DATA.questions.filter(q => {
      if (state.catFilter !== "all" && q.category !== state.catFilter) return false;
      if (state.filter === "done") return isDone(q.id);
      if (state.filter === "todo") return !isDone(q.id);
      return true;
    });
    if (!items.length) {
      list.innerHTML = '<p style="color:var(--dim);padding:1rem">NO QUESTS MATCH.</p>';
      return;
    }
    items.forEach(q => {
      const card = document.createElement("div");
      card.className = "quest-card" + (isDone(q.id) ? " done" : "");
      card.innerHTML = `
        <span class="q-id">${q.id}</span>
        <span class="q-title">${escapeHtml(q.title)}</span>
        <span class="q-diff ${q.difficulty}">${q.difficulty.toUpperCase()}</span>
        <span class="q-status ${isDone(q.id) ? "done" : ""}">${isDone(q.id) ? "[CLR]" : "[...]"}</span>
      `;
      card.addEventListener("click", () => go("quest", q.id));
      list.appendChild(card);
    });
  }

  // ---------- SQL execution (in-browser via sql.js) ----------
  function normRow(values) {
    return values.map(v => (v === null || v === undefined) ? "" : String(v));
  }

  function extractResult(res) {
    if (!res || !res.length) return { columns: [], rows: [] };
    const last = res[res.length - 1];
    return { columns: last.columns || [], rows: (last.values || []).map(normRow) };
  }

  function freshDb(SQL, q) {
    const db = new SQL.Database();
    db.run(q.setupSql);
    return db;
  }

  function runUserSql(SQL, q, userSql) {
    const db = freshDb(SQL, q);
    let actual;
    if (q.verifyTable) {
      db.run(userSql);
      const qt = q.verifyTable.replace(/"/g, '""');
      actual = extractResult(db.exec(`SELECT * FROM "${qt}" ORDER BY id`));
    } else {
      actual = extractResult(db.exec(userSql));
    }
    db.close();
    return actual;
  }

  function getExpected(SQL, q) {
    if (q.expectedSql) {
      const db = freshDb(SQL, q);
      const exp = extractResult(db.exec(q.expectedSql));
      db.close();
      return exp;
    }
    if (q.expectedResult) {
      return {
        columns: q.expectedResult.columns,
        rows: q.expectedResult.rows.map(normRow),
      };
    }
    return null;
  }

  function resultsMatch(actual, expected, orderSensitive) {
    if (!expected) return false;
    if (actual.columns.join("|") !== expected.columns.join("|")) return false;
    const a = actual.rows.map(r => r.join("\u0001"));
    const e = expected.rows.map(r => r.join("\u0001"));
    if (orderSensitive) return a.length === e.length && a.every((v, i) => v === e[i]);
    if (a.length !== e.length) return false;
    const sa = [...a].sort(), se = [...e].sort();
    return sa.every((v, i) => v === se[i]);
  }

  function resultTableHtml(columns, rows) {
    if (!columns.length && (!rows || !rows.length)) return '<p class="result-empty">-- NO ROWS RETURNED --</p>';
    let h = '<table class="result"><thead><tr>';
    columns.forEach(c => { h += `<th>${escapeHtml(c)}</th>`; });
    h += '</tr></thead><tbody>';
    if (!rows.length) { h += `<tr><td colspan="${columns.length}" class="result-empty">-- 0 ROWS --</td></tr>`; }
    rows.forEach(r => {
      h += "<tr>" + r.map(v => `<td>${escapeHtml(v)}</td>`).join("") + "</tr>";
    });
    h += "</tbody></table>";
    h += `<p class="result-count">${rows.length} ROW(S)</p>`;
    return h;
  }

  function sqlKey(id) { return SQL_STORE_PREFIX + id; }
  function loadSql(id) {
    try { return localStorage.getItem(sqlKey(id)) || ""; } catch (e) { return ""; }
  }
  function saveSql(id, sql) {
    try { localStorage.setItem(sqlKey(id), sql); } catch (e) {}
  }

  async function handleRun(q, userSql, resultArea, statusEl) {
    if (!userSql.trim()) { showStatus(statusEl, "EMPTY SQL", "err"); return; }
    showStatus(statusEl, "COMPILING...", "dim");
    try {
      const SQL = await getSql();
      const actual = runUserSql(SQL, q, userSql);
      resultArea.innerHTML = resultTableHtml(actual.columns, actual.rows);
      showStatus(statusEl, "RUN OK", "ok");
      beep("nav");
    } catch (e) {
      resultArea.innerHTML = `<pre class="result-error">SQL ERROR: ${escapeHtml(String(e.message || e))}</pre>`;
      showStatus(statusEl, "ERROR", "err");
      beep("err");
    }
  }

  async function handleTest(q, userSql, resultArea, statusEl) {
    if (!userSql.trim()) { showStatus(statusEl, "EMPTY SQL", "err"); return; }
    showStatus(statusEl, "TESTING...", "dim");
    try {
      const SQL = await getSql();
      const actual = runUserSql(SQL, q, userSql);
      const expected = getExpected(SQL, q);
      const passed = resultsMatch(actual, expected, q.orderSensitive);
      let html = "";
      if (passed) {
        html = `<div class="test-banner pass">*** PASS ***</div>`;
        html += resultTableHtml(actual.columns, actual.rows);
        if (!isDone(q.id)) { state.progress.add(String(q.id)); saveProgress(); }
        showStatus(statusEl, "PASS", "ok");
        beep("up");
      } else {
        html = `<div class="test-banner fail">XXX FAIL XXX</div>`;
        html += `<div class="result-cols"><div><h4>EXPECTED</h4>${resultTableHtml(expected.columns, expected.rows)}</div><div><h4>YOURS</h4>${resultTableHtml(actual.columns, actual.rows)}</div></div>`;
        showStatus(statusEl, "FAIL", "err");
        beep("err");
      }
      resultArea.innerHTML = html;
      renderHud();
      if (passed) updateCompleteBtn(q.id);
    } catch (e) {
      resultArea.innerHTML = `<pre class="result-error">SQL ERROR: ${escapeHtml(String(e.message || e))}</pre>`;
      showStatus(statusEl, "ERROR", "err");
      beep("err");
    }
  }

  function showStatus(el, text, kind) {
    el.textContent = text;
    el.className = "sql-status " + (kind || "");
  }

  function updateCompleteBtn(id) {
    const btn = document.getElementById("completeBtn");
    if (!btn) return;
    const done = isDone(id);
    btn.classList.toggle("done", done);
    btn.textContent = done ? "[ CLEARED ] - UNDO" : "[ MARK CLEARED ]";
  }

  // ---------- quest detail ----------
  function renderQuest(id) {
    const q = DATA.questions.find(x => String(x.id) === String(id));
    if (!q) { go("quests"); return; }
    const node = tpl("tpl-quest");
    view.replaceChildren(node);
    const detail = document.getElementById("questDetail");
    const done = isDone(q.id);
    detail.innerHTML = `
      <div class="qd-head">
        <div>
          <div class="qd-title">${q.id} :: ${escapeHtml(q.title)}</div>
          <div class="qd-meta">CATEGORY: <b>${escapeHtml(q.category)}</b> &nbsp; DIFF: <b>${q.difficulty}</b> &nbsp; ${q.runnable ? `FIXTURE: <b>${q.fixtureKind}</b>` : "<b>NO LOCAL FIXTURE</b>"}</div>
        </div>
        <a class="ext-link" href="${q.leetcode}" target="_blank" rel="noopener">&gt; LEETCODE</a>
      </div>

      <div class="qd-section">
        <h3>&gt; BRIEFING</h3>
        <div class="qd-prompt">${q.promptHtml || "<p>No dumped prompt for this question.</p>"}</div>
      </div>

      <div class="qd-section">
        <h3>&gt; HINT</h3>
        <div class="reveal-wrap">
          <button class="reveal-btn" data-target="hint">SHOW HINT</button>
          <div class="reveal-body" id="hint"><pre>${escapeHtml(q.hint)}</pre></div>
        </div>
      </div>

      <div class="qd-section">
        <h3>&gt; SOLUTION</h3>
        <div class="reveal-wrap">
          <button class="reveal-btn" data-target="sol">REVEAL</button>
          <div class="reveal-body" id="sol"><pre><code>${escapeHtml(q.solution)}</code></pre></div>
        </div>
      </div>

      ${q.runnable && q.setupSql ? renderEditorSlot() : '<p class="no-fixture">-- NO LOCAL FIXTURE: BRIEFING ONLY --</p>'}

      <button class="complete-btn ${done ? "done" : ""}" id="completeBtn">
        ${done ? "[ CLEARED ] - UNDO" : "[ MARK CLEARED ]"}
      </button>
    `;
    detail.querySelectorAll(".reveal-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const body = detail.querySelector("#" + btn.dataset.target);
        const open = body.classList.toggle("open");
        btn.textContent = open ? "HIDE" : (btn.dataset.target === "sol" ? "REVEAL" : "SHOW HINT");
        beep("nav");
      });
    });
    document.getElementById("completeBtn").addEventListener("click", () => {
      toggleDone(q.id);
      renderQuest(q.id);
    });
    if (q.runnable && q.setupSql) wireEditor(q);
  }

  function renderEditorSlot() {
    const node = tpl("tpl-editor");
    const slot = document.createElement("div");
    slot.appendChild(node);
    return slot.innerHTML;
  }

  function wireEditor(q) {
    const input = document.getElementById("sqlInput");
    const runBtn = document.getElementById("runBtn");
    const testBtn = document.getElementById("testBtn");
    const loadSolBtn = document.getElementById("loadSolBtn");
    const clearBtn = document.getElementById("clearBtn");
    const resultArea = document.getElementById("resultArea");
    const statusEl = document.getElementById("sqlStatus");

    input.value = loadSql(q.id);
    input.addEventListener("input", () => saveSql(q.id, input.value));

    // Ctrl/Cmd+Enter runs; Shift+Enter tests
    input.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (e.shiftKey) handleTest(q, input.value, resultArea, statusEl);
        else handleRun(q, input.value, resultArea, statusEl);
      }
      // Tab inserts two spaces instead of leaving the textarea
      if (e.key === "Tab") {
        e.preventDefault();
        const s = input.selectionStart, en = input.selectionEnd;
        input.value = input.value.slice(0, s) + "  " + input.value.slice(en);
        input.selectionStart = input.selectionEnd = s + 2;
        saveSql(q.id, input.value);
      }
    });

    runBtn.addEventListener("click", () => handleRun(q, input.value, resultArea, statusEl));
    testBtn.addEventListener("click", () => handleTest(q, input.value, resultArea, statusEl));
    loadSolBtn.addEventListener("click", () => {
      if (!q.solution || q.solution.startsWith("--")) {
        showStatus(statusEl, "NO SOLUTION", "err");
        beep("err");
        return;
      }
      input.value = q.solution;
      saveSql(q.id, input.value);
      showStatus(statusEl, "SOLUTION LOADED", "ok");
      beep("nav");
    });
    clearBtn.addEventListener("click", () => {
      input.value = "";
      saveSql(q.id, "");
      resultArea.innerHTML = "";
      showStatus(statusEl, "CLEARED", "dim");
      beep("down");
    });
  }

  // ---------- lessons ----------
  function renderLessons() {
    const node = tpl("tpl-lessons");
    view.replaceChildren(node);
    const list = document.getElementById("lessonList");
    DATA.lessons.forEach(l => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="ll-id">${l.id.toUpperCase().slice(0, 8)}</span> ${escapeHtml(l.title)}`;
      li.addEventListener("click", () => go("lesson", l.id));
      list.appendChild(li);
    });
  }

  function renderLesson(id) {
    const l = DATA.lessons.find(x => x.id === id);
    if (!l) { go("lessons"); return; }
    const node = tpl("tpl-lesson");
    view.replaceChildren(node);
    const detail = document.getElementById("lessonDetail");
    detail.innerHTML = `<h2>${escapeHtml(l.title)}</h2>${l.html}`;
  }

  // ---------- progress ----------
  function renderProgress() {
    const node = tpl("tpl-progress");
    view.replaceChildren(node);
    const board = document.getElementById("progressBoard");
    const total = DATA.questions.length;
    const done = DATA.questions.filter(q => isDone(q.id)).length;
    const pct = total ? Math.round((done / total) * 100) : 0;

    let catHtml = "";
    DATA.categories.forEach(c => {
      const ids = c.questionIds;
      const cd = ids.filter(id => isDone(id)).length;
      const cpct = ids.length ? Math.round((cd / ids.length) * 100) : 0;
      catHtml += `
        <div class="cat-row"><span class="cname">${escapeHtml(c.name)}</span><span class="ccount">${cd}/${ids.length} (${cpct}%)</span></div>
        <div class="bar"><div class="bar-fill" style="width:${cpct}%"></div></div>
      `;
    });

    const diff = { Easy: [0, 0], Medium: [0, 0], Hard: [0, 0] };
    DATA.questions.forEach(q => { diff[q.difficulty][1]++; if (isDone(q.id)) diff[q.difficulty][0]++; });

    board.innerHTML = `
      <div class="stat-grid">
        <div class="stat-box"><div class="num">${done}</div><div class="cap">CLEARED</div></div>
        <div class="stat-box"><div class="num">${total - done}</div><div class="cap">REMAINING</div></div>
        <div class="stat-box"><div class="num">${pct}%</div><div class="cap">COMPLETE</div></div>
        <div class="stat-box"><div class="num">${Math.max(1, Math.floor(done / 5) + 1)}</div><div class="cap">LEVEL</div></div>
      </div>

      <div class="bar-row">
        <div class="lbl"><span>&gt; TOTAL PROGRESS</span><span>${done}/${total}</span></div>
        <div class="bar"><div class="bar-fill" style="width:${pct}%"></div></div>
      </div>

      <div class="bar-row">
        <div class="lbl"><span>&gt; BY CATEGORY</span><span></span></div>
        ${catHtml}
      </div>

      <div class="bar-row">
        <div class="lbl"><span>&gt; BY DIFFICULTY</span><span></span></div>
        ${Object.entries(diff).map(([k, v]) => `
          <div class="cat-row"><span class="cname">${k}</span><span class="ccount">${v[0]}/${v[1]}</span></div>
          <div class="bar"><div class="bar-fill" style="width:${v[1] ? (v[0]/v[1]*100) : 0}%"></div></div>
        `).join("")}
      </div>

      <p style="color:var(--dim);font-size:1rem;text-align:center;margin-top:1rem">
        ${done === total ? "*** YOU CLEARED THE ENTIRE QUEST. GG. ***" : "KEEP GRINDING. THE DB IS PATIENT."}
      </p>
    `;
  }

  // ---------- helpers ----------
  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // ---------- wire up ----------
  document.addEventListener("click", (e) => {
    const goBtn = e.target.closest("[data-go]");
    if (goBtn) { e.preventDefault(); go(goBtn.dataset.go); return; }
    if (e.target.closest("#pressStart")) { go("quests"); }
  });

  document.getElementById("resetBtn").addEventListener("click", () => {
    if (!confirm("Reset all saved progress on this browser?")) return;
    state.progress = new Set();
    saveProgress();
    renderHud();
    beep("err");
    alert("Save wiped. Returning to title.");
    go("title");
  });

  // keyboard: arrows + enter on title screen
  document.addEventListener("keydown", (e) => {
    if (!titleScreen.classList.contains("active")) return;
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go("quests"); }
  });

  renderHud();
})();
