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
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
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
        <div class="actions">
          <button class="btn btn-primary" id="cta-new">Create today's video</button>
          <button class="btn btn-ghost" id="cta-lib">Browse library</button>
        </div>
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
  const flags = p.progress?.flags || {};
  stage().innerHTML = `
    <p class="kicker">Episode ${String(p.episode_number).padStart(3, "0")}</p>
    <h1 class="h1">${esc(p.title || p.topic)}</h1>
    <p class="lead">${esc(p.topic || "")}</p>
    <div class="stepper">
      ${steps
        .map((s) => {
          const cls = s === step ? "now" : flags[s] ? "done" : "";
          return `<button class="step ${cls}" data-step="${s}">${s}</button>`;
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
  ws.innerHTML = `<div class="panel"><p class="lead">Loading Visual Plan…</p></div>`;
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
        <p class="lead">No Visual Plan yet. Approve the script, then generate.</p>
        <div class="actions">
          <button class="btn btn-accent" id="rebuild">Generate Visual Plan</button>
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

  ws.innerHTML = `
    <div class="panel workspace">
      <p class="kicker">Visual Plan · illustrate the EVENT, not the sentence</p>
      <div class="meta" style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;margin:1rem 0">
        <div><span>TOTAL</span><strong>${stats.total || visuals.length || 0}</strong></div>
        <div><span>FLOW</span><strong>${stats.flow || 0}</strong></div>
        <div><span>REAL / DOC / OTHER</span><strong>${stats.real_or_other || 0}</strong></div>
        <div><span>BATCHES</span><strong>${stats.flow_batches || batches.length || 0}</strong></div>
      </div>
      <div class="actions">
        <button class="btn btn-accent" id="rebuild">Regenerate Visual Plan</button>
        <button class="btn btn-primary" id="to-images">Continue to Images</button>
      </div>

      <h2 style="margin-top:1.5rem">Master references</h2>
      <p class="lead">${masters.length} / ${masters.length} listed — generate these in Flow first, then attach when batching.</p>
      <div class="list" id="masters"></div>

      <h2 style="margin-top:1.5rem">Flow batches</h2>
      <p class="lead">Copy → paste in Google Flow with references attached → download as separate images → rename to visual numbers → import.</p>
      <div class="list" id="batches"></div>

      <h2 style="margin-top:1.5rem">Non-Flow assets</h2>
      <div class="list" id="nonflow"></div>
    </div>`;

  $("#rebuild").onclick = () => rebuildFlow();
  $("#to-images").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "images" }),
    });
    state.project = data.project;
    renderProject();
  };

  $("#masters").innerHTML = masters.length
    ? masters
        .map(
          (m) => `
      <article class="shot">
        <strong>${esc(m.name)}</strong> · ${esc(m.kind)} · used in ${m.used_in_flow || 0} Flow visuals
        <div class="ff-episode-meta">${esc(m.master_filename)} · ${esc(m.appearance_strategy || "")}</div>
        <pre style="max-height:120px;overflow:auto">${esc(m.master_prompt || "")}</pre>
        <button class="btn btn-soft" data-copy-master="${esc(m.id)}">Copy master prompt</button>
      </article>`
        )
        .join("")
    : `<div class="notice">No master references required (or regenerate after Story Plan has recurring characters).</div>`;

  $("#masters").querySelectorAll("[data-copy-master]").forEach((btn) => {
    btn.onclick = () => {
      const m = masters.find((x) => x.id === btn.dataset.copyMaster);
      if (m?.master_prompt) {
        navigator.clipboard.writeText(m.master_prompt);
        toast("Master prompt copied");
      }
    };
  });

  $("#batches").innerHTML = batches.length
    ? batches
        .map((b, bi) => {
          const refs = (b.references_needed || []).map((r) => r.name || r.id).join(", ") || "(none)";
          const nums = (b.visual_numbers || []).map((n) => String(n).padStart(3, "0")).join(", ");
          return `
      <article class="shot" id="batch-${bi}">
        <strong>${esc(b.id)}</strong> — ${esc(b.label || "")}
        <div class="ff-episode-meta">Visuals: ${esc(nums)} · Refs: ${esc(refs)} · ${esc(b.status || "ready_to_generate")}
          ${b.imported != null ? ` · ${b.imported}/${b.count || (b.visual_numbers || []).length} imported` : ""}</div>
        <div class="actions">
          <button class="btn btn-primary" data-copy-batch="${bi}">Copy batch prompt</button>
          <button class="btn btn-ghost" data-expand-batch="${bi}">Expand / edit</button>
        </div>
        <pre class="hidden" id="batch-prompt-${bi}" style="max-height:220px;overflow:auto;margin-top:0.6rem">${esc(b.prompt || "")}</pre>
        <div class="hidden" id="batch-expand-${bi}" style="margin-top:0.6rem"></div>
      </article>`;
        })
        .join("")
    : `<div class="notice">No Flow batches — regenerate Visual Plan.</div>`;

  $("#batches").querySelectorAll("[data-copy-batch]").forEach((btn) => {
    btn.onclick = () => {
      const b = batches[Number(btn.dataset.copyBatch)];
      const pre = $(`#batch-prompt-${btn.dataset.copyBatch}`);
      if (pre) pre.classList.remove("hidden");
      if (b?.prompt) {
        navigator.clipboard.writeText(b.prompt);
        toast("Batch prompt copied — paste into Flow");
      }
    };
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
            <label>${String(n).padStart(3, "0")} · ${esc(v.visual_type || "FLOW")} · beat ${esc(v.story_beat_id || "—")}</label>
            <textarea rows="2" data-edit-visual="${n}">${esc(v.description || v.action || "")}</textarea>
            <button class="btn btn-soft" data-save-visual="${n}">Save scene</button>
            <button class="btn btn-ghost" data-single="${n}">Copy single</button>
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
            toast(`Visual ${String(num).padStart(3, "0")} updated — batch prompt refreshed`);
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
            toast("Single prompt copied");
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
        <strong>${String(v.number).padStart(3, "0")}</strong> — ${esc(v.visual_type)}
        <div class="ff-episode-meta">${esc(v.acquisition_note || v.description || "")}</div>
        <div>Status: ${esc(v.status || "MISSING")} · expected ${esc(v.expected_file)}</div>
      </article>`
        )
        .join("")
    : `<div class="notice">All visuals are Flow reenactments for this plan.</div>`;
}

async function rebuildFlow() {
  try {
    const data = await withBusy("Building Visual Plan + Flow batches…", () =>
      api(`/api/projects/${encodeURIComponent(state.project.id)}/flow`, { method: "POST" })
    );
    state.project = data.project;
    state.shots = data.shots;
    state.visualPlan = data.visual_plan;
    toast("Visual Plan ready");
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
  const miss = (sync.missing || []).slice(0, 30).join(", ");
  ws.innerHTML = `
    <div class="panel workspace">
      <p class="kicker">Bulk import</p>
      <p class="lead"><strong>${sync.ready || 0} / ${sync.expected || 0}</strong> visual assets ready (file on disk = READY).</p>
      ${miss ? `<div class="notice">Missing: ${esc(miss)}${(sync.missing || []).length > 30 ? "…" : ""}</div>` : ""}
      <p class="lead">Drop numbered files into the project <code>flow-import</code> folder as <code>001.png</code>… then import.</p>
      <div class="actions">
        <button class="btn btn-accent" id="do-import">Import from flow-import/</button>
        <button class="btn btn-ghost" id="refresh-sync">Refresh status</button>
        <button class="btn btn-primary" id="to-voice">Continue to voice</button>
      </div>
    </div>`;
  $("#do-import").onclick = async () => {
    try {
      const data = await withBusy("Importing stills…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/images/import`, {
          method: "POST",
          body: JSON.stringify({ source_dir: "" }),
        })
      );
      state.project = data.project;
      toast(`Imported — ${data.sync?.ready || 0}/${data.sync?.expected || 0} ready`);
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#refresh-sync").onclick = () => renderProject();
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
