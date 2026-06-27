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

  // ---------- backend API ----------
  let backendOk = null;
  let lastHealth = null;
  let sqlJsPromise = null;
  let activeEngine = null; // "mysql" | "sqlite" | null

  async function api(path, opts) {
    const r = await fetch(path, opts);
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }
  async function checkBackend() {
    if (backendOk !== null) return backendOk;
    try {
      const h = await api("/api/health");
      backendOk = !!(h && h.ok);
      lastHealth = h;
      if (backendOk) activeEngine = "mysql";
    } catch (e) { backendOk = false; }
    return backendOk;
  }

  // ---------- sql.js fallback (SQLite WASM, for static hosting like Vercel) ----------
  function getSqlJs() {
    if (!sqlJsPromise) {
      sqlJsPromise = new Promise((resolve, reject) => {
        if (window.initSqlJs) return resolve(window.initSqlJs({ locateFile: f => "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/" + f }));
        const s = document.createElement("script");
        s.src = "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/sql-wasm.js";
        s.onload = () => {
          if (!window.initSqlJs) return reject(new Error("sql.js failed to load"));
          resolve(window.initSqlJs({ locateFile: f => "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/" + f }));
        };
        s.onerror = () => reject(new Error("sql.js CDN unreachable"));
        document.head.appendChild(s);
      });
    }
    return sqlJsPromise;
  }

  function sqlNormRow(v) { return (v === null || v === undefined) ? "" : String(v); }
  function sqlExtractResult(res) {
    if (!res || !res.length) return { columns: [], rows: [] };
    const last = res[res.length - 1];
    return { columns: last.columns || [], rows: (last.values || []).map(r => r.map(sqlNormRow)) };
  }
  function sqlFreshDb(SQL, q) {
    const db = new SQL.Database();
    db.run(q.setupSql);
    return db;
  }
  function sqlRunUser(SQL, q, userSql) {
    const db = sqlFreshDb(SQL, q);
    let actual;
    if (q.verifyTable) {
      db.run(userSql);
      const qt = q.verifyTable.replace(/"/g, '""');
      actual = sqlExtractResult(db.exec(`SELECT * FROM "${qt}" ORDER BY id`));
    } else {
      actual = sqlExtractResult(db.exec(userSql));
    }
    db.close();
    return actual;
  }
  function sqlGetExpected(SQL, q) {
    if (q.expectedSql) {
      const db = sqlFreshDb(SQL, q);
      const exp = sqlExtractResult(db.exec(q.expectedSql));
      db.close();
      return exp;
    }
    if (q.expectedResult) {
      return { columns: q.expectedResult.columns, rows: q.expectedResult.rows.map(r => r.map(sqlNormRow)) };
    }
    return null;
  }

  // ---------- pixel-art sprites ----------
  // Each icon: array of strings, '1' = fill (currentColor). Built into an SVG sprite.
  const ICONS = {
    "ic-trophy": [
      "..11....11..",".1111..1111.",".1111111111.",".1111111111.","..11111111..","...111111...",
      "....1111....","....1..1....","..11111111..","..1......1..",
    ],
    "ic-sword": [
      ".......11...","......11....",".....11.....","....11......","...11.......","..11........",
      ".11.........","11..........",".1..........","..11........","..11........","..11........",
    ],
    "ic-shield": [
      "..1111..",".111111.","11111111","11111111","11111111",".111111.",".1.11.1.","...11...",
    ],
    "ic-scroll": [
      ".1111111.","1.......1","1.11111.1","1.1...1.1","1.1...1.1","1.11111.1","1.......1",".1111111.",
    ],
    "ic-key": [
      "....11....","....11....","....11....",".11111111.","1.1....1.1",".1111111..","....1.1...","....11....","....1.....",
    ],
    "ic-play": [
      "1.......","11......","111.....","1111....","11111...","1111....","111.....","11......","1.......",
    ],
    "ic-star": [
      "...11...","...11...","11111111","11111111",".111111.","..1111..",".111111.",".1.11.1.","1......1",
    ],
    "ic-skull": [
      "..1111..",".111111.","11111111","11.11.11","11111111",".111111.","..1..1..",".111111.","..11.11.",
    ],
    "ic-controller": [
      ".1111111111.","1..........1","1.111..111.1","1.1.1..1.1.1","1.111..111.1","1..........1",".1111111111.",
    ],
    "ic-crystal": [
      "...11...","..1111..",".111111.","11111111","11111111",".111111.","..1111..","...11...",
    ],
    "ic-book": [
      ".111111.","1......1","1.1111.1","1.1..1.1","1.1..1.1","1.1111.1","1......1",".111111.",
    ],
    "ic-quest": [
      "...11...","...11...","..1111..",".111111.","11111111","11111111",".111111.","..1..1..","..1..1..",
    ],
    "ic-check": [
      "........1.",".......11.","......11..",".....11...",".11.11....",".1111.....","..11......","..........",
    ],
    "ic-arrow": [
      "....1....","...111...","..11111..",".1111111.","111111111",".1.....1.","..1....1.","...1...1.",
    ],
    "ic-lock": [
      "..1..1..",".1.11.1.",".111111.","11111111","1.1.1.1.","1.1.1.1.","1.1.1.1.","11111111",
    ],
  };

  // Avatars: multi-color pixel portraits. chars map to palette colors.
  const AVATARS = [
    { id: "av-knight", name: "KNIGHT", map: { "h": "#c9ccd6", "s": "#e8b48c", "a": "#3a4a8c", "r": "#ff2e88", "k": "#222233" }, art: [
      "..hhhh..",".hhhhhh.","hhs sshh","hhs sshh",".hssssh.","..aaaa..",".aaaaaa.","..aaaa..",
    ]},
    { id: "av-mage", name: "MAGE", map: { "h": "#7b4aff", "s": "#e8b48c", "b": "#1a1a4a", "w": "#ffb000", "k": "#222233" }, art: [
      "..hhhh..",".hhhhhh.","hhw  whh","hhs sshh",".hssssh.","..bbbb..",".bwwbww.","..bbbb..",
    ]},
    { id: "av-rogue", name: "ROGUE", map: { "h": "#2a2a3a", "s": "#c9a07a", "g": "#39ff14", "c": "#0a0a12", "k": "#222233" }, art: [
      "..hhhh..",".hggggh.","hggs ggh","hggs ggh",".hssssh.","..cccc..",".ccggcc.","..cccc..",
    ]},
    { id: "av-robot", name: "ROBOT", map: { "m": "#9aa3b2", "e": "#00e5ff", "b": "#3a4a8c", "k": "#222233" }, art: [
      ".mmmmmm.","mmeeee m","memm mem","mmmmmmmm",".mkmmkm.",".bbbbbb.",".b.b.b.b",".bbbbbb.",
    ]},
  ];

  function buildSprite() {
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("aria-hidden", "true");
    svg.style.cssText = "position:absolute;width:0;height:0;overflow:hidden";
    // single-color icons (use currentColor via fill)
    for (const [id, rows] of Object.entries(ICONS)) {
      const w = rows[0].length, h = rows.length;
      const sym = document.createElementNS(NS, "symbol");
      sym.setAttribute("id", id);
      sym.setAttribute("viewBox", `0 0 ${w} ${h}`);
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          if (rows[y][x] === "1") {
            const r = document.createElementNS(NS, "rect");
            r.setAttribute("x", x); r.setAttribute("y", y);
            r.setAttribute("width", 1); r.setAttribute("height", 1);
            sym.appendChild(r);
          }
        }
      }
      svg.appendChild(sym);
    }
    // multi-color avatars
    for (const av of AVATARS) {
      const w = av.art[0].length, h = av.art.length;
      const sym = document.createElementNS(NS, "symbol");
      sym.setAttribute("id", av.id);
      sym.setAttribute("viewBox", `0 0 ${w} ${h}`);
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const ch = av.art[y][x];
          if (ch === "." || ch === " ") continue;
          const r = document.createElementNS(NS, "rect");
          r.setAttribute("x", x); r.setAttribute("y", y);
          r.setAttribute("width", 1); r.setAttribute("height", 1);
          r.setAttribute("fill", av.map[ch] || "#fff");
          sym.appendChild(r);
        }
      }
      svg.appendChild(sym);
    }
    document.getElementById("spriteMount").appendChild(svg);
  }

  // ---------- starfield ----------
  function buildStarfield() {
    const sf = document.getElementById("starfield");
    const n = 40;
    for (let i = 0; i < n; i++) {
      const s = document.createElement("div");
      s.className = "star";
      s.style.left = Math.random() * 100 + "%";
      s.style.animationDuration = (4 + Math.random() * 8) + "s";
      s.style.animationDelay = (-Math.random() * 8) + "s";
      const sz = 1 + Math.floor(Math.random() * 3);
      s.style.width = s.style.height = sz + "px";
      sf.appendChild(s);
    }
  }

  // ---------- avatars ----------
  const AVATAR_KEY = "dbms_quest_avatar_v1";
  function loadAvatar() {
    try { return localStorage.getItem(AVATAR_KEY) || "av-knight"; } catch (e) { return "av-knight"; }
  }
  function saveAvatar(id) { try { localStorage.setItem(AVATAR_KEY, id); } catch (e) {} }
  state.avatar = loadAvatar();

  function renderAvatarPicker() {
    const row = document.getElementById("avatarRow");
    const nameEl = document.getElementById("avatarName");
    row.innerHTML = "";
    AVATARS.forEach(av => {
      const card = document.createElement("div");
      card.className = "avatar-card" + (av.id === state.avatar ? " sel" : "");
      card.innerHTML = `<svg viewBox="0 0 8 8"><use href="#${av.id}"/></svg>`;
      card.title = av.name;
      card.addEventListener("click", () => {
        state.avatar = av.id; saveAvatar(av.id); beep("nav");
        renderAvatarPicker(); updateHudAvatar();
      });
      row.appendChild(card);
    });
    const cur = AVATARS.find(a => a.id === state.avatar) || AVATARS[0];
    nameEl.textContent = "-- " + cur.name + " --";
  }

  function updateHudAvatar() {
    const u = document.getElementById("hudAvatar").querySelector("use");
    if (u) u.setAttribute("href", "#" + state.avatar);
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
  // Track where we came from so BACK can return to the Guide lesson, not just
  // the Quest Log, when a quest was opened from inside a lesson.
  let cameFrom = null; // { target, payload } of the previous view, set when navigating to a quest/lesson

  function go(target, payload) {
    if (target === "title") {
      cameFrom = null;
      state.currentLessonId = null;
      titleScreen.classList.add("active");
      hud.classList.add("hidden");
      view.innerHTML = "";
      beep("nav");
      return;
    }
    titleScreen.classList.remove("active");
    hud.classList.remove("hidden");
    beep("nav");
    // Clear currentLessonId when leaving the guide, so qlinks only record the
    // guide origin when actually inside a lesson.
    if (target !== "lesson" && target !== "quest") {
      state.currentLessonId = null;
    }
    if (target === "quests") renderQuests();
    else if (target === "quest") renderQuest(payload);
    else if (target === "lessons") renderLessons();
    else if (target === "lesson") renderLesson(payload);
    else if (target === "progress") renderProgress();
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  // Open a quest and remember where we came from (used by guide qlinks).
  function openQuestFrom(fromTarget, fromPayload, questId) {
    cameFrom = { target: fromTarget, payload: fromPayload };
    go("quest", questId);
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
      const done = isDone(q.id);
      const diffIcon = q.difficulty === "Hard" ? "ic-skull" : (q.difficulty === "Medium" ? "ic-sword" : "ic-shield");
      const card = document.createElement("div");
      card.className = "quest-card" + (done ? " done" : "");
      card.innerHTML = `
        <span class="q-id">${q.id}</span>
        <span class="q-title">${escapeHtml(q.title)}</span>
        <span class="q-diff ${q.difficulty}"><svg class="ic"><use href="#${diffIcon}"/></svg>${q.difficulty.toUpperCase()}</span>
        <svg class="ic q-icon ${done ? "done" : "todo"}"><use href="#${done ? "ic-check" : "ic-quest"}"/></svg>
        <span class="q-status ${done ? "done" : ""}">${done ? "CLR" : "..."}</span>
      `;
      card.addEventListener("click", () => go("quest", q.id));
      list.appendChild(card);
    });
  }

  // ---------- SQL execution (via backend MySQL API) ----------
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

  function offlineBanner() {
    return `<div class="result-error">NO SQL ENGINE AVAILABLE.<br>Run locally with <code>site/.venv/bin/python site/server.py</code> for MySQL,<br>or ensure you have internet access for in-browser SQLite.</div>`;
  }

  async function handleRun(q, userSql, resultArea, statusEl) {
    if (!userSql.trim()) { showStatus(statusEl, "EMPTY SQL", "err"); return; }
    const hasBackend = await checkBackend();
    if (hasBackend) {
      showStatus(statusEl, "RUNNING...", "dim");
      try {
        const res = await api("/api/run", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: q.id, sql: userSql }),
        });
        if (!res.ok) throw new Error(res.error || "run failed");
        resultArea.innerHTML = resultTableHtml(res.result.columns, res.result.rows);
        showStatus(statusEl, "RUN OK", "ok");
        beep("nav");
        return;
      } catch (e) {
        resultArea.innerHTML = `<pre class="result-error">SQL ERROR: ${escapeHtml(String(e.message || e))}</pre>`;
        showStatus(statusEl, "ERROR", "err");
        beep("err");
        return;
      }
    }
    // Fallback: sql.js (SQLite WASM in browser)
    showStatus(statusEl, "LOADING SQLITE...", "dim");
    try {
      const SQL = await getSqlJs();
      activeEngine = "sqlite";
      updateEngineBadge();
      const actual = sqlRunUser(SQL, q, userSql);
      resultArea.innerHTML = resultTableHtml(actual.columns, actual.rows);
      showStatus(statusEl, "RUN OK", "ok");
      beep("nav");
    } catch (e) {
      resultArea.innerHTML = offlineBanner();
      showStatus(statusEl, "NO ENGINE", "err");
      beep("err");
    }
  }

  async function handleTest(q, userSql, resultArea, statusEl) {
    if (!userSql.trim()) { showStatus(statusEl, "EMPTY SQL", "err"); return; }
    const hasBackend = await checkBackend();
    if (hasBackend) {
      showStatus(statusEl, "TESTING...", "dim");
      try {
        const res = await api("/api/test", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: q.id, sql: userSql }),
        });
        if (!res.ok) throw new Error(res.error || "test failed");
        renderTestResult(res.passed, res.actual, res.expected || { columns: [], rows: [] }, q, resultArea, statusEl);
        return;
      } catch (e) {
        resultArea.innerHTML = `<pre class="result-error">SQL ERROR: ${escapeHtml(String(e.message || e))}</pre>`;
        showStatus(statusEl, "ERROR", "err");
        beep("err");
        return;
      }
    }
    // Fallback: sql.js (SQLite WASM in browser)
    showStatus(statusEl, "LOADING SQLITE...", "dim");
    try {
      const SQL = await getSqlJs();
      activeEngine = "sqlite";
      updateEngineBadge();
      const actual = sqlRunUser(SQL, q, userSql);
      const expected = sqlGetExpected(SQL, q);
      const passed = resultsMatch(actual, expected, q.orderSensitive);
      renderTestResult(passed, actual, expected, q, resultArea, statusEl);
    } catch (e) {
      resultArea.innerHTML = offlineBanner();
      showStatus(statusEl, "NO ENGINE", "err");
      beep("err");
    }
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

  function renderTestResult(passed, actual, expected, q, resultArea, statusEl) {
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
  }

  function updateEngineBadge() {
    const badge = document.getElementById("engineBadge");
    if (!badge) return;
    if (activeEngine === "mysql" && lastHealth) {
      badge.textContent = "MYSQL " + (lastHealth.version || "").split("-")[0];
      badge.className = "console-engine mysql";
    } else if (activeEngine === "sqlite") {
      badge.textContent = "SQLITE (BROWSER)";
      badge.className = "console-engine sqlite";
    } else {
      badge.textContent = "...";
      badge.className = "console-engine";
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
    btn.innerHTML = `<svg class="ic"><use href="#${done ? "ic-check" : "ic-trophy"}"/></svg> ${done ? "[ CLEARED ] - UNDO" : "[ MARK CLEARED ]"}`;
  }

  // ---------- quest detail ----------
  function renderQuest(id) {
    const q = DATA.questions.find(x => String(x.id) === String(id));
    if (!q) { go("quests"); return; }
    const node = tpl("tpl-quest");
    view.replaceChildren(node);
    // Wire the BACK button: return to the guide lesson if we came from one,
    // otherwise return to the Quest Log.
    const backBtn = view.querySelector(".back");
    if (cameFrom && cameFrom.target === "lesson") {
      backBtn.setAttribute("data-go", "lesson");
      backBtn.setAttribute("data-payload", cameFrom.payload);
      backBtn.innerHTML = '<svg class="ic"><use href="#ic-book"/></svg> GUIDE';
    } else {
      backBtn.setAttribute("data-go", "quests");
      backBtn.innerHTML = '<svg class="ic"><use href="#ic-arrow"/></svg> BACK';
    }
    const detail = document.getElementById("questDetail");
    const done = isDone(q.id);
    const runnable = q.runnable && q.setupSql;
    detail.innerHTML = `
      <div class="qd-head">
        <div>
          <div class="qd-title">${q.id} :: ${escapeHtml(q.title)}</div>
          <div class="qd-meta">CATEGORY: <b>${escapeHtml(q.category)}</b> &nbsp; DIFF: <b>${q.difficulty}</b> &nbsp; ${runnable ? `FIXTURE: <b>${q.fixtureKind}</b>` : "<b>NO LOCAL FIXTURE</b>"}</div>
        </div>
        <a class="ext-link" href="${q.leetcode}" target="_blank" rel="noopener">&gt; LEETCODE</a>
      </div>

      <div class="qd-split">
        <div class="qd-pane" id="qdLeft">
          <div class="qd-section">
            <h3><svg class="ic"><use href="#ic-scroll"/></svg> BRIEFING</h3>
            <div class="qd-prompt">${q.promptHtml || "<p>No dumped prompt for this question.</p>"}</div>
          </div>
          <div class="qd-section" id="schemaSection">
            <h3><svg class="ic"><use href="#ic-shield"/></svg> TABLE DATA</h3>
            <div id="schemaArea"><p class="result-empty">-- LOADING SCHEMA... --</p></div>
          </div>
          <div class="qd-section">
            <h3><svg class="ic"><use href="#ic-scroll"/></svg> HINT</h3>
            <div class="reveal-wrap">
              <button class="reveal-btn" data-target="hint"><svg class="ic"><use href="#ic-scroll"/></svg> SHOW HINT</button>
              <div class="reveal-body" id="hint"><pre>${escapeHtml(q.hint)}</pre></div>
            </div>
          </div>
          <div class="qd-section">
            <h3><svg class="ic"><use href="#ic-key"/></svg> SOLUTION</h3>
            <div class="reveal-wrap">
              <button class="reveal-btn" data-target="sol"><svg class="ic"><use href="#ic-key"/></svg> REVEAL</button>
              <div class="reveal-body" id="sol"><pre><code>${escapeHtml(q.solution)}</code></pre></div>
            </div>
          </div>
        </div>

        <div class="qd-pane" id="qdRight">
          ${runnable ? renderEditorSlot() : '<p class="no-fixture">-- NO LOCAL FIXTURE: BRIEFING ONLY --</p>'}

          <button class="complete-btn ${done ? "done" : ""}" id="completeBtn">
            <svg class="ic"><use href="#${done ? "ic-check" : "ic-trophy"}"/></svg> ${done ? "[ CLEARED ] - UNDO" : "[ MARK CLEARED ]"}
          </button>
        </div>
      </div>
    `;
    detail.querySelectorAll(".reveal-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const body = detail.querySelector("#" + btn.dataset.target);
        const open = body.classList.toggle("open");
        btn.innerHTML = open
          ? `<svg class="ic"><use href="#${btn.dataset.target === "sol" ? "ic-key" : "ic-scroll"}"/></svg> HIDE`
          : `<svg class="ic"><use href="#${btn.dataset.target === "sol" ? "ic-key" : "ic-scroll"}"/></svg> ${btn.dataset.target === "sol" ? "REVEAL" : "SHOW HINT"}`;
        beep("nav");
      });
    });
    document.getElementById("completeBtn").addEventListener("click", () => {
      toggleDone(q.id);
      renderQuest(q.id);
    });
    if (runnable) wireEditor(q);
    if (runnable) loadSchema(q);
    else document.getElementById("schemaArea").innerHTML = '<p class="result-empty">-- NO LOCAL FIXTURE --</p>';
  }

  async function loadSchema(q) {
    const area = document.getElementById("schemaArea");
    if (!area) return;
    const hasBackend = await checkBackend();
    if (hasBackend) {
      try {
        const res = await api("/api/schema/" + q.id);
        if (!res.tables || !res.tables.length) {
          area.innerHTML = '<p class="result-empty">-- NO TABLES --</p>';
          return;
        }
        let html = "";
        res.tables.forEach(t => {
          html += `<div class="schema-table"><h4>${escapeHtml(t.name)}</h4>`;
          html += '<table class="result"><thead><tr><th>column</th><th>type</th></tr></thead><tbody>';
          t.columns.forEach(c => { html += `<tr><td>${escapeHtml(c[0])}</td><td>${escapeHtml(c[1])}</td></tr>`; });
          html += '</tbody></table>';
          if (t.sample && t.sample.rows.length) {
            html += '<p class="schema-sample-label">SAMPLE ROWS:</p>';
            html += resultTableHtml(t.sample.columns, t.sample.rows);
          }
          html += '</div>';
        });
        area.innerHTML = html;
        return;
      } catch (e) {
        area.innerHTML = `<pre class="result-error">SCHEMA ERROR: ${escapeHtml(String(e.message || e))}</pre>`;
        return;
      }
    }
    // Fallback: use sql.js to introspect schema in-browser
    try {
      const SQL = await getSqlJs();
      const db = new SQL.Database();
      db.run(q.setupSql);
      const tablesRes = db.exec("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name");
      const tables = tablesRes.length ? tablesRes[0].values.map(r => r[0]) : [];
      let html = "";
      tables.forEach(t => {
        const infoRes = db.exec(`PRAGMA table_info("${t.replace(/"/g,'""')}")`);
        html += `<div class="schema-table"><h4>${escapeHtml(t)}</h4>`;
        html += '<table class="result"><thead><tr><th>column</th><th>type</th></tr></thead><tbody>';
        if (infoRes.length) {
          infoRes[0].values.forEach(row => {
            html += `<tr><td>${escapeHtml(row[1])}</td><td>${escapeHtml(row[2])}</td></tr>`;
          });
        }
        html += '</tbody></table>';
        const sampleRes = db.exec(`SELECT * FROM "${t.replace(/"/g,'""')}" LIMIT 5`);
        if (sampleRes.length) {
          html += '<p class="schema-sample-label">SAMPLE ROWS:</p>';
          html += resultTableHtml(sampleRes[0].columns, sampleRes[0].values.map(r => r.map(sqlNormRow)));
        }
        html += '</div>';
      });
      db.close();
      area.innerHTML = html || '<p class="result-empty">-- NO TABLES --</p>';
    } catch (e) {
      area.innerHTML = `<pre class="result-error">SCHEMA ERROR: ${escapeHtml(String(e.message || e))}</pre>`;
    }
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
    const badge = document.getElementById("engineBadge");

    input.value = loadSql(q.id);
    input.addEventListener("input", () => saveSql(q.id, input.value));

    // engine badge: check backend, fall back to sqlite label
    checkBackend().then(ok => {
      if (ok) {
        activeEngine = "mysql";
      } else {
        activeEngine = "sqlite"; // will use sql.js on first RUN/TEST
      }
      updateEngineBadge();
    });

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
      li.innerHTML = `<svg class="ic"><use href="#ic-book"/></svg><span class="ll-id">${l.id.toUpperCase().slice(0, 8)}</span> ${escapeHtml(l.title)}`;
      li.addEventListener("click", () => go("lesson", l.id));
      list.appendChild(li);
    });
  }

  function renderLesson(id) {
    const l = DATA.lessons.find(x => x.id === id);
    if (!l) { go("lessons"); return; }
    state.currentLessonId = id;
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
    if (goBtn) {
      e.preventDefault();
      const target = goBtn.dataset.go;
      const payload = goBtn.dataset.payload || null;
      // Returning to a lesson from a quest: clear cameFrom so we don't loop
      if (target === "lesson" && cameFrom && cameFrom.target === "lesson") {
        cameFrom = null;
        go("lesson", payload);
        return;
      }
      go(target, payload);
      return;
    }
    const qlink = e.target.closest("[data-quest]");
    if (qlink) {
      e.preventDefault();
      // If we're inside a lesson, remember it so BACK returns to the guide
      if (state.currentLessonId != null) {
        cameFrom = { target: "lesson", payload: state.currentLessonId };
      } else {
        cameFrom = { target: "quests", payload: null };
      }
      go("quest", qlink.dataset.quest);
      return;
    }
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

  buildSprite();
  buildStarfield();
  renderAvatarPicker();
  updateHudAvatar();
  renderHud();
})();
