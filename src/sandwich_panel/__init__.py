"""Verified sandwich-panel mechanics for preliminary honeycomb core selection.

Milestone 1 establishes the verified sandwich-panel mechanics only. Candidate
honeycomb materials and final core selection are intentionally deferred.

SI units throughout.
"""

from __future__ import annotations

from .core_database import CANDIDATE_CORES, ILLUSTRATIVE_DATA_NOTE, core_names, get_core
from .design_screen import (
    CandidateDesignAssessment,
    CoreDepthCapacityRow,
    LoadSensitivityRow,
    PreliminaryLoadCapacity,
    assess_candidate_design,
    assess_strength,
    build_design_table,
    core_depth_capacity_sweep,
    is_dominated_by_capacity,
    load_sensitivity_sweep,
    pareto_front_by_capacity,
    preliminary_load_capacity,
)
from .directions import CoreShearDirection
from .geometry import SandwichGeometry
from .local_failure import (
    CoreCompressionProperties,
    LocalFailureAssessment,
    LocalFailureMode,
    LocalPatchLoad,
    SandwichConstraint,
    WrinklingModel,
    core_compression_margin,
    core_crush_force_limit,
    wrinkling_margin,
    wrinkling_screening_stress,
)
from .local_failure_database import (
    CANDIDATE_CORE_COMPRESSION,
    ILLUSTRATIVE_LOCAL_NOTE,
    core_compression_names,
    get_core_compression,
)
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
from .sandwich_screen import (
    CoreDepthWrinklingRow,
    GlobalSandwichCapacity,
    LocalPatchSweepRow,
    LocalScreenBasis,
    RetentionStatus,
    SandwichDesignAssessment,
    assess_local_failure,
    assess_sandwich_design,
    build_sandwich_table,
    core_depth_wrinkling_sweep,
    global_sandwich_capacity,
    local_patch_force_sweep,
    local_patch_size_sweep,
)
from .section import Layer, SectionProperties, section_properties
from .strength import (
    FaceStrength,
    LimitingConstraint,
    OrthotropicCoreStrength,
    StrengthAssessment,
    StrengthBasis,
    core_shear_margin,
    face_stress_margin,
)
from .strength_database import (
    CANDIDATE_CORE_STRENGTHS,
    ILLUSTRATIVE_FACE_STRENGTH,
    ILLUSTRATIVE_STRENGTH_NOTE,
    core_strength_names,
    get_core_strength,
)
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

__version__ = "0.4.0"

__all__ = [
    "__version__",
    "assess_candidate_design",
    "assess_local_failure",
    "assess_sandwich_design",
    "assess_strength",
    "build_design_table",
    "build_sandwich_table",
    "build_trade_table",
    "CANDIDATE_CORE_COMPRESSION",
    "CANDIDATE_CORE_STRENGTHS",
    "CANDIDATE_CORES",
    "CandidateDesignAssessment",
    "central_point_load_response",
    "CentralPointLoadResult",
    "core_compression_margin",
    "core_compression_names",
    "core_crush_force_limit",
    "core_density_sweep",
    "core_depth_capacity_sweep",
    "core_depth_directional_sweep",
    "core_depth_sweep",
    "core_depth_wrinkling_sweep",
    "core_names",
    "core_shear_margin",
    "core_shear_modulus_sweep",
    "core_shear_modulus_sweep_at_fixed_density",
    "core_strength_names",
    "CoreCandidateResult",
    "CoreCompressionProperties",
    "CoreDepthCapacityRow",
    "CoreDepthDirectionalRow",
    "CoreDepthRow",
    "CoreDepthWrinklingRow",
    "CoreMaterial",
    "CoreShearDirection",
    "CoreShearRow",
    "DEFAULT_KAPPA",
    "DeflectionAssessment",
    "DeflectionRequirement",
    "effective_core_shear_modulus",
    "evaluate_candidate",
    "evaluate_candidates",
    "face_stress_margin",
    "face_thickness_sweep",
    "FaceMaterial",
    "FaceStrength",
    "FaceThicknessRow",
    "get_core",
    "get_core_compression",
    "get_core_strength",
    "global_sandwich_capacity",
    "GlobalSandwichCapacity",
    "ILLUSTRATIVE_DATA_NOTE",
    "ILLUSTRATIVE_FACE_STRENGTH",
    "ILLUSTRATIVE_LOCAL_NOTE",
    "ILLUSTRATIVE_STRENGTH_NOTE",
    "is_dominated",
    "is_dominated_by_capacity",
    "Layer",
    "LimitingConstraint",
    "load_sensitivity_sweep",
    "LoadSensitivityRow",
    "local_patch_force_sweep",
    "local_patch_size_sweep",
    "LocalFailureAssessment",
    "LocalFailureMode",
    "LocalPatchLoad",
    "LocalPatchSweepRow",
    "LocalScreenBasis",
    "mass_properties",
    "MassProperties",
    "OrthotropicCoreMaterial",
    "OrthotropicCoreStrength",
    "pareto_front",
    "pareto_front_by_capacity",
    "preliminary_load_capacity",
    "PreliminaryLoadCapacity",
    "RetentionStatus",
    "SandwichConstraint",
    "SandwichDesignAssessment",
    "SandwichGeometry",
    "SandwichPanel",
    "section_properties",
    "SectionProperties",
    "StrengthAssessment",
    "StrengthBasis",
    "StudyBasis",
    "TradeRow",
    "wrinkling_margin",
    "wrinkling_screening_stress",
    "WrinklingModel",
]
