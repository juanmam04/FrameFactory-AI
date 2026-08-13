document.addEventListener("gesturestart", (e) => e.preventDefault());
document.addEventListener("gesturechange", (e) => e.preventDefault());
document.addEventListener(
  "touchmove",
  (e) => {
    if (e.touches && e.touches.length > 1) e.preventDefault();
  },
  { passive: false }
);

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
const IMG_BOOT = Date.now();

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
  const raw = await res.text();
  let data = null;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail =
      data?.detail ||
      data?.message ||
      data?.error ||
      (raw && raw.slice(0, 400)) ||
      res.statusText ||
      "Request failed";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (data && data.boot_error) {
    console.error(data.boot_error);
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

function pad3(n) {
  return String(n).padStart(3, "0");
}

function slotCard(v, projectId, previewSrc = "") {
  const n = Number(v.number);
  const id = pad3(n);
  const has = String(v.status || "").toUpperCase() === "READY";
  const desc = v.description || v.action || v.acquisition_note || "";
  const kind = v.visual_type === "FLOW_REENACTMENT" ? "Google Flow" : "documento / foto real";
  const src = previewSrc || `/api/projects/${encodeURIComponent(projectId)}/images/${n}?v=${IMG_BOOT}`;
  return `
    <article class="shot" data-slot="${n}">
      <strong>Imagen ${id}</strong>
      <div class="ff-episode-meta">${has ? "✓ ya está" : "○ falta"} · ${esc(kind)}</div>
      <div class="ff-episode-meta">${esc(String(desc).slice(0, 240))}</div>
      <div class="slot-frame">
        ${has
          ? `<img class="slot-thumb" src="${esc(src)}" alt="${id}" loading="lazy" decoding="async" />`
          : `<div class="slot-placeholder">16:9</div>`}
      </div>
      <div class="slot-actions">
        ${kind === "Google Flow"
          ? `<button type="button" class="btn btn-soft" data-copy-slot="${n}">1) Copiar prompt ${id}</button>`
          : ""}
        <label class="btn ${has ? "btn-soft" : "btn-primary"} slot-upload">
          ${has ? "Cambiar esta" : "2) Subir esta imagen"}
          <input type="file" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" data-slot-file="${n}" hidden />
        </label>
        ${has ? `<button type="button" class="btn btn-danger" data-slot-delete="${n}">Eliminar esta</button>` : ""}
      </div>
    </article>`;
}

function replaceSlotCard(card, projectId, v, previewSrc = "") {
  const wrap = document.createElement("div");
  wrap.innerHTML = slotCard(v, projectId, previewSrc);
  const next = wrap.firstElementChild;
  card.replaceWith(next);
  bindSlotUploads(next, projectId);
  return next;
}

