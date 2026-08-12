"""FrameFactory Streamlit theme — cinematic, quiet, intentional."""
from __future__ import annotations

import streamlit as st

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,650&family=Sora:wght@400;500;600&display=swap');

:root {
  --ff-ink: #0b0a09;
  --ff-ink-2: #141210;
  --ff-panel: #171512;
  --ff-line: rgba(235, 226, 214, 0.10);
  --ff-line-strong: rgba(235, 226, 214, 0.18);
  --ff-bone: #ebe2d6;
  --ff-bone-dim: #a89f92;
  --ff-accent: #d2b48c;
  --ff-accent-deep: #b8956a;
  --ff-good: #7dba8a;
  --ff-bad: #d9897a;
  --ff-warn: #d4b56a;
  --ff-radius: 10px;
  --ff-ease: cubic-bezier(0.22, 1, 0.36, 1);
}

html, body, [class*="css"], .stApp, .stMarkdown, .stText, .stCaption {
  font-family: "Sora", system-ui, sans-serif !important;
}

.stApp {
  background:
    radial-gradient(900px 480px at 12% -8%, rgba(210, 180, 140, 0.07), transparent 55%),
    radial-gradient(700px 420px at 92% 8%, rgba(90, 70, 50, 0.18), transparent 50%),
    linear-gradient(180deg, #100e0c 0%, var(--ff-ink) 42%, #090807 100%);
  color: var(--ff-bone);
}

/* Kill Streamlit chrome noise */
#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
div[data-testid="stToolbar"] { display: none; }
div[data-testid="stDecoration"] { display: none; }
div[data-testid="stStatusWidget"] { display: none; }

.main .block-container {
  max-width: 1040px;
  padding: 1.75rem 1.5rem 4rem;
  animation: ff-in 420ms var(--ff-ease) both;
}

@keyframes ff-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Sidebar */
div[data-testid="stSidebar"] {
  background: rgba(12, 11, 10, 0.96) !important;
  border-right: 1px solid var(--ff-line) !important;
}
div[data-testid="stSidebar"] * { color: var(--ff-bone); }
div[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: 1px solid transparent !important;
  color: var(--ff-bone-dim) !important;
  justify-content: flex-start !important;
  border-radius: 8px !important;
  font-weight: 500 !important;
  letter-spacing: 0.01em;
  transition: border-color 160ms var(--ff-ease), color 160ms var(--ff-ease), background 160ms var(--ff-ease);
}
div[data-testid="stSidebar"] .stButton > button:hover {
  border-color: var(--ff-line-strong) !important;
  color: var(--ff-bone) !important;
  background: rgba(235, 226, 214, 0.04) !important;
}

/* Typography helpers */
.saas-tag, .ff-kicker {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--ff-bone-dim);
  margin: 0 0 0.55rem;
}
.saas-brand {
  font-family: "Fraunces", Georgia, serif !important;
  font-size: 1.2rem;
  font-weight: 650;
  color: var(--ff-bone);
  letter-spacing: -0.02em;
}
.saas-hero, .ff-title {
  font-family: "Fraunces", Georgia, serif !important;
  font-size: clamp(1.85rem, 3.2vw, 2.55rem);
  font-weight: 650;
  letter-spacing: -0.03em;
  line-height: 1.12;
  color: var(--ff-bone);
  margin: 0 0 0.45rem;
}
.saas-sub, .ff-sub {
  color: var(--ff-bone-dim);
  font-size: 0.95rem;
  line-height: 1.55;
  margin: 0 0 1.5rem;
  max-width: 42rem;
}

/* Buttons — calm, solid, no purple pills */
.stButton > button {
  border-radius: 9px !important;
  font-weight: 500 !important;
  letter-spacing: 0.01em;
  min-height: 2.55rem;
  transition: transform 140ms var(--ff-ease), background 160ms var(--ff-ease), border-color 160ms var(--ff-ease), opacity 160ms;
}
.stButton > button:hover { transform: translateY(-1px); }
.stButton > button:active { transform: translateY(0); }
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: var(--ff-bone) !important;
  color: #151210 !important;
  border: 1px solid var(--ff-bone) !important;
  box-shadow: none !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
  background: #f5efe6 !important;
  border-color: #f5efe6 !important;
}
.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"] {
  background: transparent !important;
  color: var(--ff-bone) !important;
  border: 1px solid var(--ff-line-strong) !important;
}

/* Inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input, div[data-baseweb="select"] > div {
  background: rgba(235, 226, 214, 0.035) !important;
  border: 1px solid var(--ff-line) !important;
  border-radius: 9px !important;
  color: var(--ff-bone) !important;
  transition: border-color 160ms var(--ff-ease), background 160ms var(--ff-ease);
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: rgba(210, 180, 140, 0.55) !important;
  box-shadow: 0 0 0 1px rgba(210, 180, 140, 0.25) !important;
}

/* Metrics / cards */
div[data-testid="stMetric"] {
  background: rgba(235, 226, 214, 0.03);
  border: 1px solid var(--ff-line);
  border-radius: var(--ff-radius);
  padding: 0.85rem 1rem;
}
div[data-testid="stMetric"] label { color: var(--ff-bone-dim) !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-family: "Fraunces", Georgia, serif !important;
  color: var(--ff-bone) !important;
}

/* Soften Streamlit alert boxes */
div[data-testid="stAlert"] {
  border-radius: 10px !important;
  border: 1px solid var(--ff-line) !important;
  background: rgba(235, 226, 214, 0.04) !important;
}
div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
  color: var(--ff-bone) !important;
}

