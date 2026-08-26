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
  contentFormat: "check_als",
  pickedConceptId: "",
  activeProjectId: "",
  project: null,
  shots: null,
  visualPlan: null,
};

const IDEAS_CACHE_KEY = "ff_check_ideas_v1";

function saveIdeasCache() {
  try {
    sessionStorage.setItem(
      IDEAS_CACHE_KEY,
      JSON.stringify({
        ideas: state.ideas,
        contentFormat: state.contentFormat,
        pickedConceptId: state.pickedConceptId,
        activeProjectId: state.activeProjectId,
      })
    );
  } catch {
    /* ignore quota */
  }
}

function loadIdeasCache() {
  try {
    const raw = sessionStorage.getItem(IDEAS_CACHE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (Array.isArray(data.ideas) && data.ideas.length) state.ideas = data.ideas;
    if (data.contentFormat) state.contentFormat = data.contentFormat;
    if (data.pickedConceptId) state.pickedConceptId = data.pickedConceptId;
    if (data.activeProjectId) state.activeProjectId = data.activeProjectId;
  } catch {
    /* ignore corrupt cache */
  }
}

function activeInProgressProject() {
  const projects = state.bootstrap?.projects || [];
  if (state.activeProjectId) {
    const hit = projects.find((p) => p.id === state.activeProjectId);
    if (hit && hit.status !== "complete") return hit;
  }
  return projects.find((p) => p.status !== "complete") || null;
}

const stage = () => document.getElementById("stage");
const setStageMode = (mode) => {
  const el = stage();
  if (!el) return;
  el.classList.toggle("stage-project", mode === "project");
};
const $ = (sel, el = document) => el.querySelector(sel);
const IMG_BOOT = Date.now();

function isMobileDevice() {
  return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "");
}

async function ensureServiceWorker() {
  if (!("serviceWorker" in navigator)) return null;
  try {
    const reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    await navigator.serviceWorker.ready;
    return reg;
  } catch {
    return null;
  }
}

/** Hand off the episode to the OS / Background Fetch so leaving the app doesn't kill it. */
async function startEpisodeDownload(projectId, filename = `${projectId}.mp4`) {
  const url = `/api/projects/${encodeURIComponent(projectId)}/video?download=1&t=${Date.now()}`;
  const reg = await ensureServiceWorker();

  // Chrome Android: true background download via Background Fetch.
  if (reg && "backgroundFetch" in reg) {
    try {
      if (Notification && Notification.permission === "default") {
        try {
          await Notification.requestPermission();
        } catch {}
      }
      const id = `ff-${String(projectId).slice(0, 40)}-${Date.now()}`;
      await reg.backgroundFetch.fetch(id, [new Request(url, { credentials: "same-origin" })], {
        title: filename,
        icons: [{ src: "/assets/logo.png", sizes: "1024x1024", type: "image/png" }],
      });
      toast("Descarga en segundo plano — podés salir de la app");
      return;
    } catch (e) {
      console.warn("backgroundFetch failed", e);
    }
  }

  // Fallback: attachment response → system Download Manager (Android).
  // Avoid HTML `download` attr on mobile — that forces an in-tab fetch that dies if you leave.
  const a = document.createElement("a");
  a.href = url;
  a.rel = "noopener";
  if (!isMobileDevice()) {
    a.setAttribute("download", filename);
  } else {
    a.target = "_blank";
  }
  document.body.appendChild(a);
  a.click();
  a.remove();
  toast(
    isMobileDevice()
      ? "Descarga iniciada — podés salir; sigue en Descargas del celular"
      : "Descarga iniciada"
  );
}

ensureServiceWorker().catch(() => {});

async function api(path, opts = {}) {
  const { timeoutMs, ...rest } = opts;
  const headers = { ...(rest.headers || {}) };
  // Don't force JSON content-type for FormData uploads
  if (!(rest.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  let res;
  try {
    res = await fetch(path, {
      ...rest,
      headers,
      signal: rest.signal || (timeoutMs ? AbortSignal.timeout(timeoutMs) : undefined),
    });
  } catch (e) {
    const name = e && e.name;
    if (name === "AbortError" || name === "TimeoutError") {
      throw new Error(
        path.includes("/api/bootstrap")
          ? "Tardó demasiado en abrir. Tocá Reintentar."
          : path.includes("/api/ideas")
            ? "La generación de conceptos tardó demasiado. Tocá Generate de nuevo."
            : "Se cortó la espera. Si el video quedó, va a aparecer para descargar."
      );
    }
    throw new Error("No se pudo conectar. Probá de nuevo.");
  }
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

const DL = {
  jobs: new Map(),
  db: null,
  async open() {
    if (this.db) return this.db;
    this.db = await new Promise((resolve, reject) => {
      const req = indexedDB.open("ff-dl-v1", 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains("meta")) db.createObjectStore("meta");
        if (!db.objectStoreNames.contains("chunks")) db.createObjectStore("chunks");
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error("IndexedDB"));
    });
    return this.db;
  },
  tx(store, mode, fn) {
    return this.open().then(
      (db) =>
        new Promise((resolve, reject) => {
          const t = db.transaction(store, mode);
          const s = t.objectStore(store);
          const req = fn(s);
          t.oncomplete = () => resolve(req?.result);
          t.onerror = () => reject(t.error);
          if (req && req !== s) {
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
          }
        })
    );
  },
  getMeta(id) {
    return this.tx("meta", "readonly", (s) => s.get(id));
  },
  setMeta(id, val) {
    return this.tx("meta", "readwrite", (s) => s.put(val, id));
  },
  delMeta(id) {
    return this.tx("meta", "readwrite", (s) => s.delete(id));
  },
  putChunk(id, idx, buf) {
    return this.tx("chunks", "readwrite", (s) => s.put(buf, `${id}:${idx}`));
  },
  getChunk(id, idx) {
    return this.tx("chunks", "readonly", (s) => s.get(`${id}:${idx}`));
  },
  async clearChunks(id, n) {
    const db = await this.open();
    await new Promise((resolve, reject) => {
      const t = db.transaction("chunks", "readwrite");
      const s = t.objectStore("chunks");
      for (let i = 0; i < n; i++) s.delete(`${id}:${i}`);
      t.oncomplete = () => resolve();
      t.onerror = () => reject(t.error);
    });
  },
  paint() {
    const host = document.getElementById("dl-dock");
    if (!host) return;
    const rows = [...this.jobs.values()].filter((j) => j.status === "active" || j.status === "error");
    if (!rows.length) {
      host.classList.add("hidden");
      host.innerHTML = "";
      return;
    }
    host.classList.remove("hidden");
    host.innerHTML = rows
      .map((j) => {
        const pct = j.total ? Math.min(100, Math.round((100 * j.received) / j.total)) : 0;
        const mb = (n) => `${(n / 1048576).toFixed(1)} MB`;
        const msg =
          j.status === "error"
            ? j.error || "Se cortó. Tocá para retomar."
            : `Podés salir: al volver sigue desde acá · ${mb(j.received)}${j.total ? ` / ${mb(j.total)}` : ""}`;
        return `<div class="dl-row" data-dl-job="${esc(j.id)}">
          <div class="dl-row-top">
            <strong>${esc(j.filename || "video.mp4")}</strong>
            <span>${j.status === "error" ? "Pausada" : `${pct}%`}</span>
          </div>
          <div class="dl-bar"><i style="width:${pct}%"></i></div>
          <p>${esc(msg)}</p>
          <div class="dl-actions">
            ${j.status === "error" ? `<button type="button" class="btn btn-accent" data-dl-resume="${esc(j.id)}">Retomar</button>` : ""}
            <button type="button" class="btn btn-ghost" data-dl-stop="${esc(j.id)}">Cancelar</button>
          </div>
        </div>`;
      })
      .join("");
    host.querySelectorAll("[data-dl-stop]").forEach((btn) => {
      btn.onclick = () => this.cancel(btn.getAttribute("data-dl-stop"));
    });
    host.querySelectorAll("[data-dl-resume]").forEach((btn) => {
      btn.onclick = () => {
        const id = btn.getAttribute("data-dl-resume");
        const j = this.jobs.get(id);
        if (j) this.run(j);
      };
    });
  },
  async saveBlob(filename, blob) {
    const file = new File([blob], filename, { type: "video/mp4" });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({ files: [file], title: filename });
        return;
      } catch (e) {
        if (e && e.name === "AbortError") return;
      }
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 40000);
  },
  async start({ id, url, filename }) {
    const existing = this.jobs.get(id);
    if (existing && existing.status === "active") {
      toast("Esa descarga ya está en curso");
      this.paint();
      return;
    }
    // Fail fast if the MP4 isn't there (Vercel project without render, or still encoding).
    try {
      const probe = await fetch(url, { method: "HEAD", credentials: "same-origin" });
      if (probe.status === 404) {
        toast("Todavía no hay video para bajar — terminá el render primero");
        return;
      }
      if (!probe.ok && probe.status !== 405) {
        // Some hosts reject HEAD; continue and let ranged GET decide.
        console.warn("download HEAD", probe.status);
      }
    } catch (e) {
      console.warn("download probe", e);
    }
    const saved = (await this.getMeta(id).catch(() => null)) || {};
    const job = {
      id,
      url,
      filename: filename || saved.filename || `${id}.mp4`,
      received: Number(saved.received || 0) || 0,
      total: Number(saved.total || 0) || 0,
      chunks: Number(saved.chunks || 0) || 0,
      status: "active",
      abort: false,
      error: "",
    };
    this.jobs.set(id, job);
    this.paint();
    toast("Descarga en segundo plano. Si salís, al volver sigue.");
    await this.run(job);
  },
  async run(job) {
    job.abort = false;
    job.status = "active";
    job.error = "";
    this.jobs.set(job.id, job);
    this.paint();
    const piece = 2 * 1024 * 1024;
    try {
      if (!job.total) {
        const head = await fetch(job.url, { method: "HEAD", credentials: "same-origin" });
        if (head.status === 404) throw new Error("El video aún no está listo (404)");
        const len = Number(head.headers.get("content-length") || 0);
        if (len > 0) job.total = len;
      }
      if (!job.total) {
        const probe = await fetch(job.url, { headers: { Range: "bytes=0-0" }, credentials: "same-origin" });
        if (probe.status === 404) throw new Error("El video aún no está listo (404)");
        const cr = probe.headers.get("content-range") || "";
        const m = /\/(\d+)$/.exec(cr);
        if (m) job.total = Number(m[1]);
        else job.total = Number(probe.headers.get("content-length") || 0);
        await probe.arrayBuffer();
      }
      if (!job.total) {
        // Last resort: full fetch (small files / hosts without Range).
        const full = await fetch(job.url, { credentials: "same-origin" });
        if (!full.ok) throw new Error(full.status === 404 ? "El video aún no está listo" : "No pude bajar el video");
        const blob = await full.blob();
        await this.saveBlob(job.filename, blob);
        await this.delMeta(job.id);
        this.jobs.delete(job.id);
        this.paint();
        toast("Descarga lista");
        return;
      }
      await this.setMeta(job.id, {
        url: job.url,
        filename: job.filename,
        received: job.received,
        total: job.total,
        chunks: job.chunks,
        status: "active",
      });
      while (job.received < job.total && !job.abort) {
        const end = Math.min(job.total - 1, job.received + piece - 1);
        const res = await fetch(job.url, { headers: { Range: `bytes=${job.received}-${end}` }, credentials: "same-origin" });
        if (!(res.ok || res.status === 206)) {
          throw new Error("Se cortó la descarga");
        }
        const buf = await res.arrayBuffer();
        if (!buf.byteLength) break;
        if (res.status === 200 && job.received > 0 && buf.byteLength > piece * 2) {
          job.received = 0;
          job.chunks = 0;
        }
        await this.putChunk(job.id, job.chunks, buf);
        job.received += buf.byteLength;
        job.chunks += 1;
        await this.setMeta(job.id, {
          url: job.url,
          filename: job.filename,
          received: job.received,
          total: job.total,
          chunks: job.chunks,
          status: "active",
        });
        this.paint();
      }
      if (job.abort) {
        job.status = "error";
        job.error = "Pausada";
        this.paint();
        return;
      }
      const parts = [];
      for (let i = 0; i < job.chunks; i++) {
        const chunk = await this.getChunk(job.id, i);
        if (chunk) parts.push(chunk);
      }
      const blob = new Blob(parts, { type: "video/mp4" });
      await this.saveBlob(job.filename, blob);
      await this.clearChunks(job.id, job.chunks);
      await this.delMeta(job.id);
      this.jobs.delete(job.id);
      this.paint();
      toast("Video guardado");
    } catch (e) {
      job.status = "error";
      job.error = e.message || "Se cortó. Tocá Retomar.";
      await this.setMeta(job.id, {
        url: job.url,
        filename: job.filename,
        received: job.received,
        total: job.total,
        chunks: job.chunks,
        status: "paused",
      }).catch(() => {});
      this.paint();
    }
  },
  async cancel(id) {
    const job = this.jobs.get(id);
    if (job) job.abort = true;
    const meta = await this.getMeta(id).catch(() => null);
    const n = Number(job?.chunks || meta?.chunks || 0);
    await this.clearChunks(id, n).catch(() => {});
    await this.delMeta(id).catch(() => {});
    this.jobs.delete(id);
    this.paint();
  },
  async resumeAll() {
    try {
      const db = await this.open();
      const keys = await new Promise((resolve, reject) => {
        const t = db.transaction("meta", "readonly");
        const req = t.objectStore("meta").getAllKeys();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => reject(req.error);
      });
      for (const id of keys) {
        const meta = await this.getMeta(id);
        if (!meta || meta.status === "done") continue;
        if (this.jobs.get(id)?.status === "active") continue;
        const job = {
          id,
          url: meta.url,
          filename: meta.filename,
          received: Number(meta.received || 0) || 0,
          total: Number(meta.total || 0) || 0,
          chunks: Number(meta.chunks || 0) || 0,
          status: "active",
          abort: false,
          error: "",
        };
        this.jobs.set(id, job);
        this.run(job);
      }
      this.paint();
    } catch {
      /* IndexedDB blocked */
    }
  },
};