function bindDeleteAll(btn, projectId) {
  if (!btn) return;
  btn.onclick = async () => {
    if (!confirm("¿Borrar todas las imágenes de este episodio?")) return;
    try {
      await withBusy("Eliminando imágenes…", () =>
        api(`/api/projects/${encodeURIComponent(projectId)}/images`, { method: "DELETE" })
      );
      toast("Todas las imágenes eliminadas");
      state.shots = null;
      state.visualPlan = null;
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
}

function bindSlotUploads(root, projectId) {
  if (!root) return;
  root.querySelectorAll(".slot-thumb").forEach((img) => {
    img.onerror = () => {
      if ((img.src || "").startsWith("blob:")) return;
      const frame = img.closest(".slot-frame");
      img.remove();
      if (frame && !frame.querySelector(".slot-placeholder")) {
        frame.innerHTML = `<div class="slot-placeholder">16:9</div>`;
      }
    };
  });
  root.querySelectorAll("[data-copy-slot]").forEach((btn) => {
    btn.onclick = async () => {
      const n = Number(btn.dataset.copySlot);
      try {
        const data = await api(`/api/projects/${encodeURIComponent(projectId)}/visuals/${n}/prompt`);
        await navigator.clipboard.writeText(data.prompt || "");
        toast(`Prompt ${pad3(n)} copiado. Pegalo en Flow, generá UNA, y subila acá.`);
      } catch (e) {
        toast(e.message);
      }
    };
  });
  root.querySelectorAll("[data-slot-delete]").forEach((btn) => {
    btn.onclick = async () => {
      const n = Number(btn.dataset.slotDelete);
      const card = btn.closest("[data-slot]");
      btn.disabled = true;
      try {
        await api(`/api/projects/${encodeURIComponent(projectId)}/images/${n}`, { method: "DELETE" });
        const metas = [...(card?.querySelectorAll(".ff-episode-meta") || [])];
        const desc = metas[1]?.textContent || "";
        const visual_type = (metas[0]?.textContent || "").includes("documento")
          ? "OTHER"
          : "FLOW_REENACTMENT";
        replaceSlotCard(card, projectId, {
          number: n,
          status: "MISSING",
          description: desc,
          visual_type,
        });
        toast(`${pad3(n)} eliminada`);
      } catch (e) {
        toast(e.message);
        btn.disabled = false;
      }
    };
  });
  root.querySelectorAll("[data-slot-file]").forEach((inp) => {
    inp.onchange = async () => {
      const n = Number(inp.dataset.slotFile);
      const file = inp.files && inp.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append("files", file, file.name);
      fd.append("force_number", String(n));
      const card = inp.closest("[data-slot]");
      const desc = [...(card?.querySelectorAll(".ff-episode-meta") || [])][1]?.textContent || "";
      const previewSrc = URL.createObjectURL(file);
      const next = replaceSlotCard(
        card,
        projectId,
        { number: n, status: "READY", description: desc, visual_type: "FLOW_REENACTMENT" },
        previewSrc
      );
      api(`/api/projects/${encodeURIComponent(projectId)}/images/upload`, {
        method: "POST",
        body: fd,
      })
        .then(() => {
          toast(`${pad3(n)} lista`);
          // Keep the local preview. Switching to the API URL on Vercel often 404s
          // for a few seconds and the onerror handler used to wipe the slot.
        })
        .catch((e) => {
          toast(e.message);
          replaceSlotCard(next, projectId, {
            number: n,
            status: "MISSING",
            description: desc,
            visual_type: "FLOW_REENACTMENT",
          });
          URL.revokeObjectURL(previewSrc);
        });
    };
  });
}

function setNav(view) {
  document.querySelectorAll(".nav-link").forEach((b) => {
    b.classList.toggle("active", b.dataset.go === view || (view === "project" && b.dataset.go === "library"));
  });
}

async function recheckKeys({ busy = false } = {}) {
  const run = () => api("/api/credentials/recheck", { method: "POST" });
  const c = busy ? await withBusy("Checking keys…", run) : await run();
  if (state.bootstrap) state.bootstrap.credentials = c;
  renderCreds(c);
  return c;
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
      const c = await recheckKeys({ busy: true });
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
    recheckKeys().catch((e) => toast(e.message));
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
  const goal = Math.max(1, s.goal || 100);
  const pct = Math.min(100, Math.round((s.day / goal) * 100));
  const ringC = 2 * Math.PI * 54;
  const ringDash = (pct / 100) * ringC;
  const ticks = Array.from({ length: goal }, (_, i) =>
    `<i class="${i < s.day ? "on" : ""}${ (i + 1) % 10 === 0 ? " mark" : "" }"></i>`
  ).join("");
  stage().innerHTML = `
    <section class="hero">
      <div class="panel soft">
        <p class="kicker">Channel</p>
        <h1 class="h1">${esc(b.channel.name)}</h1>
        <p class="lead">${esc(b.channel.tagline)} One true story a day. Research → script → Flow → voice → render.</p>
        <p class="lead ws-line" style="font-size:0.9rem;opacity:.85">
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
        <div class="day-card-glow" aria-hidden="true"></div>
        <div class="day-card-top">
          <span>100-day challenge</span>
          <span>${pct}%</span>
        </div>
        <div class="day-dial">
          <svg viewBox="0 0 120 120" aria-hidden="true">
            <defs>
              <linearGradient id="dayGlow" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#0f766e"/>
                <stop offset="100%" stop-color="#14b8a6"/>
              </linearGradient>
            </defs>
            <circle cx="60" cy="60" r="54" fill="none" stroke="rgba(15,23,32,.08)" stroke-width="2.5"/>
            <circle cx="60" cy="60" r="54" fill="none" stroke="url(#dayGlow)" stroke-width="3.5"
              stroke-linecap="round" stroke-dasharray="${ringDash} ${ringC}" transform="rotate(-90 60 60)"/>
          </svg>
          <div class="day-dial-num">
            <em>Day</em>
            <strong>${String(s.day).padStart(2, "0")}</strong>
          </div>
        </div>
        <p class="day-of">of ${s.goal} cinematic stories</p>
        <div class="day-ticks" aria-hidden="true">${ticks}</div>
        <p class="day-tagline">One true story a day</p>
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
  const steps = ["topic", "research", "story", "script", "flow", "images", "voice", "music", "render", "subs", "publish"];
  const stepLabel = {
    topic: "1 Tema",
    research: "2 Info",
    story: "3 Historia",
    script: "4 Guion",
    flow: "5 Pedir imgs",
    images: "6 Subir imgs",
    voice: "7 Voz",
    music: "8 Música",
    render: "9 Video",
    subs: "10 Subs",
    publish: "11 YouTube",
    done: "11 YouTube",
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
      btn.onclick = () => {
        const next = btn.dataset.step;
        state.project.ui_step = next;
        renderProject();
        api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
          method: "PATCH",
          body: JSON.stringify({ step: next }),
        }).catch((e) => toast(e.message));
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
  if (step === "music") return paintMusic(ws, p);
  if (step === "render") return paintRender(ws, p);
  if (step === "subs") return paintSubs(ws, p);
  if (step === "publish" || step === "done") return paintPublish(ws, p);
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
          <li><strong>De a UNA.</strong> En el recuadro 007 tocá “Copiar prompt 007” → pegalo en Flow → generá esa sola.</li>
          <li><strong>Subila en ESE recuadro</strong> (007). Flow mezcla el orden si pedís 10 juntas: no mires el nombre del archivo.</li>
          <li>La escena del texto (elevador, hotel, storefront) es la pista. El número del recuadro es la verdad.</li>
        </ol>
        <p class="lead" style="margin-top:0.75rem;margin-bottom:0">
          No uses el pedido de 10 a la vez si no vas a reconocer cada escena a ojo.
        </p>
      </div>

      <p class="lead">Este episodio necesita <strong>${total} imágenes</strong>:
        ${needAi} las pedís a Google Flow · ${needReal} son documentos/fotos reales (no las inventa la IA).
      </p>
      <div class="actions">
        <button class="btn btn-ghost" id="rebuild">Rehacer plan de imágenes</button>
        <button class="btn btn-ghost" id="to-images">Ver todas juntas</button>
        <button class="btn btn-danger" id="delete-all-stills">Eliminar todas</button>
      </div>

      <h2 style="margin-top:1.6rem">A) Caras que se repiten</h2>
      <p class="lead">Copiá el texto → Google Flow → descargá → <strong>subí acá</strong>. El nombre que ponga Flow no importa.</p>
      <div class="list" id="masters"></div>

      <h2 style="margin-top:1.6rem">B) Still por still</h2>
      <p class="lead">Cada recuadro tiene su número. Copiá ESE prompt, generá esa imagen, subila ahí. Flow no respeta el orden del lote.</p>
      <div class="list" id="batches"></div>

      <h2 style="margin-top:1.6rem">C) Cosas reales (no pedirle esto a la IA)</h2>
      <p class="lead">Documentos, gráficos, etc. Subilos en el recuadro de esa imagen.</p>
      <div class="list" id="nonflow"></div>
    </div>`;

  const goImages = () => {
    state.project.ui_step = "images";
    renderProject();
    api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "images" }),
    }).catch((e) => toast(e.message));
  };
  $("#rebuild").onclick = () => rebuildFlow();
  const toImagesBtn = $("#to-images");
  if (toImagesBtn) toImagesBtn.onclick = goImages;

  $("#masters").innerHTML = masters.length
    ? masters.map((m) => masterCard(m, p.id)).join("")
    : `<div class="notice">No hace falta una imagen “maestra” especial en este episodio.</div>`;
  bindMasterUploads($("#masters"), p.id, masters);

  $("#batches").innerHTML = batches.length
    ? batches
        .map((b, bi) => {
          const refs = (b.references_needed || []).map((r) => r.name || r.id).join(", ") || "ninguna especial";
          const totalB = b.count || (b.visual_numbers || []).length;
          const done = b.imported || 0;
          const byNum = Object.fromEntries(visuals.map((v) => [Number(v.number), v]));
          const slots = (b.visual_numbers || [])
            .map((n) => slotCard(byNum[Number(n)] || { number: n, visual_type: "FLOW_REENACTMENT" }, p.id))
            .join("");
          return `
      <article class="shot" id="batch-${bi}">
        <strong>Grupo ${bi + 1}</strong> — ${totalB} imágenes
        <div class="ff-episode-meta">Referencias a adjuntar en Flow: ${esc(refs)}</div>
        <div class="ff-episode-meta">Subidas: <strong>${done} / ${totalB}</strong></div>
        <div class="actions">
          <button class="btn btn-ghost" data-copy-batch="${bi}">Copiar las 10 (Flow las desordena)</button>
          <button class="btn btn-ghost" data-expand-batch="${bi}">Editar textos</button>
        </div>
        <pre class="hidden" id="batch-prompt-${bi}" style="max-height:220px;overflow:auto;margin-top:0.6rem">${esc(b.prompt || "")}</pre>
        <div class="hidden" id="batch-expand-${bi}" style="margin-top:0.6rem"></div>
        <div class="list" style="margin-top:0.8rem">${slots}</div>
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
        toast("Lote copiado. Flow NO las devuelve en orden — mejor copiá de a un recuadro.");
      }
    };
  });
  bindSlotUploads($("#batches"), p.id);
  bindDeleteAll($("#delete-all-stills"), p.id);

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
    ? nonFlow.map((v) => slotCard(v, p.id)).join("")
    : `<div class="notice">En este episodio casi todo se pide a Google Flow.</div>`;
  bindSlotUploads($("#nonflow"), p.id);
}

function masterCard(m, projectId, previewSrc = "") {
  const id = m.id;
  const has = String(m.status || "").toUpperCase() === "READY" || Boolean(previewSrc);
  const src =
    previewSrc ||
    (has
      ? `/api/projects/${encodeURIComponent(projectId)}/masters/${encodeURIComponent(id)}?v=${IMG_BOOT}`
      : "");
  const kind = m.kind === "character" ? "cara" : m.kind || "referencia";
  return `
    <article class="shot" data-master="${esc(id)}">
      <strong>${esc(m.name || id)}</strong>
      <div class="ff-episode-meta">${has ? "✓ ya está" : "○ falta"} · ${esc(kind)} · ${m.used_in_flow || 0} escenas</div>
      <pre>${esc(m.master_prompt || "")}</pre>
      <div class="slot-frame">
        ${has
          ? `<img class="slot-thumb" src="${esc(src)}" alt="${esc(m.name || id)}" loading="lazy" decoding="async" />`
          : `<div class="slot-placeholder">16:9</div>`}
      </div>
      <div class="slot-actions">
        <button type="button" class="btn btn-soft" data-copy-master="${esc(id)}">1) Copiar texto</button>
        <label class="btn ${has ? "btn-soft" : "btn-primary"} slot-upload">
          ${has ? "Cambiar esta cara" : "2) Subir esta cara"}
          <input type="file" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" data-master-file="${esc(id)}" hidden />
        </label>
        ${has ? `<button type="button" class="btn btn-danger" data-master-delete="${esc(id)}">Eliminar</button>` : ""}
      </div>
    </article>`;
}

function replaceMasterCard(card, projectId, m, previewSrc = "") {
  const wrap = document.createElement("div");
  wrap.innerHTML = masterCard(m, projectId, previewSrc);
  const next = wrap.firstElementChild;
  card.replaceWith(next);
  bindMasterUploads(next, projectId, [m]);
  return next;
}

function bindMasterUploads(root, projectId, masters) {
  if (!root) return;
  const list = masters || [];
  root.querySelectorAll(".slot-thumb").forEach((img) => {
    img.onerror = () => {
      if ((img.src || "").startsWith("blob:")) return;
      const frame = img.closest(".slot-frame");
      img.remove();
      if (frame && !frame.querySelector(".slot-placeholder")) {
        frame.innerHTML = `<div class="slot-placeholder">16:9</div>`;
      }
    };
  });
  root.querySelectorAll("[data-copy-master]").forEach((btn) => {
    btn.onclick = () => {
      const m = list.find((x) => x.id === btn.dataset.copyMaster);
      if (m?.master_prompt) {
        navigator.clipboard.writeText(m.master_prompt);
        toast("Copiado. Pegalo en Google Flow.");
      }
    };
  });
  root.querySelectorAll("[data-master-delete]").forEach((btn) => {
    btn.onclick = async () => {
      const id = btn.dataset.masterDelete;
      const card = btn.closest("[data-master]");
      const m = list.find((x) => x.id === id) || {
        id,
        master_prompt: card?.querySelector("pre")?.textContent || "",
      };
      btn.disabled = true;
      try {
        await api(`/api/projects/${encodeURIComponent(projectId)}/masters/${encodeURIComponent(id)}`, {
          method: "DELETE",
        });
        m.status = "MISSING";
        replaceMasterCard(card, projectId, m);
        toast("Cara eliminada");
      } catch (e) {
        toast(e.message);
        btn.disabled = false;
      }
    };
  });
  root.querySelectorAll("[data-master-file]").forEach((inp) => {
    inp.onchange = async () => {
      const id = inp.dataset.masterFile;
      const file = inp.files && inp.files[0];
      if (!file) return;
      const card = inp.closest("[data-master]");
      const m = list.find((x) => x.id === id) || {
        id,
        name: id,
        master_prompt: card?.querySelector("pre")?.textContent || "",
      };
      const fd = new FormData();
      fd.append("files", file, file.name);
      fd.append("force_id", id);
      const previewSrc = URL.createObjectURL(file);
      m.status = "READY";
      const next = replaceMasterCard(card, projectId, m, previewSrc);
      api(`/api/projects/${encodeURIComponent(projectId)}/masters/upload`, {
        method: "POST",
        body: fd,
      })
        .then(() => toast(`${m.name || id} lista`))
        .catch((e) => {
          toast(e.message);
          m.status = "MISSING";
          replaceMasterCard(next, projectId, m);
          URL.revokeObjectURL(previewSrc);
        });
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
  let visuals = [];
  try {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/visual-plan`);
    sync = data.sync || sync;
    visuals = (data.plan && data.plan.visuals) || [];
    if (data.project) state.project = data.project;
  } catch {
    /* pack may be missing */
  }
  const ready = sync.ready || 0;
  const expected = sync.expected || 0;
  const readySet = new Set(sync.ready_ids || []);
  visuals = visuals.map((v) => ({
    ...v,
    status: readySet.has(pad3(v.number)) || String(v.status || "").toUpperCase() === "READY" ? "READY" : "MISSING",
  }));

  ws.innerHTML = `
    <div class="panel workspace">
      <div class="panel soft" style="border:2px solid var(--ink,#111);margin-bottom:1.2rem">
        <h2 style="margin-top:0">Una imagen, un botón</h2>
        <p class="lead">Progreso: <strong>${ready} de ${expected}</strong></p>
        <p class="lead">El número del recuadro es el still. Copiá ese prompt, generá UNA en Flow, subila acá. El nombre del archivo no importa: Flow desordena.</p>
        <div class="actions" style="margin-top:0.8rem">
          <button class="btn btn-danger" id="delete-all-stills">Eliminar todas</button>
        </div>
      </div>
      <div class="list" id="slots">${
        visuals.length
          ? visuals.map((v) => slotCard(v, p.id)).join("")
          : `<div class="notice">Todavía no hay plan. Volvé a “Pedir imgs”.</div>`
      }</div>
      <div class="actions" style="margin-top:1.2rem">
        <button class="btn btn-ghost" id="back-flow">Volver a pedir imágenes</button>
        <button class="btn btn-primary" id="to-voice" ${ready < 1 ? "disabled" : ""}>Seguir a la voz</button>
      </div>
    </div>`;

  bindSlotUploads($("#slots"), p.id);
  bindDeleteAll($("#delete-all-stills"), p.id);
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

