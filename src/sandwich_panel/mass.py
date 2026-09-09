"""Sandwich areal mass and strip mass."""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import SandwichGeometry
from .materials import CoreMaterial, FaceMaterial

__all__ = ["MassProperties", "mass_properties"]


@dataclass(frozen=True)
class MassProperties:
    """Mass breakdown of a sandwich panel.

    ``m_A = 2 rho_f t_f + rho_c t_c``  [kg/m^2]
    ``m_total = m_A b L``              [kg]

    Adhesive/film mass, edge close-outs, inserts and doublers are NOT included.
    """

    face_areal_mass: float
    core_areal_mass: float
    total_areal_mass: float
    plan_area: float
    face_mass: float
    core_mass: float
    total_mass: float

    @property
    def face_mass_fraction(self) -> float:
        return self.face_areal_mass / self.total_areal_mass

    @property
    def core_mass_fraction(self) -> float:
        return self.core_areal_mass / self.total_areal_mass


def mass_properties(
    geometry: SandwichGeometry, face: FaceMaterial, core: CoreMaterial
) -> MassProperties:
    """Areal mass and total strip mass for the sandwich (bare faces + core only)."""
    face_areal = 2.0 * face.density * geometry.face_thickness
    core_areal = core.density * geometry.core_thickness
    total_areal = face_areal + core_areal
    plan_area = geometry.plan_area
    return MassProperties(
        face_areal_mass=face_areal,
        core_areal_mass=core_areal,
        total_areal_mass=total_areal,
        plan_area=plan_area,
        face_mass=face_areal * plan_area,
        core_mass=core_areal * plan_area,
        total_mass=total_areal * plan_area,
    )
