const state = {
  view: "home",
  bootstrap: null,
  ideas: [],
  project: null,
  shots: null,
  visualPlan: null,
};

const stage = () => document.getElementById("stage");
const $ = (sel, el = document) => el.querySelector(sel);

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  // Don't force JSON content-type for FormData uploads
  if (!(opts.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(path, {
    ...opts,
    headers,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = data?.detail || data?.message || res.statusText || "Request failed";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function toast(msg, ms = 4200) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add("hidden"), ms);
}

function overlay(on, text = "Working…") {
  const el = document.getElementById("overlay");
  document.getElementById("overlay-text").textContent = text;
  el.classList.toggle("hidden", !on);
}

async function withBusy(text, fn) {
  overlay(true, text);
  try {
    return await fn();
  } finally {
    overlay(false);
  }
}

function esc(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setNav(view) {
  document.querySelectorAll(".nav-link").forEach((b) => {
    b.classList.toggle("active", b.dataset.go === view || (view === "project" && b.dataset.go === "library"));
  });
}

function renderCreds(creds) {
  const host = document.getElementById("cred-pills");
  if (!creds) {
    host.innerHTML = "";
    return;
  }
  const cls = (s) => (s === "ok" ? "ok" : s === "unchecked" ? "" : "bad");
  host.innerHTML = `
    <span class="pill ${cls(creds.openai.status)}">OpenAI · ${esc(creds.openai.status)}</span>
    <span class="pill ${cls(creds.elevenlabs.status)}">ElevenLabs · ${esc(creds.elevenlabs.status)}</span>
    <button class="btn btn-ghost" style="padding:0.35rem 0.7rem;font-size:0.75rem" id="recheck">Recheck</button>
  `;
  $("#recheck", host)?.addEventListener("click", async () => {
    try {
      const c = await withBusy("Checking keys…", () => api("/api/credentials/recheck", { method: "POST" }));
      state.bootstrap.credentials = c;
      renderCreds(c);
      toast(c.ready_research ? "OpenAI ready" : c.openai.detail);
    } catch (e) {
      toast(e.message);
    }
  });
}

function go(view, payload = null) {
  state.view = view;
  if (payload) Object.assign(state, payload);
  setNav(view === "project" ? "library" : view);
  render();
}

async function boot() {
  try {
    state.bootstrap = await api("/api/bootstrap");
    renderCreds(state.bootstrap.credentials);
    const hash = location.hash.replace("#", "");
    if (hash.startsWith("project/")) {
      const id = decodeURIComponent(hash.slice("project/".length));
      await openProject(id);
      return;
    }
    if (hash === "ideas") return go("ideas");
    if (hash === "library") return go("library");
    go("home");
  } catch (e) {
    stage().innerHTML = `<div class="panel"><p class="notice bad">${esc(e.message)}</p></div>`;
  }
}

async function openProject(id) {
  const data = await withBusy("Opening episode…", () => api(`/api/projects/${encodeURIComponent(id)}`));
  state.project = data.project;
  state.shots = null;
  location.hash = `project/${id}`;
  go("project");
}

function render() {
  const v = state.view;
  if (v === "home") return renderHome();
  if (v === "ideas") return renderIdeas();
  if (v === "library") return renderLibrary();
  if (v === "project") return renderProject();
}

function renderHome() {
  const b = state.bootstrap;
  const s = b.stats;
  const pct = Math.min(100, Math.round((s.day / Math.max(1, s.goal)) * 100));
  stage().innerHTML = `
    <section class="hero">
      <div class="panel soft">
        <p class="kicker">Channel</p>
        <h1 class="h1">${esc(b.channel.name)}</h1>
        <p class="lead">${esc(b.channel.tagline)} One true story a day. Research → script → Flow → voice → render.</p>
        <p class="lead" style="font-size:0.9rem;opacity:.85">
          Datos: <code>${esc((b.workspace && b.workspace.projects_dir) || "projects/")}</code>
          ${b.workspace && b.workspace.supabase
            ? " · Supabase listo (Subir / Bajar entre PCs)"
            : b.workspace && b.workspace.synced
              ? " · sync carpeta activo"
              : " · solo esta PC"}
        </p>
        <div class="actions">
          <button class="btn btn-primary" id="cta-new">Create today's video</button>
          <button class="btn btn-ghost" id="cta-lib">Browse library</button>
          ${b.workspace && b.workspace.supabase ? `
          <button class="btn btn-ghost" id="cta-push">Subir a la nube</button>
          <button class="btn btn-ghost" id="cta-pull">Bajar de la nube</button>` : ""}
        </div>
        <p id="sync-msg" class="lead" style="font-size:0.85rem;min-height:1.2em;opacity:.9"></p>
      </div>
      <div class="day-card">
        <div class="label">Challenge progress · ${pct}%</div>
        <div class="big">${String(s.day).padStart(2, "0")}<span style="opacity:.45;font-size:.45em"> / ${s.goal}</span></div>
        <div class="meta">
          <div><span>Done</span><strong>${s.completed}</strong></div>
          <div><span>Active</span><strong>${s.in_progress}</strong></div>
          <div><span>Left</span><strong>${s.remaining}</strong></div>
        </div>
      </div>
    </section>
    <div class="section-head">
      <div>
        <h2>Recent episodes</h2>
        <p>Continue where you left off</p>
      </div>
    </div>
    <div class="list" id="recent"></div>
  `;
  $("#cta-new").onclick = () => {
    location.hash = "ideas";
    go("ideas");
  };
  $("#cta-lib").onclick = () => {
    location.hash = "library";
    go("library");
  };
  const syncMsg = $("#sync-msg");
  const bindSync = (id, path, label) => {
    const btn = $(id);
    if (!btn) return;
    btn.onclick = async () => {
      btn.disabled = true;
      if (syncMsg) syncMsg.textContent = `${label}…`;
      try {
        const r = await api(path, { method: "POST" });
        const n = (r.projects || []).length;
        if (syncMsg) {
          syncMsg.textContent =
            path.includes("push")
              ? `Subido: ${n} episodio(s) + sesión.`
              : `Bajado: ${(r.remote_ids || []).length} episodio(s) + sesión. Recargá Home.`;
        }
        if (path.includes("pull")) {
          await refreshBootstrap();
          go("home");
        }
      } catch (e) {
        if (syncMsg) syncMsg.textContent = String(e.message || e);
      } finally {
        btn.disabled = false;
      }
    };
  };
  bindSync("#cta-push", "/api/sync/push", "Subiendo a Supabase");
  bindSync("#cta-pull", "/api/sync/pull", "Bajando de Supabase");
  const host = $("#recent");
  if (!b.projects.length) {
    host.innerHTML = `<div class="panel"><p class="lead">No episodes yet. Start today's video.</p></div>`;
    return;
  }
  const firstOpen = b.projects.find((p) => p.status !== "complete") || b.projects[0];
  host.innerHTML =
    (firstOpen
      ? `<div class="panel" style="margin-bottom:1rem">
          <p class="kicker">Continuar Video ${String(firstOpen.episode_number).padStart(3, "0")}</p>
          <h3>${esc(firstOpen.title)}</h3>
          <p class="lead">No abras “New episode” si todavía estás en el Video 1.</p>
          <button class="btn btn-primary" data-open="${esc(firstOpen.id)}">Abrir este episodio</button>
        </div>`
      : "") +
    b.projects
      .slice(0, 8)
      .map(
        (p) => `
      <article class="row">
        <div class="ep">${String(p.episode_number).padStart(3, "0")}</div>
        <div>
          <h3>${esc(p.title)}</h3>
          <p>${p.status === "complete" ? "Complete" : "In progress"} · ${esc(p.ui_step)}</p>
        </div>
        <button class="btn btn-soft" data-open="${esc(p.id)}">Continue</button>
      </article>`
      )
      .join("");
  host.querySelectorAll("[data-open]").forEach((btn) => {
    btn.onclick = () => openProject(btn.dataset.open);
  });
}

async function renderIdeas() {
  stage().innerHTML = `
    <p class="kicker">New episode</p>
    <h1 class="h1">Pick a story engine</h1>
    <p class="lead">Five true-story angles. Choose one, or drop your own topic.</p>
    <div class="actions" style="margin-bottom:1.2rem">
      <button class="btn btn-accent" id="gen-ideas">Generate ideas</button>
      <button class="btn btn-ghost" id="manual">I have a topic</button>
      <button class="btn btn-ghost" id="back-home">Back</button>
    </div>
    <div id="manual-box" class="panel hidden field" style="margin-bottom:1rem">
      <label>Topic / working title</label>
      <input id="manual-topic" placeholder="e.g. The SoftBank bet that almost buried WeWork"/>
      <div class="actions">
        <button class="btn btn-primary" id="manual-go">Continue</button>
      </div>
    </div>
    <div class="idea-grid" id="ideas"></div>
  `;
  $("#back-home").onclick = () => {
    location.hash = "";
    go("home");
  };
  $("#manual").onclick = () => $("#manual-box").classList.toggle("hidden");
  $("#manual-go").onclick = async () => {
    const topic = $("#manual-topic").value.trim();
    if (!topic) return toast("Write a topic first");
    try {
      const data = await withBusy("Creating episode…", () =>
        api("/api/projects", { method: "POST", body: JSON.stringify({ topic, title: topic }) })
      );
      state.project = data.project;
      location.hash = `project/${data.project.id}`;
      go("project");
      await refreshBootstrap();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#gen-ideas").onclick = () => loadIdeas(true);
  if (state.ideas.length) paintIdeas();
  else {
    $("#ideas").innerHTML = `
      <div class="panel">
        <p class="lead">No ideas yet. Press <strong>Generate ideas</strong> when you want AI suggestions — it does not run automatically.</p>
      </div>`;
  }
}

async function loadIdeas(force) {
  try {
    const data = await withBusy("Finding story engines…", () =>
      api("/api/ideas", { method: "POST", body: JSON.stringify({ count: 5 }) })
    );
    state.ideas = data.ideas || [];
    paintIdeas();
    if (force) toast("Ideas ready");
  } catch (e) {
    toast(e.message);
    $("#ideas").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`;
  }
}

function paintIdeas() {
  const host = $("#ideas");
  if (!host) return;
  host.innerHTML = state.ideas
    .map(
      (idea, i) => `
      <article class="idea">
        <h3>${esc(idea.title_concept || "Untitled")}</h3>
        <p>${esc(idea.story || "")}</p>
        <p><strong style="color:var(--ink)">Hook</strong> — ${esc(idea.hook || "—")}</p>
        <div class="tags">
          <span class="tag">${esc(idea.content_pillar || "story")}</span>
          <span class="tag">visual ${esc(idea.visual_potential || "—")}</span>
          <span class="tag">research ${esc(idea.research_risk || "—")}</span>
        </div>
        <div class="actions">
          <button class="btn btn-primary" data-pick="${i}">Choose this story</button>
        </div>
      </article>`
    )
    .join("");
  host.querySelectorAll("[data-pick]").forEach((btn) => {
    btn.onclick = async () => {
      const idea = state.ideas[Number(btn.dataset.pick)];
      try {
        const data = await withBusy("Creating episode…", () =>
          api("/api/projects", { method: "POST", body: JSON.stringify({ idea }) })
        );
        state.project = data.project;
        state.ideas = [];
        location.hash = `project/${data.project.id}`;
        go("project");
        await refreshBootstrap();
      } catch (e) {
        toast(e.message);
      }
    };
  });
}

function renderLibrary() {
  const projects = state.bootstrap?.projects || [];
  stage().innerHTML = `
    <p class="kicker">Library</p>
    <h1 class="h1">All episodes</h1>
    <div class="actions" style="margin-bottom:1rem">
      <button class="btn btn-primary" id="new">New episode</button>
      <button class="btn btn-ghost" id="home">Home</button>
    </div>
    <div class="list" id="lib"></div>
  `;
  $("#new").onclick = () => {
    location.hash = "ideas";
    go("ideas");
  };
  $("#home").onclick = () => {
    location.hash = "";
    go("home");
  };
  $("#lib").innerHTML = projects.length
    ? projects
        .map(
          (p) => `
        <article class="row">
          <div class="ep">${String(p.episode_number).padStart(3, "0")}</div>
          <div>
            <h3>${esc(p.title)}</h3>
            <p>${p.status === "complete" ? "Complete" : "In progress"} · ${esc(p.ui_step)}</p>
          </div>
          <button class="btn btn-soft" data-open="${esc(p.id)}">Open</button>
        </article>`
        )
        .join("")
    : `<div class="panel"><p class="lead">Empty library.</p></div>`;
  document.querySelectorAll("[data-open]").forEach((btn) => {
    btn.onclick = () => openProject(btn.dataset.open);
  });
}

function renderProject() {
  const p = state.project;
  if (!p) return go("home");
  const step = p.ui_step || "research";
  const steps = ["topic", "research", "story", "script", "flow", "images", "voice", "render", "done"];
  const stepLabel = {
    topic: "1 Tema",
    research: "2 Info",
    story: "3 Historia",
    script: "4 Guion",
    flow: "5 Pedir imgs",
    images: "6 Subir imgs",
    voice: "7 Voz",
    render: "8 Video",
    done: "Listo",
  };
  const flags = p.progress?.flags || {};
  stage().innerHTML = `
    <p class="kicker">Episodio ${String(p.episode_number).padStart(3, "0")}</p>
    <h1 class="h1">${esc(p.title || p.topic)}</h1>
    <p class="lead">${esc(p.topic || "")}</p>
    <div class="stepper">
      ${steps
        .map((s) => {
          const cls = s === step ? "now" : flags[s] ? "done" : "";
          return `<button class="step ${cls}" data-step="${s}">${stepLabel[s] || s}</button>`;
        })
        .join("")}
    </div>
    <div class="workspace" id="ws"></div>
  `;
  stage()
    .querySelectorAll("[data-step]")
    .forEach((btn) => {
      btn.onclick = async () => {
        try {
          const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
            method: "PATCH",
            body: JSON.stringify({ step: btn.dataset.step }),
          });
          state.project = data.project;
          renderProject();
        } catch (e) {
          toast(e.message);
        }
      };
    });
  const ws = $("#ws");
  if (step === "topic") return paintStory(ws, p);
  if (step === "research") return paintResearch(ws, p);
  if (step === "story") return paintStoryPlan(ws, p);
  if (step === "script") return paintScript(ws, p);
  if (step === "flow") return paintFlow(ws, p);
  if (step === "images") return paintImages(ws, p);
  if (step === "voice") return paintVoice(ws, p);
  if (step === "render" || step === "done") return paintRender(ws, p);
  paintResearch(ws, p);
}

function paintStory(ws, p) {
  const idea = p.idea || {};
  ws.innerHTML = `
    <div class="panel">
      <p class="kicker">Topic</p>
      <p>${esc(idea.story || p.topic)}</p>
      <p style="margin-top:0.8rem"><strong>Hook</strong> — ${esc(idea.hook || "—")}</p>
      <div class="actions">
        <button class="btn btn-primary" id="to-research">Continue to research</button>
      </div>
    </div>`;
  $("#to-research").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "research" }),
    });
    state.project = data.project;
    renderProject();
  };
}

function paintResearch(ws, p) {
  ws.innerHTML = `
    <div class="panel workspace">
      <div class="actions">
        <button class="btn btn-accent" id="gen-research">Generate research with AI</button>
        <button class="btn btn-primary" id="save-research">Save & continue to Story Plan</button>
        <button class="btn btn-ghost" id="skip-research">Skip for now</button>
      </div>
      <div class="field">
        <label>Research notes</label>
        <textarea id="notes" rows="14">${esc(p.research_notes)}</textarea>
      </div>
      <div class="field">
        <label>Sources (one per line)</label>
        <textarea id="sources" rows="4">${esc((p.sources || []).join("\n"))}</textarea>
      </div>
    </div>`;
  $("#gen-research").onclick = async () => {
    try {
      const data = await withBusy("Investigating…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/research/generate`, { method: "POST" })
      );
      state.project = data.project;
      toast("Research brief ready — edit anything wrong");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  const save = async (skipped) => {
    try {
      const data = await api(`/api/projects/${encodeURIComponent(p.id)}/research`, {
        method: "PUT",
        body: JSON.stringify({
          notes: $("#notes").value,
          sources: $("#sources").value.split("\n").map((s) => s.trim()).filter(Boolean),
          skipped,
        }),
      });
      state.project = data.project;
      state.project.ui_step = "story";
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#save-research").onclick = () => save(false);
  $("#skip-research").onclick = () => save(true);
}

function paintStoryPlan(ws, p) {
  const plan = p.story_plan || {};
  const md = p.story_plan_markdown || "";
  const warnings = (plan.warnings || []).map((w) => `<div class="notice">${esc(w)}</div>`).join("");
  const beats = (plan.beats || [])
    .map((b) => {
      const ids = plan.selected_beat_ids || [];
      const pri = String(b.priority || "").toLowerCase();
      const checked =
        ids.length > 0
          ? ids.map(Number).includes(Number(b.id))
            ? "checked"
            : ""
          : pri === "essential" || pri === "strong"
            ? "checked"
            : "";
      return `<label class="shot" style="display:block;margin:0.35rem 0">
        <input type="checkbox" data-beat="${b.id}" ${checked}/> 
        <strong>[${esc(b.priority)}]</strong> ${esc(b.event)}
        <div class="ff-episode-meta">${esc(b.time_period || "")} — ${esc(b.why_it_matters || "")}</div>
      </label>`;
    })
    .join("");
  ws.innerHTML = `
    <div class="panel workspace">
      ${warnings}
      ${plan.central_story && !p.story_plan_approved ? `<div class="notice">Plan listo — apretá <strong>Approve Story → Script</strong> para desbloquear Generate script.</div>` : ""}
      ${p.story_plan_approved ? `<div class="notice">Story Plan aprobado. Ya podés ir a Script.</div>` : ""}
      <div class="actions">
        <button class="btn btn-accent" id="gen-story">Generate Story Plan</button>
        <button class="btn btn-ghost" id="save-story">Save edits</button>
        <button class="btn btn-primary" id="approve-story">Approve Story → Script</button>
      </div>
      <div class="field"><label>Central story</label><textarea id="cs" rows="2">${esc(plan.central_story || "")}</textarea></div>
      <div class="field"><label>Central question</label><textarea id="cq" rows="2">${esc(plan.central_question || "")}</textarea></div>
      <div class="field"><label>Core contradiction</label><textarea id="cc" rows="2">${esc(plan.core_contradiction || "")}</textarea></div>
      <div class="field"><label>Hook</label><textarea id="hk" rows="2">${esc(plan.hook || "")}</textarea></div>
      <div class="field"><label>Ending state</label><textarea id="es" rows="2">${esc(plan.ending_state || "")}</textarea></div>
      <div class="field"><label>Story beats (Essential/Strong selected)</label><div id="beats">${beats || "<p class='lead'>Generate a plan first.</p>"}</div></div>
      <pre class="shot" style="white-space:pre-wrap;max-height:220px;overflow:auto">${esc(md)}</pre>
    </div>`;
  $("#gen-story").onclick = async () => {
    try {
      const data = await withBusy("Designing story engine + beats…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/story/generate`, { method: "POST" })
      );
      state.project = data.project;
      toast("Story Plan ready — review before approving");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  const collectPlan = () => {
    const selected = [...document.querySelectorAll("[data-beat]:checked")].map((el) => Number(el.dataset.beat));
    return {
      ...plan,
      central_story: $("#cs").value,
      central_question: $("#cq").value,
      core_contradiction: $("#cc").value,
      hook: $("#hk").value,
      ending_state: $("#es").value,
      selected_beat_ids: selected.length ? selected : plan.selected_beat_ids || [],
      beats: plan.beats || [],
      characters: plan.characters || [],
      research_gaps: plan.research_gaps || {},
      unknown_or_weakly_supported: plan.unknown_or_weakly_supported || [],
    };
  };
  $("#save-story").onclick = async () => {
    try {
      const data = await api(`/api/projects/${encodeURIComponent(p.id)}/story`, {
        method: "PUT",
        body: JSON.stringify({ plan: collectPlan() }),
      });
      state.project = data.project;
      toast("Story Plan saved");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#approve-story").onclick = async () => {
    try {
      await api(`/api/projects/${encodeURIComponent(p.id)}/story`, {
        method: "PUT",
        body: JSON.stringify({ plan: collectPlan() }),
      });
      const data = await api(`/api/projects/${encodeURIComponent(p.id)}/story/approve`, { method: "POST" });
      state.project = data.project;
      toast("Story Plan approved");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
}

function paintScript(ws, p) {
  const tw = Number(p.target_words) || 2000;
  const plan = p.story_plan || {};
  const planReady = Boolean(plan.central_story) && Array.isArray(plan.beats) && plan.beats.length > 0;
  if (!p.story_plan_approved) {
    ws.innerHTML = `
      <div class="panel workspace">
        <div class="notice">Falta marcar el Story Plan como aprobado (no es lo mismo que guardar Research).</div>
        ${
          planReady
            ? `<p class="lead">Ya tenés central story + ${plan.beats.length} beats. Un clic y seguís.</p>
               <div class="actions">
                 <button class="btn btn-primary" id="approve-now">Aprobar Story Plan y continuar</button>
                 <button class="btn btn-ghost" id="go-story">Revisar Story</button>
               </div>`
            : `<p class="lead">Todavía no hay Story Plan. Generálo en el paso Story.</p>
               <div class="actions">
                 <button class="btn btn-primary" id="go-story">Ir a Story Plan</button>
               </div>`
        }
        <div class="field">
          <label>Narration (~${tw} words · flexible 1800–2200)</label>
          <textarea id="script" class="script-box" disabled>${esc(p.script)}</textarea>
        </div>
      </div>`;
    $("#go-story")?.addEventListener("click", async () => {
      const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
        method: "PATCH",
        body: JSON.stringify({ step: "story" }),
      });
      state.project = data.project;
      renderProject();
    });
    $("#approve-now")?.addEventListener("click", async () => {
      try {
        const data = await withBusy("Approving Story Plan…", () =>
          api(`/api/projects/${encodeURIComponent(p.id)}/story/approve`, { method: "POST" })
        );
        state.project = data.project;
        toast("Story Plan aprobado — ya podés Generate script");
        renderProject();
      } catch (e) {
        toast(e.message);
      }
    });
    return;
  }
  ws.innerHTML = `
    <div class="panel workspace">
      ${(p.script_warnings || []).length ? (p.script_warnings || []).map((w) => `<div class="notice">${esc(w)}</div>`).join("") : ""}
      <div class="actions">
        <button class="btn btn-accent" id="gen-script">Generate script</button>
        <button class="btn btn-ghost" id="save-script">Save edits</button>
        <button class="btn btn-primary" id="approve">Approve → Flow</button>
      </div>
      <div class="field">
        <label>Narration (~${tw} words · flexible 1800–2200)</label>
        <textarea id="script" class="script-box">${esc(p.script)}</textarea>
      </div>
    </div>`;
  $("#gen-script").onclick = async () => {
    try {
      const data = await withBusy("Writing from Story Plan (1 draft + quality if needed)…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/script/generate`, { method: "POST" })
      );
      state.project = data.project;
      toast("Script ready");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#save-script").onclick = async () => {
    try {
      const data = await api(`/api/projects/${encodeURIComponent(p.id)}/script`, {
        method: "PUT",
        body: JSON.stringify({ script: $("#script").value }),
      });
      state.project = data.project;
      toast("Saved");
    } catch (e) {
      toast(e.message);
    }
  };
  $("#approve").onclick = async () => {
    try {
      await api(`/api/projects/${encodeURIComponent(p.id)}/script`, {
        method: "PUT",
        body: JSON.stringify({ script: $("#script").value }),
      });
      const data = await withBusy("Approving & building Flow pack…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/script/approve`, { method: "POST" })
      );
      state.project = data.project;
      toast("Approved");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
}

async function paintFlow(ws, p) {
  ws.innerHTML = `<div class="panel"><p class="lead">Cargando plan de imágenes…</p></div>`;
  let plan = null;
  let shots = null;
  try {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/flow`);
    state.shots = data.shots;
    state.visualPlan = data.visual_plan;
    if (data.project) state.project = data.project;
    plan = data.visual_plan;
    shots = data.shots;
  } catch (e) {
    ws.innerHTML = `
      <div class="panel workspace">
        <h2>Todavía no hay plan de imágenes</h2>
        <p class="lead">Primero aprobá el guion. Después tocá el botón de abajo.</p>
        <div class="actions">
          <button class="btn btn-accent" id="rebuild">Crear plan de imágenes</button>
        </div>
        <div class="notice">${esc(e.message || "")}</div>
      </div>`;
    $("#rebuild").onclick = () => rebuildFlow();
    return;
  }

  const stats = (plan && plan.stats) || (shots && shots.stats) || {};
  const masters = (plan && plan.master_references) || (shots && shots.master_references) || [];
  const batches = (plan && plan.flow_batches) || (shots && shots.flow_batches) || [];
  const visuals = (plan && plan.visuals) || (shots && shots.shots) || [];
  const nonFlow = visuals.filter((v) => v.visual_type && v.visual_type !== "FLOW_REENACTMENT");
  const total = stats.total || visuals.length || 0;
  const needAi = stats.flow || 0;
  const needReal = stats.real_or_other || 0;

  ws.innerHTML = `
    <div class="panel workspace">
      <div class="panel soft" style="margin-bottom:1.2rem;border:2px solid var(--ink,#111)">
        <h2 style="margin:0 0 0.5rem">Qué tenés que hacer acá (paso a paso)</h2>
        <ol style="margin:0;padding-left:1.2rem;line-height:1.55">
          <li><strong>Pedí las imágenes en Google Flow</strong> (abajo hay grupos listos para copiar).</li>
          <li><strong>Descargalas</strong> a tu compu.</li>
          <li><strong>Renombrialas</strong> tipo <code>001.png</code>, <code>002.png</code>…</li>
          <li><strong>Subilas acá</strong> — tocá el botón negro grande.</li>
        </ol>
        <div class="actions" style="margin-top:1rem">
          <button class="btn btn-primary" id="to-images" style="font-size:1.05rem;padding:0.85rem 1.4rem">
            Ya las tengo → Subir imágenes
          </button>
        </div>
        <p class="lead" style="margin-top:0.75rem;margin-bottom:0">
          Estás en el paso <strong>5 Pedir imgs</strong>. La subida está en el paso <strong>6 Subir imgs</strong>
          (o usá el botón de arriba).
        </p>
      </div>

      <p class="lead">Este episodio necesita <strong>${total} imágenes</strong>:
        ${needAi} las pedís a Google Flow · ${needReal} son documentos/fotos reales (no las inventa la IA).
      </p>
      <div class="actions">
        <button class="btn btn-ghost" id="rebuild">Rehacer plan de imágenes</button>
      </div>

      <h2 style="margin-top:1.6rem">A) Caras / lugares que se repiten</h2>
      <p class="lead">Generá estas <strong>primero</strong> en Google Flow (1 imagen cada una) y después usalas como referencia cuando pidas los grupos.</p>
      <div class="list" id="masters"></div>

      <h2 style="margin-top:1.6rem">B) Grupos para pedir en Google Flow</h2>
      <p class="lead">Cada grupo = ~10 imágenes. Copiá el texto → pegalo en Google Flow → generá → descargá.</p>
      <div class="list" id="batches"></div>

      <h2 style="margin-top:1.6rem">C) Cosas reales (no pedirle esto a la IA)</h2>
      <p class="lead">Documentos, gráficos, etc. Los conseguís vos y los subís en el paso 6.</p>
      <div class="list" id="nonflow"></div>

      <div class="actions" style="margin-top:1.5rem">
        <button class="btn btn-primary" id="to-images-2">Ir a subir imágenes</button>
      </div>
    </div>`;

  const goImages = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "images" }),
    });
    state.project = data.project;
    renderProject();
  };
  $("#rebuild").onclick = () => rebuildFlow();
  $("#to-images").onclick = goImages;
  $("#to-images-2").onclick = goImages;

  $("#masters").innerHTML = masters.length
    ? masters
        .map(
          (m) => `
      <article class="shot">
        <strong>${esc(m.name)}</strong>
        <div class="ff-episode-meta">Se usa en ${m.used_in_flow || 0} escenas · guardala como ${esc(m.master_filename)}</div>
        <pre style="max-height:100px;overflow:auto">${esc(m.master_prompt || "")}</pre>
        <button class="btn btn-soft" data-copy-master="${esc(m.id)}">1) Copiar texto para Google Flow</button>
      </article>`
        )
        .join("")
    : `<div class="notice">No hace falta una imagen “maestra” especial en este episodio.</div>`;

  $("#masters").querySelectorAll("[data-copy-master]").forEach((btn) => {
    btn.onclick = () => {
      const m = masters.find((x) => x.id === btn.dataset.copyMaster);
      if (m?.master_prompt) {
        navigator.clipboard.writeText(m.master_prompt);
        toast("Copiado. Pegalo en Google Flow.");
      }
    };
  });

  $("#batches").innerHTML = batches.length
    ? batches
        .map((b, bi) => {
          const refs = (b.references_needed || []).map((r) => r.name || r.id).join(", ") || "ninguna especial";
          const totalB = b.count || (b.visual_numbers || []).length;
          const done = b.imported || 0;
          const nums = (b.visual_numbers || []).map((n) => String(n).padStart(3, "0")).join(", ");
          return `
      <article class="shot" id="batch-${bi}">
        <strong>Grupo ${bi + 1}</strong> — ${totalB} imágenes
        <div class="ff-episode-meta">Números: ${esc(nums)}</div>
        <div class="ff-episode-meta">Referencias a adjuntar en Flow: ${esc(refs)}</div>
        <div class="ff-episode-meta">Subidas: <strong>${done} / ${totalB}</strong></div>
        <div class="actions">
          <button class="btn btn-primary" data-copy-batch="${bi}">2) Copiar pedido a Google Flow</button>
          <button class="btn btn-ghost" data-expand-batch="${bi}">Ver detalle</button>
          <button class="btn btn-accent" data-go-upload="${bi}">3) Ya las bajé → subir</button>
        </div>
        <pre class="hidden" id="batch-prompt-${bi}" style="max-height:220px;overflow:auto;margin-top:0.6rem">${esc(b.prompt || "")}</pre>
        <div class="hidden" id="batch-expand-${bi}" style="margin-top:0.6rem"></div>
      </article>`;
        })
        .join("")
    : `<div class="notice">No hay grupos. Tocá “Rehacer plan de imágenes”.</div>`;

  $("#batches").querySelectorAll("[data-copy-batch]").forEach((btn) => {
    btn.onclick = () => {
      const b = batches[Number(btn.dataset.copyBatch)];
      const pre = $(`#batch-prompt-${btn.dataset.copyBatch}`);
      if (pre) pre.classList.remove("hidden");
      if (b?.prompt) {
        navigator.clipboard.writeText(b.prompt);
        toast("Pedido copiado. Pegalo en Google Flow y generá las imágenes.");
      }
    };
  });
  $("#batches").querySelectorAll("[data-go-upload]").forEach((btn) => {
    btn.onclick = goImages;
  });

  $("#batches").querySelectorAll("[data-expand-batch]").forEach((btn) => {
    btn.onclick = () => {
      const bi = Number(btn.dataset.expandBatch);
      const b = batches[bi];
      const host = $(`#batch-expand-${bi}`);
      if (!host) return;
      host.classList.toggle("hidden");
      if (host.dataset.built) return;
      host.dataset.built = "1";
      const byNum = Object.fromEntries(visuals.map((v) => [Number(v.number), v]));
      host.innerHTML = (b.visual_numbers || [])
        .map((n) => {
          const v = byNum[Number(n)] || {};
          return `<div class="field" style="margin:0.5rem 0">
            <label>Imagen ${String(n).padStart(3, "0")}</label>
            <textarea rows="2" data-edit-visual="${n}">${esc(v.description || v.action || "")}</textarea>
            <button class="btn btn-soft" data-save-visual="${n}">Guardar</button>
            <button class="btn btn-ghost" data-single="${n}">Copiar solo esta</button>
          </div>`;
        })
        .join("");
      host.querySelectorAll("[data-save-visual]").forEach((sb) => {
        sb.onclick = async () => {
          const num = Number(sb.dataset.saveVisual);
          const ta = host.querySelector(`[data-edit-visual="${num}"]`);
          try {
            await api(`/api/projects/${encodeURIComponent(p.id)}/visuals/${num}`, {
              method: "PUT",
              body: JSON.stringify({ description: ta.value }),
            });
            toast("Guardado");
            state.shots = null;
            state.visualPlan = null;
            renderProject();
          } catch (e) {
            toast(e.message);
          }
        };
      });
      host.querySelectorAll("[data-single]").forEach((sb) => {
        sb.onclick = async () => {
          try {
            const data = await api(`/api/projects/${encodeURIComponent(p.id)}/visuals/${sb.dataset.single}/prompt`);
            await navigator.clipboard.writeText(data.prompt || "");
            toast("Copiado");
          } catch (e) {
            toast(e.message);
          }
        };
      });
    };
  });

  $("#nonflow").innerHTML = nonFlow.length
    ? nonFlow
        .slice(0, 40)
        .map(
          (v) => `
      <article class="shot">
        <strong>Imagen ${String(v.number).padStart(3, "0")}</strong> — documento / gráfico real
        <div class="ff-episode-meta">${esc(v.description || v.acquisition_note || "")}</div>
        <div>${v.status === "READY" ? "✓ Ya la subiste" : "○ Todavía falta — subila en el paso 6"}</div>
        <button class="btn btn-soft" data-upload-one="${v.number}">Subir esta imagen</button>
      </article>`
        )
        .join("")
    : `<div class="notice">En este episodio casi todo se pide a Google Flow.</div>`;

  $("#nonflow").querySelectorAll("[data-upload-one]").forEach((btn) => {
    btn.onclick = async () => {
      await goImages();
      // force_num will be filled if possible after paint — toast hint
      toast(`En Subir imgs, poné el número ${String(btn.dataset.uploadOne).padStart(3, "0")} y subí el archivo`);
    };
  });
}

async function rebuildFlow() {
  try {
    const data = await withBusy("Armando el plan de imágenes…", () =>
      api(`/api/projects/${encodeURIComponent(state.project.id)}/flow`, { method: "POST" })
    );
    state.project = data.project;
    state.shots = data.shots;
    state.visualPlan = data.visual_plan;
    toast("Plan listo");
    renderProject();
  } catch (e) {
    toast(e.message);
  }
}

async function paintImages(ws, p) {
  let sync = { ready: 0, expected: 0, missing: [] };
  try {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/visual-plan`);
    sync = data.sync || sync;
    if (data.project) state.project = data.project;
  } catch {
    /* pack may be missing */
  }
  const missList = sync.missing || [];
  const miss = missList.slice(0, 24).join(", ");
  const ready = sync.ready || 0;
  const expected = sync.expected || 0;

  ws.innerHTML = `
    <div class="panel workspace">
      <div class="panel soft" style="border:2px solid var(--ink,#111);margin-bottom:1.2rem">
        <h2 style="margin-top:0">Acá se suben las imágenes</h2>
        <p class="lead">Progreso: <strong>${ready} de ${expected}</strong> listas</p>
        ${miss ? `<p class="lead">Todavía faltan: <code>${esc(miss)}</code>${missList.length > 24 ? "…" : ""}</p>` : `<p class="lead">✓ No falta ninguna.</p>`}
      </div>

      <div class="panel soft" style="margin:1rem 0;background:rgba(0,128,128,0.08)">
        <h2 style="margin-top:0">Subir varias de una</h2>
        <ol style="padding-left:1.2rem;line-height:1.5">
          <li>En Google Flow, descargá las imágenes.</li>
          <li>Renombrialas: <code>001.png</code>, <code>003.png</code>, etc. (el número del plan).</li>
          <li>Elegilas acá abajo y tocá <strong>Subir</strong>.</li>
        </ol>
        <input type="file" id="file-upload" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" multiple style="margin:0.8rem 0;display:block" />
        <div class="actions">
          <button class="btn btn-primary" id="btn-upload" style="font-size:1.05rem;padding:0.85rem 1.4rem">Subir las que elegí</button>
        </div>
      </div>

      <div class="panel soft" style="margin:1rem 0">
        <h2 style="margin-top:0">Subir / reemplazar UNA sola</h2>
        <p class="lead">Si una salió mal o falta solo la 023:</p>
        <div class="field">
          <label>Número de la imagen (ejemplo: 23)</label>
          <input id="force-num" type="number" min="1" placeholder="23" style="max-width:8rem" />
        </div>
        <input type="file" id="file-one" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" style="margin:0.6rem 0;display:block" />
        <div class="actions">
          <button class="btn btn-accent" id="btn-replace">Subir esta</button>
        </div>
      </div>

      <div class="actions">
        <button class="btn btn-ghost" id="refresh-sync">Actualizar contador</button>
        <button class="btn btn-ghost" id="back-flow">Volver a pedir imágenes</button>
        <button class="btn btn-primary" id="to-voice" ${ready < 1 ? "disabled" : ""}>Seguir a la voz</button>
      </div>
    </div>`;

  const uploadFiles = async (fileList, forceNumber = null) => {
    const files = [...(fileList || [])];
    if (!files.length) return toast("Elegí al menos una imagen");
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f, f.name));
    if (forceNumber != null && forceNumber !== "") {
      fd.append("force_number", String(Number(forceNumber)));
    }
    try {
      const data = await withBusy(`Subiendo ${files.length}…`, () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/images/upload`, {
          method: "POST",
          body: fd,
        })
      );
      state.project = data.project;
      const r = data.report || {};
      if (r.invalid_files?.length) {
        toast(`Algunas no se entendieron (poneles tipo 001.png): ${r.invalid_files.slice(0, 3).join(", ")}`);
      } else {
        toast(`Listo: ${data.sync?.ready || 0} de ${data.sync?.expected || 0} imágenes`);
      }
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };

  $("#btn-upload").onclick = () => uploadFiles($("#file-upload").files);
  $("#btn-replace").onclick = () => {
    const n = $("#force-num").value;
    if (!n) return toast("Escribí el número (ej. 23)");
    uploadFiles($("#file-one").files, n);
  };
  $("#refresh-sync").onclick = () => renderProject();
  $("#back-flow").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "flow" }),
    });
    state.project = data.project;
    renderProject();
  };
  $("#to-voice").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "voice" }),
    });
    state.project = data.project;
    renderProject();
  };
}