function onVercel() {
  return !!state.bootstrap?.runtime?.vercel;
}

function paintVoice(ws, p) {
  const dur = p.voice?.duration_sec;
  const ready = !!(p.voice?.path || p.checkpoints?.voice_ready);
  const clock = dur
    ? `${Math.floor(dur / 60)}:${String(Math.floor(dur % 60)).padStart(2, "0")}`
    : "";
  ws.innerHTML = `
    <div class="panel workspace">
      <h2 style="margin-top:0">Voz</h2>
      <p class="lead">${ready
        ? `Narración lista${clock ? ` · ${clock}` : ""} · x1.20.`
        : "Generá la narración acá (OpenAI / ElevenLabs). Sale un poco más rápida (x1.20)."}</p>
      ${ready ? `<audio controls src="/api/projects/${encodeURIComponent(p.id)}/audio?t=${Date.now()}" style="width:min(100%,640px);margin:0.4rem 0 1rem;display:block"></audio>` : ""}
      <div class="actions">
        <button class="btn btn-accent" id="gen-voice">${ready ? "Volver a generar voz" : "Generar voz"}</button>
        <button class="btn btn-primary" id="to-music">Seguir a la música</button>
      </div>
    </div>`;
  $("#gen-voice").onclick = async () => {
    try {
      const data = await withBusy("Generando narración…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/voice`, { method: "POST" })
      );
      state.project = data.project;
      toast("Voz lista");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#to-music").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "music" }),
    });
    state.project = data.project;
    renderProject();
  };
}