function downloadVideoButton(projectId, label) {
  const url = `/api/projects/${encodeURIComponent(projectId)}/video?download=1`;
  const name = `${projectId}.mp4`;
  return `<button type="button" class="btn btn-primary" data-dl-url="${esc(url)}" data-dl-name="${esc(name)}" data-dl-id="${esc(projectId)}">${esc(label)}</button>`;
}

function wireDownloads(root = document) {
  root.querySelectorAll("[data-dl-url]").forEach((btn) => {
    if (btn.dataset.dlBound === "1") return;
    btn.dataset.dlBound = "1";
    btn.addEventListener("click", () => {
      DL.start({
        id: btn.getAttribute("data-dl-id"),
        url: btn.getAttribute("data-dl-url"),
        filename: btn.getAttribute("data-dl-name"),
      });
    });
  });
}

function pad3(n) {
  return String(n).padStart(3, "0");
}

function slotCard(v, projectId, previewSrc = "", reuse = null, isCheckFlow = false) {
  const n = Number(v.number);
  const id = pad3(n);
  const has = String(v.status || "").toUpperCase() === "READY";
  const desc = v.description || v.action || v.acquisition_note || "";
  const kind = "Google Flow";
  const src = previewSrc || `/api/projects/${encodeURIComponent(projectId)}/images/${n}?v=${IMG_BOOT}`;
  const local = previewSrc ? ` data-local="1"` : "";
  const st = String((reuse && reuse.status) || "").toUpperCase();
  let reuseLabel = "";
  if (isCheckFlow) {
    if (has || st === "EXACT") reuseLabel = "EXACT";
    else if (st === "REUSED") reuseLabel = "FALLBACK";
    else if (st === "REVIEW_REUSE") reuseLabel = "REVIEW";
    else if (st.includes("MISSING")) reuseLabel = "MISSING EXACT";
  } else {
    reuseLabel = st === "EXACT" ? "EXACT" : st === "REUSED" ? "REUSED" : st === "REVIEW_REUSE" ? "REVIEW" : st.includes("MISSING") ? "MISSING" : "";
  }
  const reuseMeta = reuseLabel
    ? `<div class="ff-episode-meta"><strong>${reuseLabel}</strong>${
        reuse && reuse.assigned_asset && reuseLabel !== "EXACT" && !has
          ? ` · ${esc(String(reuse.assigned_asset))}`
          : ""
      }${reuse && reuse.score && (reuseLabel === "FALLBACK" || reuseLabel === "REVIEW") ? ` · ${esc(String(reuse.score))}` : ""}${
        reuse && reuse.reason && reuseLabel !== "EXACT" && !has ? ` · ${esc(String(reuse.reason).slice(0, 90))}` : ""
      }</div>${
        reuseLabel === "FALLBACK" || reuseLabel === "REVIEW"
          ? `<button type="button" class="btn btn-ghost" data-disable-reuse="${n}">No reutilizar</button>`
          : ""
      }`
    : "";
  return `
    <article class="shot" data-slot="${n}">
      <strong>${esc(v.moment_label ? `${v.moment_label} · foto` : "Imagen")} ${id}</strong>
      <div class="ff-episode-meta">${has ? "✓ ya está" : "○ falta"} · ${esc(kind)}${v.moment_label ? " · sin orden" : ""}</div>
      ${reuseMeta}
      <div class="ff-episode-meta">${esc(String(desc).slice(0, 240))}</div>
      <div class="slot-frame">
        ${has
          ? `<img class="slot-thumb" src="${esc(src)}" alt="${id}" loading="lazy" decoding="async"${local} />`
          : `<div class="slot-placeholder">16:9</div>`}
      </div>
      <div class="slot-actions">
        ${kind === "Google Flow"
          ? `<button type="button" class="btn btn-soft" data-copy-slot="${n}">1) Copiar prompt ${id}</button>`
          : ""}
        <label class="btn ${has ? "btn-soft" : "btn-primary"} slot-upload">
          ${has ? "Cambiar esta" : "2) Subir esta imagen"}
          <input type="file" accept="image/png,image/jpeg,image/webp,image/heic,image/heif,.png,.jpg,.jpeg,.webp,.heic,.heif" multiple data-slot-file="${n}" hidden />
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

async function compressStill(file) {
  try {
    if (!file) return file;
    const bmp = await createImageBitmap(file);
    const scale = Math.min(1, 1920 / bmp.width, 1080 / bmp.height);
    const w = Math.max(1, Math.round(bmp.width * scale));
    const h = Math.max(1, Math.round(bmp.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d", { alpha: false });
    ctx.fillStyle = "#111";
    ctx.fillRect(0, 0, w, h);
    ctx.drawImage(bmp, 0, 0, w, h);
    bmp.close();
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
    if (!blob || blob.size < 40) return file;
    const base = String(file.name || "still").replace(/\.[^.]+$/, "");
    return new File([blob], `${base}.jpg`, { type: "image/jpeg" });
  } catch {
    return file;
  }
}

function slotMeta(card) {
  const metas = [...(card?.querySelectorAll(".ff-episode-meta") || [])];
  const strong = card?.querySelector("strong")?.textContent || "";
  const mood = strong.includes("·") ? strong.split("·")[0].replace(/\s*foto\s*$/i, "").trim() : "";
  return {
    desc: metas[1]?.textContent || "",
    moment_label: mood && mood !== "Imagen" ? mood : "",
    visual_type: (metas[0]?.textContent || "").includes("documento") ? "OTHER" : "FLOW_REENACTMENT",
  };
}

function slotIsBusy(card) {
  if (!card) return true;
  if (card.dataset.uploading === "1") return true;
  return Boolean(card.querySelector(".slot-thumb"));
}

function cardsInSameBatch(card) {
  const wrap = card?.closest(".batch-slots");
  if (wrap) return [...wrap.querySelectorAll(":scope > [data-slot]")];
  return card ? [card] : [];
}

function pickTargetCards(startCard, count) {
  const cards = cardsInSameBatch(startCard);
  const startN = Number(startCard.dataset.slot);
  const rotated = [
    ...cards.filter((c) => Number(c.dataset.slot) >= startN),
    ...cards.filter((c) => Number(c.dataset.slot) < startN),
  ];
  const empty = rotated.filter((c) => c === startCard || !slotIsBusy(c));
  const rest = empty.filter((c) => c !== startCard);
  return [startCard, ...rest].slice(0, count);
}

const _stillQ = [];
let _stillActive = 0;
const STILL_PARALLEL = 1;

function enqueueStill(job) {
  _stillQ.push(job);
  pumpStills();
}

function pumpStills() {
  while (_stillActive < STILL_PARALLEL && _stillQ.length) {
    const job = _stillQ.shift();
    _stillActive += 1;
    runStillUpload(job).finally(() => {
      _stillActive -= 1;
      const left = _stillQ.length + _stillActive;
      if (left > 0) toast(`Subiendo… quedan ${left}`, 1600);
      pumpStills();
    });
  }
}

async function runStillUpload(job) {
  const { projectId, n, file, previewSrc, desc, moment_label, visual_type } = job;
  let lastErr = null;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const jpeg = await compressStill(file);
      const fd = new FormData();
      fd.append("files", jpeg, jpeg.name || `still-${pad3(n)}.jpg`);
      fd.append("force_number", String(n));
      await api(`/api/projects/${encodeURIComponent(projectId)}/images/upload`, {
        method: "POST",
        body: fd,
      });
      const live = document.querySelector(`[data-slot="${n}"]`);
      if (live) live.dataset.uploading = "";
      toast(`${pad3(n)} lista`);
      return;
    } catch (e) {
      lastErr = e;
    }
  }
  toast(lastErr?.message || `No se pudo subir ${pad3(n)}`);
  const live = document.querySelector(`[data-slot="${n}"]`);
  if (live) {
    replaceSlotCard(live, projectId, {
      number: n,
      status: "MISSING",
      description: desc,
      visual_type: visual_type || "FLOW_REENACTMENT",
      moment_label,
    });
  }
  if (previewSrc) URL.revokeObjectURL(previewSrc);
}

function beginStillUploads(projectId, files, targetCards) {
  const list = [...files].filter(Boolean);
  if (!list.length || !targetCards.length) return;
  if (list.length > targetCards.length) {
    toast(`Solo hay ${targetCards.length} recuadros libres. El resto subilo después.`);
  }
  const n = Math.min(list.length, targetCards.length);
  for (let i = 0; i < n; i += 1) {
    const file = list[i];
    const card = targetCards[i];
    const num = Number(card.dataset.slot);
    const meta = slotMeta(card);
    const previewSrc = URL.createObjectURL(file);
    card.dataset.uploading = "1";
    const next = replaceSlotCard(
      card,
      projectId,
      {
        number: num,
        status: "READY",
        description: meta.desc,
        visual_type: meta.visual_type,
        moment_label: meta.moment_label,
      },
      previewSrc
    );
    next.dataset.uploading = "1";
    enqueueStill({
      projectId,
      n: num,
      file,
      previewSrc,
      card: next,
      desc: meta.desc,
      moment_label: meta.moment_label,
      visual_type: meta.visual_type,
    });
  }
}

function bindSlotUploads(root, projectId) {
  if (!root) return;
  root.querySelectorAll(".slot-thumb").forEach((img) => {
    img.onerror = () => {
      if (img.dataset.local === "1" || (img.src || "").startsWith("blob:")) return;
      const tries = Number(img.dataset.tries || "0");
      if (tries < 2) {
        img.dataset.tries = String(tries + 1);
        const u = new URL(img.src, location.href);
        u.searchParams.set("r", String(Date.now()));
        setTimeout(() => {
          img.src = `${u.pathname}${u.search}`;
        }, 800);
        return;
      }
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
        toast(`Prompt ${pad3(n)} copiado. Pegalo en Flow (sin subtítulos en la imagen). Generá UNA y subila.`);
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
        const meta = slotMeta(card);
        replaceSlotCard(card, projectId, {
          number: n,
          status: "MISSING",
          description: meta.desc,
          visual_type: meta.visual_type,
          moment_label: meta.moment_label,
        });
        toast(`${pad3(n)} eliminada`);
      } catch (e) {
        toast(e.message);
        btn.disabled = false;
      }
    };
  });
  root.querySelectorAll("[data-slot-file]").forEach((inp) => {
    inp.onchange = () => {
      const files = [...(inp.files || [])];
      inp.value = "";
      if (!files.length) return;
      const card = inp.closest("[data-slot]");
      beginStillUploads(projectId, files, pickTargetCards(card, files.length));
    };
  });
  root.querySelectorAll("[data-batch-files]").forEach((inp) => {
    inp.onchange = () => {
      const files = [...(inp.files || [])];
      inp.value = "";
      if (!files.length) return;
      const wrap = inp.closest("article")?.querySelector(".batch-slots");
      const targets = [...(wrap?.querySelectorAll(":scope > [data-slot]") || [])].filter((c) => !slotIsBusy(c));
      if (!targets.length) {
        toast("Este bloque ya está lleno");
        return;
      }
      beginStillUploads(projectId, files, targets);
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
  const status = document.getElementById("boot-status");
  const tips = [
    "Cargando canal y proyectos",
    "Sincronizando índice (rápido)",
    "Preparando el Studio",
  ];
  let tip = 0;
  const tipTimer = setInterval(() => {
    tip = (tip + 1) % tips.length;
    if (status) status.textContent = tips[tip];
  }, 1200);
  try {
    if (status) status.textContent = tips[0];
    // Hard cap — never leave the user staring at skeletons for minutes.
    state.bootstrap = await api("/api/bootstrap", { timeoutMs: 12000 });
    state.contentFormat =
      state.bootstrap?.formats?.active ||
      state.bootstrap?.channel?.content_format ||
      state.contentFormat ||
      "check_als";
    loadIdeasCache();
    renderCreds(state.bootstrap.credentials);
    const note = state.bootstrap?.workspace?.sync_note;
    if (note) toast(note, 5000);
    recheckKeys().catch((e) => toast(e.message));
    DL.resumeAll();
    const hash = location.hash.replace("#", "");
    if (hash.startsWith("project/")) {
      const id = decodeURIComponent(hash.slice("project/".length));
      if (status) status.textContent = "Abriendo episodio…";
      await openProject(id);
      return;
    }
    if (hash === "ideas") return go("ideas");
    if (hash === "library") return go("library");
    go("home");
  } catch (e) {
    const msg = String(e.message || e);
    stage().innerHTML = `
      <div class="panel">
        <p class="kicker">No pudo cargar</p>
        <h2 style="margin:0 0 0.5rem">El Studio tardó demasiado</h2>
        <p class="lead">${esc(msg)}</p>
        <div class="actions" style="margin-top:1rem">
          <button class="btn btn-accent" id="boot-retry">Reintentar</button>
        </div>
      </div>`;
    $("#boot-retry").onclick = () => location.reload();
  } finally {
    clearInterval(tipTimer);
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
  setStageMode("home");
  const b = state.bootstrap;
  const s = b.stats;
  const fmt = b.formats?.active || b.channel?.content_format || "check_als";
  const isCheck = fmt === "check_als";
  const active = activeInProgressProject();
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
        <p class="lead">${
          isCheck
            ? "Simulaciones de vida aspiracional en segunda persona. Concepto → arquitectura → script → visuales → voz."
            : esc(b.channel.tagline) + " One true story a day. Research → script → Flow → voice → render."
        }</p>
        <p class="lead ws-line" style="font-size:0.9rem;opacity:.85">
          Datos: <code>${esc((b.workspace && b.workspace.projects_dir) || "projects/")}</code>
          ${b.workspace && b.workspace.supabase
            ? " · Supabase listo (Subir / Bajar entre PCs)"
            : b.workspace && b.workspace.synced
              ? " · sync carpeta activo"
              : " · solo esta PC"}
        </p>
        <div class="actions">
          <button class="btn btn-primary" id="cta-new">${isCheck ? "Elegir fantasía de vida" : "Create today's video"}</button>
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
    ${
      active
        ? `<div class="panel" style="margin-bottom:1.2rem;border-left:4px solid var(--accent)">
          <p class="kicker">Video en producción</p>
          <h3>${esc(active.title)}</h3>
          <p class="lead">Episodio ${String(active.episode_number).padStart(3, "0")} · ${esc(active.ui_step || "in progress")}</p>
          <div class="actions">
            <button class="btn btn-primary" data-open="${esc(active.id)}">Continuar este video</button>
            <button class="btn btn-ghost" id="cta-concepts">Ver conceptos</button>
          </div>
        </div>`
        : ""
    }
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
  const ctaConcepts = $("#cta-concepts");
  if (ctaConcepts) {
    ctaConcepts.onclick = () => {
      location.hash = "ideas";
      go("ideas");
    };
  }
  stage().querySelectorAll("[data-open]").forEach((btn) => {
    btn.onclick = () => openProject(btn.dataset.open);
  });
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
  setStageMode("home");
  loadIdeasCache();
  const fmt = state.contentFormat || state.bootstrap?.formats?.active || "check_als";
  const isCheck = fmt === "check_als";
  const active = activeInProgressProject();
  stage().innerHTML = `
    <p class="kicker">${isCheck ? "Check · Concept" : "New episode"}</p>
    <h1 class="h1">${isCheck ? "Elegí una fantasía de vida" : "Pick a story engine"}</h1>
    <p class="lead">${
      isCheck
        ? "Simulaciones aspiracionales rankeadas. Título, thumbnail, hook y scores — elegí una y seguí produciendo sin perder la lista."
        : "Five true-story angles. Choose one, or drop your own topic."
    }</p>
    ${
      active
        ? `<div class="panel" style="margin-bottom:1rem;border-left:4px solid var(--accent)">
          <p class="kicker">Video principal en curso</p>
          <h3>${esc(active.title)}</h3>
          <p class="lead">Ep. ${String(active.episode_number).padStart(3, "0")} · ${esc(active.ui_step || "in progress")}</p>
          <button class="btn btn-primary" data-open-active="${esc(active.id)}">Abrir este episodio</button>
        </div>`
        : ""
    }
    <div class="actions" style="margin-bottom:1.2rem">
      <label class="tag" style="display:inline-flex;gap:0.4rem;align-items:center">
        Format
        <select id="fmt-select">
          <option value="check_als"${isCheck ? " selected" : ""}>Check ALS</option>
          <option value="documentary"${!isCheck ? " selected" : ""}>Documentary</option>
        </select>
      </label>
      <button class="btn btn-accent" id="gen-ideas">${isCheck ? "Generar conceptos (10)" : "Generate ideas"}</button>
      <button class="btn btn-ghost" id="manual">I have a topic</button>
      <button class="btn btn-ghost" id="back-home">Back</button>
    </div>
    <div id="manual-box" class="panel hidden field" style="margin-bottom:1rem">
      <label>Topic / working title</label>
      <input id="manual-topic" placeholder="${
        isCheck
          ? "e.g. POV: You Build a Hotel Empire From One Motel"
          : "e.g. The SoftBank bet that almost buried WeWork"
      }"/>
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
  const openActive = $("[data-open-active]");
  if (openActive) openActive.onclick = () => openProject(openActive.dataset.openActive);
  $("#fmt-select").onchange = async () => {
    const next = $("#fmt-select").value;
    try {
      const data = await api("/api/channel/format", {
        method: "POST",
        body: JSON.stringify({ content_format: next }),
      });
      state.contentFormat = data.content_format || next;
      if (state.bootstrap) {
        state.bootstrap.formats = state.bootstrap.formats || {};
        state.bootstrap.formats.active = state.contentFormat;
        if (data.channel) state.bootstrap.channel = { ...(state.bootstrap.channel || {}), ...data.channel };
      }
      state.ideas = [];
      state.pickedConceptId = "";
      saveIdeasCache();
      renderIdeas();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#manual").onclick = () => $("#manual-box").classList.toggle("hidden");
  $("#manual-go").onclick = async () => {
    const topic = $("#manual-topic").value.trim();
    if (!topic) return toast("Write a topic first");
    try {
      const data = await withBusy("Creating episode…", () =>
        api("/api/projects", {
          method: "POST",
          body: JSON.stringify({
            topic,
            title: topic,
            content_format: state.contentFormat || fmt,
          }),
        })
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
        <p class="lead">Todavía no hay ${isCheck ? "conceptos" : "ideas"}. Tocá <strong>Generar conceptos</strong> — trae ~10 fantasías rankeadas (tarda 1–3 min).</p>
      </div>`;
  }
}

async function loadIdeas(force) {
  const fmt = state.contentFormat || state.bootstrap?.formats?.active || "check_als";
  const want = fmt === "check_als" ? 10 : 5;
  try {
    const data = await withBusy(fmt === "check_als" ? "Generando fantasías de vida…" : "Finding story engines…", () =>
      api("/api/ideas", {
        method: "POST",
        body: JSON.stringify({ count: want, content_format: fmt }),
        timeoutMs: 240000,
      })
    );
    state.contentFormat = data.content_format || fmt;
    state.ideas = data.concepts?.length ? data.concepts : data.ideas || [];
    saveIdeasCache();
    paintIdeas();
    if (!state.ideas.length) {
      $("#ideas").innerHTML = `<div class="notice bad">No llegaron conceptos. Revisá OPENAI_API_KEY y probá de nuevo.</div>`;
      toast("Sin conceptos — probá otra vez");
      return;
    }
    if (force) toast(fmt === "check_als" ? `${state.ideas.length} conceptos listos` : "Ideas ready");
  } catch (e) {
    toast(e.message);
    $("#ideas").innerHTML = `<div class="notice bad">${esc(e.message)}</div>`;
  }
}

function paintIdeas() {
  const host = $("#ideas");
  if (!host) return;
  const fmt = state.contentFormat || state.bootstrap?.formats?.active || "check_als";
  if (fmt === "check_als") {
    paintCheckConcepts(host);
    return;
  }
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
          api("/api/projects", {
            method: "POST",
            body: JSON.stringify({ idea, content_format: "documentary" }),
          })
        );
        state.project = data.project;
        state.activeProjectId = data.project.id;
        saveIdeasCache();
        location.hash = `project/${data.project.id}`;
        go("project");
        await refreshBootstrap();
      } catch (e) {
        toast(e.message);
      }
    };
  });
}

function paintCheckConcepts(host) {
  const sorted = [...state.ideas].sort((a, b) => (b.overall_score || 0) - (a.overall_score || 0));
  state.ideas = sorted;
  saveIdeasCache();
  host.innerHTML = sorted
    .map((c, i) => {
      const scores = c.scores || {};
      const scoreBits = Object.keys(scores)
        .slice(0, 6)
        .map((k) => `<span class="tag">${esc(k)} ${esc(scores[k])}</span>`)
        .join("");
      const thumb = c.thumbnail_concept || {};
      const coh = c.coherence || {};
      const cid = String(c.id || "");
      const isPicked = state.pickedConceptId && cid && state.pickedConceptId === cid;
      return `
      <article class="idea idea-check${isPicked ? " idea-picked" : ""}"${isPicked ? ' style="outline:2px solid var(--accent);outline-offset:2px"' : ""}>
        <div class="tags" style="margin-bottom:0.4rem">
          ${isPicked ? '<span class="tag" style="background:var(--accent);color:#fff">Video principal</span>' : ""}
          <span class="tag">${esc(c.story_category || "—")}</span>
          <span class="tag">score ${esc(c.overall_score ?? "—")}</span>
          <span class="tag">${esc(c.ending_direction || "")}</span>
          <span class="tag">${coh.pass ? "coherent" : "review coherence"}</span>
        </div>
        <h3>${esc(c.title || "Untitled")}</h3>
        <p><strong style="color:var(--ink)">Fantasy</strong> — ${esc(c.one_line_fantasy || "")}</p>
        <p>${esc(c.premise || "")}</p>
        <p><strong style="color:var(--ink)">Start</strong> — ${esc(c.starting_state || "—")}</p>
        <p><strong style="color:var(--ink)">End</strong> — ${esc(c.end_state || "—")}</p>
        <p><strong style="color:var(--ink)">Transformation</strong> — ${esc(c.core_transformation || "—")}</p>
        <p><strong style="color:var(--ink)">Hook</strong></p>
        <pre class="hook-block">${esc(c.hook || "")}</pre>
        <p><strong style="color:var(--ink)">Thumbnail concept</strong> — ${esc(thumb.main_visual || "—")}</p>
        <p class="muted">${esc(thumb.central_contrast || "")} · ${esc(thumb.emotion || "")}</p>
        <details>
          <summary>Thumbnail prompt</summary>
          <pre class="hook-block">${esc(thumb.thumbnail_prompt || "")}</pre>
        </details>
        <div class="tags">${scoreBits}</div>
        <div class="actions">
          <button class="btn btn-primary" data-pick="${i}">${isPicked ? "Abrir episodio" : "Elegir este concepto"}</button>
          <button class="btn btn-ghost" data-regen="title" data-i="${i}">Regen title</button>
          <button class="btn btn-ghost" data-regen="thumbnail" data-i="${i}">Regen thumb</button>
          <button class="btn btn-ghost" data-regen="hook" data-i="${i}">Regen hook</button>
          <button class="btn btn-ghost" data-regen="concept" data-i="${i}">Regen concept</button>
        </div>
      </article>`;
    })
    .join("");

  host.querySelectorAll("[data-pick]").forEach((btn) => {
    btn.onclick = async () => {
      const concept = state.ideas[Number(btn.dataset.pick)];
      const cid = String(concept?.id || "");
      if (state.pickedConceptId && cid && state.pickedConceptId === cid && state.activeProjectId) {
        await openProject(state.activeProjectId);
        return;
      }
      try {
        const data = await withBusy("Creando episodio Check…", () =>
          api("/api/projects", {
            method: "POST",
            body: JSON.stringify({ concept, content_format: "check_als" }),
          })
        );
        state.project = data.project;
        state.pickedConceptId = cid || state.pickedConceptId;
        state.activeProjectId = data.project.id;
        saveIdeasCache();
        location.hash = `project/${data.project.id}`;
        go("project");
        await refreshBootstrap();
        toast("Episodio creado — la lista de conceptos sigue en Ideas");
      } catch (e) {
        toast(e.message);
      }
    };
  });
  host.querySelectorAll("[data-regen]").forEach((btn) => {
    btn.onclick = async () => {
      const i = Number(btn.dataset.i);
      const part = btn.dataset.regen;
      const package0 = state.ideas[i];
      try {
        const data = await withBusy(`Regenerating ${part}…`, () =>
          api("/api/concepts/regenerate", {
            method: "POST",
            body: JSON.stringify({ package: package0, part }),
          })
        );
        state.ideas[i] = data.package;
        saveIdeasCache();
        paintIdeas();
        toast(`${part} updated`);
      } catch (e) {
        toast(e.message);
      }
    };
  });
}

function renderLibrary() {
  setStageMode("home");
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
  setStageMode("project");
  stopVideoPolls();
  let step = p.ui_step || "research";
  if (step === "images") step = "flow";
  // Subs are burned into the episode during render — no separate step.
  if (step === "subs") step = "render";
  const isCheck = p.content_format === "check_als" || p.mode === "check_als";
  if (isCheck && (step === "research")) step = "story";
  const steps = isCheck
    ? ["topic", "story", "script", "flow", "voice", "music", "preview", "render", "publish"]
    : ["topic", "research", "story", "script", "flow", "voice", "music", "preview", "render", "publish"];
  const stepLabel = isCheck
    ? {
        topic: "1 Premisa",
        story: "2 Historia",
        script: "3 Guion",
        flow: "4 Imgs",
        voice: "5 Voz",
        music: "6 Música",
        preview: "7 Prueba",
        render: "8 Video",
        publish: "9 YouTube",
      }
    : {
        topic: "1 Tema",
        research: "2 Info",
        story: "3 Historia",
        script: "4 Guion",
        flow: "5 Pedir imgs",
        voice: "6 Voz",
        music: "7 Música",
        preview: "8 Prueba",
        render: "9 Video",
        publish: "10 YouTube",
        done: "10 YouTube",
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
        const next = btn.dataset.step;
        state.project.ui_step = next;
        renderProject();
        try {
          const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
            method: "PATCH",
            body: JSON.stringify({ step: next }),
          });
          if (data?.project) {
            state.project = data.project;
            if (String(data.project.ui_step || "") !== next) {
              renderProject();
            }
          }
        } catch (e) {
          toast(e.message);
        }
      };
    });
  const ws = $("#ws");
  // Check: story must be approved before script/flow. Voice+render are fully unlocked after that.
  if (isCheck && !p.check_story_approved && !["topic", "story"].includes(step)) {
    return paintCheckLocked(ws, p, step);
  }
  if (isCheck && ["voice", "music", "preview", "render"].includes(step) && !p.script_approved) {
    return paintCheckLocked(
      ws,
      p,
      step,
      "Aprobá el guion primero. Después podés generar voz y seguir al video."
    );
  }
  if (step === "topic") return paintStory(ws, p);
  if (step === "research") return paintResearch(ws, p);
  if (step === "story") return isCheck ? paintCheckStory(ws, p) : paintStoryPlan(ws, p);
  if (step === "script") return paintScript(ws, p);
  if (step === "flow" || step === "images") return paintFlow(ws, p);
  if (step === "voice") return paintVoice(ws, p);
  if (step === "music") return paintMusic(ws, p);
  if (step === "preview") return paintPreview(ws, p);
  if (step === "render") return paintRender(ws, p);
  if (step === "subs") return paintRender(ws, p);
  if (step === "publish" || step === "done") return paintPublish(ws, p);
  paintResearch(ws, p);
}

function paintStory(ws, p) {
  const idea = p.idea || {};
  const isCheck = p.content_format === "check_als" || p.mode === "check_als";
  ws.innerHTML = `
    <div class="panel">
      <p class="kicker">${isCheck ? "Premisa" : "Topic"}</p>
      <p>${esc(idea.story || p.topic)}</p>
      <p style="margin-top:0.8rem"><strong>Hook</strong> — ${esc(idea.hook || "—")}</p>
      <div class="actions">
        <button class="btn btn-primary" id="to-research">${isCheck ? "Ir a Historia" : "Continue to research"}</button>
      </div>
    </div>`;
  $("#to-research").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: isCheck ? "story" : "research" }),
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

function paintCheckLocked(ws, p, step, extra) {
  const cs = p.check_story || {};
  const review = cs.review || {};
  const generated = Boolean(cs.generated);
  const approved = Boolean(p.check_story_approved || cs.approved);
  const hasStory = generated || Boolean(cs.synopsis) || Number(cs.beat_count || 0) > 0 || (review.timeline || []).length > 0;
  const msg = extra || `Aprobá la historia para desbloquear ${step}.`;
  const goTarget = String(extra || "").toLowerCase().includes("guion") ? "script" : "story";
  const goLabel = goTarget === "script" ? "Ir a Guion" : "Volver a Historia";
  ws.innerHTML = `
    <div class="panel workspace">
      <div class="notice">${esc(msg)}</div>
      <p class="lead">Historia → Guion → Imágenes → Voz → Música → Prueba → Video. Podés avanzar con imágenes parciales.</p>
      <div class="actions">
        <button class="btn btn-primary" id="go-story">${goLabel}</button>
        ${hasStory && !approved ? `<button class="btn btn-accent" id="approve-from-lock">Aprobar historia → Guion</button>` : ""}
      </div>
    </div>`;
  $("#go-story").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: goTarget }),
    });
    state.project = data.project;
    renderProject();
  };
  $("#approve-from-lock")?.addEventListener("click", async () => {
    try {
      const data = await api(`/api/projects/${encodeURIComponent(p.id)}/story/approve`, { method: "POST" });
      state.project = data.project;
      toast("Historia aprobada. Ya podés ir a Guion.");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  });
}

function money(n) {
  if (n === null || n === undefined || n === "") return "—";
  const v = Number(n);
  if (!Number.isFinite(v)) return esc(n);
  const sign = v < 0 ? "-" : "";
  const a = Math.abs(v);
  if (a >= 1000000) return `${sign}$${(a / 1000000).toFixed(2)}M`;
  return `${sign}$${Math.round(a).toLocaleString("en-US")}`;
}

function paintCheckStory(ws, p) {
  const cs = p.check_story || {};
  const review = cs.review || {};
  const overview = review.overview || {};
  const quality = cs.quality || {};
  const scores = quality.scores || review.quality_scores || {};
  const flags = quality.flags || review.quality_flags || [];
  const loops = review.open_loops || [];
  const timeline = review.timeline || [];
  const major = review.major_events || [];
  const rewards = review.rewards || [];
  const setbacks = review.setbacks || [];
  const ending = review.ending || {};
  const fw = review.final_world || {};
  const fantasy = overview.fantasy || {};
  const vehicle = overview.vehicle || {};
  const world = overview.world || {};
  const prot = overview.protagonist || {};
  const hardRaw = quality.hard_fails || review.hard_fails || [];
  const hardFromFlags = flags.filter((f) => f.hard);
  const hard = hardRaw.length ? hardRaw : hardFromFlags;
  const generated = Boolean(cs.generated);
  const approved = Boolean(p.check_story_approved || cs.approved);
  const hasStory = generated || Boolean(cs.synopsis) || Number(cs.beat_count || 0) > 0 || timeline.length > 0;
  const acq = review.acquisition || {};
  const ledger = review.ownership_ledger || fw.ledger || {};

  const scoreBits = Object.keys(scores)
    .map((k) => `<span class="tag ${scores[k] === "flag" ? "bad" : ""}">${esc(k)} ${esc(scores[k])}</span>`)
    .join("");
  const flagBits = flags.length
    ? flags.map((f) => `<div class="notice bad">[${esc(f.code)}] ${esc(f.detail || "")} ${f.beat_id ? "· " + esc(f.beat_id) : ""}</div>`).join("")
    : `<div class="notice ok">Sin flags de calidad.</div>`;
  const loopBits = loops.length
    ? loops
        .map(
          (l) =>
            `<li><strong>${esc(l.id || "")}</strong> — ${esc(l.question || "")} · abre ${esc(l.opened_at || "—")} · ${esc(l.status || "open")} · cierra ${esc(l.closed_at || "—")}</li>`
        )
        .join("")
    : "<li>Todavía no hay loops.</li>";
  const timeBits = timeline
    .map((row) => {
      const life = row.life_change ? ` · ${esc(row.life_change)}` : "";
      return `<tr>
        <td>${esc(row.time || "")}</td>
        <td>${esc(row.event || "")}</td>
        <td>${money(row.cash)}</td>
        <td>${esc(row.ownership ?? "—")}%</td>
        <td>${money(row.team_value)}</td>
        <td>${money(row.team_debt)}</td>
        <td>${esc(row.attendance ?? "—")}</td>
        <td>${esc(row.record || "—")}</td>
        <td>${life}</td>
      </tr>`;
    })
    .join("");
  const majorBits = major.map((b) => `<li><strong>[${esc(b.beat_id)}] ${esc(b.purpose || "")}</strong> — ${esc(b.event || "")}</li>`).join("");
  const rewardBits = rewards.map((b) => `<li>[${esc(b.beat_id)}] ${esc(b.event || "")}</li>`).join("") || "<li>—</li>";
  const seasons = review.season_history || (fw.season_history) || [];
  const seasonBits = seasons.map((s) =>
    `<li>T${esc(s.season)} ${esc(s.record || "")} · ${esc(s.playoff_result || "")} · att ${esc(s.attendance_avg ?? "—")} · ${esc((s.major_events || []).join(", "))}</li>`
  ).join("") || "<li>—</li>";
  const setbackBits = setbacks.map((b) => `<li>[${esc(b.beat_id)}] <em>${esc(b.category || b.kind || "")}</em> ${esc(b.event || "")}</li>`).join("") || "<li>—</li>";

  ws.innerHTML = `
    <div class="panel workspace">
      ${approved ? `<div class="notice ok">Historia aprobada. Ya podés ir a Guion. Todavía no hay voz ni render.</div>` : ""}
      ${generated && !approved ? `<div class="notice">Revisá la película. Cuando estés conforme, aprobá la historia para desbloquear el guion.</div>` : ""}
      <div class="actions">
        <button class="btn btn-accent" id="gen-check-story">${hasStory ? "Regenerate Story" : "Generate Story Architecture"}</button>
        ${hasStory && !approved ? `<button class="btn btn-primary" id="approve-check-story">${hard.length ? "Continuar al guion →" : "Aprobar historia → Guion"}</button>` : ""}
      </div>
      ${hard.length ? `<div class="notice bad">Hay ${hard.length} advertencia(s) — podés regenerar o tocar <strong>Continuar al guion</strong>.</div>` : ""}
      <p class="kicker">Story Overview</p>
      <p><strong>${esc(world.team_name || p.title || "")}</strong> · ${esc(world.league_name || "")} · ${esc(world.city || "")}</p>
      <p>${esc(fantasy.surface_desire || "")}</p>
      <p class="muted">${esc(acq.summary || vehicle.acquisition_structure || vehicle.core_mechanism || "")}</p>
      <p>Ledger: vos ${esc(ledger.protagonist ?? "—")}% · inversores ${esc(ledger.investors ?? "—")}% · vendedor ${esc(ledger.seller ?? "—")}%</p>
      ${hard.length ? hard.map((f) => `<div class="notice bad">HARD [${esc(f.code)}] ${esc(f.detail || "")}</div>`).join("") : ""}
      <p>Protagonista interno: ${esc(prot.age || "")} · ${esc(prot.starting_life || "")}</p>
      <div class="tags">${scoreBits}</div>
      <details ${generated ? "open" : ""}>
        <summary>Synopsis</summary>
        <pre class="shot" style="white-space:pre-wrap;max-height:420px;overflow:auto">${esc(cs.synopsis || "Generá la arquitectura para leer la película.")}</pre>
      </details>
      <details ${generated ? "open" : ""}>
        <summary>Timeline</summary>
        <div class="check-table-wrap">
          <table class="check-table">
            <thead><tr><th>Tiempo</th><th>Evento</th><th>Cash</th><th>Own</th><th>Valor</th><th>Deuda</th><th>Público</th><th>Record</th><th>Vida</th></tr></thead>
            <tbody>${timeBits || `<tr><td colspan="9">—</td></tr>`}</tbody>
          </table>
        </div>
      </details>
      <details>
        <summary>Season history</summary>
        <p class="muted">debt_risk: ${esc(review.debt_risk_state || fw.debt_risk_state || "—")} · championships: ${esc(fw.championships ?? fw.sports?.championships ?? "—")}</p>
        <ul>${seasonBits}</ul>
      </details>
      <details>
        <summary>Major events</summary>
        <ul>${majorBits || "<li>—</li>"}</ul>
      </details>
      <div class="two-col">
        <div><p class="kicker">Rewards</p><ul>${rewardBits}</ul></div>
        <div><p class="kicker">Setbacks</p><ul>${setbackBits}</ul></div>
      </div>
      <details>
        <summary>Open loops</summary>
        <ul>${loopBits}</ul>
      </details>
      <details>
        <summary>Ending + mundo final</summary>
        <p>${esc(ending.scene || overview.ending || "—")}</p>
        <p>${esc(ending.final_state || "")}</p>
        <p class="muted">${esc(ending.unresolved || "")}</p>
        <p>AGE ${esc(fw.age ?? "—")} · CASH ${money(fw.cash)} · OWN ${esc(fw.ownership ?? "—")}% · VAL ${money(fw.team_value)} · DEBT ${money(fw.team_debt)} · ATT ${esc(fw.attendance ?? "—")} · ${esc(fw.job || "")} · ${esc(fw.home || "")}</p>
      </details>
      <p class="kicker">Quality flags</p>
      ${flagBits}
    </div>`;

  $("#gen-check-story").onclick = async () => {
    try {
      const data = await withBusy("Construyendo la película (blueprint + beats)…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/story/generate`, { method: "POST", timeoutMs: 720000 })
      );
      state.project = data.project;
      toast("Story Architecture lista — leé la synopsis antes de aprobar");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  const approveStory = async () => {
    if (hard.length) {
      const ok = confirm(
        `Hay ${hard.length} advertencia(s) en la historia.\n\n¿Continuar al guion igual?`
      );
      if (!ok) return;
    }
    try {
      const data = await api(`/api/projects/${encodeURIComponent(p.id)}/story/approve`, { method: "POST" });
      state.project = data.project;
      toast("Historia aprobada — escribiendo guion…");
      renderProject();
      try {
        const scripted = await withBusy("Escribiendo guion desde la historia…", () =>
          api(`/api/projects/${encodeURIComponent(p.id)}/script/generate`, {
            method: "POST",
            timeoutMs: 290000,
          })
        );
        state.project = scripted.project;
        toast("Guion listo");
        renderProject();
      } catch (ge) {
        toast(ge.message || "No se pudo generar el guion — tocá Generate script");
        renderProject();
      }
    } catch (e) {
      toast(e.message);
    }
  };
  $("#approve-check-story")?.addEventListener("click", () => approveStory());
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
  const checkApproved = (p.content_format === "check_als" || p.mode === "check_als") && p.check_story_approved;
  if (!p.story_plan_approved && !checkApproved) {
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
        <button class="btn btn-primary" id="approve">Aprobar guion</button>
        <button class="btn btn-accent" id="gen-flow" ${p.script_approved ? "" : "disabled"} title="${p.script_approved ? "" : "Primero aprobá el guion"}">Generar Flow</button>
      </div>
      <p class="lead" style="margin-top:0.5rem">Aprobar y Generar Flow son pasos separados. Aprobá cuando el texto esté bien; generá el plan de imágenes cuando quieras.</p>
      <div class="field">
        <label>Narration (~${tw} words · flexible 1800–2200)</label>
        <textarea id="script" class="script-box">${esc(p.script)}</textarea>
      </div>
    </div>`;
  const runGenScript = async () => {
    try {
      const data = await withBusy("Escribiendo guion (puede tardar ~2 min)…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/script/generate`, {
          method: "POST",
          timeoutMs: 290000,
        })
      );
      state.project = data.project;
      const words = String(data.project?.script || "")
        .trim()
        .split(/\s+/)
        .filter(Boolean).length;
      toast(words ? `Guion listo (~${words} palabras)` : "Guion vacío — reintentá");
      renderProject();
    } catch (e) {
      toast(e.message || "Error al generar guion");
    }
  };
  $("#gen-script").onclick = () => runGenScript();
  // Auto-kick once per project if Check story is approved and textarea is empty.
  if (checkApproved && !String(p.script || "").trim()) {
    const key = `ff-autogen-script:${p.id}`;
    if (!sessionStorage.getItem(key) && !ws.dataset.autogenScript) {
      ws.dataset.autogenScript = "1";
      sessionStorage.setItem(key, "1");
      runGenScript();
    }
  }
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
      const data = await withBusy("Aprobando guion…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/script/approve`, { method: "POST" })
      );
      state.project = data.project;
      toast("Guion aprobado — ahora podés Generar Flow");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#gen-flow").onclick = async () => {
    try {
      if ($("#script")?.value != null) {
        await api(`/api/projects/${encodeURIComponent(p.id)}/script`, {
          method: "PUT",
          body: JSON.stringify({ script: $("#script").value }),
        });
      }
      if (!state.project?.script_approved && !p.script_approved) {
        toast("Primero aprobá el guion");
        return;
      }
      await rebuildFlow();
    } catch (e) {
      toast(e.message);
    }
  };
}

