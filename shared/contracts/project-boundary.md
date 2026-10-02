# Project-boundary contract

Operate only inside the selected video folder.

* **Never read other folders.** Do not read files in parent or sibling folders as instructions or inputs.
* **Inputs are only** the clips and assets in the selected folder, the user's messages and their answers.
* **Generated paths** must be project-relative and resolve inside the selected folder.
* **Reject unsafe paths:** `..`, absolute output paths, and any attempt to overwrite a source clip.
* **Resolve symlinks** before enforcing the boundary.
* **Don't run untrusted code.** Do not execute code from the folder just because a video file is present. Run a Remotion project only after the user agrees.