/* Radio as step track */
div[role="radiogroup"] {
  gap: 0.35rem !important;
  flex-wrap: wrap !important;
}
div[role="radiogroup"] label {
  background: rgba(235, 226, 214, 0.03) !important;
  border: 1px solid var(--ff-line) !important;
  border-radius: 999px !important;
  padding: 0.35rem 0.85rem !important;
  transition: border-color 160ms var(--ff-ease), background 160ms var(--ff-ease);
}
div[role="radiogroup"] label:hover {
  border-color: var(--ff-line-strong) !important;
}
div[role="radiogroup"] label[data-checked="true"],
div[role="radiogroup"] label:has(input:checked) {
  background: rgba(210, 180, 140, 0.14) !important;
  border-color: rgba(210, 180, 140, 0.45) !important;
}

/* Spinner */
div[data-testid="stSpinner"] > div {
  color: var(--ff-accent) !important;
}
.stSpinner > div > div {
  border-top-color: var(--ff-accent) !important;
}

/* Dividers */
hr { border-color: var(--ff-line) !important; opacity: 1 !important; }

/* Code blocks quieter */
.stCodeBlock, pre {
  background: #12100e !important;
  border: 1px solid var(--ff-line) !important;
  border-radius: 10px !important;
}

/* Documentary components */
.ff-stepper {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
  margin: 0.75rem 0 1.1rem;
  padding: 0;
  list-style: none;
}
.ff-step {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.38rem 0.75rem;
  border-radius: 999px;
  border: 1px solid var(--ff-line);
  color: var(--ff-bone-dim);
  font-size: 0.78rem;
  letter-spacing: 0.02em;
  background: rgba(235, 226, 214, 0.02);
}
.ff-step.is-done {
  color: var(--ff-good);
  border-color: rgba(125, 186, 138, 0.28);
}
.ff-step.is-now {
  color: var(--ff-ink);
  background: var(--ff-bone);
  border-color: var(--ff-bone);
  font-weight: 600;
}
.ff-cred {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 0.75rem;
  align-items: center;
  justify-content: space-between;
  margin: 0 0 1.1rem;
  padding: 0.7rem 0.9rem;
  border: 1px solid var(--ff-line);
  border-radius: 10px;
  background: rgba(235, 226, 214, 0.03);
}
.ff-cred-pills { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.ff-pill {
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.28rem 0.55rem;
  border-radius: 999px;
  border: 1px solid var(--ff-line);
  color: var(--ff-bone-dim);
}
.ff-pill.ok { color: var(--ff-good); border-color: rgba(125, 186, 138, 0.35); }
.ff-pill.bad { color: var(--ff-bad); border-color: rgba(217, 137, 122, 0.4); }
.ff-pill.warn { color: var(--ff-warn); border-color: rgba(212, 181, 106, 0.35); }
.ff-cred-note {
  margin: 0.35rem 0 0;
  font-size: 0.8rem;
  color: var(--ff-bone-dim);
  line-height: 1.4;
}
.ff-episode {
  border: 1px solid var(--ff-line);
  border-radius: 12px;
  padding: 0.95rem 1.05rem;
  margin: 0 0 0.65rem;
  background: rgba(235, 226, 214, 0.025);
  transition: border-color 160ms var(--ff-ease), background 160ms var(--ff-ease);
}
.ff-episode:hover {
  border-color: var(--ff-line-strong);
  background: rgba(235, 226, 214, 0.045);
}
.ff-episode-title {
  font-family: "Fraunces", Georgia, serif !important;
  font-size: 1.05rem;
  margin: 0 0 0.2rem;
  color: var(--ff-bone);
}
.ff-episode-meta {
  margin: 0;
  color: var(--ff-bone-dim);
  font-size: 0.8rem;
}
.ff-idea {
  border-top: 1px solid var(--ff-line);
  padding: 1.15rem 0 0.35rem;
  margin-top: 0.85rem;
  animation: ff-in 480ms var(--ff-ease) both;
}
.ff-idea h3 {
  font-family: "Fraunces", Georgia, serif !important;
  font-size: 1.25rem;
  margin: 0 0 0.45rem;
  color: var(--ff-bone);
  font-weight: 650;
}
.ff-idea p { color: var(--ff-bone-dim); margin: 0 0 0.45rem; }
.ff-loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 0;
  color: var(--ff-bone-dim);
  font-size: 0.92rem;
}
.ff-loading-bar {
  width: 120px;
  height: 2px;
  border-radius: 999px;
  background: rgba(235, 226, 214, 0.08);
  overflow: hidden;
}
.ff-loading-bar > span {
  display: block;
  width: 40%;
  height: 100%;
  background: var(--ff-accent);
  animation: ff-load 1.1s var(--ff-ease) infinite;
}
@keyframes ff-load {
  0% { transform: translateX(-120%); }
  100% { transform: translateX(320%); }
}

/* Reduce boxed vertical wrappers looking like random cards */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
  background: transparent !important;
  border-color: var(--ff-line) !important;
  border-radius: 12px !important;
}
</style>
"""


def inject_theme() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", kicker: str = "") -> None:
    bits = []
    if kicker:
        bits.append(f'<p class="ff-kicker">{kicker}</p>')
    bits.append(f'<p class="ff-title">{title}</p>')
    if subtitle:
        bits.append(f'<p class="ff-sub">{subtitle}</p>')
    st.markdown("\n".join(bits), unsafe_allow_html=True)


def loading_hint(text: str = "Working…") -> None:
    st.markdown(
        f'<div class="ff-loading"><div class="ff-loading-bar"><span></span></div>{text}</div>',
        unsafe_allow_html=True,
    )