function paintMusic(ws, p) {
  ws.innerHTML = `
    <div class="panel workspace">
      <h2 style="margin-top:0">Música</h2>
      <p class="lead">La misma cama en todos los episodios. En el video va muy bajita. Escuchala acá.</p>
      <audio id="music-bed" controls loop src="/api/music?v=20260813v" style="width:min(100%,640px);margin:0.4rem 0 1rem;display:block"></audio>
      <div class="actions">
        <button class="btn btn-primary" id="to-render">Seguir al video</button>
      </div>
    </div>`;
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
      <h2 style="margin-top:0">Video</h2>
      <p class="lead">${done ? "El episodio ya está armado." : "Junta las imágenes con la narración, música bajita y fundidos simples."}</p>
      ${done ? `<video controls src="/api/projects/${encodeURIComponent(p.id)}/video?t=${Date.now()}" style="width:min(100%,720px);aspect-ratio:16/9;background:#111;border-radius:14px;margin:0.5rem 0 1rem"></video>` : ""}
      <div class="actions">
        <button class="btn btn-accent" id="render">${done ? "Volver a renderizar" : "Renderizar video"}</button>
        ${done ? `<a class="btn btn-ghost" href="/api/projects/${encodeURIComponent(p.id)}/video" download>Descargar MP4</a>` : ""}
        <button class="btn btn-primary" id="to-subs">Seguir a subtítulos</button>
        <button class="btn btn-ghost" id="home">Volver al inicio</button>
      </div>
    </div>`;
  $("#to-subs").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "subs" }),
    });
    state.project = data.project;
    renderProject();
  };
  $("#render").onclick = async () => {
    try {
      const data = await withBusy("Armando el video… esto puede tardar un par de minutos", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/render`, { method: "POST" })
      );
      state.project = data.project;
      toast("Video listo");
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

