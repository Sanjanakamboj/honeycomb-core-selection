"""The assembled sandwich panel: geometry + materials + response."""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import SandwichGeometry
from .loads import DEFAULT_KAPPA, CentralPointLoadResult, central_point_load_response
from .mass import MassProperties, mass_properties
from .materials import CoreMaterial, FaceMaterial
from .section import SectionProperties, section_properties
from .validation import require_positive_finite

__all__ = ["SandwichPanel"]


@dataclass(frozen=True)
class SandwichPanel:
    """Symmetric sandwich beam strip: two identical faces bonded to a light core.

    Assumptions (Milestone 1): identical isotropic-equivalent faces, symmetric
    layup, small deflections, linear elasticity, perfect bonding, core carries
    transverse shear only, faces carry the bending normal stress.

    ``core_modulus`` is ``None`` by default: the core normal-stress bending
    stiffness is neglected. Supply a value only if you have a sourced core
    modulus; nothing in this package invents one.
    """

    geometry: SandwichGeometry
    face: FaceMaterial
    core: CoreMaterial
    core_modulus: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.geometry, SandwichGeometry):
            raise TypeError("geometry must be a SandwichGeometry")
        if not isinstance(self.face, FaceMaterial):
            raise TypeError("face must be a FaceMaterial")
        if not isinstance(self.core, CoreMaterial):
            raise TypeError("core must be a CoreMaterial")
        if self.core_modulus is not None:
            object.__setattr__(
                self, "core_modulus", require_positive_finite(self.core_modulus, "core_modulus")
            )

    # -- derived properties ------------------------------------------------

    def section(self) -> SectionProperties:
        """Neutral axis, second moments and ``EI`` for this panel."""
        return section_properties(self.geometry, self.face, self.core_modulus)

    def mass(self) -> MassProperties:
        """Areal mass and strip mass for this panel."""
        return mass_properties(self.geometry, self.face, self.core)

    @property
    def flexural_rigidity(self) -> float:
        """``EI`` of the beam strip [N m^2]."""
        return self.section().flexural_rigidity

    @property
    def areal_mass(self) -> float:
        """``m_A`` [kg/m^2]."""
        return self.mass().total_areal_mass

    # -- load cases --------------------------------------------------------

    def central_point_load(
        self, load: float, shear_correction_factor: float = DEFAULT_KAPPA
    ) -> CentralPointLoadResult:
        """Simply supported strip with a central transverse point load ``P`` [N].

        This is a stiffness/stress demonstration case, not a qualification or
        launch load case.
        """
        sec = self.section()
        return central_point_load_response(
            load=load,
            span=self.geometry.span,
            flexural_rigidity=sec.flexural_rigidity,
            second_moment_for_stress=sec.second_moment_for_stress,
            outer_fibre_distance=sec.outer_fibre_distance,
            core_shear_modulus=self.core.shear_modulus,
            core_shear_area=self.geometry.core_shear_area,
            shear_correction_factor=shear_correction_factor,
        )

    # -- convenience for sweeps -------------------------------------------

    def with_geometry(self, **changes: float) -> "SandwichPanel":
        """Return a copy with selected geometry fields replaced."""
        current = {
            "width": self.geometry.width,
            "face_thickness": self.geometry.face_thickness,
            "core_thickness": self.geometry.core_thickness,
            "span": self.geometry.span,
        }
        unknown = set(changes) - set(current)
        if unknown:
            raise ValueError(f"unknown geometry field(s): {sorted(unknown)}")
        current.update(changes)
        return SandwichPanel(
            geometry=SandwichGeometry(**current),
            face=self.face,
            core=self.core,
            core_modulus=self.core_modulus,
        )

    def with_core_shear_modulus(self, shear_modulus: float) -> "SandwichPanel":
        """Return a copy whose core has a different effective shear modulus."""
        return SandwichPanel(
            geometry=self.geometry,
            face=self.face,
            core=CoreMaterial(
                name=self.core.name, density=self.core.density, shear_modulus=shear_modulus
            ),
            core_modulus=self.core_modulus,
        )
