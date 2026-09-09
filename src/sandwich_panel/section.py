"""Sandwich section properties: neutral axis, second moment of area, EI.

Modelling decision (Milestone 1)
--------------------------------
**Core normal-stress bending stiffness is neglected; the core contributes
transverse shear stiffness only.** This is the standard lightweight-honeycomb
idealisation: ``E_core << E_face`` and the core sits close to the neutral axis,
so its normal-stress contribution is negligible.

No core Young's modulus is invented. A core modulus may be supplied explicitly
by the caller (``core_modulus=``) if a later study needs it; when it is ``None``
(the default) the core is bending-inactive.

Neutral axis
------------
The neutral axis is *computed* from a modulus-weighted first moment over the
layers::

    z_na = sum(E_i A_i z_i) / sum(E_i A_i)

rather than being hard-coded to zero. For the symmetric layup this evaluates to
``z = 0`` (the mid-plane), which the test suite checks numerically.
"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import SandwichGeometry
from .materials import FaceMaterial
from .validation import require_positive_finite

__all__ = ["Layer", "SectionProperties", "section_properties"]


@dataclass(frozen=True)
class Layer:
    """One rectangular layer of the cross-section, for section-property assembly."""

    name: str
    modulus: float  # E [Pa]; 0.0 for a bending-inactive layer
    width: float  # b [m]
    thickness: float  # t [m]
    z_centroid: float  # centroid position relative to the mid-plane [m]

    @property
    def area(self) -> float:
        return self.width * self.thickness

    @property
    def local_second_moment(self) -> float:
        """Second moment about the layer's OWN centroid, ``b t^3 / 12`` [m^4]."""
        return self.width * self.thickness**3 / 12.0

    @property
    def axial_rigidity(self) -> float:
        """``E A`` [N]."""
        return self.modulus * self.area


@dataclass(frozen=True)
class SectionProperties:
    """Section properties of a symmetric sandwich strip.

    Attributes
    ----------
    neutral_axis_z:
        Computed neutral-axis position relative to the mid-plane [m].
    face_centroid_offset:
        ``z_f = t_c/2 + t_f/2`` [m].
    face_local_second_moment:
        ``b t_f^3 / 12`` for one face [m^4].
    face_parallel_axis_term:
        ``(b t_f) z_f^2`` for one face [m^4].
    face_second_moment:
        Exact ``I_face`` for one face about the neutral axis [m^4].
    faces_second_moment:
        Exact ``I_faces_total = 2 I_face`` [m^4].
    faces_second_moment_thin_face:
        Thin-face approximation ``2 (b t_f) z_f^2``, which drops each face's own
        ``b t_f^3 / 12`` [m^4].
    core_second_moment:
        Core second moment about the neutral axis [m^4]; reported for
        information even when the core is bending-inactive.
    second_moment_for_stress:
        Second moment used for the face bending-stress calculation. Milestone 1
        uses the faces-only value (``faces_second_moment``).
    flexural_rigidity:
        ``EI`` of the strip [N m^2].
    core_modulus:
        Core Young's modulus actually used, or ``None`` if the core is
        bending-inactive (the default).
    """

    neutral_axis_z: float
    face_centroid_offset: float
    face_local_second_moment: float
    face_parallel_axis_term: float
    face_second_moment: float
    faces_second_moment: float
    faces_second_moment_thin_face: float
    core_second_moment: float
    second_moment_for_stress: float
    flexural_rigidity: float
    core_modulus: float | None
    total_thickness: float
    width: float

    @property
    def faces_thin_face_relative_error(self) -> float:
        """Signed relative error of the thin-face approximation vs the exact value.

        ``(I_approx - I_exact) / I_exact``; always negative because the
        approximation drops the (positive) local ``b t_f^3 / 12`` terms.
        """
        return (
            self.faces_second_moment_thin_face - self.faces_second_moment
        ) / self.faces_second_moment

    @property
    def flexural_rigidity_per_width(self) -> float:
        """``D_strip = EI / b`` [N m], a unit-width plate-style rigidity.

        This is *not* the plate rigidity ``D = E t^3 / (12 (1 - nu^2))``: no
        Poisson correction is applied in Milestone 1. The beam-strip ``EI``
        remains the primary structural quantity.
        """
        return self.flexural_rigidity / self.width

    @property
    def outer_fibre_distance(self) -> float:
        """Distance from the neutral axis to the outer face surface [m]."""
        return 0.5 * self.total_thickness - self.neutral_axis_z


def build_layers(
    geometry: SandwichGeometry,
    face: FaceMaterial,
    core_modulus: float | None = None,
) -> list[Layer]:
    """Assemble the three layers of the sandwich for section-property work."""
    z_f = geometry.face_centroid_offset
    e_core = 0.0 if core_modulus is None else require_positive_finite(core_modulus, "core_modulus")
    return [
        Layer("top face", face.youngs_modulus, geometry.width, geometry.face_thickness, +z_f),
        Layer("core", e_core, geometry.width, geometry.core_thickness, 0.0),
        Layer("bottom face", face.youngs_modulus, geometry.width, geometry.face_thickness, -z_f),
    ]


def neutral_axis_position(layers: list[Layer]) -> float:
    """Modulus-weighted neutral-axis position relative to the mid-plane [m]."""
    ea_total = sum(layer.axial_rigidity for layer in layers)
    if ea_total <= 0.0:
        raise ValueError("section has no axial rigidity; cannot locate a neutral axis")
    return sum(layer.axial_rigidity * layer.z_centroid for layer in layers) / ea_total


def section_properties(
    geometry: SandwichGeometry,
    face: FaceMaterial,
    core_modulus: float | None = None,
) -> SectionProperties:
    """Compute the sandwich section properties.

    The face second moment is built **exactly** with the parallel-axis theorem::

        I_face = b t_f^3 / 12 + (b t_f) z_f^2      with z_f = t_c/2 + t_f/2
        I_faces_total = 2 I_face

    The thin-face approximation ``2 (b t_f) z_f^2`` is computed alongside it for
    comparison, never used in its place.
    """
    layers = build_layers(geometry, face, core_modulus)
    z_na = neutral_axis_position(layers)

    top_face, core_layer, _bottom_face = layers

    face_local = top_face.local_second_moment
    face_parallel = top_face.area * (top_face.z_centroid - z_na) ** 2
    face_exact = face_local + face_parallel
    faces_exact = 2.0 * face_exact
    faces_thin = 2.0 * (geometry.face_area * geometry.face_centroid_offset**2)

    core_i = core_layer.local_second_moment + core_layer.area * (core_layer.z_centroid - z_na) ** 2

    ei = face.youngs_modulus * faces_exact + core_layer.modulus * core_i

    return SectionProperties(
        neutral_axis_z=z_na,
        face_centroid_offset=geometry.face_centroid_offset,
        face_local_second_moment=face_local,
        face_parallel_axis_term=face_parallel,
        face_second_moment=face_exact,
        faces_second_moment=faces_exact,
        faces_second_moment_thin_face=faces_thin,
        core_second_moment=core_i,
        second_moment_for_stress=faces_exact,
        flexural_rigidity=ei,
        core_modulus=core_modulus,
        total_thickness=geometry.total_thickness,
        width=geometry.width,
    )
