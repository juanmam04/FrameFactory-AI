# Documentary 100 Days — Implementation

MVP that turns FrameFactory into a **publisher toolchain** for daily English business documentaries, with **Google Flow** as the manual image step.

## Docs

| File | Content |
|------|---------|
| [01-architecture-changes.md](./01-architecture-changes.md) | What changed |
| [02-documentary-workflow.md](./02-documentary-workflow.md) | End-to-end workflow |
| [03-flow-workspace.md](./03-flow-workspace.md) | Flow Pack UI |
| [04-image-import.md](./04-image-import.md) | Bulk import / replace |
| [05-render-pipeline.md](./05-render-pipeline.md) | Voice + assemble |
| [06-testing.md](./06-testing.md) | Tests + dogfood |
| [07-known-limitations.md](./07-known-limitations.md) | Gaps |
| [08-video-1-runbook.md](./08-video-1-runbook.md) | **Produce Video 1** |

## Quick start

```bash
./run.sh
# Sidebar → Documentary
```

Or dogfood offline:

```bash
venv/bin/python scripts/dogfood_100_days_test.py
```
