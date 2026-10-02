# Camera pulse

A subtle camera move on every pulse (default 1 s). A locked-off talking head held still reads as a photo with a voice over it. A change of framing every second gives the viewer a reason to keep watching that they cannot name.

**Felt, not seen.** If a viewer could describe it ("it zooms in"), it is too big.

This is a camera rhythm, not a visual reset. It does not conflict with "no visual resets on an arbitrary timer": cards and cutaways still follow the content.

## How it is built

* **Keys:** one key per pulse (`edit_rules.camera_pulse_seconds`), plus:
  * one at the clip's end;
  * punch keys on the words that matter;
  * a pair of keys at every jump cut.
* **Sine ease** in and out between keys, `e = 0.5 − 0.5·cos(πu)`. Each move leaves from rest and settles exactly on its key, and the settle is what registers. Linear drift becomes invisible after two seconds.
* **Bands:** the scale alternates between a low band and a high band. No two consecutive moves are the same size; a regular in-out becomes a metronome, which is as invisible as no motion.
* **Bounds:** scale is in `camera_scale_min..max` (default 1.03–1.075). Drift is ≤ `camera_drift_max` (default 0.6% of the frame).
* **Punch keys** go on emphasis words, near the top of the scale band. Put a quieter lead key about 80 ms before each.
* **Jump cuts** get an instant reframe: a visible scale step across the cut hides the jump.
* **Shakes:** a short decaying shake (≤ 4 px, ~0.25 s) on the hero moment only, plus at most one or two other hard beats.
* **The camera moves the footage only.** Captions, cards and graphics live in screen space. If the type drifts with the picture, the whole frame looks like it is sliding.

## Generate it

```bash
m-edit camera --duration 6.5 --punch 0.0 2.2 4.22 --jump 3.1 --seed 7 [--shake-px 4.5] [--config .m-edit/config.json]
```

* The generator is deterministic for a given seed. Its output passes the audit by construction, including with a shake margin.
* Paste the keys into `edit.json` for that clip.
* If the footage already has handheld motion, lower `camera_scale_max` and `camera_drift_max`. Do not drop the pulse.

## Enforced by the audit

* A key at least every pulse.
* Keys span the whole clip.
* Scale and drift stay inside their bounds.
* **No frame edge is ever exposed**, shake included: `|x|·W + shake ≤ (s − 1)·W/2 − margin`, and likewise for y about the origin.
* Every move is large enough to be felt.
* No two consecutive moves are the same size.

## Keep captions and cards clear of the moving face

* Caption and card positions are measured against the **moved** frame, not the source.
* Solve each caption chunk's position from the tracked chin under that chunk's camera.
* Check card clearance against the highest point the eyes reach across the card's span.
* When face rows are present in `edit.json`, the audit checks both.
