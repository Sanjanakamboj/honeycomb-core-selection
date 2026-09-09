"""Material representations for the Milestone 1 sandwich model.

SI units throughout:

* Young's modulus      [Pa]
* shear modulus        [Pa]
* density              [kg/m^3]
"""

from __future__ import annotations

from dataclasses import dataclass

from .directions import CoreShearDirection
from .validation import require_finite, require_non_empty_name, require_positive_finite

__all__ = [
    "FaceMaterial",
    "CoreMaterial",
    "OrthotropicCoreMaterial",
    "effective_core_shear_modulus",
]


@dataclass(frozen=True)
class FaceMaterial:
    """Isotropic (or isotropic-equivalent) face-sheet material.

    Parameters
    ----------
    name:
        Human-readable label.
    youngs_modulus:
        In-plane Young's modulus ``E_f`` [Pa].
    density:
        Mass density ``rho_f`` [kg/m^3].
    poissons_ratio:
        Optional, unused in Milestone 1. Retained for later milestones
        (plate rigidity, wrinkling, buckling).
    """

    name: str
    youngs_modulus: float
    density: float
    poissons_ratio: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", require_non_empty_name(self.name))
        object.__setattr__(
            self, "youngs_modulus", require_positive_finite(self.youngs_modulus, "youngs_modulus")
        )
        object.__setattr__(self, "density", require_positive_finite(self.density, "density"))
        if self.poissons_ratio is not None:
            nu = require_finite(self.poissons_ratio, "poissons_ratio")
            if not (-1.0 < nu < 0.5):
                raise ValueError(f"poissons_ratio must satisfy -1 < nu < 0.5, got {nu!r}")
            object.__setattr__(self, "poissons_ratio", nu)


@dataclass(frozen=True)
class CoreMaterial:
    """Lightweight core modelled as an effective transverse shear layer.

    For Milestone 1 the core is represented **only** by

    * a density ``rho_c`` [kg/m^3], and
    * an effective transverse (through-thickness) shear modulus ``G_c`` [Pa].

    Real honeycomb is strongly orthotropic: the ribbon (L) and expansion (W)
    directions have different transverse shear moduli. This class deliberately
    collapses that to a single effective value. Later milestones may introduce
    separate ``G_L`` / ``G_W`` values; nothing here should be read as a claim
    that honeycomb is isotropic.

    No core Young's modulus is stored: the core normal-stress bending
    contribution is neglected in this milestone (see :mod:`sandwich_panel.section`).
    """

    name: str
    density: float
    shear_modulus: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", require_non_empty_name(self.name))
        object.__setattr__(self, "density", require_positive_finite(self.density, "density"))
        object.__setattr__(
            self, "shear_modulus", require_positive_finite(self.shear_modulus, "shear_modulus")
        )


@dataclass(frozen=True)
class OrthotropicCoreMaterial:
    """Honeycomb core with DISTINCT L and W transverse shear moduli.

    This is the Milestone 2 core representation. It does not replace
    :class:`CoreMaterial`, which remains the Milestone 1 direction-independent
    effective shear layer; use :meth:`as_effective_core` to obtain a
    ``CoreMaterial`` for a chosen direction and feed the unchanged Milestone 1
    panel equations.

    Parameters
    ----------
    name:
        Candidate identifier, unique within a database.
    density:
        Core density ``rho_c`` [kg/m^3].
    shear_modulus_L:
        Transverse shear modulus in the ribbon direction ``G_L`` [Pa].
    shear_modulus_W:
        Transverse shear modulus in the expansion direction ``G_W`` [Pa].
    family:
        Optional material family label (e.g. an aluminium- or aramid-equivalent).
    notes:
        Optional free-text engineering note.
    source_note:
        Provenance of the numbers. Required in the shipped database so that
        illustrative values can never be mistaken for datasheet values.

    Only transverse shear moduli and density are represented. There is no core
    compression modulus, no in-plane stiffness, no full orthotropic constitutive
    tensor, and no strength allowable of any kind.
    """

    name: str
    density: float
    shear_modulus_L: float
    shear_modulus_W: float
    family: str | None = None
    notes: str | None = None
    source_note: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", require_non_empty_name(self.name))
        object.__setattr__(self, "density", require_positive_finite(self.density, "density"))
        object.__setattr__(
            self, "shear_modulus_L", require_positive_finite(self.shear_modulus_L, "shear_modulus_L")
        )
        object.__setattr__(
            self, "shear_modulus_W", require_positive_finite(self.shear_modulus_W, "shear_modulus_W")
        )

    # -- directional access ------------------------------------------------

    def shear_modulus(self, direction: CoreShearDirection | str) -> float:
        """Transverse shear modulus in the requested direction [Pa].

        ``direction`` must be ``L`` or ``W``; the two are never averaged.
        """
        chosen = CoreShearDirection.parse(direction)
        if chosen is CoreShearDirection.L:
            return self.shear_modulus_L
        return self.shear_modulus_W

    @property
    def directional_shear_ratio(self) -> float:
        """``G_L / G_W`` - the directional shear penalty of this core [-].

        For the same geometry and load this equals ``delta_s,W / delta_s,L``.
        """
        return self.shear_modulus_L / self.shear_modulus_W

    def specific_shear_stiffness(self, direction: CoreShearDirection | str) -> float:
        """First-order shear-stiffness-to-density indicator, ``G_eff / rho_c``.

        Units are m^2/s^2. This is a coarse screening indicator only - it is NOT
        a universal optimisation index, it ignores every strength, stability and
        manufacturing consideration, and it must not be used on its own to rank
        cores.
        """
        return self.shear_modulus(direction) / self.density

    def as_effective_core(self, direction: CoreShearDirection | str) -> CoreMaterial:
        """Collapse to a Milestone 1 :class:`CoreMaterial` for one direction.

        This is the bridge that keeps orientation knowledge out of the panel
        equations: the panel receives a single scalar effective shear modulus and
        knows nothing about honeycomb ribbons.
        """
        chosen = CoreShearDirection.parse(direction)
        return CoreMaterial(
            name=f"{self.name} [{chosen.value}]",
            density=self.density,
            shear_modulus=self.shear_modulus(chosen),
        )


def effective_core_shear_modulus(
    core: CoreMaterial | OrthotropicCoreMaterial, direction: CoreShearDirection | str
) -> float:
    """Select the scalar transverse shear modulus to use in the strip response.

    For an :class:`OrthotropicCoreMaterial` this picks ``G_L`` or ``G_W``.

    For a Milestone 1 :class:`CoreMaterial` the stored value is a single
    *direction-independent* effective shear modulus, so the same number is
    returned for either direction. ``direction`` is still validated, so a typo
    fails loudly rather than silently selecting the wrong idealisation.
    """
    chosen = CoreShearDirection.parse(direction)
    if isinstance(core, OrthotropicCoreMaterial):
        return core.shear_modulus(chosen)
    if isinstance(core, CoreMaterial):
        return core.shear_modulus
    raise TypeError(
        f"core must be a CoreMaterial or OrthotropicCoreMaterial, got {type(core).__name__}"
    )
