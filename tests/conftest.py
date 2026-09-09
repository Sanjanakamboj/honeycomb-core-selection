"""Shared reference case for the Milestone 1 verification tests.

The reference case below is deliberately simple so that every expected value in
the test suite can be written as INDEPENDENT arithmetic (literal formulas or
hand-computed constants) rather than by calling the package under test.
"""

from __future__ import annotations

import pytest

from sandwich_panel import CoreMaterial, FaceMaterial, SandwichGeometry, SandwichPanel

# Reference case (SI). Illustrative values, not datasheet values.
B = 0.40  # width            [m]
T_F = 0.0005  # face thickness   [m]
T_C = 0.015  # core thickness   [m]
L = 1.20  # span             [m]
E_F = 70.0e9  # face modulus     [Pa]
RHO_F = 2700.0  # face density     [kg/m^3]
RHO_C = 48.0  # core density     [kg/m^3]
G_C = 50.0e6  # core shear mod   [Pa]
P = 100.0  # point load       [N]


@pytest.fixture
def geometry() -> SandwichGeometry:
    return SandwichGeometry(width=B, face_thickness=T_F, core_thickness=T_C, span=L)


@pytest.fixture
def face() -> FaceMaterial:
    return FaceMaterial(name="illustrative face", youngs_modulus=E_F, density=RHO_F)


@pytest.fixture
def core() -> CoreMaterial:
    return CoreMaterial(name="illustrative core", density=RHO_C, shear_modulus=G_C)


@pytest.fixture
def panel(geometry, face, core) -> SandwichPanel:
    return SandwichPanel(geometry=geometry, face=face, core=core)


# ---------------------------------------------------------------------------
# Milestone 2 study basis (additive; the Milestone 1 fixtures above are
# unchanged). This is the Milestone 1 representative panel, reused verbatim so
# the candidate trade is a clean material-property-only comparison.
# ---------------------------------------------------------------------------

from sandwich_panel import OrthotropicCoreMaterial, StudyBasis  # noqa: E402

M2_B = 0.500  # width           [m]
M2_T_F = 0.0004  # face thickness  [m]
M2_T_C = 0.020  # core thickness  [m]
M2_L = 1.500  # span            [m]
M2_E_F = 70.0e9  # face modulus    [Pa]
M2_RHO_F = 2700.0  # face density    [kg/m^3]
M2_P = 50.0  # point load      [N]

# Independent hand values for this basis:
#   z_f     = 0.020/2 + 0.0004/2                                  = 0.0102 m
#   I_faces = 2 * (0.5*0.0004^3/12 + 0.5*0.0004*0.0102^2)         = 4.1621333333e-8 m^4
#   EI      = 70e9 * 4.1621333333e-8                              = 2913.4933333 N m^2
#   delta_b = 50 * 1.5^3 / (48 * 2913.4933333)                    = 1.2066699998e-3 m
#   A_s     = 0.5 * 0.020                                         = 0.010 m^2
#   delta_s = 50 * 1.5 / (4 * 1 * G * 0.010)                      = 1875 / G  [m]
#   m_faces = 2 * 2700 * 0.0004                                   = 2.16 kg/m^2
M2_EI = 2913.4933333333
M2_DELTA_B = 1.2066699998e-3
M2_SHEAR_AREA = 0.010
M2_FACE_AREAL_MASS = 2.16


@pytest.fixture
def m2_geometry() -> SandwichGeometry:
    return SandwichGeometry(
        width=M2_B, face_thickness=M2_T_F, core_thickness=M2_T_C, span=M2_L
    )


@pytest.fixture
def m2_face() -> FaceMaterial:
    return FaceMaterial(
        name="illustrative M2 face", youngs_modulus=M2_E_F, density=M2_RHO_F
    )


@pytest.fixture
def basis(m2_geometry, m2_face) -> StudyBasis:
    return StudyBasis(geometry=m2_geometry, face=m2_face, load=M2_P)


@pytest.fixture
def ortho_core() -> OrthotropicCoreMaterial:
    """A single orthotropic core with easy round numbers (G_L/G_W = 2.5)."""
    return OrthotropicCoreMaterial(
        name="TEST-CORE",
        density=40.0,
        shear_modulus_L=50.0e6,
        shear_modulus_W=20.0e6,
        family="test",
        source_note="Illustrative test input.",
    )


# ---------------------------------------------------------------------------
# Milestone 3 strength fixtures (additive; Milestone 1-2 fixtures unchanged).
# The study basis is the same M2 basis, so strength demands are:
#
#   sigma_face(P) = (P L / 4)(h/2) / I_faces = P * 0.375 * 0.0104 / 4.1621333e-8
#                                            = P * 93701.923...  Pa
#   tau_core(P)   = (P/2) / (b t_c) = P / (2 * 0.010) = P * 50 Pa
#
# At the P = 50 N reference load: sigma = 4.6850974 MPa, tau = 2500 Pa.
# ---------------------------------------------------------------------------

from sandwich_panel import (  # noqa: E402
    DeflectionRequirement,
    FaceStrength,
    OrthotropicCoreStrength,
    StrengthBasis,
)

M3_FACE_YIELD = 270.0e6  # illustrative face yield [Pa]
M3_SIGMA_PER_N = 0.375 * 0.0104 / (2 * (0.5 * 0.0004**3 / 12 + 0.5 * 0.0004 * 0.0102**2))
M3_TAU_PER_N = 0.5 / (0.5 * 0.020)  # = 50.0 Pa/N
M3_SIGMA_AT_50N = M3_SIGMA_PER_N * 50.0
M3_TAU_AT_50N = M3_TAU_PER_N * 50.0  # = 2500 Pa


@pytest.fixture
def face_strength() -> FaceStrength:
    return FaceStrength(
        name="illustrative test face",
        yield_strength=M3_FACE_YIELD,
        source_note="Illustrative test input.",
    )


@pytest.fixture
def strength_basis(face_strength) -> StrengthBasis:
    return StrengthBasis(face_strength=face_strength, face_design_factor=1.0)


@pytest.fixture
def ortho_core_strength() -> OrthotropicCoreStrength:
    """Strength record matching the ``ortho_core`` fixture (tau_L/tau_W = 2.5)."""
    return OrthotropicCoreStrength(
        name="TEST-CORE",
        shear_strength_L=1.0e6,
        shear_strength_W=0.4e6,
        source_note="Illustrative test input.",
    )


@pytest.fixture
def requirement() -> DeflectionRequirement:
    return DeflectionRequirement(
        maximum_total_deflection=1.5e-3, label="illustrative test limit"
    )