function paintVoice(ws, p) {
  const dur = p.voice?.duration_sec;
  ws.innerHTML = `
    <div class="panel workspace">
      <p class="lead">${dur ? `Voice ready · ${Math.floor(dur / 60)}:${String(Math.floor(dur % 60)).padStart(2, "0")}` : "Generate one continuous narration track."}</p>
      <div class="actions">
        <button class="btn btn-accent" id="gen-voice">Generate voice</button>
        <button class="btn btn-primary" id="to-render">Continue to render</button>
      </div>
    </div>`;
  $("#gen-voice").onclick = async () => {
    try {
      const data = await withBusy("Generating narration…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/voice`, { method: "POST" })
      );
      state.project = data.project;
      toast("Voice ready");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#to-render").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "render" }),
    });
    state.project = data.project;
    renderProject();
  };
}

function paintRender(ws, p) {
  const done = p.checkpoints?.render_ready || p.ui_step === "done";
  ws.innerHTML = `
    <div class="panel workspace">
      <p class="lead">${done ? "Final render is ready in the project folder." : "Assemble images + voice into the final video."}</p>
      <div class="actions">
        <button class="btn btn-accent" id="render">${done ? "Re-render" : "Render video"}</button>
        <button class="btn btn-primary" id="home">Back to home</button>
      </div>
    </div>`;
  $("#render").onclick = async () => {
    try {
      const data = await withBusy("Rendering…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/render`, { method: "POST" })
      );
      state.project = data.project;
      toast("Render complete");
      await refreshBootstrap();
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#home").onclick = () => {
    location.hash = "";
    go("home");
  };
}

async function refreshBootstrap() {
  state.bootstrap = await api("/api/bootstrap");
  renderCreds(state.bootstrap.credentials);
}

document.querySelectorAll("[data-go]").forEach((el) => {
  el.addEventListener("click", () => {
    const v = el.dataset.go;
    if (v === "home") location.hash = "";
    else location.hash = v;
    if (v === "ideas") state.ideas = state.ideas || [];
    go(v);
  });
});

window.addEventListener("hashchange", () => {
  const hash = location.hash.replace("#", "");
  if (hash.startsWith("project/")) openProject(decodeURIComponent(hash.slice(8)));
  else if (hash === "ideas") go("ideas");
  else if (hash === "library") go("library");
  else go("home");
});

boot();
