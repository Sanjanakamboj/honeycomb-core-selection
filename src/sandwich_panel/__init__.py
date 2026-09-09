"""Verified sandwich-panel mechanics for preliminary honeycomb core selection.

Milestone 1 establishes the verified sandwich-panel mechanics only. Candidate
honeycomb materials and final core selection are intentionally deferred.

SI units throughout.
"""

from __future__ import annotations

from .core_database import CANDIDATE_CORES, ILLUSTRATIVE_DATA_NOTE, core_names, get_core
from .directions import CoreShearDirection
from .geometry import SandwichGeometry
from .loads import DEFAULT_KAPPA, CentralPointLoadResult, central_point_load_response
from .mass import MassProperties, mass_properties
from .materials import (
    CoreMaterial,
    FaceMaterial,
    OrthotropicCoreMaterial,
    effective_core_shear_modulus,
)
from .panel import SandwichPanel
from .requirements import DeflectionAssessment, DeflectionRequirement
from .section import Layer, SectionProperties, section_properties
from .sensitivity import (
    CoreDepthRow,
    CoreShearRow,
    FaceThicknessRow,
    core_depth_sweep,
    core_shear_modulus_sweep,
    face_thickness_sweep,
)
from .trade import (
    CoreCandidateResult,
    CoreDepthDirectionalRow,
    StudyBasis,
    TradeRow,
    build_trade_table,
    core_density_sweep,
    core_depth_directional_sweep,
    core_shear_modulus_sweep_at_fixed_density,
    evaluate_candidate,
    evaluate_candidates,
    is_dominated,
    pareto_front,
)

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "build_trade_table",
    "CANDIDATE_CORES",
    "central_point_load_response",
    "CentralPointLoadResult",
    "core_density_sweep",
    "core_depth_directional_sweep",
    "core_depth_sweep",
    "core_names",
    "core_shear_modulus_sweep",
    "core_shear_modulus_sweep_at_fixed_density",
    "CoreCandidateResult",
    "CoreDepthDirectionalRow",
    "CoreDepthRow",
    "CoreMaterial",
    "CoreShearDirection",
    "CoreShearRow",
    "DEFAULT_KAPPA",
    "DeflectionAssessment",
    "DeflectionRequirement",
    "effective_core_shear_modulus",
    "evaluate_candidate",
    "evaluate_candidates",
    "face_thickness_sweep",
    "FaceMaterial",
    "FaceThicknessRow",
    "get_core",
    "ILLUSTRATIVE_DATA_NOTE",
    "is_dominated",
    "Layer",
    "mass_properties",
    "MassProperties",
    "OrthotropicCoreMaterial",
    "pareto_front",
    "SandwichGeometry",
    "SandwichPanel",
    "section_properties",
    "SectionProperties",
    "StudyBasis",
    "TradeRow",
]
