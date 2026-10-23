const $ = (id) => document.getElementById(id);
const script = $("script");
const status = $("status");
const player = $("player");
const dl = $("dl");
const go = $("go");
const words = $("words");
const keyStatus = $("key-status");

function count() {
  const t = script.value.trim();
  const w = t ? t.split(/\s+/).filter(Boolean).length : 0;
  words.textContent = `${w} palabras · ${t.length} caracteres`;
}
script.addEventListener("input", count);
count();

async function pingKeys() {
  try {
    const r = await fetch("/api/voice-lab/status");
    const j = await r.json();
    if (j.elevenlabs_ok) {
      keyStatus.textContent = "ElevenLabs listo";
      keyStatus.style.color = "#2dd4bf";
    } else {
      keyStatus.textContent = j.detail || "Falta ELEVENLABS_API_KEY";
      keyStatus.style.color = "#fbbf24";
    }
    if (j.default_voice && !$("voice").value) {
      $("voice").placeholder = j.default_voice;
    }
  } catch {
    keyStatus.textContent = "No se pudo chequear la API";
  }
}
pingKeys();

go.onclick = async () => {
  const text = script.value.trim();
  if (text.length < 20) {
    status.className = "status err";
    status.textContent = "Pegá un guion un poco más largo.";
    return;
  }
  go.disabled = true;
  status.className = "status";
  status.textContent = "Generando con ElevenLabs (puede tardar)…";
  player.hidden = true;
  dl.hidden = true;
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 600000);
    const res = await fetch("/api/voice-lab/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: ctrl.signal,
      body: JSON.stringify({
        script: text,
        voice_id: $("voice").value.trim() || null,
        speed: Number($("speed").value) || 1.1,
        filename: $("name").value.trim() || "narracion",
      }),
    });
    clearTimeout(timer);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "No se pudo generar la voz.");
    const url = data.url + (data.url.includes("?") ? "&" : "?") + "t=" + Date.now();
    player.src = url;
    player.hidden = false;
    player.load();
    dl.href = url;
    dl.download = data.filename || "narracion.mp3";
    dl.hidden = false;
    status.className = "status ok";
    status.textContent = `Listo · ~${data.words || "?"} palabras · ${(data.bytes / 1024).toFixed(0)} KB`;
  } catch (e) {
    status.className = "status err";
    status.textContent = e.name === "AbortError" ? "Timeout: el texto es muy largo o la API tardó." : e.message;
  } finally {
    go.disabled = false;
  }
};
