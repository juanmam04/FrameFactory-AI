"""Tests for Documentary 100-days MVP + channel workflow (offline-friendly)."""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.documentary.assemble_service import build_preview
from src.documentary.channel import business_documentary_profile, is_documentary_profile, script_context_from_session
from src.documentary.flow_pack import export_flow_pack, load_shot_list, update_shot_status
from src.documentary.ideas import generate_story_ideas
from src.documentary.import_images import import_images, replace_shot_image, sync_shot_statuses_from_images
from src.documentary.project import (
    create_project,
    derive_progress,
    load_project,
    project_dir,
    session_stats,
)
from src.documentary.script_service import approve_script, generate_documentary_script, save_edited_script
from src.voice_generator import generar_voz


@pytest.fixture()
def tmp_projects(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    return root


def test_create_persist_reload(tmp_projects):
    p = create_project("The Rise and Fall of WeWork", project_id="100-days-test", target_words=1200)
    assert p["id"] == "100-days-test"
    assert (tmp_projects / "100-days-test" / "project.json").exists()
    p2 = load_project("100-days-test")
    assert p2["topic"].startswith("The Rise")
    assert p2["checkpoints"]["script_ready"] is False


def test_channel_profile_and_ideas_offline():
    prof = business_documentary_profile()
    assert is_documentary_profile(prof)
    assert prof["channel"]["goal_count"] == 100
    ideas = generate_story_ideas(prof, prior_videos=[], count=5, use_llm=False)
    assert len(ideas) == 5
    assert ideas[0]["title_concept"]
    # Avoid repeating WeWork if already produced
    prior = [{"topic": "WeWork", "title": "WeWork", "idea": {"primary_entity": "WeWork"}}]
    ideas2 = generate_story_ideas(prof, prior_videos=prior, count=5, use_llm=False)
    assert all("wework" not in (i.get("primary_entity") or "").lower() for i in ideas2)
    ctx = script_context_from_session(prof, idea=ideas[0])
    assert "PERFIL DEL CREADOR" in ctx or "CREATOR" in ctx.upper() or "business" in ctx.lower()


def test_session_linked_project_and_progress(tmp_projects):
    prof = business_documentary_profile()
    p = create_project(
        "Theranos story",
        project_id="001-theranos",
        session_id="sess-100",
        creative_profile=prof,
        idea={"title_concept": "THERANOS", "primary_entity": "Theranos"},
        episode_number=1,
    )
    assert p["session_id"] == "sess-100"
    assert p["episode_number"] == 1
    assert p["creative_profile_snapshot"]["workflow"] == "documentary"
    prog = derive_progress(p)
    assert prog["current"] in ("research", "story")
    stats = session_stats("sess-100", 100)
    assert stats["in_progress"] == 1
    assert stats["completed"] == 0


def test_script_approve_flow_import_replace(tmp_projects, tmp_path):
    p = create_project(
        "WeWork story",
        project_id="doc-a",
        target_words=400,
        research_notes="SoftBank invested.",
        creative_profile=business_documentary_profile(),
        session_id="sess-a",
    )
    generate_documentary_script(p, use_llm=False)
    p = load_project("doc-a")
    assert p["checkpoints"]["script_ready"] is True
    assert p["script_approved"] is False

    save_edited_script(p, p["script"] + " SoftBank remained a major backer.")
    p = load_project("doc-a")
    approve_script(p)
    p = load_project("doc-a")
    assert p["script_approved"] is True

    export_flow_pack(p, use_llm=False, rebuild_visuals=True)
    p = load_project("doc-a")
    assert p["checkpoints"]["flow_pack_ready"] is True
    data = load_shot_list("doc-a")
    shots = data["shots"]
    assert 5 <= len(shots) <= 80
    assert (project_dir("doc-a") / "flow-pack" / "shots" / "001.txt").exists()

    update_shot_status("doc-a", 1, "generated")
    assert load_shot_list("doc-a")["shots"][0]["status"] == "generated"

    src = tmp_path / "flow_out"
    src.mkdir()
    for s in shots:
        n = int(s["number"])
        if n == 2:
            continue
        img = Image.new("RGB", (1280, 720), color=(n * 3 % 255, 40, 80))
        img.save(src / f"{n:03d}.png")

    report = import_images(p, src)
    assert "002" in report["missing"]
    assert report["ready"] == len(shots) - 1
    # Auto-status: imported shots marked generated
    synced = load_shot_list("doc-a")
    assert synced["shots"][0]["status"] == "generated"

    one = tmp_path / "002.png"
    Image.new("RGB", (1280, 720), color=(10, 200, 10)).save(one)
    replace_shot_image(p, 2, one)
    assert (project_dir("doc-a") / "images" / "002.png").exists()
    sync_shot_statuses_from_images("doc-a")
    assert load_shot_list("doc-a")["shots"][1]["status"] == "generated"

    p_b = create_project("Other", project_id="doc-b", target_words=300)
    generate_documentary_script(p_b, use_llm=False)
    approve_script(p_b)
    export_flow_pack(load_project("doc-b"), use_llm=False, rebuild_visuals=True)
    assert (project_dir("doc-a") / "images" / "001.png").exists()
    assert not (project_dir("doc-b") / "images" / "001.png").exists()


def test_voice_fail_without_keys(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="No se pudo generar voz"):
        generar_voz("Hello world test.", nombre_archivo="doc_test_empty")


def test_preview_warns_missing(tmp_projects):
    p = create_project("X", project_id="doc-prev", target_words=300)
    generate_documentary_script(p, use_llm=False)
    approve_script(p)
    export_flow_pack(load_project("doc-prev"), use_llm=False, rebuild_visuals=True)
    prev = build_preview(load_project("doc-prev"))
    assert prev["missing_images"]
    assert prev["voice_ok"] is False
