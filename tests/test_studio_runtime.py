"""Production regressions: workspace routing and FFmpeg without a system install."""
from pathlib import Path


def test_projects_stay_in_configured_workspace(monkeypatch, tmp_path):
    from src.documentary import project

    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    monkeypatch.delenv("FRAMEFACTORY_PROJECTS_DIR", raising=False)
    monkeypatch.setenv("FRAMEFACTORY_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(project, "PROJECTS_ROOT", project.PROJECTS_ROOT)
    p = project.create_project("Workspace regression", project_id="workspace-regression")
    assert (tmp_path / "projects" / p["id"] / "project.json").is_file()
    assert project.load_project(p["id"])["topic"] == "Workspace regression"


def test_ffmpeg_bundled_fallback_preserves_home(monkeypatch):
    import os
    import imageio_ffmpeg
    from src import video_assembler

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(video_assembler.shutil, "which", lambda _: None)
    before = os.environ.get("HOME")
    executable = video_assembler.ffmpeg_exe()
    assert executable == imageio_ffmpeg.get_ffmpeg_exe()
    assert Path(executable).is_file()
    assert os.environ.get("HOME") == before
