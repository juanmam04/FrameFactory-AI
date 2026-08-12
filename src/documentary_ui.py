"""Streamlit UI: Documentary 100-days workflow + Flow Workspace."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.documentary.assemble_service import assemble_and_render, build_preview
from src.documentary.flow_pack import export_flow_pack, load_shot_list, update_shot_status
from src.documentary.import_images import import_images, replace_shot_image
from src.documentary.project import create_project, list_projects, load_project, project_dir, save_project
from src.documentary.script_service import approve_script, generate_documentary_script, save_edited_script
from src.documentary.voice_service import generate_project_voice


def page_documentary() -> None:
    st.markdown('<p class="saas-hero">Documentary</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="saas-sub">100 Days — English business documentaries · Google Flow for images · FrameFactory for everything else.</p>',
        unsafe_allow_html=True,
    )

    pending = st.session_state.pop("_doc_pending_project_id", None)
    if pending:
        st.session_state.doc_project_id = str(pending)
        st.session_state.doc_project_select = "— new —" if pending == "__new__" else str(pending)

    projects = list_projects()
    ids = [p["id"] for p in projects]
    options = ["— new —"] + ids
    cur = st.session_state.get("doc_project_id")
    if cur not in ids and cur != "__new__":
        if ids:
            st.session_state.doc_project_id = ids[0]
            cur = ids[0]
        else:
            st.session_state.doc_project_id = "__new__"
            cur = "__new__"

    want = "— new —" if cur == "__new__" else cur
    if st.session_state.get("doc_project_select") not in options:
        st.session_state.doc_project_select = want

    col_a, col_b = st.columns([2, 1])
    with col_a:
        sel = st.selectbox(
            "Project",
            options=options,
            key="doc_project_select",
        )
    with col_b:
        st.caption(f"{len(ids)} project(s)")

    if sel == "— new —":
        st.session_state.doc_project_id = "__new__"
        _create_form()
        return

    st.session_state.doc_project_id = sel
    project = load_project(sel)
    _status_panel(project)

    tabs = st.tabs(
        ["Overview", "Script", "Flow Workspace", "Images", "Voice & Render"]
    )
    with tabs[0]:
        _tab_overview(project)
    with tabs[1]:
        _tab_script(project)
    with tabs[2]:
        _tab_flow(project)
    with tabs[3]:
        _tab_images(project)
    with tabs[4]:
        _tab_render(project)


def _create_form() -> None:
    st.subheader("Create Documentary Project")
    topic = st.text_input("Topic", placeholder="The Rise and Fall of WeWork")
    title = st.text_input("Title (optional)", placeholder="Leave blank to use topic")
    words = st.slider("Target words", 1000, 2000, 1500, 50)
    notes = st.text_area("Research notes", height=120, placeholder="Verified facts only…")
    sources = st.text_area("Sources (one per line)", height=80)
    pid_opt = st.text_input("Project id (optional)", placeholder="001-wework or 100-days-test")
    if st.button("Create project", type="primary"):
        try:
            src_list = [s.strip() for s in (sources or "").splitlines() if s.strip()]
            data = create_project(
                topic,
                title=title or None,
                project_id=pid_opt.strip() or None,
                target_words=words,
                research_notes=notes,
                sources=src_list,
            )
            st.session_state.doc_project_id = data["id"]
            st.session_state._doc_pending_project_id = data["id"]
            st.success(f"Created `{data['id']}`")
            st.rerun()
        except Exception as e:
            st.error(str(e))


def _status_panel(project: dict) -> None:
    cps = project.get("checkpoints") or {}
    report = project.get("import_report") or {}
    ready = report.get("ready")
    expected = report.get("expected")
    voice = project.get("voice") or {}
    dur = voice.get("duration_sec")
    dur_s = f"{int(dur)//60:02d}:{int(dur)%60:02d}" if isinstance(dur, (int, float)) else "—"

    def mark(ok: bool, extra: str = "") -> str:
        return f"{'✓' if ok else '○'} {extra}".strip()

    st.markdown(
        f"**`{project['id']}`** · {project.get('topic','')[:80]}\n\n"
        f"| Step | Status |\n|---|---|\n"
        f"| Topic | {mark(bool(project.get('topic')))} |\n"
        f"| Research | {mark(bool(project.get('research_notes') or project.get('sources')))} |\n"
        f"| Script | {mark(cps.get('script_ready'), 'APPROVED' if project.get('script_approved') else 'draft')} |\n"
        f"| Flow Pack | {mark(cps.get('flow_pack_ready'), str((project.get('flow_pack') or {}).get('shot_count') or '') + ' shots')} |\n"
        f"| Images | {mark(cps.get('images_imported'), f'{ready}/{expected}' if expected else '')} |\n"
        f"| Voice | {mark(cps.get('voice_ready'), dur_s)} |\n"
        f"| Assembly | {mark(cps.get('assembly_ready'), 'READY' if cps.get('assembly_ready') else '')} |\n"
        f"| Render | {mark(cps.get('render_ready'), 'final.mp4' if cps.get('render_ready') else 'NOT STARTED')} |\n"
    )


def _tab_overview(project: dict) -> None:
    st.write(f"Workspace: `{project_dir(project['id'])}`")
    st.text_area("Topic", value=project.get("topic") or "", disabled=True)
    notes = st.text_area("Research notes", value=project.get("research_notes") or "", height=140)
    sources = st.text_area(
        "Sources (one per line)",
        value="\n".join(project.get("sources") or []),
        height=80,
    )
    if st.button("Save research"):
        project["research_notes"] = notes
        project["sources"] = [s.strip() for s in sources.splitlines() if s.strip()]
        save_project(project)
        st.success("Saved")
        st.rerun()


def _tab_script(project: dict) -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Generate script (LLM)", type="primary"):
            with st.spinner("Generating…"):
                try:
                    generate_documentary_script(project, use_llm=True)
                    st.success("Script generated — review before approve")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    with c2:
        if st.button("Generate mock script (offline)"):
            generate_documentary_script(project, use_llm=False)
            st.info("Mock script for pipeline testing only")
            st.rerun()
    with c3:
        if st.button("Approve script", disabled=not (project.get("script") or "").strip()):
            approve_script(project)
            st.success("APPROVED")
            st.rerun()

    script = st.text_area("Script (editable)", value=project.get("script") or "", height=360)
    if st.button("Save script edits"):
        save_edited_script(project, script)
        st.success("Saved (approval cleared)")
        st.rerun()
    st.caption(f"Fact status: **{project.get('fact_check_status')}** · Approved: **{project.get('script_approved')}**")


def _tab_flow(project: dict) -> None:
    if st.button("Generate / refresh Flow Pack", type="primary", disabled=not project.get("script_approved")):
        with st.spinner("Visual director + Flow Pack…"):
            try:
                export_flow_pack(project, use_llm=True, rebuild_visuals=True)
                st.success("Flow Pack ready")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    if st.button("Flow Pack offline (no LLM beats)"):
        try:
            export_flow_pack(project, use_llm=False, rebuild_visuals=True)
            st.success("Flow Pack (heuristic)")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    if not (project.get("checkpoints") or {}).get("flow_pack_ready"):
        st.info("Approve script, then generate Flow Pack.")
        return

    try:
        data = load_shot_list(project["id"])
    except Exception as e:
        st.error(str(e))
        return

    shots = data.get("shots") or []
    batches = data.get("batches") or []
    batch_size = int(data.get("batch_size") or project.get("batch_size") or 10)

    # Master references
    with st.expander("MASTER REFERENCES", expanded=True):
        bible = data.get("story_bible") or {}
        st.text_area("Global style", value=str(bible.get("global_style") or ""), height=80)
        for label, key in [
            ("Characters", "characters"),
            ("Locations", "locations"),
            ("Objects", "important_objects"),
        ]:
            ents = bible.get(key) or []
            if not ents:
                continue
            st.markdown(f"**{label}**")
            for ent in ents:
                st.code(
                    f"{ent.get('id')} — {ent.get('name')}\nGenerate reference image:\n{ent.get('visual_description')}",
                    language=None,
                )

    if not shots:
        st.warning("No shots")
        return

    idx = int(st.session_state.get("doc_flow_idx", project.get("flow_shot_index") or 0))
    idx = max(0, min(len(shots) - 1, idx))
    batch_i = idx // batch_size
    if batches:
        st.caption(f"{batches[batch_i]['id'] if batch_i < len(batches) else ''} · shot {idx+1}/{len(shots)}")

    # Batch strip
    bcols = st.columns(min(6, max(1, len(batches))))
    for i, b in enumerate(batches[:6]):
        with bcols[i % len(bcols)]:
            if st.button(b["id"], key=f"batch_{b['id']}"):
                st.session_state.doc_flow_idx = int(b["start"]) - 1
                st.rerun()

    shot = shots[idx]
    st.markdown(f"### SHOT {int(shot['number']):03d}")
    st.write("**Narration**")
    st.write(shot.get("narration") or "")
    st.write("**References:**", ", ".join(shot.get("references") or []) or "—")
    st.write("**Continuity:**", shot.get("continuity") or "—")
    st.write("**Shot:**", shot.get("shot_type") or "—")
    st.write("**Expected:**", shot.get("expected_file"))

    prompt = shot.get("prompt") or ""
    st.text_area("Prompt", value=prompt, height=200, key=f"prompt_view_{idx}")
    ref_blob = _ref_instructions(shot, data.get("story_bible") or {})

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.code(prompt, language=None)
        st.caption("Select & ⌘C — Copy Prompt")
    with c2:
        st.code(f"{prompt}\n\n---\nREFERENCE INSTRUCTIONS\n{ref_blob}", language=None)
        st.caption("Copy Prompt + References")
    with c3:
        if st.button("◀ Previous"):
            st.session_state.doc_flow_idx = max(0, idx - 1)
            st.rerun()
    with c4:
        if st.button("Next ▶"):
            st.session_state.doc_flow_idx = min(len(shots) - 1, idx + 1)
            st.rerun()

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        if st.button("Mark generated"):
            update_shot_status(project["id"], int(shot["number"]), "generated")
            st.session_state.doc_flow_idx = min(len(shots) - 1, idx + 1)
            st.rerun()
    with s2:
        if st.button("Mark approved"):
            update_shot_status(project["id"], int(shot["number"]), "approved")
            st.rerun()
    with s3:
        if st.button("Needs regen"):
            update_shot_status(project["id"], int(shot["number"]), "needs_regen")
            st.rerun()
    with s4:
        st.caption(f"Status: **{shot.get('status')}**")

    # Persist index
    project["flow_shot_index"] = idx
    save_project(project)

    st.divider()
    st.markdown("#### Batch prompts (quick scan)")
    start = (idx // batch_size) * batch_size
    end = min(len(shots), start + batch_size)
    for s in shots[start:end]:
        st.markdown(f"**{int(s['number']):03d}** `{s.get('status')}` — {(s.get('narration') or '')[:80]}")
        with st.expander(f"Prompt {int(s['number']):03d}"):
            st.code(s.get("prompt") or "", language=None)


def _ref_instructions(shot: dict, bible: dict) -> str:
    lines = []
    ids = set(shot.get("references") or [])
    for group in ("characters", "locations", "important_objects"):
        for ent in bible.get(group) or []:
            if ent.get("id") in ids:
                lines.append(f"{ent.get('id')} {ent.get('name')}: {ent.get('visual_description')}")
    return "\n".join(lines) or "(no master refs linked)"


def _tab_images(project: dict) -> None:
    folder = st.text_input(
        "Folder with 001.png, 002.png, …",
        value=str(project_dir(project["id"]) / "flow-import"),
        help="Absolute path to a folder of zero-padded stills from Google Flow",
    )
    Path(folder).mkdir(parents=True, exist_ok=True)
    if st.button("Bulk import", type="primary"):
        try:
            report = import_images(project, folder)
            st.success(f"{report.get('ready')} / {report.get('expected')} READY")
            if report.get("missing"):
                st.warning("Missing: " + ", ".join(report["missing"][:40]))
            st.json(report)
            st.rerun()
        except Exception as e:
            st.error(str(e))

    report = project.get("import_report") or {}
    if report:
        st.markdown(f"**{report.get('ready')} / {report.get('expected')} READY**")
        if report.get("missing"):
            st.error("Missing: " + ", ".join(report["missing"]))

    st.subheader("Replace one shot")
    n = st.number_input("Shot number", min_value=1, value=1, step=1)
    up = st.file_uploader("New image", type=["png", "jpg", "jpeg", "webp"])
    if st.button("Replace shot") and up is not None:
        tmp = project_dir(project["id"]) / "logs" / f"replace_{int(n)}.png"
        tmp.write_bytes(up.getvalue())
        replace_shot_image(project, int(n), tmp)
        st.success(f"Replaced {int(n):03d}.png (voice kept)")
        st.rerun()


def _tab_render(project: dict) -> None:
    if st.button("Generate voice (continuous)", type="primary"):
        with st.spinner("TTS…"):
            try:
                generate_project_voice(project)
                st.success("Voice ready")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    music = st.text_input("Music path (optional)", value=str(project.get("music_path") or ""))
    vol = st.slider("Music volume", 0.0, 0.4, float(project.get("music_volume") or 0.12), 0.01)
    if st.button("Save audio settings"):
        project["music_path"] = music
        project["music_volume"] = vol
        save_project(project)
        st.rerun()

    if st.button("Preview checks"):
        prev = build_preview(project)
        st.json(prev)

    allow_missing = st.checkbox("Allow assemble with missing images (not recommended)", value=False)
    if st.button("Assemble + Render final.mp4", type="primary"):
        with st.spinner("FFmpeg…"):
            try:
                project["music_path"] = music
                project["music_volume"] = vol
                save_project(project)
                out = assemble_and_render(project, allow_missing=allow_missing, transiciones_suaves=True)
                st.success(f"Rendered: {out}")
                st.video(str(out))
                st.rerun()
            except Exception as e:
                st.error(str(e))

    final = project_dir(project["id"]) / "render" / "final.mp4"
    if final.exists():
        st.video(str(final))
