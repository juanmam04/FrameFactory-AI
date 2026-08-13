"""Regression tests: Documentary script must never accept Reddit/Spanish contamination."""
from __future__ import annotations

import pytest

from src.documentary.channel import business_documentary_profile, documentary_script_context
from src.documentary.project import create_project, load_project
from src.documentary.script_service import (
    TEMPLATE_ID,
    build_documentary_tema,
    generate_documentary_script,
)
from src.documentary.script_validation import validate_documentary_script
from src.script_generator import generar_guion


@pytest.fixture()
def tmp_projects(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    return root


def test_a_wework_offline_mock_is_english_third_person(tmp_projects):
    prof = business_documentary_profile()
    p = create_project(
        "WeWork's rise from coworking startup to one of the world's most valuable private companies — and the IPO filing that changed everything.",
        title="THE $47 BILLION COMPANY THAT ALMOST COLLAPSED OVERNIGHT",
        project_id="wework-script-a",
        target_words=400,
        research_notes=(
            "WeWork was co-founded by Adam Neumann. SoftBank was a major investor. "
            "The 2019 IPO attempt collapsed amid governance and valuation concerns. "
            "UNKNOWN: exact private valuation peaks — do not invent."
        ),
        sources=["Public reporting on WeWork IPO attempt (2019)"],
        creative_profile=prof,
        idea={
            "title_concept": "THE $47 BILLION COMPANY THAT ALMOST COLLAPSED OVERNIGHT",
            "primary_entity": "WeWork",
            "story": "WeWork rise and IPO collapse",
        },
        language="en",
    )
    generate_documentary_script(p, use_llm=False)
    p = load_project("wework-script-a")
    script = p["script"]
    ok, reasons = validate_documentary_script(script, language="en", target_words=400, allow_short_if_thin_research=True)
    assert ok, reasons
    assert "no debí" not in script.lower()
    assert "working title:" not in script.lower()
    meta = (tmp_projects / "wework-script-a" / "script" / "script_meta.json").read_text(encoding="utf-8")
    assert TEMPLATE_ID in meta


def test_b_reject_reddit_contamination():
    bad = (
        "No debí ignorarlo.\n\n"
        "WeWork's rise...\n\n"
        "Working title: THE $47 BILLION...\n\n"
        "El primer detalle fue pequeño. Lo dejé pasar.\n"
        "Cada vez que pienso en lo que encontré después, me cuesta respirar.\n"
        "La tensión subía y yo seguía adentro, sin poder parar."
    )
    ok, reasons = validate_documentary_script(bad, language="en", target_words=1500)
    assert not ok
    assert any("confession" in r.lower() or "spanish" in r.lower() or "storytime" in r.lower() for r in reasons)


def test_c_reject_first_person_narrator():
    bad = (
        "I walked into the office and immediately knew something was wrong. "
        "I couldn't believe what I discovered next. My friend told me to leave. "
        "I kept digging anyway."
    )
    ok, reasons = validate_documentary_script(bad, language="en", target_words=100, allow_short_if_thin_research=True)
    assert not ok
    assert any("first-person" in r.lower() for r in reasons)


def test_d_legitimate_quote_with_i_allowed():
    good = (
        "In 2019, WeWork filed paperwork for a public offering. "
        'Neumann later said, "I always believed we were building something that would last." '
        "Investors were not convinced. The IPO collapsed within weeks."
    )
    ok, reasons = validate_documentary_script(good, language="en", target_words=50, allow_short_if_thin_research=True)
    assert ok, reasons


def test_e_spanish_contamination_on_english_session():
    bad = (
        "El imperio de WeWork creció sin control. La empresa era enorme y los inversores "
        "creían en el sueño. Pero los números no cerraban y el fracaso fue inevitable. "
        "La gente no sabía qué hacer después de la caída."
    )
    ok, reasons = validate_documentary_script(bad, language="en", target_words=40, allow_short_if_thin_research=True)
    assert not ok
    assert any("spanish" in r.lower() for r in reasons)


def test_f_metadata_leak_invalid():
    bad = (
        "Working title: THE $47 BILLION COMPANY\n\n"
        "In January 2019, WeWork looked unstoppable. SoftBank had poured billions into the company. "
        "Then the S-1 filing exposed how fragile the story really was."
    )
    ok, reasons = validate_documentary_script(bad, language="en", target_words=40, allow_short_if_thin_research=True)
    assert not ok
    assert any("metadata" in r.lower() for r in reasons)


def test_documentary_never_uses_spanish_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY|Documentary script"):
        generar_guion(
            "SUBJECT:\nWeWork\n\nRESEARCH NOTES:\nSoftBank invested.\n\nSOURCES:\n- mock",
            target_words=400,
            plantilla="business_documentary_en",
            creative_context="documentary",
            force_este_eres_tu_opening=False,
        )


def test_tema_has_no_working_title_label(tmp_projects):
    p = create_project(
        "WeWork story",
        project_id="tema-x",
        idea={"title_concept": "BIG TITLE", "story": "WeWork story", "hook": "In 2019..."},
        research_notes="SoftBank invested. IPO collapsed in 2019.",
    )
    tema = build_documentary_tema(p)
    assert "Working title:" not in tema
    assert "SUBJECT:" in tema
    ctx = documentary_script_context(business_documentary_profile(), idea=p["idea"])
    assert "reddit_dark_storytime" in ctx  # listed as forbidden_legacy
    assert "business_documentary" in ctx


def test_abrupt_ending_detected_without_ending_state():
    from src.documentary.script_quality import ending_is_abrupt

    cliff = (
        "In 2019 the IPO was pulled.\n\n"
        "SoftBank stepped in with a bailout.\n\n"
        "The vibrant spaces now faced an uncertain future. "
        "WeWork's struggle highlighted the vulnerabilities inherent in its business model."
    )
    landed = (
        cliff
        + "\n\nIn 2021 WeWork went public through a SPAC merger that valued the company at about $9 billion. "
        "The $47 billion company had become a $9 billion listing."
    )
    state = "WeWork goes public via a SPAC merger in 2021, valuing the company at approximately $9 billion."
    assert ending_is_abrupt(cliff, state)
    assert not ending_is_abrupt(landed, state)
