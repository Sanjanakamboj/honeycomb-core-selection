"""Milestone 4: sandwich-specific local failure screens.

TWO modes are implemented, and only two, because only two can be stated
transparently from the inputs this model actually has:

1. **Face wrinkling** - local instability of the compression face on an elastic
   core, screened with an explicitly illustrative analytical convention.
2. **Core through-thickness compression (crushing)** under a prescribed local
   patch footprint.

WHY LOCAL INDENTATION IS DEFERRED, NOT IMPLEMENTED
--------------------------------------------------
A local indentation screen would need to be *physically distinct* from the core
compression screen above. With the current inputs it cannot be:

* the simplest "contact pressure vs allowable" form is numerically the SAME
  equation as the core compression check, against the SAME allowable - two names
  for one margin, which would be a fabricated failure mode;
* a genuinely distinct indentation model (load spread through the face into a
  crushed core zone) needs a face plate-bending rigidity - hence a face Poisson
  ratio, which is optional and unset in the canonical face material - plus a
  contact/load-spread model and a characteristic-length constant that this
  project has no sourced value for.

Inventing either an allowable or a constant to produce a second margin would be
exactly the kind of box-ticking the milestone forbids. Indentation is therefore
DEFERRED, and this module deliberately exposes no indentation margin. See also
:class:`LocalFailureAssessment`.

SHEAR CRIMPING is likewise deferred: its standard derivation is a limiting case of
overall buckling under IN-PLANE compression, and this model has no in-plane
compressive load case at all - only transverse bending. The load case, not the
data, is what is missing.

WRINKLING SCREENING CONVENTION
------------------------------
The screening stress uses the common analytical form::

    sigma_wr,screen = C_wr * (E_f * E_c * G_eff)^(1/3)

with, deliberately:

* ``C_wr`` a REQUIRED explicit input - there is no default, so no empirical
  constant can hide inside this package;
* ``E_c`` the core through-thickness compression modulus;
* ``G_eff`` the core transverse shear modulus in an EXPLICIT L or W direction,
  using the same convention as Milestones 2-3.

This is an **illustrative wrinkling screening stress**, not a validated allowable.
Published coefficients for this form vary substantially between references and
with face/core imperfection assumptions; no coefficient here is sourced to a
standard. Applicability limits: it assumes a thin, flat, isotropic-equivalent face
perfectly bonded to a thick elastic core, no initial waviness, no bondline
compliance and no core cell-size effect (anti-symmetric/symmetric wrinkling modes
are not distinguished).

MARGIN CONVENTION
-----------------
As in Milestone 3, all margins are dimensionless::

    MS = allowable / demand - 1        MS >= 0 passes (boundary passes)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .directions import CoreShearDirection
from .validation import require_non_empty_name, require_positive_finite

__all__ = [
    "LocalFailureMode",
    "SandwichConstraint",
    "CoreCompressionProperties",
    "LocalPatchLoad",
    "WrinklingModel",
    "LocalFailureAssessment",
    "wrinkling_screening_stress",
    "core_compression_margin",
    "wrinkling_margin",
    "core_crush_force_limit",
]


class LocalFailureMode(str, Enum):
    """The local failure modes screened in Milestone 4.

    Indentation is deliberately absent - see the module docstring.
    """

    WRINKLING = "wrinkling"
    CORE_COMPRESSION = "core_compression"

    def __str__(self) -> str:
        return self.value


class SandwichConstraint(str, Enum):
    """Constraints on the GLOBAL central-point-load capacity, Milestone 4 set.

    This extends the Milestone 3 :class:`~sandwich_panel.strength.LimitingConstraint`
    set with face wrinkling. The three shared members carry identical string
    values, so they compare equal across the two enums. The Milestone 3 enum is
    left untouched.

    Core compression is NOT here: it belongs to a separate local patch load case
    with no defined physical relationship to the global central load.
    """

    DEFLECTION = "deflection"
    FACE_YIELD = "face_yield"
    CORE_SHEAR = "core_shear"
    WRINKLING = "wrinkling"

    def __str__(self) -> str:
        return self.value


# -- material / model records ---------------------------------------------


@dataclass(frozen=True)
class CoreCompressionProperties:
    """Core THROUGH-THICKNESS (flatwise) compression properties.

    This is a distinct property axis from the L/W transverse shear directions of
    Milestones 2-3: L and W describe in-plane ribbon orientation, whereas these
    describe the through-thickness (z) response. They are never interchanged.

    Parameters
    ----------
    name:
        Candidate identifier, matching the elastic and strength databases.
    compression_strength:
        Through-thickness compressive strength ``sigma_c,allow`` [Pa], a positive
        magnitude.
    compression_modulus:
        Through-thickness compression modulus ``E_c`` [Pa]. Required because the
        wrinkling screening convention consumes it.
    """

    name: str
    compression_strength: float
    compression_modulus: float
    source_note: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", require_non_empty_name(self.name))
        object.__setattr__(
            self,
            "compression_strength",
            require_positive_finite(self.compression_strength, "compression_strength"),
        )
        object.__setattr__(
            self,
            "compression_modulus",
            require_positive_finite(self.compression_modulus, "compression_modulus"),
        )


@dataclass(frozen=True)
class LocalPatchLoad:
    """A prescribed local footprint carrying a transverse force into the panel.

    This is a **preliminary local core compression screen for a prescribed
    footprint**, using a deliberately uniform pressure over a rectangular patch.
    It may stand in for a hard point, an equipment foot or a nominal insert
    footprint, but it is **NOT an insert analysis**.

    A detailed insert or potting assessment would require potting geometry, the
    load-transfer path into the core, bearing and shear at the insert wall, local
    face bending, local core shear, and pull-out / push-through mechanics. All of
    that remains deferred.

    The patch force is an INDEPENDENT load case: it has no defined physical
    relationship to the global central point load, and the two are never summed or
    minimised together.
    """

    force: float  # F_local [N]
    patch_width: float  # [m]
    patch_length: float  # [m]

    def __post_init__(self) -> None:
        for field_name in ("force", "patch_width", "patch_length"):
            object.__setattr__(
                self, field_name, require_positive_finite(getattr(self, field_name), field_name)
            )

    @classmethod
    def square(cls, force: float, side: float) -> "LocalPatchLoad":
        """A square patch of the given side length."""
        return cls(force=force, patch_width=side, patch_length=side)

    @property
    def patch_area(self) -> float:
        """``A_patch = patch_width * patch_length`` [m^2]."""
        return self.patch_width * self.patch_length

    @property
    def pressure(self) -> float:
        """Uniform patch pressure ``F_local / A_patch`` [Pa].

        This is both the local core compressive stress and the nominal contact
        pressure - they are the same quantity in this first-order model, which is
        precisely why no separate indentation margin is reported.
        """
        return self.force / self.patch_area

    def with_force(self, force: float) -> "LocalPatchLoad":
        return LocalPatchLoad(force=force, patch_width=self.patch_width, patch_length=self.patch_length)

    def with_square_side(self, side: float) -> "LocalPatchLoad":
        return LocalPatchLoad(force=self.force, patch_width=side, patch_length=side)


@dataclass(frozen=True)
class WrinklingModel:
    """The explicit wrinkling screening convention.

    ``coefficient`` (``C_wr``) is REQUIRED - there is deliberately no default, so
    this package never applies an unstated empirical constant. It is not a
    universal constant: published values for this form vary by reference and by
    imperfection assumption.
    """

    coefficient: float
    source_note: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "coefficient", require_positive_finite(self.coefficient, "coefficient")
        )

    def screening_stress(
        self,
        face_modulus: float,
        core_compression_modulus: float,
        core_shear_modulus: float,
    ) -> float:
        """``C_wr * (E_f * E_c * G_eff)^(1/3)`` [Pa]."""
        return wrinkling_screening_stress(
            self, face_modulus, core_compression_modulus, core_shear_modulus
        )


def wrinkling_screening_stress(
    model: WrinklingModel,
    face_modulus: float,
    core_compression_modulus: float,
    core_shear_modulus: float,
) -> float:
    """Illustrative wrinkling screening stress [Pa].

    ``sigma_wr,screen = C_wr * (E_f * E_c * G_eff)^(1/3)``

    Not a validated allowable. All three moduli must be strictly positive and
    finite; ``G_eff`` must already have been resolved to one explicit L/W
    direction by the caller.
    """
    if not isinstance(model, WrinklingModel):
        raise TypeError("model must be a WrinklingModel")
    e_f = require_positive_finite(face_modulus, "face_modulus")
    e_c = require_positive_finite(core_compression_modulus, "core_compression_modulus")
    g = require_positive_finite(core_shear_modulus, "core_shear_modulus")
    return model.coefficient * (e_f * e_c * g) ** (1.0 / 3.0)


# -- margins ---------------------------------------------------------------


def wrinkling_margin(demand: float, screening_stress: float) -> float:
    """``MS = sigma_wr,screen / sigma_face,max - 1`` [-]."""
    d = require_positive_finite(demand, "demand")
    a = require_positive_finite(screening_stress, "screening_stress")
    return a / d - 1.0


def core_compression_margin(demand: float, allowable: float) -> float:
    """``MS = sigma_c,allow / sigma_core,local - 1`` [-]."""
    d = require_positive_finite(demand, "demand")
    a = require_positive_finite(allowable, "allowable")
    return a / d - 1.0


def core_crush_force_limit(compression_strength: float, patch_area: float) -> float:
    """``F_crush = sigma_c,allow * A_patch`` [N] for a fixed footprint.

    This is a preliminary core crushing capacity for the prescribed patch. It is
    NOT an insert allowable, NOT a pull-out capacity and NOT a design load.
    """
    s = require_positive_finite(compression_strength, "compression_strength")
    a = require_positive_finite(patch_area, "patch_area")
    return s * a


@dataclass(frozen=True)
class LocalFailureAssessment:
    """Milestone 4 local failure screen for one candidate in one shear direction.

    There is deliberately NO indentation field: with the current inputs an
    indentation margin would either duplicate the core compression margin exactly
    or require invented data. See the module docstring.

    ``governing_local_mode`` is the mode with the smaller dimensionless margin,
    computed from the margins rather than assumed.
    """

    candidate: str
    direction: CoreShearDirection
    # wrinkling (demand is the global beam-theory face stress)
    face_stress: float  # sigma_face,max [Pa]
    wrinkling_screening_stress: float  # [Pa]
    wrinkling_margin: float  # [-]
    wrinkling_pass: bool
    # core through-thickness compression under the prescribed local patch
    local_patch_force: float  # F_local [N]
    patch_area: float  # A_patch [m^2]
    local_core_compression_stress: float  # [Pa]
    core_compression_allowable: float  # [Pa]
    core_compression_margin: float  # [-]
    core_compression_pass: bool
    core_crush_force_limit: float  # [N], for this patch area
    # roll-up
    governing_local_mode: LocalFailureMode
    governing_local_margin: float  # [-]
    local_failure_feasible: bool

    @property
    def label(self) -> str:
        return f"{self.candidate} [{self.direction.value}]"