function paintSubs(ws, p) {
  const cap = p.captions || {};
  const burned = !!(cap.burned || p.checkpoints?.captions_ready);
  ws.innerHTML = `
    <div class="panel workspace">
      <h2 style="margin-top:0">Subtítulos</h2>
      <p class="lead">Inglés, abajo, sincronizados con la narración. Primero el texto, después el video con los captions quemados.</p>
      <div class="field">
        <label>Preview del texto (SRT)</label>
        <textarea id="srt-box" rows="12" style="font-family:ui-monospace,monospace;font-size:0.85rem" placeholder="Tocá Armar subtítulos…"></textarea>
      </div>
      <div class="actions" style="margin-bottom:1rem">
        <button class="btn btn-accent" id="gen-subs">Armar subtítulos</button>
        <button class="btn btn-ghost" id="save-subs">Guardar texto</button>
        <button class="btn btn-primary" id="burn-subs">Ponerlos en el video</button>
      </div>
      ${burned ? `<video controls src="/api/projects/${encodeURIComponent(p.id)}/video/captions?t=${Date.now()}" style="width:min(100%,720px);aspect-ratio:16/9;background:#111;border-radius:14px;margin:0.5rem 0 1rem"></video>` : `<p class="lead">Cuando los quemes, el preview del video aparece acá.</p>`}
      <div class="actions">
        ${burned ? `<a class="btn btn-ghost" href="/api/projects/${encodeURIComponent(p.id)}/video/captions" download>Descargar con subtítulos</a>` : ""}
        <button class="btn btn-primary" id="to-publish">Seguir a YouTube</button>
      </div>
    </div>`;
  const box = $("#srt-box");
  api(`/api/projects/${encodeURIComponent(p.id)}/captions`)
    .then((data) => {
      if (box && data.srt) box.value = data.srt;
    })
    .catch(() => {});
  $("#gen-subs").onclick = async () => {
    try {
      const data = await withBusy("Armando subtítulos…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/captions`, { method: "POST" })
      );
      state.project = data.project;
      if (box) box.value = data.srt || "";
      toast(`${(data.cues || []).length} carteles`);
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#save-subs").onclick = async () => {
    try {
      const data = await api(`/api/projects/${encodeURIComponent(p.id)}/captions`, {
        method: "PUT",
        body: JSON.stringify({ srt: box.value || "" }),
      });
      state.project = data.project;
      toast("Subtítulos guardados");
    } catch (e) {
      toast(e.message);
    }
  };
  $("#burn-subs").onclick = async () => {
    try {
      if (box && box.value.trim()) {
        await api(`/api/projects/${encodeURIComponent(p.id)}/captions`, {
          method: "PUT",
          body: JSON.stringify({ srt: box.value }),
        });
      }
      const data = await withBusy("Quemando subtítulos en el video…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/captions/burn`, { method: "POST" })
      );
      state.project = data.project;
      toast("Video con subtítulos listo");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#to-publish").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "publish" }),
    });
    state.project = data.project;
    renderProject();
  };
}

