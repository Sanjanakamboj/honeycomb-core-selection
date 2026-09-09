"""Canonical candidate honeycomb cores for the Milestone 2 trade framework.

============================================================================
ILLUSTRATIVE HONEYCOMB-EQUIVALENT CANDIDATES
============================================================================

**No value in this module is a manufacturer datasheet value.** Every density and
shear modulus below is a representative engineering-study input, chosen only to
span a realistic range of density and directional shear stiffness so that the
trade framework can be exercised and verified.

Specifically, these values are:

* NOT manufacturer data,
* NOT design allowables,
* NOT qualification or certification data,
* NOT a substitute for a datasheet in any real selection.

Every candidate carries an explicit ``source_note`` recording this. No candidate
in this module mixes sourced and illustrative numbers: the whole set is
illustrative, uniformly and visibly. If sourced data is introduced in a later
milestone it must be added with its own provenance note, and the two must never
be silently blended.

Magnitudes were checked against the Milestone 1 study basis before being fixed,
to confirm the set produces a useful, non-pathological comparison (core shear
deflection between roughly 1 % and 17 % of total deflection at a 20 mm core
depth) rather than a degenerate one.

Families
--------
``aluminium-honeycomb-equivalent``
    Higher shear stiffness for a given density, strongly anisotropic
    (``G_L / G_W`` around 2.5-2.8).

``aramid-paper-honeycomb-equivalent``
    Lower shear stiffness at comparable density and less anisotropic. Included
    so the trade is not a single monotonic family, and so the
    shear-stiffness-to-density indicator has something real to discriminate.

Only density and the two transverse shear moduli are represented. No strength,
compression modulus, temperature dependence or environmental knockdown exists in
this database.
"""

from __future__ import annotations

from .materials import OrthotropicCoreMaterial

__all__ = ["CANDIDATE_CORES", "core_names", "get_core", "ILLUSTRATIVE_DATA_NOTE"]

ILLUSTRATIVE_DATA_NOTE = (
    "ILLUSTRATIVE HONEYCOMB-EQUIVALENT VALUE - representative engineering-study "
    "input only; not a manufacturer datasheet value, not a design allowable, "
    "not qualification data."
)

_ALUMINIUM = "aluminium-honeycomb-equivalent"
_ARAMID = "aramid-paper-honeycomb-equivalent"

MPA = 1.0e6

#: Candidate cores, in a fixed, deterministic order (ascending density).
CANDIDATE_CORES: tuple[OrthotropicCoreMaterial, ...] = (
    OrthotropicCoreMaterial(
        name="HC-AL-30",
        density=30.0,
        shear_modulus_L=20.0 * MPA,
        shear_modulus_W=8.0 * MPA,
        family=_ALUMINIUM,
        notes="Low density, low shear stiffness; lightest candidate, softest core.",
        source_note=ILLUSTRATIVE_DATA_NOTE,
    ),
    OrthotropicCoreMaterial(
        name="HC-AL-45",
        density=45.0,
        shear_modulus_L=40.0 * MPA,
        shear_modulus_W=15.0 * MPA,
        family=_ALUMINIUM,
        notes="Mid density, mid shear stiffness.",
        source_note=ILLUSTRATIVE_DATA_NOTE,
    ),
    OrthotropicCoreMaterial(
        name="HC-AR-48",
        density=48.0,
        shear_modulus_L=30.0 * MPA,
        shear_modulus_W=16.0 * MPA,
        family=_ARAMID,
        notes=(
            "Different family: comparable density to HC-AL-45 but lower shear "
            "stiffness and weaker anisotropy (G_L/G_W ~ 1.9)."
        ),
        source_note=ILLUSTRATIVE_DATA_NOTE,
    ),
    OrthotropicCoreMaterial(
        name="HC-AL-60",
        density=60.0,
        shear_modulus_L=70.0 * MPA,
        shear_modulus_W=25.0 * MPA,
        family=_ALUMINIUM,
        notes="Higher density, higher shear stiffness.",
        source_note=ILLUSTRATIVE_DATA_NOTE,
    ),
    OrthotropicCoreMaterial(
        name="HC-AL-80",
        density=80.0,
        shear_modulus_L=120.0 * MPA,
        shear_modulus_W=45.0 * MPA,
        family=_ALUMINIUM,
        notes="Heaviest and shear-stiffest candidate.",
        source_note=ILLUSTRATIVE_DATA_NOTE,
    ),
)


def core_names() -> tuple[str, ...]:
    """Candidate names in database order."""
    return tuple(core.name for core in CANDIDATE_CORES)


def get_core(name: str) -> OrthotropicCoreMaterial:
    """Look up a candidate by exact name."""
    for core in CANDIDATE_CORES:
        if core.name == name:
            return core
    raise KeyError(f"unknown candidate core {name!r}; available: {list(core_names())}")
