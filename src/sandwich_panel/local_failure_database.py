"""Illustrative core through-thickness compression records for the candidate set.

============================================================================
ILLUSTRATIVE LOCAL-FAILURE INPUT - NOT MANUFACTURER ALLOWABLE
============================================================================

As with the Milestone 2 stiffness data and the Milestone 3 strength data, no
verifiable manufacturer data was obtained, so every value here is a
representative engineering-study input: not a manufacturer allowable, not a
design allowable, not qualification data. Sourced and illustrative values are
never blended; each record carries an explicit ``source_note``.

Magnitudes were checked BEFORE being fixed (see the README Milestone 4 section).
Two physical trends are represented deliberately, and neither was chosen to make
any candidate win or lose:

* within the aluminium-equivalent family, compression strength and modulus both
  rise with density, and faster than linearly at the light end;
* the aramid-paper-equivalent candidate has a **much lower compression modulus**
  than an aluminium-equivalent core of similar density, because aramid paper is
  far less stiff than aluminium foil. Its compression strength is not
  correspondingly low.

That second trend matters: the wrinkling screening stress goes as ``E_c^(1/3)``,
so a low-modulus core is penalised in wrinkling even when its strength is
respectable. The consequence was not designed in - it fell out of the audit.

Ordering matches :data:`sandwich_panel.core_database.CANDIDATE_CORES` exactly,
one record per candidate, no extras.
"""

from __future__ import annotations

from .core_database import CANDIDATE_CORES
from .local_failure import CoreCompressionProperties

__all__ = [
    "ILLUSTRATIVE_LOCAL_NOTE",
    "CANDIDATE_CORE_COMPRESSION",
    "core_compression_names",
    "get_core_compression",
]

ILLUSTRATIVE_LOCAL_NOTE = (
    "ILLUSTRATIVE LOCAL-FAILURE INPUT - NOT MANUFACTURER ALLOWABLE; representative "
    "engineering-study input only, not a design allowable and not qualification data."
)

MPA = 1.0e6

#: Through-thickness compression records, in CANDIDATE_CORES order.
CANDIDATE_CORE_COMPRESSION: tuple[CoreCompressionProperties, ...] = (
    CoreCompressionProperties(
        name="HC-AL-30",
        compression_strength=1.20 * MPA,
        compression_modulus=300.0 * MPA,
        source_note=ILLUSTRATIVE_LOCAL_NOTE,
        notes="Lightest candidate: lowest crush strength and lowest aluminium-family modulus.",
    ),
    CoreCompressionProperties(
        name="HC-AL-45",
        compression_strength=2.40 * MPA,
        compression_modulus=700.0 * MPA,
        source_note=ILLUSTRATIVE_LOCAL_NOTE,
        notes="Mid-density aluminium-equivalent.",
    ),
    CoreCompressionProperties(
        name="HC-AR-48",
        compression_strength=2.00 * MPA,
        compression_modulus=130.0 * MPA,
        source_note=ILLUSTRATIVE_LOCAL_NOTE,
        notes=(
            "Aramid-paper-equivalent: respectable crush strength but a MUCH lower "
            "compression modulus than the aluminium-equivalent of similar density. "
            "This penalises it in the wrinkling screen, which goes as E_c^(1/3)."
        ),
    ),
    CoreCompressionProperties(
        name="HC-AL-60",
        compression_strength=4.00 * MPA,
        compression_modulus=1200.0 * MPA,
        source_note=ILLUSTRATIVE_LOCAL_NOTE,
        notes="Higher density, higher crush strength and modulus.",
    ),
    CoreCompressionProperties(
        name="HC-AL-80",
        compression_strength=6.50 * MPA,
        compression_modulus=2000.0 * MPA,
        source_note=ILLUSTRATIVE_LOCAL_NOTE,
        notes="Heaviest candidate: highest crush strength and modulus.",
    ),
)


def core_compression_names() -> tuple[str, ...]:
    """Compression-record names in database order."""
    return tuple(c.name for c in CANDIDATE_CORE_COMPRESSION)


def get_core_compression(name: str) -> CoreCompressionProperties:
    """Look up a candidate's compression record by exact name."""
    for record in CANDIDATE_CORE_COMPRESSION:
        if record.name == name:
            return record
    raise KeyError(
        f"unknown candidate core compression record {name!r}; "
        f"available: {list(core_compression_names())}"
    )


# Fail loudly at import time if the databases ever drift apart.
if core_compression_names() != tuple(c.name for c in CANDIDATE_CORES):  # pragma: no cover
    raise RuntimeError(
        "compression database is not aligned one-to-one with the elastic candidate database"
    )