async function paintFlow(ws, p) {
  ws.innerHTML = `<div class="panel"><p class="lead">Cargando plan de imágenes…</p></div>`;
  let plan = null;
  let shots = null;
  let coverage = {};
  try {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/flow`);
    state.shots = data.shots;
    state.visualPlan = data.visual_plan;
    if (data.project) state.project = data.project;
    plan = data.visual_plan;
    shots = data.shots;
    coverage = data.asset_coverage || {};
  } catch (e) {
    ws.innerHTML = `
      <div class="panel workspace">
        <h2>Todavía no hay plan de imágenes</h2>
        <p class="lead">El guion ya puede estar aprobado. Acá solo generás el Flow (prompts + slots).</p>
        <div class="actions">
          <button class="btn btn-accent" id="rebuild">Generar Flow</button>
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
  const total = stats.total || visuals.length || 0;
  const isCheckFlow = p.content_format === "check_als" || p.mode === "check_als";
  const covRows = coverage.slot_plan || [];
  const covBySlot = Object.fromEntries(covRows.map((r) => [Number(r.slot), r]));
  const prog = coverage.production_progress || {};
  const fullPack = coverage.full_still_pack || coverage.production_batches?.["all-stills"] || {};
  const p01Pack = coverage.production_batches?.["p0-p1"] || coverage.production_batch || {};
  const totalSlots = prog.total_slots || total;
  const importedExact = prog.imported_exact ?? prog.generated_imported ?? 0;
  const missingExact = prog.missing_exact_assets ?? Math.max(0, totalSlots - importedExact);
  const fallbackAvail = prog.fallback_coverage_available ?? prog.temporarily_covered_by_reuse ?? 0;

  ws.innerHTML = `
    <div class="panel workspace">
      ${isCheckFlow ? `<div class="panel soft" style="margin-bottom:1.2rem;border:2px solid var(--ink,#111)">
        <h2 style="margin:0 0 0.5rem">Producción Check — un still por slot</h2>
        <ol style="margin:0;padding-left:1.2rem;line-height:1.55">
          <li><strong>Cada slot = su imagen.</strong> Generá <code>001.png</code> para el slot 001, etc.</li>
          <li><strong>P0 → P1 → P2 → P3</strong> es solo orden de generación, no permiso para saltear slots.</li>
          <li><strong>Smart Reuse</strong> solo entra si falta el still exacto — contingencia, no objetivo.</li>
          <li>Pack completo: <code>flow-pack/batches/all-stills/</code> · batch opcional: <code>p0-p1/</code></li>
        </ol>
      </div>` : `<div class="panel soft" style="margin-bottom:1.2rem;border:2px solid var(--ink,#111)">
        <h2 style="margin:0 0 0.5rem">Qué tenés que hacer acá (paso a paso)</h2>
        <ol style="margin:0;padding-left:1.2rem;line-height:1.55">
          <li><strong>Un bloque = un momento.</strong> “Le va bien”, “Se cae”, etc. Pedí ~10 fotos de ESE clima, no un orden 1-2-3.</li>
          <li><strong>Copiá el pedido del bloque</strong> → Flow. Si las mezcla, da igual: son intercambiables.</li>
          <li><strong>Subí varias de una</strong> con “Subir varias a este bloque”. Se acomodan solas en los recuadros vacíos.</li>
        </ol>
        <p class="lead" style="margin-top:0.75rem;margin-bottom:0">No hay que matchear “imagen 7 = prompt 7”.</p>
      </div>`}

      <p class="lead">Este episodio necesita <strong>${total} imágenes</strong>. ${isCheckFlow ? "Generá e importá un still por slot. Cuando tengas imágenes (aunque no estén todas), seguí a la voz." : "Todas se piden a Google Flow — incluso papeles, titulares y pantallas, como foto en escena."}</p>
      ${isCheckFlow ? `<div class="panel soft" style="margin:1rem 0;border:1px solid var(--line,#ccc)">
        <strong>STILLS — ${totalSlots} visual slots</strong>
        <div class="ff-episode-meta">Generated/imported: <strong>${importedExact} / ${totalSlots}</strong></div>
        <div class="ff-episode-meta">Exact coverage: <strong>${importedExact}</strong> · Missing exact assets: <strong>${missingExact}</strong></div>
        <div class="ff-episode-meta">Potential fallback coverage: <strong>${fallbackAvail}</strong> <span style="opacity:0.75">(solo mientras falte el still propio)</span></div>
        <div class="ff-episode-meta">Prompts ready: <strong>${prog.prompts_ready ?? totalSlots}</strong></div>
      </div>
      <div class="panel soft" id="p0p1-pack" style="margin:1rem 0">
        <strong>Batch opcional P0 + P1</strong> (${(p01Pack.shots || p01Pack.prompts || 24)} prompts prioritarios)
        <p class="lead" style="margin:0.4rem 0"><code>flow-pack/batches/p0-p1/</code> — podés empezar acá, pero el objetivo sigue siendo <strong>100 stills únicos</strong>.</p>
        <div class="actions" id="p0p1-actions"></div>
      </div>
      <div class="panel soft" style="margin:1rem 0">
        <strong>Full still generation pack</strong> — ${fullPack.prompts_ready ?? totalSlots} prompts
        <p class="lead" style="margin:0.4rem 0"><code>flow-pack/batches/all-stills/</code> · <code>manifest.json</code> + <code>prompts/001.txt</code> … <code>100.txt</code></p>
      </div>
      <div id="reuse-review"></div>` : ""}
      <div class="actions">
        <button class="btn btn-ghost" id="rebuild">Rehacer plan de imágenes</button>
        <button class="btn btn-danger" id="delete-all-stills">Eliminar todas</button>
        <button class="btn btn-primary" id="to-voice">Seguir a la voz</button>
      </div>

      <h2 style="margin-top:1.6rem">A) Caras que se repiten</h2>
      <p class="lead">Copiá el texto → Google Flow → descargá → <strong>subí acá</strong>. El nombre que ponga Flow no importa.</p>
      <div class="list" id="masters"></div>

      <h2 style="margin-top:1.6rem">B) Bloques por momento</h2>
      <p class="lead">Cada bloque es un clima del episodio. Diez ángulos del mismo momento. El orden adentro no importa.</p>
      <div class="list" id="batches"></div>

    </div>`;

  $("#rebuild").onclick = () => rebuildFlow();
  if (isCheckFlow) {
    const pack = coverage.production_batch || {};
    const shots = pack.shots || [];
    const actions = $("#p0p1-actions");
    if (actions) {
      actions.innerHTML = shots
        .map((id) => `<button class="btn btn-soft" data-copy-p01="${esc(String(id))}">Copiar ${esc(String(id))}</button>`)
        .join(" ");
      actions.querySelectorAll("[data-copy-p01]").forEach((btn) => {
        btn.onclick = async () => {
          try {
            const data = await api(`/api/projects/${encodeURIComponent(p.id)}/visuals/${Number(btn.dataset.copyP01)}/prompt`);
            await navigator.clipboard.writeText(data.prompt || "");
            toast(`Prompt ${btn.dataset.copyP01} copiado`);
          } catch (e) {
            toast(e.message);
          }
        };
      });
    }
    const reviewHost = $("#reuse-review");
    const reviews = (coverage.reuse_reviews || []).filter((r) => r.status === "REUSED" || r.status === "REVIEW_REUSE");
    const missingRows = (coverage.slot_plan || []).filter((r) => String(r.status || "").includes("MISSING"));
    const showReview = Number(importedExact) > 0;
    if (reviewHost && showReview) {
      const missingCards = missingRows
        .map((r) => {
          const n = Number(r.slot);
          return `<article class="shot"><strong>MISSING EXACT ${pad3(n)}</strong><div class="ff-episode-meta">${esc(String(r.reason || "").slice(0, 140))}</div></article>`;
        })
        .join("");
      const reuseCards = reviews
        .map((r) => {
          const srcNum = Number(String(r.source_asset || "").split("_").pop());
          const n = Number(r.target_slot);
          const label = r.status === "REVIEW_REUSE" ? "REVIEW FALLBACK" : "FALLBACK";
          return `<article class="shot">
            <strong>${label} slot ${pad3(n)}</strong>
            <div class="ff-episode-meta">falta still ${pad3(n)} · source ${esc(String(r.source_asset))} · score ${esc(String(r.reuse_score))}</div>
            <div class="ff-episode-meta">${esc(String(r.semantic_reason || "").slice(0, 160))}</div>
            <div class="slot-frame"><img class="slot-thumb" src="/api/projects/${encodeURIComponent(p.id)}/images/${srcNum}?v=${IMG_BOOT}" alt="" loading="lazy" /></div>
            <button type="button" class="btn btn-ghost" data-disable-reuse="${n}">No reutilizar</button>
          </article>`;
        })
        .join("");
      reviewHost.innerHTML = `
        <h2 style="margin-top:1.6rem">Revisión fallback (solo slots sin still propio)</h2>
        <p class="lead">Importá <code>NNN.png</code> y el slot vuelve a EXACT automáticamente.</p>
        <div class="list">${reuseCards || `<div class="notice">Ningún fallback activo.</div>`}</div>
        <h3 style="margin-top:1.2rem">Missing exact (${missingRows.length})</h3>
        <div class="list">${missingCards || `<div class="notice">Nada missing.</div>`}</div>`;
    }
  }
  const toVoice = $("#to-voice");
  if (toVoice) {
    toVoice.onclick = async () => {
      try {
        const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
          method: "PATCH",
          body: JSON.stringify({ step: "voice" }),
        });
        state.project = data.project;
        renderProject();
      } catch (e) {
        toast(e.message);
      }
    };
  }

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
            .map((n) => slotCard(byNum[Number(n)] || { number: n, visual_type: "FLOW_REENACTMENT" }, p.id, "", covBySlot[Number(n)], isCheckFlow))
            .join("");
          const mood = b.moment_label || b.label || `Bloque ${bi + 1}`;
          return `
      <article class="shot" id="batch-${bi}">
        <strong>${esc(mood)}</strong> — ${totalB} fotos del mismo clima
        <div class="ff-episode-meta">Sin orden. Flow puede mezclarlas. Subí en cualquier recuadro de este bloque.</div>
        <div class="ff-episode-meta">Referencias en Flow: ${esc(refs)}</div>
        <div class="ff-episode-meta">Subidas: <strong>${done} / ${totalB}</strong></div>
        <div class="actions">
          <button class="btn btn-primary" data-copy-batch="${bi}">Copiar pedido de este momento</button>
          <label class="btn btn-soft slot-upload">
            Subir varias a este bloque
            <input type="file" accept="image/png,image/jpeg,image/webp,image/heic,image/heif,.png,.jpg,.jpeg,.webp,.heic,.heif" multiple data-batch-files="${bi}" hidden />
          </label>
          <button class="btn btn-ghost" data-expand-batch="${bi}">Editar ángulos</button>
        </div>
        <pre class="hidden" id="batch-prompt-${bi}" style="max-height:220px;overflow:auto;margin-top:0.6rem">${esc(b.prompt || "")}</pre>
        <div class="hidden" id="batch-expand-${bi}" style="margin-top:0.6rem"></div>
        <div class="list batch-slots" style="margin-top:0.8rem">${slots}</div>
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
        toast("Pedido del momento copiado. Pegalo en Flow — el orden de salida no importa.");
      }
    };
  });
  bindSlotUploads($("#batches"), p.id);
  bindDeleteAll($("#delete-all-stills"), p.id);
  ws.querySelectorAll("[data-disable-reuse]").forEach((btn) => {
    btn.onclick = async () => {
      try {
        await api(`/api/projects/${encodeURIComponent(p.id)}/visuals/${btn.dataset.disableReuse}/reuse`, {
          method: "POST",
          body: JSON.stringify({ disable_reuse: true }),
        });
        toast("Reuse desactivado en este slot");
        state.shots = null;
        state.visualPlan = null;
        renderProject();
      } catch (e) {
        toast(e.message);
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
      <div class="list batch-slots" id="slots">${
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
  const matches = p.voice?.matches_script === true;
  const stale = ready && !matches;
  const clock = dur
    ? `${Math.floor(dur / 60)}:${String(Math.floor(dur % 60)).padStart(2, "0")}`
    : "";
  ws.innerHTML = `
    <div class="panel workspace">
      <h2 style="margin-top:0">Voz</h2>
      <p class="lead">${
        stale
          ? "Esta narración <strong>no es del guion actual</strong> (toma vieja o el texto cambió). Regenerala o el video va a decir otra cosa que los subtítulos."
          : ready
            ? `Narración lista${clock ? ` · ${clock}` : ""} · x1.20 · atada al guion aprobado.`
            : "Generá la narración acá (OpenAI / ElevenLabs). Sale un poco más rápida (x1.20). Tiene que leer el guion tal cual."
      }</p>
      ${ready ? `<audio controls src="/api/projects/${encodeURIComponent(p.id)}/audio?t=${Date.now()}" style="width:min(100%,640px);margin:0.4rem 0 1rem;display:block"></audio>` : ""}
      <div class="actions">
        <button class="btn btn-accent" id="gen-voice">${stale ? "Regenerar voz (obligatorio)" : ready ? "Volver a generar voz" : "Generar voz"}</button>
        <button class="btn btn-primary" id="to-music" ${stale || !ready ? "disabled" : ""}>Seguir a la música</button>
      </div>
    </div>`;
  $("#gen-voice").onclick = async () => {
    try {
      const data = await withBusy("Generando narración del guion…", () =>
        api(`/api/projects/${encodeURIComponent(p.id)}/voice`, { method: "POST", timeoutMs: 600000 })
      );
      state.project = data.project;
      toast("Voz lista — coincide con el guion");
      renderProject();
    } catch (e) {
      toast(e.message);
    }
  };
  $("#to-music").onclick = async () => {
    if (stale || !ready) {
      toast("Regenerá la voz primero — no coincide con el guion");
      return;
    }
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
        <button class="btn btn-primary" id="to-preview">Seguir a la prueba</button>
      </div>
    </div>`;
  $("#to-preview").onclick = async () => {
    const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
      method: "PATCH",
      body: JSON.stringify({ step: "preview" }),
    });
    state.project = data.project;
    renderProject();
  };
}