function paintPublish(ws, p) {
  const y = p.youtube || {};
  const alts = (y.alt_titles || []).join("\n");
  ws.innerHTML = `
    <div class="panel workspace">
      <h2 style="margin-top:0">YouTube</h2>
      <p class="lead">Título y miniatura pensados para que alguien pare el scroll. No un still más del video.</p>
      <div class="actions" style="margin-bottom:1rem">
        <button class="btn btn-accent" id="gen-yt">Generar con IA</button>
        <button class="btn btn-ghost" id="save-yt">Guardar</button>
      </div>
      <div class="field">
        <label>Título</label>
        <input id="yt-title" value="${esc(y.title || "")}" />
        <button class="btn btn-soft" id="copy-title" style="margin-top:0.45rem">Copiar título</button>
      </div>
      <div class="field">
        <label>Títulos alternativos</label>
        <textarea id="yt-alts" rows="3">${esc(alts)}</textarea>
      </div>
      <div class="field">
        <label>Descripción</label>
        <textarea id="yt-desc" rows="10">${esc(y.description || "")}</textarea>
        <button class="btn btn-soft" id="copy-desc" style="margin-top:0.45rem">Copiar descripción</button>
      </div>
      <div class="field">
        <label>Texto overlay (2–4 palabras, se lee en el celular)</label>
        <input id="yt-thumb-text" value="${esc(y.thumbnail_text || "")}" />
        <button class="btn btn-soft" id="copy-thumb-text" style="margin-top:0.45rem">Copiar overlay</button>
      </div>
      <div class="field">
        <label>Prompt de miniatura — cara grande + un objeto de la historia (Google Flow)</label>
        <textarea id="yt-thumb" rows="8">${esc(y.thumbnail_prompt || "")}</textarea>
        <button class="btn btn-soft" id="copy-thumb" style="margin-top:0.45rem">Copiar prompt</button>
      </div>
      <div class="actions">
        <button class="btn btn-ghost" id="back-video">Volver al video</button>
        <button class="btn btn-primary" id="home">Listo</button>
      </div>
    </div>`;
  const packFromForm = () => ({
    title: $("#yt-title").value,
    alt_titles: $("#yt-alts").value.split("\n").map((s) => s.trim()).filter(Boolean),
    description: $("#yt-desc").value,
    thumbnail_text: $("#yt-thumb-text").value,
    thumbnail_prompt: $("#yt-thumb").value,
  });
  $("#gen-yt").onclick = async () => {
    try {
      const data = await withBusy("Escribiendo título y miniatura…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/youtube`, { method: "POST" })
      );
      state.project = data.project;
      toast("Pack de YouTube listo");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#save-yt").onclick = async () => {
    try {
      const data = await api(`/api/projects/${encodeURIComponent(p.id)}/youtube`, {
        method: "PUT",
        body: JSON.stringify(packFromForm()),
      });
      state.project = data.project;
      toast("Guardado");
    } catch (e) {
      toast(e.message);
    }
  };
  const copy = (sel, label) => {
    navigator.clipboard.writeText($(sel).value || "");
    toast(`${label} copiado`);
  };
  $("#copy-title").onclick = () => copy("#yt-title", "Título");
  $("#copy-desc").onclick = () => copy("#yt-desc", "Descripción");
  $("#copy-thumb-text").onclick = () => copy("#yt-thumb-text", "Overlay");
  $("#copy-thumb").onclick = () => copy("#yt-thumb", "Prompt");
  $("#back-video").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "render" }),
    });
    state.project = data.project;
    renderProject();
  };
  $("#home").onclick = () => {
    location.hash = "";
    go("home");
  };
}

async function refreshBootstrap() {
  const prev = state.bootstrap?.credentials;
  state.bootstrap = await api("/api/bootstrap");
  if (prev && prev.openai?.status && prev.openai.status !== "unchecked") {
    state.bootstrap.credentials = prev;
  }
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
