"""Verified sandwich-panel mechanics for preliminary honeycomb core selection.

Milestone 1 establishes the verified sandwich-panel mechanics only. Candidate
honeycomb materials and final core selection are intentionally deferred.

SI units throughout.
"""

from __future__ import annotations

from .geometry import SandwichGeometry
from .loads import DEFAULT_KAPPA, CentralPointLoadResult, central_point_load_response
from .mass import MassProperties, mass_properties
from .materials import CoreMaterial, FaceMaterial
from .panel import SandwichPanel
from .section import Layer, SectionProperties, section_properties
from .sensitivity import (
    CoreDepthRow,
    CoreShearRow,
    FaceThicknessRow,
    core_depth_sweep,
    core_shear_modulus_sweep,
    face_thickness_sweep,
)

__version__ = "0.1.0"

__all__ = [
    "CentralPointLoadResult",
    "CoreDepthRow",
    "CoreMaterial",
    "CoreShearRow",
    "DEFAULT_KAPPA",
    "FaceMaterial",
    "FaceThicknessRow",
    "Layer",
    "MassProperties",
    "SandwichGeometry",
    "SandwichPanel",
    "SectionProperties",
    "central_point_load_response",
    "core_depth_sweep",
    "core_shear_modulus_sweep",
    "face_thickness_sweep",
    "mass_properties",
    "section_properties",
    "__version__",
]
