"""Generate and filter candidate rotation sequences."""
from __future__ import annotations

from itertools import product

from app.engine.rotation_scoring import passes_agronomic_rules


def generate_candidate_sequences(
    crops: dict[str, dict], sequence_length: int = 3, min_family_gap_years: int = 2
) -> list[list[dict]]:
    """All sequences of length `sequence_length` drawn from `crops` that
    pass the hard agronomic rules (e.g. no same family within the gap window).
    """
    named_crops = []
    for name, crop in crops.items():
        if name.startswith("_"):
            continue
        crop_with_name = {**crop, "_name": name}
        named_crops.append(crop_with_name)

    candidates = []
    for combo in product(named_crops, repeat=sequence_length):
        sequence = list(combo)
        if passes_agronomic_rules(sequence, min_family_gap_years):
            candidates.append(sequence)
    return candidates
