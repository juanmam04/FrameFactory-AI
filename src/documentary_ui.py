"""Streamlit UI: Documentary daily workflow (Session = channel)."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.documentary.assemble_service import assemble_and_render, build_preview
from src.documentary.channel import (
    business_documentary_profile,
    channel_display_name,
    duration_range_from_profile,
    goal_count_from_profile,
    is_documentary_profile,
    language_from_profile,
    profile_snapshot,
    target_words_from_profile,
)
from src.documentary.flow_pack import export_flow_pack, load_shot_list, update_shot_status
from src.documentary.ideas import generate_story_ideas
from src.documentary.import_images import import_images, replace_shot_image, sync_shot_statuses_from_images
from src.documentary.project import (
    create_project,
    derive_progress,
    list_projects_for_session,
    load_project,
    project_dir,
    save_project,
    session_stats,
)
from src.documentary.script_service import approve_script, generate_documentary_script, save_edited_script
from src.documentary.voice_service import generate_project_voice
from src.saas_creative_profile import merge_profile_disk
from src.saas_sessions import ensure_store, get_session, load_store, persist_session, set_active_session
from src.script_generator import count_words


STEP_LABELS = {
    "story": "Story",
    "research": "Research",
    "script": "Script",
    "flow": "Flow",
    "images": "Images",
    "voice": "Voice",
    "render": "Render",
    "done": "Done",
}


def _active_session() -> dict | None:
    store = ensure_store()
    sid = st.session_state.get("active_session_id") or store.get("active_id")
    return get_session(store, sid)


def _active_profile() -> dict:
    sess = _active_session() or {}
    return merge_profile_disk(sess.get("creative_profile") or st.session_state.get("creative_profile"))


def _copy_button(label: str, text: str, key: str) -> None:
    st.code(text or "", language=None)
    if st.button(label, key=key):
        try:
            import pyperclip

            pyperclip.copy(text or "")
            st.toast("Copied — paste into Google Flow")
        except Exception:
            st.info("Select the prompt above and press Ctrl/Cmd+C (clipboard helper not available).")


def _human_error(exc: BaseException) -> str:
    msg = str(exc)
    low = msg.lower()
    if "openai_api_key" in low or ("documentary script generation requires" in low):
        return (
            "Script generation needs an OpenAI API key. Add OPENAI_API_KEY to your `.env` file and restart. "
            "FrameFactory will no longer silently insert the old Spanish storytime text."
        )
    if "failed documentary" in low or "quality checks" in low:
        return msg
    if "elevenlabs" in low or ("openai" in low and "key" in low):
        return "Voice generation failed. Check your ElevenLabs or OpenAI API key in `.env` and try again."
    if "ffmpeg" in low:
        return "Rendering needs FFmpeg installed and available in your PATH."
    if "missing images" in low or "images are still missing" in low:
        return msg.replace("Missing images:", "Some images are still missing:")
    if "script must be approved" in low or "approve the script" in low:
        return "Approve the script first, then continue to Flow."
    return msg


def _render_stepper(project: dict) -> None:
    prog = derive_progress(project)
    current = prog["current"]
    flags = prog["flags"]
    parts = []
    for i, step in enumerate(prog["steps"], start=1):
        label = STEP_LABELS.get(step, step)
        if flags.get(step) and step != current:
            mark = "✓"
        elif step == current:
            mark = "●"
        else:
            mark = "○"
        parts.append(f"{mark} {i} {label}")
    st.caption("  ·  ".join(parts))


def page_documentary() -> None:
    """Entry: channel home, ideas, or active video stepper."""
    ensure_100_days_session_ready()
    profile = _active_profile()
    sess = _active_session() or {}
    name = channel_display_name(profile, str(sess.get("title") or ""))

    view = st.session_state.get("doc_view") or "home"
    pending = st.session_state.pop("_doc_pending_project_id", None)
    if pending:
        st.session_state.doc_project_id = str(pending)
        st.session_state.doc_view = "project"
        view = "project"

    if not is_documentary_profile(profile):
        st.markdown(f'<p class="saas-hero">{name or "Documentary"}</p>', unsafe_allow_html=True)
        st.info(
            "This session is not set as a Documentary channel yet. "
            "Open **Channel Profile**, describe your channel, or load **100 Days — Business Documentaries**."
        )
        if st.button("Load 100 Days Business Documentaries channel", type="primary"):
            _activate_100_days_session()
            st.rerun()
        st.divider()
        _legacy_project_picker()
        return

    if view == "ideas":
        _page_ideas(sess, profile, name)
        return
    if view == "project" and st.session_state.get("doc_project_id"):
        try:
            project = load_project(str(st.session_state.doc_project_id))
        except Exception as e:
            st.error(_human_error(e))
            st.session_state.doc_view = "home"
            st.rerun()
            return
        _page_project(project, sess, profile, name)
        return
    if view == "library":
        _page_library(sess, profile, name)
        return

    _page_home(sess, profile, name)


def ensure_100_days_session_ready() -> None:
    """Ensure the canonical challenge session exists (idempotent)."""
    store = ensure_store()
    for s in store.get("sessions") or []:
        if not isinstance(s, dict):
            continue
        title = str(s.get("title") or "")
        prof = merge_profile_disk(s.get("creative_profile"))
        ch_name = str((prof.get("channel") or {}).get("name") or "")
        if "100 Days — Business Documentaries" in title or "100 Days — Business Documentaries" in ch_name:
            # Keep channel profile upgraded to latest editorial definition
            fresh = business_documentary_profile()
            if (prof.get("channel") or {}).get("tagline") != (fresh.get("channel") or {}).get("tagline") or not is_documentary_profile(
                prof
            ):
                s["creative_profile"] = fresh
                persist_session(store, str(s["id"]), list(s.get("messages") or []), fresh)
                if str(st.session_state.get("active_session_id") or "") == str(s.get("id")):
                    st.session_state.creative_profile = fresh
            return

    from src.saas_sessions import add_session, persist_session_summary

    profile = business_documentary_profile()
    opening = (
        "This channel is ready: **100 Days — Business Documentaries**. "
        "English cinematic true stories about companies, founders, money, power, fraud, and ambition. "
        "One video a day. Images via Google Flow. Tell me if you want to adjust tone or pillars."
    )
    store, sid = add_session(store, "100 Days — Business Documentaries", profile)
    messages = [
        {"role": "assistant", "content": "Hola. ¿Qué tipo de videos querés publicar en esta sesión?"},
        {
            "role": "user",
            "content": (
                "I want to create cinematic narrative documentaries in English about extraordinary true stories "
                "involving companies, founders, money, power, ambition, fraud, competition, spectacular success "
                "and catastrophic failure. Storytelling comes before business education. Videos should be 8–12 minutes, "
                "accessible to a general audience, highly clickable without being misleading, and visually designed "
                "around Google Flow. I want to publish one every day for 100 days."
            ),
        },
        {"role": "assistant", "content": opening},
    ]
    memory = (
        "Channel: 100 Days Business Documentaries. EN, 8–12 min, story-first true business stories, "
        "Google Flow visuals, 100 daily videos."
    )
    persist_session(load_store(), sid, messages, profile)
    persist_session_summary(load_store(), sid, memory)
    cur = get_session(load_store(), st.session_state.get("active_session_id"))
    if not cur or not is_documentary_profile(cur.get("creative_profile")):
        set_active_session(load_store(), sid)
        st.session_state.active_session_id = sid
        st.session_state._saas_pending_session_id = sid
        st.session_state.creative_profile = profile


def _activate_100_days_session() -> None:
    ensure_100_days_session_ready()
    store = load_store()
    for s in store.get("sessions") or []:
        if not isinstance(s, dict):
            continue
        if "100 Days" in str(s.get("title") or "") or is_documentary_profile(s.get("creative_profile")):
            set_active_session(store, str(s["id"]))
            st.session_state.active_session_id = str(s["id"])
            st.session_state._saas_pending_session_id = str(s["id"])
            st.session_state.creative_profile = merge_profile_disk(s.get("creative_profile"))
            st.session_state.doc_view = "home"
            return


def _page_home(sess: dict, profile: dict, name: str) -> None:
    goal = goal_count_from_profile(profile, 100)
    stats = session_stats(str(sess.get("id") or ""), goal)
    st.markdown(f'<p class="saas-hero">{name.upper()}</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="saas-sub">DAY {stats["day"]} / {stats["goal"]} · Fascinating true stories about companies · '
        f"Story first · English · 8–12 min · Google Flow</p>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Completed", stats["completed"])
    with c2:
        st.metric("In progress", stats["in_progress"])
    with c3:
        st.metric("Remaining", stats["remaining"])
    st.caption("Completed = rendered final video in FrameFactory (not YouTube publish status).")

    if st.button("CREATE TODAY'S VIDEO", type="primary", use_container_width=True):
        st.session_state.doc_view = "ideas"
        st.session_state.doc_ideas = None
        st.rerun()

    items = list_projects_for_session(str(sess.get("id") or ""))
    st.subheader("Recent videos")
    if not items:
        st.write("No episodes yet. Start with **Create today's video**.")
        return
    for p in sorted(items, key=lambda x: int(x.get("episode_number") or 0), reverse=True)[:12]:
        ep = int(p.get("episode_number") or 0)
        status = "Complete" if (p.get("checkpoints") or {}).get("render_ready") else "In progress"
        cols = st.columns([4, 1, 1])
        cols[0].write(f"**VIDEO {ep:03d}** — {p.get('title') or p.get('topic')}")
        cols[1].caption(status)
        if cols[2].button("Open", key=f"open_{p['id']}"):
            st.session_state.doc_project_id = p["id"]
            st.session_state.doc_view = "project"
            st.rerun()


def _page_ideas(sess: dict, profile: dict, name: str) -> None:
    st.markdown(f'<p class="saas-hero">Choose today\'s story</p>', unsafe_allow_html=True)
    st.caption(name)
    if st.button("← Back to home"):
        st.session_state.doc_view = "home"
        st.rerun()

    prior = list_projects_for_session(str(sess.get("id") or ""))
    if st.session_state.get("doc_ideas") is None:
        with st.spinner("Generating ideas…"):
            st.session_state.doc_ideas = generate_story_ideas(
                profile,
                prior_videos=prior,
                memory_summary=str(sess.get("memory_summary") or ""),
                count=5,
                use_llm=True,
            )

    ideas = st.session_state.get("doc_ideas") or []
    for i, idea in enumerate(ideas):
        with st.container():
            st.markdown(f"### {idea.get('title_concept')}")
            st.write(idea.get("story") or "")
            st.write(f"**Hook:** {idea.get('hook') or '—'}")
            st.write(f"**Why it works:** {idea.get('why_it_works') or '—'}")
            st.write(
                f"**Pillar:** {idea.get('content_pillar') or '—'} · "
                f"**Visual:** {idea.get('visual_potential') or '—'} · "
                f"**Research:** {idea.get('research_risk') or '—'}"
            )
            if st.button("Choose", key=f"choose_idea_{i}", type="primary"):
                _create_from_idea(sess, profile, idea)
                return
        st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate 5 more", use_container_width=True):
            with st.spinner("Generating…"):
                st.session_state.doc_ideas = generate_story_ideas(
                    profile,
                    prior_videos=prior,
                    memory_summary=str(sess.get("memory_summary") or ""),
                    count=5,
                    use_llm=True,
                )
            st.rerun()
    with c2:
        if st.button("I already have a topic", use_container_width=True):
            st.session_state.doc_manual_topic = True

    if st.session_state.get("doc_manual_topic"):
        topic = st.text_input("Your topic / working title")
        if st.button("Continue with this topic", type="primary") and topic.strip():
            idea = {
                "title_concept": topic.strip(),
                "story": topic.strip(),
                "hook": "",
                "why_it_works": "User-provided topic",
                "content_pillar": "",
                "visual_potential": "Medium",
                "research_risk": "Medium",
                "primary_entity": topic.strip()[:80],
            }
            _create_from_idea(sess, profile, idea)


def _create_from_idea(sess: dict, profile: dict, idea: dict) -> None:
    topic = str(idea.get("story") or idea.get("title_concept") or "").strip()
    title = str(idea.get("title_concept") or topic).strip()
    try:
        data = create_project(
            topic,
            title=title,
            target_words=target_words_from_profile(profile, 1500),
            session_id=str(sess.get("id") or ""),
            creative_profile=profile_snapshot(profile),
            idea=idea,
            language=language_from_profile(profile),
            target_duration_min=duration_range_from_profile(profile),
        )
        st.session_state.doc_project_id = data["id"]
        st.session_state.doc_view = "project"
        st.session_state.doc_ideas = None
        st.session_state.doc_manual_topic = False
        st.success("Story selected — next: research.")
        st.rerun()
    except Exception as e:
        st.error(_human_error(e))


def _page_library(sess: dict, profile: dict, name: str) -> None:
    st.markdown(f'<p class="saas-hero">Library</p>', unsafe_allow_html=True)
    st.caption(name)
    if st.button("← Home"):
        st.session_state.doc_view = "home"
        st.rerun()
    items = list_projects_for_session(str(sess.get("id") or ""))
    for p in sorted(items, key=lambda x: int(x.get("episode_number") or 0)):
        ep = int(p.get("episode_number") or 0)
        done = (p.get("checkpoints") or {}).get("render_ready")
        st.write(f"**VIDEO {ep:03d}** — {p.get('title')} — {'Complete' if done else 'In progress'}")
        if st.button("Open", key=f"lib_{p['id']}"):
            st.session_state.doc_project_id = p["id"]
            st.session_state.doc_view = "project"
            st.rerun()


def _page_project(project: dict, sess: dict, profile: dict, name: str) -> None:
    ep = int(project.get("episode_number") or 0)
    st.markdown(
        f'<p class="saas-hero">VIDEO {ep:03d} — {(project.get("title") or "")[:60]}</p>',
        unsafe_allow_html=True,
    )
    st.caption(name)
    if st.button("← Channel home"):
        st.session_state.doc_view = "home"
        st.rerun()

    _render_stepper(project)
    prog = derive_progress(project)
    step = prog["current"]

    # Allow jumping to completed/current steps via tabs-like buttons
    labels = [STEP_LABELS[s] for s in prog["steps"]]
    # Map clickable steps: show radio of available
    choice = st.radio(
        "Step",
        options=list(prog["steps"]),
        format_func=lambda s: STEP_LABELS.get(s, s),
        index=list(prog["steps"]).index(step) if step in prog["steps"] else 0,
        horizontal=True,
        label_visibility="collapsed",
        key=f"doc_step_radio_{project['id']}",
    )

    if choice == "story":
        st.write(f"**Story:** {project.get('topic')}")
        idea = project.get("idea") or {}
        if idea.get("hook"):
            st.write(f"**Hook:** {idea.get('hook')}")
        st.info("Story is set. Continue to Research.")
        if st.button("Continue to Research", type="primary"):
            project["ui_step"] = "research"
            save_project(project)
            st.rerun()
    elif choice == "research":
        _step_research(project)
    elif choice == "script":
        _step_script(project)
    elif choice == "flow":
        _step_flow(project)
    elif choice == "images":
        _step_images(project)
    elif choice == "voice":
        _step_voice(project)
    elif choice in ("render", "done"):
        _step_render(project, sess, profile)


def _step_research(project: dict) -> None:
    st.subheader("Research")
    st.write(f"**Story:** {project.get('title') or project.get('topic')}")
    st.caption(
        "Add the facts and sources FrameFactory should rely on. The script must not invent missing information."
    )
    notes = st.text_area("Research notes", value=project.get("research_notes") or "", height=180)
    sources = st.text_area(
        "Sources",
        value="\n".join(project.get("sources") or []),
        height=100,
        placeholder="One source per line",
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Continue to Script", type="primary"):
            project["research_notes"] = notes
            project["sources"] = [s.strip() for s in sources.splitlines() if s.strip()]
            project["research_skipped"] = False
            project["ui_step"] = "script"
            root = project_dir(project["id"])
            (root / "script" / "research_notes.md").write_text(
                f"# Research — {project.get('title')}\n\n{notes}\n\n## Sources\n"
                + "\n".join(f"- {s}" for s in project["sources"]),
                encoding="utf-8",
            )
            save_project(project)
            st.rerun()
    with c2:
        if st.button("Skip for now"):
            st.session_state.doc_skip_research_warn = True
    if st.session_state.get("doc_skip_research_warn"):
        st.warning(
            "Without research notes, the script must stay high-level and must not invent facts. "
            "You will still need to fact-check before approving."
        )
        if st.button("Skip and go to Script", type="primary"):
            project["research_notes"] = notes
            project["sources"] = [s.strip() for s in sources.splitlines() if s.strip()]
            project["research_skipped"] = True
            project["ui_step"] = "script"
            save_project(project)
            st.session_state.doc_skip_research_warn = False
            st.rerun()


def _step_script(project: dict) -> None:
    st.subheader("Script")
    from src.documentary.script_service import research_is_thin

    if research_is_thin(project):
        st.warning(
            "This documentary has little or no research. FrameFactory may not have enough factual material "
            "to produce a reliable script. The model has no live web browse — it will only use what you pasted. "
            "You can still generate, but nonfiction rules stay strict (no invented filler)."
        )

    words = count_words(project.get("script") or "") if project.get("script") else int(project.get("target_words") or 1500)
    est_min = words / 140.0
    st.caption(f"Estimated duration: **{int(est_min):02d}:{int((est_min % 1) * 60):02d}** · Target ~{project.get('target_words')} words")

    for w in project.get("script_warnings") or []:
        st.info(w)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Generate script", type="primary"):
            with st.spinner("Writing script…"):
                try:
                    generate_documentary_script(project, use_llm=True)
                    st.rerun()
                except Exception as e:
                    st.error(_human_error(e))
    with c2:
        if st.button("Regenerate"):
            with st.spinner("Rewriting…"):
                try:
                    generate_documentary_script(project, use_llm=True)
                    st.rerun()
                except Exception as e:
                    st.error(_human_error(e))
    with c3:
        if st.button("Approve script", disabled=not (project.get("script") or "").strip()):
            try:
                approve_script(project)
                with st.spinner("Building Flow prompts…"):
                    export_flow_pack(load_project(project["id"]), use_llm=True, rebuild_visuals=True)
                st.success("Script approved. Flow is ready.")
                st.rerun()
            except Exception as e:
                st.error(_human_error(e))

    script = st.text_area("Script", value=project.get("script") or "", height=360)
    if st.button("Save edits"):
        try:
            save_edited_script(project, script)
            st.success("Saved — approval cleared if it was approved.")
            st.rerun()
        except Exception as e:
            st.error(_human_error(e))

    with st.expander("Advanced"):
        if st.button("Generate mock script (offline)"):
            try:
                generate_documentary_script(project, use_llm=False)
                st.rerun()
            except Exception as e:
                st.error(_human_error(e))
        tw = st.number_input("Target words override", 800, 2500, int(project.get("target_words") or 1500), 50)
        if st.button("Save word target"):
            project["target_words"] = int(tw)
            save_project(project)
            st.rerun()


def _entity_name(bible: dict, ref_id: str) -> str:
    for group in ("characters", "locations", "important_objects"):
        for ent in bible.get(group) or []:
            if ent.get("id") == ref_id:
                return str(ent.get("name") or ref_id)
    return ref_id


def _step_flow(project: dict) -> None:
    st.subheader("Flow")
    st.caption("Generate master references first, then create stills in Google Flow. FrameFactory only organizes prompts.")
    if not project.get("script_approved"):
        st.warning("Approve the script before Flow.")
        return
    if not (project.get("checkpoints") or {}).get("flow_pack_ready"):
        if st.button("Generate Flow prompts", type="primary"):
            with st.spinner("Building references and shots…"):
                try:
                    export_flow_pack(project, use_llm=True, rebuild_visuals=True)
                    st.rerun()
                except Exception as e:
                    st.error(_human_error(e))
        with st.expander("Advanced"):
            if st.button("Generate offline (no LLM)"):
                export_flow_pack(project, use_llm=False, rebuild_visuals=True)
                st.rerun()
        return

    try:
        sync_shot_statuses_from_images(project["id"])
        data = load_shot_list(project["id"])
    except Exception as e:
        st.error(_human_error(e))
        return

    bible = data.get("story_bible") or {}
    shots = data.get("shots") or []
    batches = data.get("batches") or []
    batch_size = int(data.get("batch_size") or 10)

    tab_a, tab_b = st.tabs(["References", "Shots"])
    with tab_a:
        st.write("**Global style**")
        st.code(str(bible.get("global_style") or ""), language=None)
        for label, key, kind in [
            ("Characters", "characters", "Character"),
            ("Locations", "locations", "Location"),
            ("Objects", "important_objects", "Object"),
        ]:
            ents = bible.get(key) or []
            if not ents:
                continue
            st.markdown(f"#### {label}")
            for ent in ents:
                name = ent.get("name") or ent.get("id")
                used = len(ent.get("appears_in_shots") or [])
                st.markdown(f"**{name}** · {kind} · used in {used} shots")
                prompt = f"Generate reference image:\n{ent.get('visual_description')}"
                _copy_button("Copy prompt", prompt, key=f"refcopy_{ent.get('id')}")
                st.caption("Status: create this master in Google Flow before shots that need it.")
                st.divider()

    with tab_b:
        # Batch progress
        for b in batches:
            start, end = int(b["start"]), int(b["end"])
            subset = [s for s in shots if start <= int(s["number"]) <= end]
            ready_n = sum(1 for s in subset if s.get("status") in ("generated", "approved"))
            st.caption(f"{b['id'].replace('BATCH_', 'Batch ')}    {ready_n}/{len(subset)}")

        if not shots:
            st.warning("No shots yet.")
            return

        idx = int(st.session_state.get("doc_flow_idx", project.get("flow_shot_index") or 0))
        idx = max(0, min(len(shots) - 1, idx))
        shot = shots[idx]
        st.markdown(f"### {idx + 1} / {len(shots)}")
        st.write("**Narration**")
        st.write(shot.get("narration") or "")
        ref_names = [_entity_name(bible, r) for r in (shot.get("references") or [])]
        st.write("**Use:**", ", ".join(ref_names) if ref_names else "—")
        st.write(f"**Expected filename:** `{shot.get('expected_file')}`")
        prompt = shot.get("prompt") or ""
        _copy_button("Copy prompt", prompt, key=f"shotcopy_{idx}")

        status = shot.get("status") or "pending"
        if status in ("generated", "approved"):
            st.success("✓ Image imported / Ready" if status == "generated" else "✓ Approved")
        elif status == "needs_regen":
            st.warning("↻ Needs redo")
        else:
            st.caption("○ Not generated yet")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("← Previous"):
                st.session_state.doc_flow_idx = max(0, idx - 1)
                st.rerun()
        with c2:
            if st.button("Next →"):
                st.session_state.doc_flow_idx = min(len(shots) - 1, idx + 1)
                st.rerun()
        with c3:
            if st.button("Needs redo"):
                update_shot_status(project["id"], int(shot["number"]), "needs_regen")
                st.rerun()
        with c4:
            if st.button("Continue to Images", type="primary"):
                project["ui_step"] = "images"
                project["flow_shot_index"] = idx
                save_project(project)
                st.rerun()

        project["flow_shot_index"] = idx
        save_project(project)


def _step_images(project: dict) -> None:
    st.subheader("Import Flow images")
    folder = st.text_input(
        "Folder with 001.png, 002.png, …",
        value=str(project_dir(project["id"]) / "flow-import"),
    )
    Path(folder).mkdir(parents=True, exist_ok=True)
    uploads = st.file_uploader(
        "Or drop image files here",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
    )
    if uploads:
        dest = Path(folder)
        for up in uploads:
            name = up.name
            (dest / name).write_bytes(up.getvalue())
        st.caption(f"Saved {len(uploads)} file(s) into the folder.")

    if st.button("Import images", type="primary"):
        try:
            report = import_images(load_project(project["id"]), folder)
            missing = report.get("missing") or []
            st.success(f"{report.get('ready')} / {report.get('expected')} ready")
            if missing:
                st.warning(
                    f"{len(missing)} images are still missing: " + ", ".join(missing[:40])
                    + ("…" if len(missing) > 40 else "")
                )
            st.rerun()
        except Exception as e:
            st.error(_human_error(e))

    project = load_project(project["id"])
    report = project.get("import_report") or {}
    if report:
        st.markdown(f"**{report.get('ready', 0)} / {report.get('expected', 0)} ready**")
        if report.get("missing"):
            st.error("Missing: " + ", ".join(report["missing"]))

    st.subheader("Replace one shot")
    n = st.number_input("Shot number", min_value=1, value=1, step=1)
    up = st.file_uploader("New image", type=["png", "jpg", "jpeg", "webp"], key="replace_one")
    if st.button("Replace shot") and up is not None:
        tmp = project_dir(project["id"]) / "logs" / f"replace_{int(n)}.png"
        tmp.write_bytes(up.getvalue())
        replace_shot_image(load_project(project["id"]), int(n), tmp)
        st.success(f"Replaced {int(n):03d}.png")
        st.rerun()

    expected = int(report.get("expected") or 0)
    ready = int(report.get("ready") or 0)
    if expected and ready >= expected:
        if st.button("Continue to Voice", type="primary"):
            project["ui_step"] = "voice"
            save_project(project)
            st.rerun()
    else:
        with st.expander("Advanced"):
            if st.button("Continue with missing images"):
                project["ui_step"] = "voice"
                save_project(project)
                st.rerun()


def _step_voice(project: dict) -> None:
    st.subheader("Voice")
    voice = project.get("voice") or {}
    if voice.get("duration_sec"):
        d = float(voice["duration_sec"])
        st.success(f"✓ Voice ready — {int(d)//60:02d}:{int(d)%60:02d}")
    else:
        st.caption("Voice: configured from `.env` (ElevenLabs or OpenAI TTS)")
        est = count_words(project.get("script") or "") / 140.0
        st.caption(f"Estimated duration ~ {int(est):02d}:{int((est%1)*60):02d}")

    if st.button("Generate voice", type="primary"):
        with st.spinner("Generating narration…"):
            try:
                generate_project_voice(load_project(project["id"]))
                st.success("Voice ready")
                st.rerun()
            except Exception as e:
                st.error(_human_error(e))

    if (project.get("checkpoints") or {}).get("voice_ready"):
        if st.button("Continue to Render", type="primary"):
            project["ui_step"] = "render"
            save_project(project)
            st.rerun()

    with st.expander("Advanced"):
        music = st.text_input("Music path", value=str(project.get("music_path") or ""))
        vol = st.slider("Music volume", 0.0, 0.4, float(project.get("music_volume") or 0.12), 0.01)
        if st.button("Save audio settings"):
            project["music_path"] = music
            project["music_volume"] = vol
            save_project(project)
            st.rerun()


def _step_render(project: dict, sess: dict, profile: dict) -> None:
    final = project_dir(project["id"]) / "render" / "final.mp4"
    if final.exists() and (project.get("checkpoints") or {}).get("render_ready"):
        ep = int(project.get("episode_number") or 0)
        goal = goal_count_from_profile(profile, 100)
        st.subheader(f"VIDEO {ep} / {goal} COMPLETE")
        st.write(f"**Title:** {project.get('title')}")
        dur = (project.get("voice") or {}).get("duration_sec")
        if dur:
            st.write(f"**Duration:** {int(dur)//60:02d}:{int(float(dur)%60):02d}")
        st.write(f"`{final}`")
        try:
            st.video(str(final))
        except Exception:
            pass
        st.info("Next (manual): Thumbnail · YouTube upload")
        if st.button("CREATE NEXT VIDEO", type="primary"):
            st.session_state.doc_view = "ideas"
            st.session_state.doc_ideas = None
            st.session_state.doc_project_id = None
            st.rerun()
        return

    st.subheader("Render")
    prev = build_preview(load_project(project["id"]))
    report = project.get("import_report") or {}
    voice = project.get("voice") or {}
    st.write(
        f"**{prev.get('image_count', 0)} images** · "
        f"voice {('ready' if prev.get('voice_ok') else 'missing')} · "
        f"1920 × 1080"
    )
    if voice.get("duration_sec"):
        d = float(voice["duration_sec"])
        st.write(f"Voice duration: {int(d)//60:02d}:{int(d)%60:02d}")
    if project.get("music_path"):
        st.write(f"Music: `{project.get('music_path')}`")
    if prev.get("missing_images"):
        miss = prev["missing_images"]
        st.warning(
            f"{len(miss)} images are still missing: " + ", ".join(miss[:40]) + ("…" if len(miss) > 40 else "")
        )

    allow = False
    with st.expander("Advanced"):
        allow = st.checkbox("Allow render with missing images (not recommended)", value=False)
        if st.button("Preview checks"):
            st.json(prev)

    if st.button("Render video", type="primary"):
        with st.spinner("Rendering…"):
            try:
                out = assemble_and_render(load_project(project["id"]), allow_missing=allow, transiciones_suaves=True)
                st.success(f"Video ready: {out}")
                st.rerun()
            except Exception as e:
                st.error(_human_error(e))


def _legacy_project_picker() -> None:
    """Fallback for non-channel sessions — keep MVP accessible."""
    from src.documentary.project import list_projects

    projects = list_projects()
    ids = [p["id"] for p in projects]
    sel = st.selectbox("Existing documentary projects", ["—"] + ids)
    if sel and sel != "—":
        st.session_state.doc_project_id = sel
        st.session_state.doc_view = "project"
        if st.button("Open project"):
            st.rerun()
