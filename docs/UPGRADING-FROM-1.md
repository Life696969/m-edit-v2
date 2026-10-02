# Upgrading from m-edit 1.x

## Workflow

| 1.x | 2.0 |
|---|---|
| Transcript approval, then optional story-cut approval, then a preview approval **per clip**, then a continuation **per clip** (~2 replies per clip) | **4–5 questions once**, then the whole edit, then **one** preview review, then all finals |
| Reads rule and profile Markdown files from the folder and its parents | Reads **no** instruction files; the look is proposed and confirmed in the questions |
| Captions-first, neutral | Illustrated cutaways, camera pulse, hero moment and sound design, with mechanical rules audited in code |

## Projects in progress

A `.m-edit/` folder created by 1.x is refused by 2.0, with a message:

* Finish it with your 1.x installation.
* Or rename `.m-edit/` and start again with 2.0. Your clips are untouched.

## Removed

* The `classic` gates:
  * `await-transcript`, `approve-transcript`
  * `record-guide`
  * `require-story-cut`, `approve-story-cut`
  * `await-preview`, `approve-preview`
  * `mark-final`
  * `advance-clip`
* `scan-instructions`, profiles, `instruction_policy` and `custom_profile_path`.
* The `m-edit-plan`, `m-edit-preview` and `m-edit-story-cut` skills.

## New

* **Workflow commands:**
  * `await-direction`
  * `record-direction`
  * `record-preview`
  * `await-reel-approval`
  * `approve-reel`
  * `mark-reel-final`
  * `reopen-reel`
* **Rules as code:** `camera`, `audit-edit`, `edit-props`.
* **Config sections:** `direction`, `edit_rules`, `depth`, plus the render timeout and retry settings.
* **Remotion starter:** the `ReelClip` composition.

## Unchanged

* Source preservation
* Hash-locked recipes
* Media verification
* Approval receipts
* Explicit merge
* No downloads without permission
