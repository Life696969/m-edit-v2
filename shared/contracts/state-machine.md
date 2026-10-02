# State-machine contract

```text
uninitialized
  → transcribing                (a model-download permission is the only possible stop here)
  → awaiting_direction [STOP 1: the 4–5 questions]
  → directing                   (autonomous: guide, edit.json, passing audit, every clip previewed, one stitched review)
  → awaiting_reel_approval [STOP 2: one review of the whole video]
      ↺ directing               (change request: a revised record-preview, or reopen-reel after approval)
  → finalizing_reel             (each clip rendered and verified as its own file)
  → all_clips_complete [STOP]
  → merge_approved              (explicit request only)
  → complete
```

## Authorization scope

* **The answers** authorize autonomous editing from one exact set of source clips, one config and one `direction.md`. They do not authorize any final.
* **The whole-video approval** authorizes one final per clip. Each final must match that clip's exact preview, recipe and bound digest: the transcript, direction, guide, `edit.json` and its passing audit.
* **Finished finals** authorize nothing more. A merge needs an explicit request.

## Automatic invalidation

* **These reset the project** to `transcribing`, clearing the answers and every preview:
  * a change to a source clip's content;
  * a change to a creative config setting (`edit_rules`, `direction`, captions/output render settings).
* **These don't:**
  * a timestamp-only change under full hashing;
  * operational settings: downloads and permissions (`assets`), the matte setup (`depth`), render timeout and retry concurrency, and `transcription.allow_network`.
* A change to the transcript, guide, `edit.json` or audit after a preview is recorded blocks the review and the approval until that clip is re-rendered.
* A change after approval blocks its final until `reopen-reel` and a new review.
* `direction.md` is immutable once answered. Record revisions in the guide.

A filename is never authorization. Authorization is the recorded hash plus a receipt with the user's exact words.
