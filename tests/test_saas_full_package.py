from src.saas_full_package import blocks_to_scenes_export


def test_blocks_to_scenes_export_duration_bounds():
    blocks = [
        {"id": "s1", "text": "Hola.", "visual_direction": "calle", "b_roll_suggestion": "noche"},
        {"id": "s2", "text": " ".join(["palabra"] * 200), "visual_direction": "", "b_roll_suggestion": ""},
    ]
    out = blocks_to_scenes_export(blocks, words_per_minute=140.0)
    assert len(out) == 2
    assert out[0]["duration"] >= 2.0
    assert out[0]["visual"]
    assert out[1]["duration"] <= 55.0
