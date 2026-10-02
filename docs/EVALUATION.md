# Evaluation

m-edit uses three test layers.

## Deterministic tests

Unit and integration tests cover state transitions, path boundaries, source mutation, recipe drift, approval evidence, media verification, installers, and release sanitization.

## Trigger tests

`tests/test_triggering.py` checks that skill descriptions contain concrete user-intent terms without becoming duplicates. This is a static guard, not a model-behavior guarantee.

## Model pressure evals

`evals/cases.json` contains adversarial scenarios such as transcript bypass, vague approval, cross-clip leakage, changed code after preview approval, unauthorized merge, and unavailable transcription. `evals/run_agent_evals.py` can drive a compatible headless agent command and save transcripts for rubric review.

A release should not claim model-behavior maturity until the eval set passes on the target agents and representative real video projects.
