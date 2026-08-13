# 03 — Ideas

`generate_story_ideas(profile, prior_videos=..., memory_summary=..., count=5)`

Each idea:

- title_concept, story, hook, why_it_works, content_pillar
- visual_potential, research_risk, primary_entity

Prior videos (same `session_id`) are passed so the same company/story is not re-proposed (offline mocks + LLM instruction).

UI: **Choose** · **Generate 5 more** · **I already have a topic**
