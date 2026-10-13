# Roadmap

## Shipped in 2.1

- **Clean final delivery**: no metadata or encoder traces, top-notch single-encode audio, and a two-round check before a final is recorded. See [`docs/CLEAN-DELIVERY.md`](docs/CLEAN-DELIVERY.md).

## Before stable 1.0

- run pressure evals on Claude Code and Codex with real video fixtures
- complete several end-to-end edits across talking-head, tutorial, podcast, and product-demo modes
- validate PowerShell installation on Windows
- validate Claude marketplace installation with `claude plugin validate`
- document measured trigger precision and workflow compliance

## Later

- additional local transcription adapters
- richer caption collision testing
- optional automated safe-zone detection
- more render-fidelity metrics
- community illustration presets kept separate from the generic core

## After 2.0

These are candidates, not commitments; see `ARCHITECTURE.md` for what would justify each.

* **Music bed builder:** drop and impact detection, and alignment of the track to the hero word.
* **A face-tracking adapter** writing face rows into `edit.json`.
* **Bundled matte-provider scripts** (RVM ONNX), with licence review.
* **More illustration presets** in the starter registry.
* **An optional OpenMontage render adapter.**
* **Black-box pressure evals** on Claude Code and Codex, with real footage.
