# Release process

1. Update `VERSION`, skill metadata, plugin manifest, marketplace entry, and changelog.
2. Run all unit/integration tests on Linux, macOS, and Windows.
3. Run `scripts/validate_skills.py` and official `skills-ref validate` when available.
4. Run the release audit and personal-data/secret scan.
5. Run model pressure evals on supported agents.
6. Test Claude plugin validation and local installation.
7. Build the deterministic ZIP and checksum.
8. Tag the exact commit and attach release artifacts.
