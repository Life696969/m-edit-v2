# Contributing

Thanks for improving m-edit.

## Principles

- Keep the public package generic.
- Never bundle a creator's personal style, examples or preferences; m-edit stays generic and self-contained.
- Convert mechanical rules into tests/scripts when possible.
- Preserve progressive disclosure: specialist skills stay focused and load references only when needed.
- Do not weaken transcript, preview, source-preservation, verification, or explicit-merge gates.

## Change process

1. Open an issue for material workflow or compatibility changes.
2. Add a failing deterministic test or pressure scenario first.
3. Implement the smallest change that closes the failure.
4. Run all tests and the release audit.
5. Update documentation and changelog.
6. Submit a focused pull request with evidence.

## Commands

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/validate_skills.py
python3 shared/scripts/release_audit.py --root .
```

For skill-behavior changes, add or update `evals/cases.json` and include target-agent transcripts when available.
