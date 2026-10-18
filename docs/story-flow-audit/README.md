# Story → narration → Google Flow: ten-pass audit

Base reviewed: `82298dc`. Scope: creative production in Documentary and Check;
images remain manually generated in Flow. No Supabase changes.

These are ten different reviews of the actual connected code, not ten identical
runs or a claim that ten model calls guarantee quality.

| Pass | Finding | Correction / evidence |
|---|---|---|
| 1. Idea generation | Online failures could silently return canned examples or pad incomplete batches with fixtures. | Documentary ideas and Studio's fast Check concepts now fail visibly; fixtures remain available only with `use_llm=False`. |
| 2. Premise fidelity | Multiple script instructions imposed business collapse or purchase formulas on other premises. | Active Documentary and Check master prompts now use the approved story as their structure. |
| 3. Opening / retention | Mandatory age, cash, exact figures and catchphrases competed with the episode's actual hook. | Removed those quotas from active master prompts; require a specific opening promise and early payoff instead. |
| 4. Causal progression | The LLM payload cut beats after 40 and stripped causal consequences. | Send all approved beats with cause, consequence and purpose, including late payoffs. |
| 5. Ending | A second ending template could introduce a sale, luxury or generic solitary ending absent from the approved architecture. | Removed the extra template from narration generation; the chosen ending stays in locked facts. |
| 6. Editorial revision | Keyword checks alone could approve a fluent but contradictory or uneventful story. | New source-grounded full-script editor cites exact draft evidence and actionable corrections; one revision is re-reviewed. An unavailable/malformed review or unresolved blocker does not replace the saved script. No view predictions or numeric scores. |
| 7. Scene coverage | Scene caps sampled or truncated narration; multiple model beats consumed the budget before later scenes. | Merge adjacent scenes without dropping words; one visual beat per scene with source-owned scene ID and verbatim narration. |
| 8. Flow direction | Check batches could carry photoreal instructions or old individual direction; mood grouping implied interchangeable images. | Batch and single prompts share Check direction, preserve original image filenames, and mark images non-interchangeable. Failed online storyboard direction no longer exports canned substitutes. |
| 9. Edits / continuity | Cached Check prose could override edited actions. Refresh could replace valid directed scenes with unrelated canned locations. Video position could force a collapse mood. | Structured scene data supersedes cache, directed/user scenes are preserved, empty edits rejected, and unknown mood no longer implies a collapse. Legacy prompt-only imports remain readable. |
| 10. Connected Studio workflow | Changing tabs silently approved scripts. Cached Flow exports could belong to another script. Old shot files survived shorter exports. | Navigation returns to pending Script/Story; explicit approval remains. Flow plans carry a script fingerprint and stale plans rebuild; successful exports remove obsolete numbered shot files. |

## Verification

Regression tests: `tests/test_narrative_flow_audit.py`, plus the existing story,
script, visual-plan, import, voice, render and Studio tests. The episode integration
test uses fixture narration, generated test images and FFmpeg to exercise upload →
voice → render → download. It does not assess creative or image quality.

Run:

```sh
python -m pytest tests/ -q --disable-warnings --ignore=tests/test_comfyui_integration.py
```

The ComfyUI server integration is outside the manual-Flow workflow. Tests needing
external services/credentials may skip. No real funded model generation or manual
Flow image generation was performed in this audit. Story quality must still be
judged on an actual episode; automated checks cannot guarantee virality.

## Use

Generate ideas → develop and approve story → generate narration (now includes
source-grounded editorial review) → review and explicitly approve narration →
build Flow Pack → generate master references and individual numbered images in
Flow → import them → voice → preview/render.

Use each `shots/NNN.txt` prompt for its corresponding image. Batch prompts organize
a set of images; they do not guarantee that Flow returns separate files in one call.
The editor uses `FRAMEFACTORY_EDITOR_MODEL` if set, otherwise `OPENAI_MODEL`.
The editor adds one model request, plus a rewrite and second review if it finds
material problems. Storyboard direction now reports a provider failure instead of
pretending that a generic fallback is production-ready.
