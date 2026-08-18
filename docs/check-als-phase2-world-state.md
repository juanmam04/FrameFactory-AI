# Check ALS — Phase 2 contract (do not implement full logic in Phase 0/1)

`world_state` will be the **source of truth** for each Check episode.

When Phase 2 lands, all of the following MUST derive from `world_state` (or fail QC if they contradict it):

- beats
- script facts
- age / dates / timeline
- cash, revenue, net worth, company valuation, employees
- assets / vehicles / homes
- locations
- metric overlays
- visual prompts (avatar + place continuity)

Concept `world_seeds` from Phase 1 are only **inputs** to initialize that world state — not a parallel truth.
