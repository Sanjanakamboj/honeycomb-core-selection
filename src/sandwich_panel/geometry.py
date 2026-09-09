"""Sandwich beam-strip geometry.

Convention
----------
Symmetric three-layer strip::

    z = +h/2  ----------------------  top face surface
              [ top face,   t_f ]
    z = 0     ======================  sandwich mid-plane
              [ core,       t_c ]
              [ bottom face, t_f ]
    z = -h/2  ----------------------  bottom face surface

with total thickness ``h = 2 t_f + t_c`` and face centroids at
``z_f = +/- (t_c/2 + t_f/2)``.

``z = 0`` is the geometric mid-plane. For the symmetric layup modelled here the
neutral axis coincides with it; that is *computed*, not assumed, in
:mod:`sandwich_panel.section`.
"""

from __future__ import annotations

from dataclasses import dataclass

from .validation import require_positive_finite

__all__ = ["SandwichGeometry"]


@dataclass(frozen=True)
class SandwichGeometry:
    """Geometry of a symmetric sandwich beam strip. All lengths in metres."""

    width: float
    face_thickness: float
    core_thickness: float
    span: float

    def __post_init__(self) -> None:
        for field_name in ("width", "face_thickness", "core_thickness", "span"):
            object.__setattr__(
                self, field_name, require_positive_finite(getattr(self, field_name), field_name)
            )

    # -- derived geometry -------------------------------------------------

    @property
    def total_thickness(self) -> float:
        """``h = 2 t_f + t_c`` [m]."""
        return 2.0 * self.face_thickness + self.core_thickness

    @property
    def face_centroid_offset(self) -> float:
        """``z_f = t_c/2 + t_f/2`` [m], the magnitude of the face centroid offset."""
        return 0.5 * self.core_thickness + 0.5 * self.face_thickness

    @property
    def face_separation(self) -> float:
        """Distance between the two face centroids, ``d = t_c + t_f`` [m]."""
        return 2.0 * self.face_centroid_offset

    @property
    def face_area(self) -> float:
        """Cross-sectional area of ONE face sheet, ``A_f = b t_f`` [m^2]."""
        return self.width * self.face_thickness

    @property
    def core_area(self) -> float:
        """Core cross-sectional area, ``A_c = b t_c`` [m^2]."""
        return self.width * self.core_thickness

    @property
    def core_shear_area(self) -> float:
        """Effective core shear area used for transverse shear, ``A_s = b t_c`` [m^2]."""
        return self.core_area

    @property
    def plan_area(self) -> float:
        """Plan area of the strip, ``b L`` [m^2]."""
        return self.width * self.span
