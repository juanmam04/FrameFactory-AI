const $ = (id) => document.getElementById(id);
const status = $("status");
const out = $("out");

$("go").onclick = async () => {
  const script = $("script").value.trim();
  if (script.length < 40) {
    status.className = "status err";
    status.textContent = "Pegá un guion un poco más largo.";
    return;
  }
  $("go").disabled = true;
  status.className = "status";
  status.textContent = "Armando pack (prompts + subtítulos)…";
  out.classList.remove("on");
  ["dl-zip", "dl-srt", "dl-prompts"].forEach((id) => {
    $(id).hidden = true;
  });
  try {
    const stills = $("stills").value;
    const duration = $("duration").value.trim();
    const res = await fetch("/api/shorts-lab/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(300000),
      body: JSON.stringify({
        script,
        language: $("lang").value,
        still_count: stills === "auto" ? null : Number(stills),
        duration_sec: duration ? Number(duration) : null,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "No se pudo generar el pack.");
    render(data);
    status.className = "status ok";
    status.textContent =
      `Listo · ${data.still_count} prompts · ${data.captions?.length || 0} cues · ~${data.duration_sec}s` +
      (data.warning ? " (fallback)" : "");
  } catch (e) {
    status.className = "status err";
    status.textContent = e.name === "TimeoutError" || e.name === "AbortError" ? "Timeout — reintentá." : e.message;
  } finally {
    $("go").disabled = false;
  }
};

function render(data) {
  out.classList.add("on");
  $("hooks").innerHTML = (data.hooks || []).map((h) => `<span class="chip">${esc(h)}</span>`).join("");
  $("cta").textContent = data.cta || "";
  $("tags").innerHTML = (data.hashtags || [])
    .map((h) => `<span class="chip">#${esc(h)}</span>`)
    .join("");
  $("cues").textContent = (data.captions || [])
    .map((c) => `[${c.start}–${c.end}] ${c.text}`)
    .join("\n");
  $("prompts").innerHTML = (data.flow_prompts || [])
    .map(
      (p) => `<div class="prompt-card">
        <strong>Still ${String(p.n).padStart(3, "0")} · ${esc(p.beat || "")}</strong>
        <div>${esc(p.prompt || "")}</div>
        <button type="button" class="ghost" data-copy="${escAttr(p.prompt || "")}">Copiar prompt</button>
      </div>`
    )
    .join("");
  $("prompts").querySelectorAll("[data-copy]").forEach((btn) => {
    btn.onclick = async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy || "");
        btn.textContent = "✓ Copiado";
      } catch {
        btn.textContent = "No se pudo copiar";
      }
    };
  });
  const files = data.files || {};
  if (files.zip) {
    $("dl-zip").href = files.zip;
    $("dl-zip").hidden = false;
  }
  if (files.srt) {
    $("dl-srt").href = files.srt;
    $("dl-srt").hidden = false;
  }
  if (files.prompts) {
    $("dl-prompts").href = files.prompts;
    $("dl-prompts").hidden = false;
  }
}

function esc(s) {
  return String(s || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
function escAttr(s) {
  return String(s || "")
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;");
}
