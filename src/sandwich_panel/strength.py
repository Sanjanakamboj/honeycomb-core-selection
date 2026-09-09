"""Milestone 3: first-order strength properties, margins and allowable loads.

SCOPE PRINCIPLE
---------------
Only strength checks directly supported by the existing beam-strip mechanics are
implemented:

* **face longitudinal normal stress** vs a face allowable stress
* **average effective core shear stress** vs a directional core shear strength

Nothing else. There is no through-thickness compression load in the model, so
there is no core crushing check. There is no face-wrinkling equation, no shear
crimping, no local indentation, no contact/bearing stress, no insert or adhesive
check. Those are deferred, not approximated.

MARGIN CONVENTION
-----------------
Both margins are dimensionless margins of safety::

    MS = allowable / demand - 1

with ``MS >= 0`` passing, so exactly reaching the allowable PASSES. Demand is
always strictly positive here because the load model requires ``P > 0``.

These are **preliminary screening margins**, not certification margins. The core
margin in particular is an *average effective* core shear margin - it carries no
cell-wall stress fidelity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .directions import CoreShearDirection
from .validation import require_finite, require_non_empty_name, require_positive_finite

__all__ = [
    "LimitingConstraint",
    "FaceStrength",
    "OrthotropicCoreStrength",
    "StrengthBasis",
    "StrengthAssessment",
    "face_stress_margin",
    "core_shear_margin",
]


class LimitingConstraint(str, Enum):
    """Which modelled constraint governs a load capacity.

    ``DEFLECTION`` is a stiffness constraint; the other two are the only two
    strength constraints the current mechanics can support.
    """

    DEFLECTION = "deflection"
    FACE_YIELD = "face_yield"
    CORE_SHEAR = "core_shear"

    def __str__(self) -> str:
        return self.value


# -- material strength records --------------------------------------------


@dataclass(frozen=True)
class FaceStrength:
    """Face-sheet strength record.

    Pure material data. The design factor deliberately does NOT live here - see
    :class:`StrengthBasis` - so that a knockdown can never hide inside a material
    property.

    Parameters
    ----------
    name:
        Label for the strength record.
    yield_strength:
        Face yield strength as a positive magnitude [Pa]. This is the Milestone 3
        allowable basis.
    ultimate_strength:
        Optional, recorded but NOT used as an allowable basis in Milestone 3.
        A single clearly defined basis (yield) is used throughout.
    source_note / notes:
        Provenance and free-text engineering note.
    """

    name: str
    yield_strength: float
    ultimate_strength: float | None = None
    source_note: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", require_non_empty_name(self.name))
        object.__setattr__(
            self, "yield_strength", require_positive_finite(self.yield_strength, "yield_strength")
        )
        if self.ultimate_strength is not None:
            ult = require_positive_finite(self.ultimate_strength, "ultimate_strength")
            if ult < self.yield_strength:
                raise ValueError(
                    f"ultimate_strength ({ult}) must not be below yield_strength "
                    f"({self.yield_strength})"
                )
            object.__setattr__(self, "ultimate_strength", ult)


@dataclass(frozen=True)
class OrthotropicCoreStrength:
    """Directional honeycomb core shear strengths, using the Milestone 2 L/W convention.

    L and W strengths are never averaged, for the same reason the moduli are not:
    a strip loaded in one direction sees one of them, not a blend.

    Only transverse shear strength is represented. There is no compressive
    (through-thickness) strength here, because the current model has no
    through-thickness load to check it against.
    """

    name: str
    shear_strength_L: float  # tau_L [Pa]
    shear_strength_W: float  # tau_W [Pa]
    source_note: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", require_non_empty_name(self.name))
        object.__setattr__(
            self,
            "shear_strength_L",
            require_positive_finite(self.shear_strength_L, "shear_strength_L"),
        )
        object.__setattr__(
            self,
            "shear_strength_W",
            require_positive_finite(self.shear_strength_W, "shear_strength_W"),
        )

    def shear_strength(self, direction: CoreShearDirection | str) -> float:
        """Transverse shear strength in the requested direction [Pa]."""
        chosen = CoreShearDirection.parse(direction)
        if chosen is CoreShearDirection.L:
            return self.shear_strength_L
        return self.shear_strength_W

    @property
    def directional_strength_ratio(self) -> float:
        """``tau_L / tau_W`` - the directional strength penalty of this core [-]."""
        return self.shear_strength_L / self.shear_strength_W


@dataclass(frozen=True)
class StrengthBasis:
    """The allowable basis applied to a screening study.

    The design factor is held here, explicitly and visibly, rather than inside
    :class:`FaceStrength`::

        sigma_face_allowable = yield_strength / face_design_factor

    ``face_design_factor`` must be >= 1 (a factor below 1 would raise the
    allowable above yield, which is never a design intent).
    """

    face_strength: FaceStrength
    face_design_factor: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.face_strength, FaceStrength):
            raise TypeError("face_strength must be a FaceStrength")
        factor = require_finite(self.face_design_factor, "face_design_factor")
        if factor < 1.0:
            raise ValueError(f"face_design_factor must be >= 1, got {factor!r}")
        object.__setattr__(self, "face_design_factor", factor)

    @property
    def face_allowable_stress(self) -> float:
        """``sigma_face_allowable = yield_strength / face_design_factor`` [Pa]."""
        return self.face_strength.yield_strength / self.face_design_factor


# -- margins ---------------------------------------------------------------


def face_stress_margin(demand: float, allowable: float) -> float:
    """Preliminary face yield margin ``MS = allowable / demand - 1`` [-]."""
    d = require_positive_finite(demand, "demand")
    a = require_positive_finite(allowable, "allowable")
    return a / d - 1.0


def core_shear_margin(demand: float, allowable: float) -> float:
    """Average effective core shear margin ``MS = allowable / demand - 1`` [-]."""
    d = require_positive_finite(demand, "demand")
    a = require_positive_finite(allowable, "allowable")
    return a / d - 1.0


@dataclass(frozen=True)
class StrengthAssessment:
    """First-order strength screen of one candidate/direction at one load.

    ``governing_mode`` is the mode with the SMALLER dimensionless margin. It is
    computed, never assumed - which mode governs is a result, not an input.
    """

    candidate: str
    direction: CoreShearDirection
    load: float | None  # P [N], recorded for traceability only
    face_stress: float  # sigma_face,max [Pa]
    face_allowable: float  # [Pa]
    face_margin: float  # MS [-]
    face_pass: bool
    core_shear_stress: float  # tau_core, average effective [Pa]
    core_shear_allowable: float  # [Pa]
    core_shear_margin: float  # MS [-]
    core_shear_pass: bool
    governing_mode: LimitingConstraint
    governing_margin: float  # [-]
    strength_feasible: bool

    @property
    def label(self) -> str:
        return f"{self.candidate} [{self.direction.value}]"
