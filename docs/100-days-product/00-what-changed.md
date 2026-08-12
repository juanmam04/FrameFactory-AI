# 00 — What changed

Branch: `feature/100-days-daily-workflow` (based on `origin/dev` Documentary MVP).

## Product shift

Documentary is no longer an isolated technical tool. A **Session** with `workflow=documentary` is the **channel**. Episodes are Documentary projects linked to that session.

## Added

- `src/documentary/channel.py` — profile helpers + **100 Days** template profile
- `src/documentary/ideas.py` — 5 daily ideas (LLM or offline mocks), de-dupe vs prior videos
- Reworked `src/documentary_ui.py` — Home → Ideas → Research → Script → Flow → Images → Voice → Render → Done
- Session seed for **100 Days — Business Documentaries**
- Documentary-first sidebar when session is documentary
- Auto shot status from imported `NNN.png`
- `docs/100-days-product/`
- `scripts/smoke_daily_workflow.py`

## Connected

- Script generation now injects `creative_profile_snapshot` + idea brief via `creative_context`
- Visual / Flow global style from profile `visual.*` (no stickman base bleed)
- Projects store `session_id`, `episode_number`, `idea`, `creative_profile_snapshot`

## Not built (by design)

Research agent, Flow automation, YouTube upload, thumbnails, subtitle overhaul, SaaS.