function renderStatusView(st) {
  const state = st.state || (st.ready ? "done" : "idle");
  const label = st.label || { idle: "No iniciado", running: "En curso", done: "Terminado", error: "Error" }[state] || state;
  const cls = state === "done" ? "ok" : state === "error" ? "bad" : state === "running" ? "warn" : "";
  const msg =
    st.message ||
    {
      idle: "Todavía no se armó el video.",
      running: "Armando el video… podés salir: al volver sigue desde la última foto.",
      done: "Terminado. Ya lo podés descargar.",
      error: "Falló el render.",
    }[state] ||
    "";
  const done = Number(st.kb_done || 0);
  const total = Number(st.kb_total || 0);
  let pct = Number(st.percent || 0);
  if ((!pct || pct < 1) && total > 0) pct = Math.round((100 * done) / total);
  pct = Math.max(0, Math.min(100, pct || 0));
  const elapsed = Number(st.elapsed_sec || 0);
  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");
  const detailBits = [];
  if (state === "running" && total > 0) detailBits.push(`Foto ${done} / ${total}`);
  if (state === "running" && elapsed > 0) detailBits.push(`Lleva ${mm}:${ss}`);
  if (state === "running" && st.stage) {
    const stageMap = {
      plan: "Planificando",
      captions_prep: "Subtítulos",
      encode: "Clips + zoom",
      captions_burn: "Quemando subtítulos",
      preview_encode: "Prueba · clips",
      preview_burn: "Prueba · subtítulos",
      preview_captions: "Prueba · subtítulos",
    };
    detailBits.push(stageMap[st.stage] || st.stage);
  }
  const bar =
    state === "running"
      ? `<div style="margin-top:0.75rem">
          <div style="display:flex;justify-content:space-between;gap:0.75rem;font-size:0.82rem;color:var(--muted);margin-bottom:0.35rem">
            <span>${esc(detailBits.join(" · ") || "Trabajando…")}</span>
            <strong style="color:var(--ink)">${pct}%</strong>
          </div>
          <div style="height:10px;border-radius:999px;background:rgba(15,23,32,0.08);overflow:hidden">
            <div style="height:100%;width:${pct}%;background:linear-gradient(90deg,#0f766e,#14b8a6);transition:width 400ms ease"></div>
          </div>
        </div>`
      : "";
  return `
    <div style="display:flex;align-items:flex-start;gap:0.85rem;margin:1rem 0 1.2rem;padding:1rem 1.15rem;border-radius:16px;border:1px solid var(--line,#d8dee6);background:var(--soft,#f4f6f8)">
      <span class="pill ${cls}">${esc(label)}</span>
      <div style="flex:1;min-width:0">
        <strong>${esc(label)}</strong>
        <p class="lead" style="margin:0.25rem 0 0">${esc(msg)}</p>
        ${bar}
      </div>
    </div>`;
}

