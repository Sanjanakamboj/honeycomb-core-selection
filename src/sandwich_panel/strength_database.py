"""Illustrative strength records aligned one-to-one with the Milestone 2 candidates.

============================================================================
ILLUSTRATIVE STRENGTH INPUT - NOT MANUFACTURER ALLOWABLE
============================================================================

The Milestone 2 stiffness database is entirely illustrative, and so is this one.
No verifiable manufacturer strength data was obtained, so every value below is a
representative engineering-study input:

* NOT a manufacturer allowable,
* NOT a design allowable or A/B-basis value,
* NOT qualification or certification data,
* NOT a substitute for a datasheet in any real selection.

Sourced and illustrative values are never blended. If sourced strengths are
introduced later they must arrive with their own provenance note, and the two
must remain separately identifiable.

Magnitudes were screened against the actual demand BEFORE being fixed. At the
50 N study load the panel carries an average core shear stress of only 2.5 kPa,
so realistic honeycomb shear strengths (hundreds of kPa to several MPa) leave the
core very far from governing. Those realistic values were kept: the strengths
were deliberately NOT reduced to manufacture a failure or a preferred candidate.
The resulting finding - that this panel is stiffness-critical, not
strength-critical - is reported as found.

Ordering matches :data:`sandwich_panel.core_database.CANDIDATE_CORES` exactly,
one strength record per elastic candidate, no extras.
"""

from __future__ import annotations

from .core_database import CANDIDATE_CORES
from .strength import FaceStrength, OrthotropicCoreStrength

__all__ = [
    "ILLUSTRATIVE_STRENGTH_NOTE",
    "ILLUSTRATIVE_FACE_STRENGTH",
    "CANDIDATE_CORE_STRENGTHS",
    "core_strength_names",
    "get_core_strength",
]

ILLUSTRATIVE_STRENGTH_NOTE = (
    "ILLUSTRATIVE STRENGTH INPUT - NOT MANUFACTURER ALLOWABLE; representative "
    "engineering-study input only, not a design allowable and not qualification data."
)

MPA = 1.0e6

#: Illustrative face-sheet yield strength for the Milestone 1 aluminium-like face.
#: No specific alloy is claimed - the elastic face material was never tied to one.
ILLUSTRATIVE_FACE_STRENGTH = FaceStrength(
    name="Illustrative aluminium-like face sheet",
    yield_strength=270.0 * MPA,
    source_note=ILLUSTRATIVE_STRENGTH_NOTE,
    notes=(
        "Illustrative face-sheet yield strength of an aluminium-like order of "
        "magnitude. No alloy is claimed. Used as the single allowable basis for "
        "Milestone 3; ultimate strength is deliberately not supplied."
    ),
)

#: Core shear strengths, in the same order as CANDIDATE_CORES.
CANDIDATE_CORE_STRENGTHS: tuple[OrthotropicCoreStrength, ...] = (
    OrthotropicCoreStrength(
        name="HC-AL-30",
        shear_strength_L=0.90 * MPA,
        shear_strength_W=0.55 * MPA,
        source_note=ILLUSTRATIVE_STRENGTH_NOTE,
        notes="Lightest candidate; lowest shear strength in both directions.",
    ),
    OrthotropicCoreStrength(
        name="HC-AL-45",
        shear_strength_L=1.60 * MPA,
        shear_strength_W=0.95 * MPA,
        source_note=ILLUSTRATIVE_STRENGTH_NOTE,
        notes="Mid-density aluminium-equivalent.",
    ),
    OrthotropicCoreStrength(
        name="HC-AR-48",
        shear_strength_L=1.20 * MPA,
        shear_strength_W=0.70 * MPA,
        source_note=ILLUSTRATIVE_STRENGTH_NOTE,
        notes=(
            "Aramid-paper-equivalent: weaker in shear than the aluminium-equivalent "
            "of comparable density, mirroring its lower shear stiffness."
        ),
    ),
    OrthotropicCoreStrength(
        name="HC-AL-60",
        shear_strength_L=2.40 * MPA,
        shear_strength_W=1.40 * MPA,
        source_note=ILLUSTRATIVE_STRENGTH_NOTE,
        notes="Higher density, higher shear strength.",
    ),
    OrthotropicCoreStrength(
        name="HC-AL-80",
        shear_strength_L=3.60 * MPA,
        shear_strength_W=2.10 * MPA,
        source_note=ILLUSTRATIVE_STRENGTH_NOTE,
        notes="Heaviest and strongest candidate in shear.",
    ),
)


def core_strength_names() -> tuple[str, ...]:
    """Strength-record names in database order."""
    return tuple(s.name for s in CANDIDATE_CORE_STRENGTHS)


def get_core_strength(name: str) -> OrthotropicCoreStrength:
    """Look up a candidate's strength record by exact name."""
    for strength in CANDIDATE_CORE_STRENGTHS:
        if strength.name == name:
            return strength
    raise KeyError(
        f"unknown candidate core strength {name!r}; available: {list(core_strength_names())}"
    )


# Fail loudly at import time if the two databases ever drift apart.
if core_strength_names() != tuple(c.name for c in CANDIDATE_CORES):  # pragma: no cover
    raise RuntimeError(
        "strength database is not aligned one-to-one with the elastic candidate database"
    )
