# 04 — Image import

## Bulk

Point Documentary → Images at a folder containing:

```text
001.png
002.png
…
```

Maps to `SHOT_001` … Validates missing, duplicates, unknown numbers, invalid names, small/portrait dimensions.

Report example: `63 / 67 READY` + missing list. Does not hard-block the project.

## Replace

Upload or path → overwrites `images/038.png` without regenerating voice (FF100-P0-004 minimum). Clears assembly/render checkpoints so you re-render only.