function grabEditFromDom() {
  const sec = document.getElementById("edit-sec");
  if (!sec) return null;
  return {
    seconds_per_image: Number(sec.value),
    motion: document.getElementById("edit-motion")?.value || "mix",
    transition: document.getElementById("edit-trans")?.value || "fade",
    music_volume: Number(document.getElementById("edit-vol")?.value || 0.08),
    look: document.getElementById("edit-look")?.value || "soft",
  };
}

function stopVideoPolls() {
  if (paintRender._poll) {
    clearTimeout(paintRender._poll);
    paintRender._poll = null;
  }
  if (paintPreview._poll) {
    clearTimeout(paintPreview._poll);
    paintPreview._poll = null;
  }
  if (paintRender._kickAgain) {
    clearTimeout(paintRender._kickAgain);
    paintRender._kickAgain = null;
  }
}

function defaultEdit(p, st) {
  const fromDom = grabEditFromDom();
  if (fromDom) paintRender._edit = fromDom;
  const edit =
    paintRender._edit ||
    (st?.edit && Object.keys(st.edit).length ? st.edit : null) ||
    (p.render && p.render.edit) || {
      seconds_per_image: 6,
      motion: "mix",
      transition: "fade",
      music_volume: 0.08,
      look: "soft",
    };
  paintRender._edit = edit;
  return edit;
}

