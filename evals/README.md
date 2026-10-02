# Agent behavior evaluations

The deterministic test suite proves state, integrity, installer, and media-tool behavior. These cases test whether a real coding agent discovers and follows the skills under pressure.

Provide a non-interactive command template containing `{prompt}`:

```bash
M_EDIT_EVAL_COMMAND='your-agent-command --prompt {prompt}' \
  python3 evals/run_agent_evals.py
```

Run the suite against every supported host before promoting a release candidate to stable. Store result JSON as a release artifact. Do not treat prose-only scenarios as evidence; retain the actual command output.
