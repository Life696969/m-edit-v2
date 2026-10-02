# Quickstart

1. **Put your clips in a folder.** Raw talking-head takes, screen recordings, anything. Add music or logo files too if you want them used.
2. **Open that folder in your coding agent** (Claude Code or Codex) and say:

   > Edit my clips into a viral, professional reel.

   "video", "short" or "TikTok" work the same way.
3. **Answer the 4–5 questions.** Each has the agent's pick filled in, so "go" accepts them all.

The agent then edits everything and comes back with one full preview. Reply "approved" and you get one finished file per clip. Say "merge them" only if you want a single file.

## First time on a machine

Run `bin/m-edit doctor --project <folder>`. On Windows, run `python shared/scripts/cli.py doctor --project <folder>`. It lists anything missing (FFmpeg, Node and npm, a transcription model) with what to install.

The agent asks before downloading anything or installing packages.