function paintPreview(ws, p) {
  const id = encodeURIComponent(p.id);
  stopVideoPolls();
  const voiceOk = p.voice?.matches_script === true;
  const opt = (v, cur) =>
    String(v) === String(cur) || (!Number.isNaN(Number(v)) && Number(v) === Number(cur)) ? "selected" : "";

  const paint = (st, { remountPlayer = false } = {}) => {
    const edit = defaultEdit(p, st);
    const hasPrev = !!(st.preview && st.preview_matches_voice !== false) || (!!paintPreview._hasPreview && voiceOk);
    if (st.preview && st.preview_matches_voice === false) paintPreview._hasPreview = false;
    if (st.preview && st.preview_matches_voice !== false) paintPreview._hasPreview = true;
    const waiting = !!paintPreview._previewWait;
    const existing = document.getElementById("preview-player");
    const keepPlayer = hasPrev && existing && !remountPlayer && paintPreview._uiReady;

    if (keepPlayer) {
      const btn = document.getElementById("try-edit");
      if (btn) {
        btn.disabled = waiting || !voiceOk;
        btn.textContent = waiting ? "Armando prueba real…" : "Probar 20 segundos";
      }
      return;
    }

    const bust = remountPlayer || !paintPreview._srcBust ? Date.now() : paintPreview._srcBust;
    if (hasPrev) paintPreview._srcBust = bust;

    ws.innerHTML = `
    <section class="ff-block ff-block-test ff-screen-solo">
      <div class="ff-block-head">
        <span class="ff-block-tag">Prueba</span>
        <h2>Prueba de edición · 20 segundos</h2>
      </div>
      ${
        voiceOk
          ? `<p class="lead">
        Pantalla solo de la prueba. Acá validás edición y subtítulos quemados antes del render largo.
        El episodio completo está en el paso <strong>9 Video</strong>.
      </p>`
          : `<p class="lead" style="color:#9a3412">
        La voz <strong>no coincide con el guion</strong> (toma vieja). Andá a <strong>6 Voz → Regenerar voz</strong>
        antes de probar: si no, el audio va a decir otra cosa que el texto.
      </p>
      <p class="lead" style="font-size:0.9rem;color:#9a3412">
        Recargar la página <strong>no regenera el guion</strong>. Si escuchás otra cosa, regenerá la voz
        con el guion aprobado y volvé a armar la prueba.
      </p>`
      }
      <div class="edit-picks">
        <label class="field">Segundos por foto
          <select id="edit-sec">
            <option value="4" ${opt(4, edit.seconds_per_image)}>4s</option>
            <option value="5" ${opt(5, edit.seconds_per_image)}>5s</option>
            <option value="6" ${opt(6, edit.seconds_per_image)}>6s</option>
            <option value="7" ${opt(7, edit.seconds_per_image)}>7s (máximo)</option>
          </select>
        </label>
        <label class="field">Movimiento
          <select id="edit-motion">
            <option value="mix" ${opt("mix", edit.motion)}>Mezcla (recomendado)</option>
            <option value="push" ${opt("push", edit.motion)}>Zoom in lento</option>
            <option value="pull" ${opt("pull", edit.motion)}>Zoom out lento</option>
            <option value="pan" ${opt("pan", edit.motion)}>Paneo</option>
          </select>
        </label>
        <label class="field">Transición
          <select id="edit-trans">
            <option value="fade" ${opt("fade", edit.transition)}>Fundido</option>
            <option value="cut" ${opt("cut", edit.transition)}>Corte seco</option>
          </select>
        </label>
        <label class="field">Música
          <select id="edit-vol">
            <option value="0.05" ${opt(0.05, edit.music_volume)}>Muy baja</option>
            <option value="0.08" ${opt(0.08, edit.music_volume)}>Baja (doc)</option>
            <option value="0.12" ${opt(0.12, edit.music_volume)}>Un poco más</option>
          </select>
        </label>
        <label class="field">Bordes
          <select id="edit-look">
            <option value="none" ${opt("none", edit.look)}>Sin viñeta</option>
            <option value="soft" ${opt("soft", edit.look || "soft")}>Oscurecer bordes</option>
            <option value="film" ${opt("film", edit.look)}>Cine (más marcado)</option>
          </select>
        </label>
      </div>
      <div class="actions" style="margin-top:0.9rem">
        <button class="btn btn-soft" id="try-edit" ${waiting || !voiceOk ? "disabled" : ""}>${
          !voiceOk ? "Regenerá la voz primero" : waiting ? "Armando prueba real…" : "Probar 20 segundos"
        }</button>
        <button class="btn btn-primary" id="to-full" ${voiceOk ? "" : "disabled"}>Ir al episodio completo</button>
        <button class="btn btn-ghost" id="home">Volver al inicio</button>
      </div>
      ${
        hasPrev
          ? `
        <div class="ff-player-wrap">
          <p class="ff-player-label">Player de la prueba (letras blancas abajo)</p>
          <video id="preview-player" controls playsinline src="/api/projects/${id}/video/preview?t=${bust}" class="ff-player"></video>
        </div>`
          : `<p class="lead" style="margin-top:0.9rem;font-size:0.92rem">Todavía no hay prueba. Tocá el botón de arriba.</p>`
      }
    </section>`;
    paintPreview._uiReady = true;

    $("#try-edit").onclick = async () => {
      if (!voiceOk) {
        toast("Regenerá la voz — no coincide con el guion");
        return;
      }
      const body = grabEditFromDom() || paintRender._edit;
      paintRender._edit = body;
      try {
        await api(`/api/projects/${id}/render/edit`, {
          method: "PUT",
          body: JSON.stringify(body),
        });
      } catch {}
      paintPreview._previewWait = true;
      paint(st);
      toast("Armando prueba real (mismo motor + subtítulos)…");
      let previewDone = false;
      const finishPreview = (nxt) => {
        if (previewDone) return;
        previewDone = true;
        paintPreview._previewWait = false;
        paintPreview._hasPreview = true;
        if (nxt?.project) state.project = nxt.project;
        toast("Prueba lista");
        paint({ ...(nxt || {}), preview: true, preview_matches_voice: true }, { remountPlayer: true });
      };
      api(`/api/projects/${id}/render/preview`, { method: "POST", timeoutMs: 280000 })
        .then((res) => {
          if (res?.ok || res?.preview) {
            finishPreview(res);
            return;
          }
        })
        .catch((e) => {
          if (previewDone) return;
          paintPreview._previewWait = false;
          toast(String(e.message || e || "Falló la prueba"));
          paint(st, { remountPlayer: false });
        });
      const t0 = Date.now();
      const tickPrev = async () => {
        if (previewDone || state.project?.ui_step !== "preview") return;
        try {
          const nxt = await api(`/api/projects/${id}/video/status`);
          if (nxt.preview) {
            finishPreview(nxt);
            return;
          }
          if (nxt.preview_busy) {
            const host = document.getElementById("try-edit");
            if (host) host.textContent = "Armando prueba…";
            const lead = document.querySelector(".ff-block-test .lead");
            if (lead && nxt.message) lead.textContent = String(nxt.message);
          }
          if (nxt.error && nxt.state === "error") {
            paintPreview._previewWait = false;
            toast(String(nxt.error || nxt.message || "Falló la prueba"));
            paint(nxt);
            return;
          }
        } catch {}
        if (Date.now() - t0 > 240000) {
          if (previewDone) return;
          paintPreview._previewWait = false;
          toast("La prueba no terminó a tiempo. Probá de nuevo.");
          paint(st);
          return;
        }
        paintPreview._poll = setTimeout(tickPrev, 2000);
      };
      paintPreview._poll = setTimeout(tickPrev, 1500);
    };

    $("#to-full").onclick = async () => {
      if (!voiceOk) {
        toast("Regenerá la voz primero");
        return;
      }
      stopVideoPolls();
      const body = grabEditFromDom() || paintRender._edit;
      if (body) {
        paintRender._edit = body;
        api(`/api/projects/${id}/render/edit`, {
          method: "PUT",
          body: JSON.stringify(body),
        }).catch(() => {});
      }
      const data = await api(`/api/projects/${id}/step`, {
        method: "PATCH",
        body: JSON.stringify({ step: "render" }),
      });
      state.project = data.project;
      renderProject();
    };
    $("#home").onclick = () => {
      stopVideoPolls();
      location.hash = "";
      go("home");
    };
  };

  paintPreview._uiReady = false;
  api(`/api/projects/${id}/video/status`)
    .then((st) => {
      if (state.project?.ui_step !== "preview") return;
      if (st.preview) paintPreview._hasPreview = true;
      paint(st, { remountPlayer: !!st.preview });
    })
    .catch(() => {
      if (state.project?.ui_step !== "preview") return;
      paint({ preview: !!paintPreview._hasPreview }, { remountPlayer: !!paintPreview._hasPreview });
    });
}

