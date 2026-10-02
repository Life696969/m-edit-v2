#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import read_json

# Fixed safety invariants: no config can skip the whole-video review or merge the finals unasked.
REQUIRED_TRUE = ('preview_approval_required', 'merge_requires_explicit_request')

RULE_RANGES = {
    'camera_pulse_seconds': (0.25, 3.0),
    'camera_scale_min': (1.0, 1.3),
    'camera_scale_max': (1.0, 1.3),
    'camera_drift_max': (0.0, 0.05),
    'camera_min_move': (0.0, 0.05),
    'edge_margin_px': (0, 200),
    'cutaway_share_max': (0.0, 0.8),
    'cutaway_max_seconds': (0.5, 30.0),
    'max_caption_words': (1, 12),
    'max_caption_hold_seconds': (0.3, 10.0),
    'max_anchor_hits': (0, 5),
    'caption_mouth_gap_px': (0, 400),
    'card_eye_clearance_px': (0, 800),
}


def validate(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if config.get('schema_version') != 3:
        errors.append('schema_version must be 3 (m-edit 2.x)')
    if config.get('source_hash_mode') not in {'full', 'stat'}:
        errors.append('source_hash_mode must be full or stat')
    output_root = config.get('output_root')
    if not isinstance(output_root, str) or not output_root or Path(output_root).is_absolute() or '..' in Path(output_root).parts:
        errors.append('output_root must be a non-empty project-relative path without ..')
    workflow = config.get('workflow')
    if not isinstance(workflow, dict):
        errors.append('workflow must be an object')
    else:
        for field in REQUIRED_TRUE:
            if workflow.get(field) is not True:
                errors.append(f'workflow.{field} is a fixed safety invariant and must be true')
    direction = config.get('direction', {})
    if not isinstance(direction, dict):
        errors.append('direction must be an object')
    else:
        high, low = direction.get('max_questions', 5), direction.get('min_questions', 4)
        if not isinstance(high, int) or not 1 <= high <= 5:
            errors.append('direction.max_questions must be an integer from 1 to 5')
        if not isinstance(low, int) or not 1 <= low <= 5 or (isinstance(high, int) and low > high):
            errors.append('direction.min_questions must be an integer from 1 to max_questions')
    rules = config.get('edit_rules', {})
    if not isinstance(rules, dict):
        errors.append('edit_rules must be an object')
    else:
        for field, (lo, hi) in RULE_RANGES.items():
            value = rules.get(field)
            if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not lo <= value <= hi):
                errors.append(f'edit_rules.{field} must be between {lo} and {hi}')
        if rules.get('camera_scale_min', 1.03) > rules.get('camera_scale_max', 1.075):
            errors.append('edit_rules.camera_scale_min must not exceed camera_scale_max')
        if rules.get('background', 'preserve') not in {'preserve', 'allow-replace'}:
            errors.append('edit_rules.background must be "preserve" or "allow-replace"')
    depth = config.get('depth', {})
    if isinstance(depth, dict) and depth.get('matte_provider', 'none') not in {'none', 'rvm-onnx', 'precomputed'}:
        errors.append('depth.matte_provider must be "none", "rvm-onnx" or "precomputed"')
    render = config.get('render')
    if not isinstance(render, dict):
        errors.append('render must be an object')
    else:
        ssim = render.get('fidelity_min_ssim')
        if not isinstance(ssim, (int, float)) or not 0 <= ssim <= 1:
            errors.append('render.fidelity_min_ssim must be between 0 and 1')
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description='Validate an m-edit config and its fixed safety invariants.')
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    path = Path(args.config).expanduser().resolve(strict=True)
    errors = validate(read_json(path))
    if errors:
        raise SystemExit('\n'.join(f'- {error}' for error in errors))
    print(f'valid: {path}')


if __name__ == '__main__':
    main()
