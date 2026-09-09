"""Material representations for the Milestone 1 sandwich model.

SI units throughout:

* Young's modulus      [Pa]
* shear modulus        [Pa]
* density              [kg/m^3]
"""

from __future__ import annotations

from dataclasses import dataclass

from .validation import require_finite, require_non_empty_name, require_positive_finite

__all__ = ["FaceMaterial", "CoreMaterial"]


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