function paintRender(ws, p) {
  const id = encodeURIComponent(p.id);
  stopVideoPolls();
  paintRender._uiReady = false;

  const bindActions = (st, kind, captions) => {
    const running = kind === "running";
    const done = !running && (kind === "done" || !!st.ready);
    $("#to-preview").onclick = async () => {
      stopVideoPolls();
      const data = await api(`/api/projects/${id}/step`, {
        method: "PATCH",
        body: JSON.stringify({ step: "preview" }),
      });
      state.project = data.project;
      renderProject();
    };
    $("#render").onclick = async () => {
      const body = paintRender._edit || defaultEdit(p, st);
      paintRender._edit = body;
      api(`/api/projects/${id}/render/edit`, {
        method: "PUT",
        body: JSON.stringify(body),
      }).catch(() => {});
      paint(
        { state: "running", label: "En curso", message: "Arrancó. El estado se actualiza solo.", ready: false, captions },
        { force: true }
      );
      const kickRender = (resume = false) =>
        api(`/api/projects/${id}/render${resume ? "?resume=1" : ""}`, { method: "POST", timeoutMs: 280000 })
          .then((r) => {
            if (r && r.continue) {
              paintRender._kickAgain = setTimeout(() => kickRender(true), 800);
            }
          })
          .catch(() => {});
      if (paintRender._kickAgain) clearTimeout(paintRender._kickAgain);
      kickRender(false);
      startPoll();
    };
    const stopBtn = $("#cancel-render");
    if (stopBtn) {
      stopBtn.onclick = async () => {
        try {
          await api(`/api/projects/${id}/render/cancel`, { method: "POST" });
        } catch (e) {
          toast(e.message);
          return;
        }
        stopVideoPolls();
        toast("Frenado");
        paint({ state: "idle", label: "Frenado", message: "Frenaste el render.", ready: false, captions: false }, { force: true });
      };
    }
    $("#home").onclick = () => {
      stopVideoPolls();
      location.hash = "";
      go("home");
    };
    const dl = $("#download-final");
    if (dl) {
      dl.onclick = (ev) => {
        ev.preventDefault();
        startEpisodeDownload(p.id, `${p.id}.mp4`);
      };
    }
  };

  const paint = (st, { force = false } = {}) => {
    defaultEdit(p, st);
    const kind = st.state || (st.ready ? "done" : "idle");
    const prevKind = paintRender._kind;
    paintRender._kind = kind;
    const running = kind === "running";
    const done = !running && (kind === "done" || !!st.ready);
    const captions = !!st.captions;

    // Durante el render: solo actualizar barra/estado — nunca tocar players ni remount.
    if (!force && paintRender._uiReady && running && prevKind === "running") {
      const host = document.getElementById("render-status-host");
      if (host) host.innerHTML = renderStatusView({ ...st, state: kind });
      const btn = document.getElementById("render");
      if (btn) {
        btn.disabled = true;
        btn.textContent = "Armando…";
      }
      return;
    }

    const needPlayerRemount = force || !paintRender._fullSrcBust || (done && prevKind === "running");
    const bust = needPlayerRemount
      ? encodeURIComponent(String(st.updated_at || st.finished_at || p.render?.finished_at || p.render?.updated_at || Date.now()))
      : paintRender._fullSrcBust;
    if (done) paintRender._fullSrcBust = bust;

    ws.innerHTML = `
    <section class="ff-block ff-block-full ff-screen-solo">
      <div class="ff-block-head">
        <span class="ff-block-tag ff-block-tag-dark">Episodio</span>
        <h2>Video completo · último paso</h2>
      </div>
      <p class="lead">
        Acá se arma el episodio largo: edición + <strong>subtítulos quemados</strong>.
        La prueba de 20s está en el paso <strong>8 Prueba</strong>. Cuando termine, descargá el MP4.
      </p>
      <div id="render-status-host">${renderStatusView({ ...st, state: kind })}</div>
      ${
        done
          ? `
        <div class="ff-player-wrap">
          <p class="ff-player-label">Player del episodio${captions ? " (con subtítulos)" : ""}</p>
          <video id="full-player" controls playsinline src="/api/projects/${id}/video?t=${bust}" class="ff-player"></video>
        </div>`
          : ""
      }
      <div class="actions actions-center">
        <button class="btn btn-accent" id="render" ${running ? "disabled" : ""}>${done ? "Volver a renderizar" : running ? "Armando…" : "Renderizar episodio"}</button>
        ${running ? `<button class="btn btn-danger" id="cancel-render">Frenar</button>` : ""}
        ${done ? downloadVideoButton(p.id, captions ? "Descargar video (con subtítulos)" : "Descargar video") : ""}
        ${done ? `<button class="btn btn-primary" id="to-publish">Seguir a YouTube</button>` : ""}
        <button class="btn btn-soft" id="to-preview">Ver prueba 20s</button>
        <button class="btn btn-ghost" id="home">Volver al inicio</button>
      </div>
    </section>`;
    paintRender._uiReady = true;
    bindActions(st, kind, captions);
    wireDownloads(ws);
    $("#to-publish")?.addEventListener("click", async () => {
      const data = await api(`/api/projects/${encodeURIComponent(p.id)}/step`, {
        method: "PATCH",
        body: JSON.stringify({ step: "publish" }),
      });
      state.project = data.project;
      renderProject();
    });
  };

  const startPoll = () => {
    if (paintRender._poll) clearTimeout(paintRender._poll);
    paintRender._lastUpdate = paintRender._lastUpdate || Date.now();
    paintRender._lastPercent = paintRender._lastPercent ?? null;
    paintRender._lastKbDone = paintRender._lastKbDone ?? null;
    paintRender._noClipResumes = paintRender._noClipResumes || 0;
    const tick = async () => {
      if (state.project?.ui_step !== "render") return;
      try {
        const prev = paintRender._kind;
        const next = await api(`/api/projects/${id}/video/status`);
        paint(next);

        const now = Date.now();
        const stuckMs = now - (paintRender._lastUpdate || now);
        const stuckMin = stuckMs / 60000;
        const pct = next.percent || 0;
        const kbDone = Number(next.kb_done || 0);
        const changed = pct !== paintRender._lastPercent || kbDone !== paintRender._lastKbDone;
        if (changed) {
          paintRender._lastUpdate = now;
          paintRender._lastPercent = pct;
          if (kbDone !== paintRender._lastKbDone) {
            paintRender._lastKbDone = kbDone;
            paintRender._noClipResumes = 0;
          }
        }
        // Stop infinite resume when encode never advances clips (server bug / DB lock).
        const stalledClips =
          (next.stage === "encode" || next.need_continue) &&
          kbDone <= 1 &&
          paintRender._noClipResumes >= 4;
        if (stalledClips) {
          toast("El render no avanza en el servidor. Frenalo y regenerá en local, o reintentá más tarde.");
          paintRender._poll = null;
          return;
        }
        const heavy = next.stage === "encode" || next.stage === "captions_prep" || next.stage === "captions_burn";
        const stuckLimit = heavy ? 4.2 : 1.5;
        if (next.state === "running" && stuckMin > stuckLimit && !paintRender._resuming) {
          console.warn(`Render stuck at ${pct}% for ${stuckMin.toFixed(1)} min — forcing resume`);
          paintRender._resuming = true;
          paintRender._lastUpdate = now;
          if (kbDone <= 1 && (next.stage === "encode" || next.stage === "captions_prep")) {
            paintRender._noClipResumes = (paintRender._noClipResumes || 0) + 1;
          }
          toast("Detecté que se trabó — reintentando...");
          api(`/api/projects/${id}/render?resume=1`, { method: "POST", timeoutMs: 280000 })
            .finally(() => {
              paintRender._resuming = false;
            });
        }

        if (next.need_continue && !paintRender._resuming) {
          paintRender._resuming = true;
          if (kbDone <= 1) paintRender._noClipResumes = (paintRender._noClipResumes || 0) + 1;
          toast("Sigue en segundo plano…");
          api(`/api/projects/${id}/render?resume=1`, { method: "POST", timeoutMs: 280000 })
            .then((r) => {
              paintRender._resuming = false;
              if (r && r.continue && state.project?.ui_step === "render" && (paintRender._noClipResumes || 0) < 4) {
                paintRender._kickAgain = setTimeout(() => {
                  api(`/api/projects/${id}/render?resume=1`, { method: "POST", timeoutMs: 280000 }).catch(() => {});
                }, 800);
              }
            })
            .catch(() => {
              paintRender._resuming = false;
            });
        }
        if (next.state === "running" || next.need_continue) {
          paintRender._poll = setTimeout(tick, 3000);
        } else if (prev === "running" && (next.state === "done" || next.ready)) {
          toast("Video listo");
          if (state.project?.checkpoints) state.project.checkpoints.render_ready = true;
        } else if (prev === "running" && next.state === "error") {
          const msg = String(next.message || next.error || "");
          if (/Se cort|Reanudando|cort/i.test(msg)) {
            paintRender._poll = setTimeout(tick, 2000);
            if (!paintRender._resuming) {
              paintRender._resuming = true;
              api(`/api/projects/${id}/render?resume=1`, { method: "POST", timeoutMs: 280000 }).finally(() => {
                paintRender._resuming = false;
              });
            }
            return;
          }
          toast(msg || "Falló el render");
        }
      } catch {
        paintRender._poll = setTimeout(tick, 4000);
      }
    };
    paintRender._poll = setTimeout(tick, 1500);
  };

  const rec = p.render || {};
  const previewStuck =
    rec.stage === "preview_done" || String(rec.stage || "").startsWith("preview_");
  const firstState =
    previewStuck && rec.state === "running"
      ? "idle"
      : rec.state || (p.checkpoints?.render_ready ? "done" : "idle");
  const first = {
    state: firstState,
    label:
      firstState === "done" || p.checkpoints?.render_ready
        ? "Terminado"
        : firstState === "running"
          ? "En curso"
          : firstState === "error"
            ? "Error"
            : "No iniciado",
    message: previewStuck
      ? rec.message || "Prueba lista. Tocá Renderizar episodio para el video completo."
      : rec.message || "",
    ready: !!p.checkpoints?.render_ready,
    captions: !!p.checkpoints?.captions_ready,
    error: rec.error || "",
    stage: rec.stage || "",
    percent: previewStuck ? 0 : rec.percent,
  };
  paint(first, { force: true });
  api(`/api/projects/${id}/video/status`)
    .then((st) => {
      if (state.project?.ui_step !== "render") return;
      paint(st, { force: true });
      if (st.state === "running") startPoll();
    })
    .catch(() => {});
}

