"""Visual Plan batching + import READY tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.documentary.project import create_project, project_dir, save_project
from src.documentary.script_service import approve_script
from src.documentary.visual_plan import (
    classify_visual_type,
    group_flow_batches,
    sync_ready_from_disk,
    update_visual_description,
)


@pytest.fixture()
def tmp_projects(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    return root


def _fake_visuals(n_flow: int, *, archival_at: list[int] | None = None):
    archival_at = set(archival_at or [])
    out = []
    for i in range(1, n_flow + len(archival_at) + 1):
        # simpler: build list with mix
        pass
    # Build explicitly: numbers 1..N with some archival
    visuals = []
    num = 1
    flow_left = n_flow
    arch = list(archival_at)
    # Create total = n_flow + len(arch) with arch at given positions
    total = n_flow + len(archival_at)
    arch_set = set(archival_at)
    for i in range(1, total + 1):
        vtype = "DOCUMENT" if i in arch_set else "FLOW_REENACTMENT"
        visuals.append(
            {
                "number": i,
                "visual_type": vtype,
                "description": f"scene {i}",
                "reference_ids": ["CHAR_001"] if vtype == "FLOW_REENACTMENT" and i % 3 == 0 else [],
                "story_beat_id": str(((i - 1) % 5) + 1),
                "expected_file": f"{i:03d}.png",
                "status": "MISSING",
            }
        )
    return visuals


def test_batch_grouping_23_flow():
    visuals = [{"number": i, "visual_type": "FLOW_REENACTMENT"} for i in range(1, 24)]
    batches = group_flow_batches(visuals, batch_size=10)
    assert len(batches) == 3
    assert batches[0]["visual_numbers"] == list(range(1, 11))
    assert batches[1]["visual_numbers"] == list(range(11, 21))
    assert batches[2]["visual_numbers"] == [21, 22, 23]
    assert batches[0].get("interchangeable") is True


def test_batches_group_by_moment_not_timeline():
    visuals = [
        {"number": 1, "visual_type": "FLOW_REENACTMENT", "narration": "The IPO was abruptly pulled overnight."},
        {"number": 2, "visual_type": "FLOW_REENACTMENT", "narration": "Adam Neumann launched WeWork in 2010."},
        {"number": 3, "visual_type": "FLOW_REENACTMENT", "narration": "SoftBank arranged a bailout after the collapse."},
        {"number": 4, "visual_type": "FLOW_REENACTMENT", "narration": "Their vision was a community-driven space."},
    ]
    batches = group_flow_batches(visuals, batch_size=10)
    by_mood = {b["moment_id"]: b["visual_numbers"] for b in batches}
    assert 1 in by_mood.get("collapse", []) and 3 in by_mood.get("collapse", [])
    assert 2 in by_mood.get("rise", []) and 4 in by_mood.get("rise", [])


def test_mixed_types_batches_only_flow():
    visuals = [
        {"number": 1, "visual_type": "FLOW_REENACTMENT"},
        {"number": 2, "visual_type": "FLOW_REENACTMENT"},
        {"number": 3, "visual_type": "DOCUMENT"},
        {"number": 4, "visual_type": "HEADLINE"},
        {"number": 5, "visual_type": "FLOW_REENACTMENT"},
    ]
    batches = group_flow_batches(visuals, batch_size=10)
    assert len(batches) == 1
    assert batches[0]["visual_numbers"] == [1, 2, 5]


def test_number_preservation_mixed():
    visuals = [
        {"number": 1, "visual_type": "FLOW_REENACTMENT"},
        {"number": 2, "visual_type": "ARCHIVAL_PHOTO"},
        {"number": 3, "visual_type": "FLOW_REENACTMENT"},
    ]
    batches = group_flow_batches(visuals, batch_size=10)
    assert batches[0]["visual_numbers"] == [1, 3]
    assert [v["number"] for v in visuals] == [1, 2, 3]


def test_classify_document_vs_flow():
    assert classify_visual_type("WeWork files its S-1 with the SEC") == "DOCUMENT"
    assert classify_visual_type("Neumann walks through a packed coworking floor") == "FLOW_REENACTMENT"


def test_reference_propagation_in_batch_prompt():
    from src.documentary.visual_plan import batch_references, format_batch_prompt

    visuals = [
        {
            "number": 1,
            "visual_type": "FLOW_REENACTMENT",
            "description": "founder in office",
            "reference_ids": ["CHAR_001"],
            "location": "NYC",
            "period": "2017",
            "shot_type": "medium_action",
        }
    ]
    masters = [{"id": "CHAR_001", "name": "Adam Neumann", "master_filename": "CHAR_001.png", "kind": "character"}]
    batch = group_flow_batches(visuals, batch_size=10)[0]
    refs = batch_references(batch, visuals, masters)
    assert refs and refs[0]["id"] == "CHAR_001"
    prompt = format_batch_prompt(batch, visuals, {"global_style": "doc"}, masters)
    assert "CHAR_001.png" in prompt or "Adam Neumann" in prompt
    assert "SAME" in prompt.upper() or "MOMENT" in prompt.upper() or "climate" in prompt.lower()


def test_bulk_import_ready(tmp_projects):
    p = create_project("WeWork visual test", title="WeWork Viz", research_notes="Adam Neumann SoftBank IPO S-1")
    p["script"] = (
        "In September 2019 the IPO collapsed. Adam Neumann founded WeWork in 2010. "
        "SoftBank invested billions. The S-1 filing revealed losses. "
    ) * 40
    p["script_approved"] = True
    p["story_plan_approved"] = True
    p["story_plan"] = {
        "central_story": "IPO collapse",
        "approved": True,
        "beats": [
            {"id": 1, "event": "IPO pulled", "priority": "essential"},
            {"id": 2, "event": "SoftBank invests", "priority": "essential"},
        ],
        "selected_beat_ids": [1, 2],
        "characters": [{"name": "Adam Neumann", "role_in_story": "CEO"}],
    }
    save_project(p)
    from src.documentary.flow_pack import export_flow_pack

    export_flow_pack(p, use_llm=False, rebuild_visuals=True)
    root = project_dir(p["id"])
    img = root / "images"
    img.mkdir(parents=True, exist_ok=True)
    # Create first visual file
    (img / "001.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    sync = sync_ready_from_disk(p["id"])
    assert "001" in sync["ready_ids"]
    assert sync["ready"] >= 1
    assert "001" not in sync["missing"]


def test_missing_detection_and_single_edit(tmp_projects):
    p = create_project("Edit visual", title="Edit", research_notes="enough notes for research")
    p["script"] = ("The company expanded across cities while SoftBank watched. " * 50)
    p["script_approved"] = True
    p["story_plan"] = {
        "central_story": "x",
        "approved": True,
        "beats": [{"id": 1, "event": "expansion SoftBank", "priority": "essential"}],
        "selected_beat_ids": [1],
        "characters": [{"name": "Founder", "role_in_story": "CEO"}],
    }
    p["story_plan_approved"] = True
    save_project(p)
    from src.documentary.flow_pack import export_flow_pack

    export_flow_pack(p, use_llm=False, rebuild_visuals=True)
    plan = update_visual_description(p["id"], 1, "2017 Manhattan packed coworking floor walkthrough")
    v1 = next(v for v in plan["visuals"] if int(v["number"]) == 1)
    assert "coworking" in v1["description"]
    # If visual 1 is Flow, its batch prompt must refresh locally
    if v1.get("visual_type") == "FLOW_REENACTMENT":
        assert any("coworking" in (b.get("prompt") or "") for b in plan.get("flow_batches") or [])
    sync = sync_ready_from_disk(p["id"])
    assert sync["expected"] >= 1
    assert len(sync["missing"]) == sync["expected"]


def test_story_beat_relationship():
    from src.documentary.visual_plan import map_story_beat

    beats = [
        {"id": 1, "event": "SoftBank invests billions in WeWork"},
        {"id": 2, "event": "S-1 filing reveals losses"},
    ]
    assert map_story_beat("SoftBank poured billions into WeWork", beats, index=1) == "1"
    assert map_story_beat("The S-1 filing showed devastating losses", beats, index=2) == "2"


def test_migration_existing_export(tmp_projects):
    p = create_project("Migrate", title="Migrate", research_notes="notes")
    p["script"] = ("A true company story with Adam Neumann and SoftBank and an IPO. " * 40)
    p = approve_script(p)
    from src.documentary.flow_pack import export_flow_pack, load_shot_list

    export_flow_pack(p, use_llm=False, rebuild_visuals=True)
    sl = load_shot_list(p["id"])
    assert sl.get("shot_count", 0) >= 1
    assert "flow_batches" in sl or (sl.get("batches") is not None)
    assert (project_dir(p["id"]) / "flow-pack" / "visual-plan.json").exists()
