from pathlib import Path

from src.documentary.formats.check_als.production_batch import export_all_stills_pack, export_p0_p1_pack, export_production_packs


def test_export_p0_p1_pack_pilot():
    out = export_p0_p1_pack("pilot-fase2-basket")
    root = Path(out["path"])
    assert out["count"] == 24
    assert len(list((root / "prompts").glob("*.txt"))) == 24
    assert (root / "manifest.json").is_file()
    manifest = __import__("json").loads((root / "manifest.json").read_text())
    assert "order of generation" in manifest["note"].lower() or "all-stills" in manifest["note"].lower()
    sample = (root / "prompts" / "007.txt").read_text(encoding="utf-8")
    assert "shot_id: 007" in sample
    assert "requires_own_still: true" in sample
    assert "---" in sample


def test_export_all_stills_pack_pilot():
    out = export_all_stills_pack("pilot-fase2-basket")
    root = Path(out["path"])
    assert out["count"] == 100
    assert out["prompts_ready"] == 100
    txts = sorted((root / "prompts").glob("*.txt"))
    assert len(txts) == 100
    assert txts[0].name == "001.txt"
    assert txts[-1].name == "100.txt"
    manifest = __import__("json").loads((root / "manifest.json").read_text())
    assert manifest["total_prompts"] == 100
    assert manifest["items"][0]["requires_own_still"] is True
    item99 = next(x for x in manifest["items"] if x["shot_id"] == "100")
    assert item99["priority"] in ("P0", "P1", "P2", "P3")
    body = (root / "prompts" / "100.txt").read_text(encoding="utf-8")
    assert len(body) > 200


def test_export_production_packs_both():
    out = export_production_packs("pilot-fase2-basket")
    assert out["p0_p1"]["count"] == 24
    assert out["all_stills"]["count"] == 100