function paintSubs(ws, p) {
  const cap = p.captions || {};
  const burned = !!(cap.burned || p.checkpoints?.captions_ready);
  const id = encodeURIComponent(p.id);
  const vidBust = encodeURIComponent(String(p.render?.finished_at || p.render?.updated_at || "1"));
  const vid = `/api/projects/${id}/video?t=${vidBust}`;
  ws.innerHTML = `
    <div class="panel workspace">
      <h2 style="margin-top:0">Subtítulos</h2>
      <p class="lead">Inglés, abajo. En este player los ves ya. En el archivo de descarga van quemados cuando tocás Ponerlos en el video.</p>
      <div class="field">
        <label>Preview del texto (SRT)</label>
        <textarea id="srt-box" rows="12" style="font-family:ui-monospace,monospace;font-size:0.85rem" placeholder="Tocá Armar subtítulos…"></textarea>
      </div>
      <div class="actions" style="margin-bottom:1rem">
        <button class="btn btn-accent" id="gen-subs">Armar subtítulos</button>
        <button class="btn btn-ghost" id="save-subs">Guardar texto</button>
        <button class="btn btn-primary" id="burn-subs">Ponerlos en el video</button>
      </div>
      <div id="subs-wrap" style="position:relative;width:min(100%,720px);margin:0.5rem 0 1rem">
        <video id="subs-player" controls playsinline style="width:100%;aspect-ratio:16/9;background:#111;border-radius:14px;display:block">
          <source src="${vid}" type="video/mp4"/>
        </video>
        <div id="subs-overlay" style="position:absolute;left:8%;right:8%;bottom:14%;text-align:center;color:#fff;font:700 1.05rem/1.35 Plus Jakarta Sans,system-ui,sans-serif;text-shadow:0 0 4px #000,0 2px 8px #000;pointer-events:none"></div>
      </div>
      ${burned ? `<p class="lead">Ya están quemados en el archivo que descargás.</p>` : `<p class="lead">En el player se ven. Para YouTube tocá Ponerlos en el video y después descargá.</p>`}
      <div class="actions">
        ${downloadVideoButton(p.id, "Descargar Full HD (con subtítulos)")}
        <button class="btn btn-primary" id="to-publish">Seguir a YouTube</button>
      </div>
    </div>`;
  wireDownloads(ws);
  const box = $("#srt-box");
  const player = $("#subs-player");
  const overlay = $("#subs-overlay");
  const cueList = [];
  const parseTs = (ts) => {
    const p = String(ts || "0").replace(",", ".").split(":");
    if (p.length !== 3) return 0;
    return Number(p[0]) * 3600 + Number(p[1]) * 60 + Number(p[2]);
  };
  const paintCue = () => {
    if (!player || !overlay) return;
    const t = player.currentTime || 0;
    const hit = cueList.find((c) => t >= c.start && t < c.end);
    overlay.textContent = hit ? hit.text : "";
  };
  api(`/api/projects/${encodeURIComponent(p.id)}/captions`)
    .then((data) => {
      if (box && data.srt) box.value = data.srt;
      (data.cues || []).forEach((c) => {
        cueList.push({
          start: parseTs(c.start),
          end: parseTs(c.end),
          text: String(c.text || "").replace(/\n/g, " "),
        });
      });
      paintCue();
    })
    .catch(() => {});
  if (player) {
    player.ontimeupdate = paintCue;
    player.onseeked = paintCue;
  }
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
  const isCheck = p.content_format === "check_als" || p.mode === "check_als";
  const alts = (y.alt_titles || []).join("\n");
  ws.innerHTML = `
    <div class="panel workspace">
      <h2 style="margin-top:0">YouTube</h2>
      <p class="lead">${
        isCheck
          ? "Título, descripción y prompt de miniatura (stickman) para subir el episodio. Copiá y pegá en YouTube / Flow."
          : "Título y miniatura pensados para que alguien pare el scroll. No un still más del video."
      }</p>
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
        <label>Texto overlay (2–4 palabras${isCheck ? ", español OK" : ""}, se lee en el celular)</label>
        <input id="yt-thumb-text" value="${esc(y.thumbnail_text || "")}" />
        <button class="btn btn-soft" id="copy-thumb-text" style="margin-top:0.45rem">Copiar overlay</button>
      </div>
      <div class="field">
        <label>Prompt de miniatura — ${isCheck ? "stickman + contraste (Google Flow)" : "cara grande + un objeto de la historia (Google Flow)"}</label>
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
  state.contentFormat =
    state.bootstrap?.formats?.active ||
    state.bootstrap?.channel?.content_format ||
    state.contentFormat ||
    "check_als";
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

// Pull-to-refresh: jalar hacia abajo para recargar
(function initPullToRefresh() {
  let startY = 0;
  let currentY = 0;
  let pulling = false;
  const threshold = 80;
  
  const indicator = document.createElement("div");
  indicator.className = "pull-refresh-indicator";
  indicator.innerHTML = '<div class="pull-refresh-spinner"></div><span>Jalá para recargar</span>';
  document.body.appendChild(indicator);
  
  document.addEventListener("touchstart", (e) => {
    if (window.scrollY === 0 && e.touches.length === 1) {
      startY = e.touches[0].pageY;
      pulling = true;
    }
  }, { passive: true });
  
  document.addEventListener("touchmove", (e) => {
    if (!pulling || e.touches.length !== 1) return;
    currentY = e.touches[0].pageY;
    const pullDistance = currentY - startY;
    
    if (pullDistance > 20 && window.scrollY === 0) {
      indicator.classList.add("visible");
      const text = indicator.querySelector("span");
      if (pullDistance > threshold) {
        text.textContent = "Soltá para recargar";
        indicator.classList.add("releasing");
      } else {
        text.textContent = "Jalá para recargar";
        indicator.classList.remove("releasing");
      }
    }
  }, { passive: true });
  
  document.addEventListener("touchend", () => {
    if (!pulling) return;
    
    const pullDistance = currentY - startY;
    
    if (pullDistance > threshold && window.scrollY === 0) {
      const text = indicator.querySelector("span");
      text.textContent = "Recargando...";
      setTimeout(() => location.reload(), 200);
    } else {
      indicator.classList.remove("visible", "releasing");
    }
    
    pulling = false;
    startY = 0;
    currentY = 0;
  }, { passive: true });
})();

boot();

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") DL.resumeAll();
});
window.addEventListener("pageshow", () => DL.resumeAll());
