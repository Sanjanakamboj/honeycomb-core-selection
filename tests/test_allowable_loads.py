"""O-V: allowable-load calculations, governing constraint and boundary behaviour."""

from __future__ import annotations

import pytest

from sandwich_panel import (
    DeflectionRequirement,
    FaceStrength,
    LimitingConstraint,
    OrthotropicCoreStrength,
    SandwichGeometry,
    StrengthBasis,
    StudyBasis,
    assess_candidate_design,
    evaluate_candidate,
    preliminary_load_capacity,
)

from .conftest import M2_B, M2_E_F, M2_L, M2_RHO_F, M2_T_C, M2_T_F, M3_SIGMA_PER_N


def _basis_at(basis, load):
    return StudyBasis(
        geometry=basis.geometry,
        face=basis.face,
        load=load,
        shear_correction_factor=basis.shear_correction_factor,
    )


def _capacity(basis, core, strength_basis, core_strength, requirement, direction="L"):
    r = evaluate_candidate(basis, core, direction)
    return preliminary_load_capacity(basis, r, strength_basis, core_strength, requirement)


# -- O. face allowable load -----------------------------------------------


def test_face_allowable_load_hand_calc(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    # sigma(P) = P * 0.375 * 0.0104 / I_faces = P * 93701.9477 Pa
    # P_face = 270e6 / 93701.9477 = 2881.4769 N
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement)
    assert c.face_limit == pytest.approx(270.0e6 / M3_SIGMA_PER_N, rel=1e-12)
    assert c.face_limit == pytest.approx(2881.4769, rel=1e-6)


def test_face_allowable_load_is_direction_independent(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    cl = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement, "L")
    cw = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement, "W")
    assert cl.face_limit == cw.face_limit  # bit-for-bit


def test_face_allowable_load_scales_with_the_allowable(
    basis, ortho_core, ortho_core_strength, requirement
):
    weak = StrengthBasis(face_strength=FaceStrength(name="a", yield_strength=135.0e6))
    strong = StrengthBasis(face_strength=FaceStrength(name="b", yield_strength=270.0e6))
    cw = _capacity(basis, ortho_core, weak, ortho_core_strength, requirement)
    cs = _capacity(basis, ortho_core, strong, ortho_core_strength, requirement)
    assert cs.face_limit == pytest.approx(2 * cw.face_limit, rel=1e-12)


def test_face_allowable_load_is_independent_of_the_reference_load(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    # The linear scaling must not depend on where it was evaluated from.
    a = _capacity(_basis_at(basis, 10.0), ortho_core, strength_basis, ortho_core_strength, requirement)
    b = _capacity(_basis_at(basis, 900.0), ortho_core, strength_basis, ortho_core_strength, requirement)
    assert a.face_limit == pytest.approx(b.face_limit, rel=1e-12)
    assert a.core_shear_limit == pytest.approx(b.core_shear_limit, rel=1e-12)
    assert a.deflection_limit == pytest.approx(b.deflection_limit, rel=1e-12)


# -- P. core shear allowable load -----------------------------------------


def test_core_shear_allowable_load_hand_calc(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    # P_core = 2 b t_c tau_allow = 2 * 0.5 * 0.020 * tau = 0.02 * tau
    cl = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement, "L")
    cw = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement, "W")
    assert cl.core_shear_limit == pytest.approx(0.02 * 1.0e6, rel=1e-12)
    assert cl.core_shear_limit == pytest.approx(20000.0, rel=1e-12)
    assert cw.core_shear_limit == pytest.approx(0.02 * 0.4e6, rel=1e-12)
    assert cw.core_shear_limit == pytest.approx(8000.0, rel=1e-12)


def test_core_shear_limit_matches_the_linear_scaling_form(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    # The closed form 2 b t_c tau must agree with P_ref * tau_allow / tau(P_ref).
    r = evaluate_candidate(basis, ortho_core, "L")
    c = preliminary_load_capacity(basis, r, strength_basis, ortho_core_strength, requirement)
    scaled = basis.load * ortho_core_strength.shear_strength_L / r.avg_core_shear_stress
    assert c.core_shear_limit == pytest.approx(scaled, rel=1e-12)


# -- Q. deflection allowable load -----------------------------------------


def test_deflection_allowable_load_hand_calc(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    r = evaluate_candidate(basis, ortho_core, "L")
    c = preliminary_load_capacity(basis, r, strength_basis, ortho_core_strength, requirement)
    # P_defl = P_ref * delta_allow / delta(P_ref) = 50 * 1.5e-3 / delta
    assert c.deflection_limit == pytest.approx(50.0 * 1.5e-3 / r.total_deflection, rel=1e-12)
    # delta at 50 N, G_L = 50 MPa: delta_b = 1.20667e-3, delta_s = 1875/50e6 = 3.75e-5
    expected_delta = 1.2066699998e-3 + 1875.0 / 50.0e6
    assert r.total_deflection == pytest.approx(expected_delta, rel=1e-6)
    assert c.deflection_limit == pytest.approx(50.0 * 1.5e-3 / expected_delta, rel=1e-6)


def test_deflection_limit_is_softer_in_W(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    cl = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement, "L")
    cw = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement, "W")
    assert cw.deflection_limit < cl.deflection_limit


# -- R. preliminary limit is the minimum of the three ---------------------


def test_preliminary_limit_is_the_minimum_of_three(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    for direction in ("L", "W"):
        c = _capacity(
            basis, ortho_core, strength_basis, ortho_core_strength, requirement, direction
        )
        assert c.preliminary_limit == min(
            c.face_limit, c.core_shear_limit, c.deflection_limit
        )
        assert c.strength_limit == min(c.face_limit, c.core_shear_limit)


def test_strength_limit_excludes_deflection(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement)
    assert c.deflection_limit < c.strength_limit  # deflection governs overall here
    assert c.strength_limit == min(c.face_limit, c.core_shear_limit)
    assert c.strength_governing_mode in (
        LimitingConstraint.FACE_YIELD,
        LimitingConstraint.CORE_SHEAR,
    )
    assert c.strength_governing_mode is not LimitingConstraint.DEFLECTION


# -- S. governing constraint is computed, not hard-coded ------------------


def test_governing_constraint_is_deflection_for_the_canonical_basis(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement)
    assert c.governing_constraint is LimitingConstraint.DEFLECTION


def test_governing_constraint_becomes_face_yield_with_a_loose_deflection_limit(
    basis, ortho_core, strength_basis, ortho_core_strength
):
    loose = DeflectionRequirement(maximum_total_deflection=1.0)  # 1 m: never governs
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, loose)
    assert c.governing_constraint is LimitingConstraint.FACE_YIELD
    assert c.preliminary_limit == pytest.approx(c.face_limit, rel=1e-15)


def test_governing_constraint_becomes_core_shear_with_a_weak_core(
    basis, ortho_core, strength_basis
):
    loose = DeflectionRequirement(maximum_total_deflection=1.0)
    weak = OrthotropicCoreStrength(
        name="TEST-CORE", shear_strength_L=1.0e4, shear_strength_W=1.0e4
    )
    c = _capacity(basis, ortho_core, strength_basis, weak, loose)
    # P_core = 0.02 * 1.0e4 = 200 N, far below the face limit of ~2881 N.
    assert c.core_shear_limit == pytest.approx(200.0, rel=1e-12)
    assert c.governing_constraint is LimitingConstraint.CORE_SHEAR
    assert c.strength_governing_mode is LimitingConstraint.CORE_SHEAR


def test_governing_constraint_always_matches_the_minimum(basis, ortho_core, strength_basis):
    """Sweep the deflection limit so each of the three constraints takes a turn."""
    weak = OrthotropicCoreStrength(
        name="TEST-CORE", shear_strength_L=5.0e4, shear_strength_W=5.0e4
    )  # P_core = 1000 N
    seen = set()
    for limit in (1.0e-4, 1.5e-3, 5.0e-2, 1.0):
        c = _capacity(basis, ortho_core, strength_basis, weak, DeflectionRequirement(limit))
        limits = {
            LimitingConstraint.DEFLECTION: c.deflection_limit,
            LimitingConstraint.FACE_YIELD: c.face_limit,
            LimitingConstraint.CORE_SHEAR: c.core_shear_limit,
        }
        assert c.preliminary_limit == pytest.approx(min(limits.values()), rel=1e-15)
        assert limits[c.governing_constraint] == pytest.approx(c.preliminary_limit, rel=1e-15)
        seen.add(c.governing_constraint)
    # The sweep must actually exercise more than one governing constraint.
    assert len(seen) >= 2


# -- T / U / V. behaviour at the returned load ----------------------------


def _screen_at(basis, load, core, core_strength, strength_basis, requirement):
    return assess_candidate_design(
        _basis_at(basis, load), core, core_strength, "L", strength_basis, requirement
    )


def test_face_limit_gives_zero_margin_at_that_load(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    # T.
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement)
    a = _screen_at(
        basis, c.face_limit, ortho_core, ortho_core_strength, strength_basis, requirement
    )
    assert a.strength.face_margin == pytest.approx(0.0, abs=1e-12)
    assert a.strength.face_pass is True


def test_core_limit_gives_zero_margin_at_that_load(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement)
    a = _screen_at(
        basis, c.core_shear_limit, ortho_core, ortho_core_strength, strength_basis, requirement
    )
    assert a.strength.core_shear_margin == pytest.approx(0.0, abs=1e-12)
    assert a.strength.core_shear_pass is True


def test_deflection_limit_gives_zero_margin_at_that_load(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement)
    a = _screen_at(
        basis, c.deflection_limit, ortho_core, ortho_core_strength, strength_basis, requirement
    )
    assert a.deflection.margin == pytest.approx(0.0, abs=1e-15)
    assert a.deflection_feasible is True
    assert a.overall_feasible is True


def test_just_below_the_preliminary_limit_passes(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    # U.
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement)
    a = _screen_at(
        basis, 0.999 * c.preliminary_limit, ortho_core, ortho_core_strength,
        strength_basis, requirement,
    )
    assert a.overall_feasible is True


def test_just_above_the_preliminary_limit_fails(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    # V.
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement)
    a = _screen_at(
        basis, 1.001 * c.preliminary_limit, ortho_core, ortho_core_strength,
        strength_basis, requirement,
    )
    assert a.overall_feasible is False


def test_just_above_the_face_limit_fails_on_strength(basis, ortho_core, strength_basis, ortho_core_strength):
    loose = DeflectionRequirement(maximum_total_deflection=1.0)
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, loose)
    below = _screen_at(basis, 0.999 * c.face_limit, ortho_core, ortho_core_strength, strength_basis, loose)
    above = _screen_at(basis, 1.001 * c.face_limit, ortho_core, ortho_core_strength, strength_basis, loose)
    assert below.strength_feasible is True
    assert above.strength_feasible is False
    assert above.strength.governing_mode is LimitingConstraint.FACE_YIELD


# -- capacity-to-mass indicator -------------------------------------------


def test_capacity_to_areal_mass_indicator_hand_calc(
    basis, ortho_core, strength_basis, ortho_core_strength, requirement
):
    c = _capacity(basis, ortho_core, strength_basis, ortho_core_strength, requirement)
    # areal mass = 2*2700*0.0004 + 40*0.020 = 2.96 kg/m^2
    assert c.areal_mass == pytest.approx(2.96, rel=1e-12)
    assert c.capacity_to_areal_mass == pytest.approx(c.preliminary_limit / 2.96, rel=1e-12)


def test_capacity_requires_a_deflection_requirement(basis, ortho_core, strength_basis, ortho_core_strength):
    r = evaluate_candidate(basis, ortho_core, "L")
    with pytest.raises(TypeError):
        preliminary_load_capacity(basis, r, strength_basis, ortho_core_strength, 1.5e-3)  # type: ignore[arg-type]


def test_capacity_uses_the_actual_geometry(ortho_core, strength_basis, ortho_core_strength, requirement, m2_face):
    # Doubling the width doubles the core shear area and so the core shear limit.
    wide = StudyBasis(
        geometry=SandwichGeometry(
            width=2 * M2_B, face_thickness=M2_T_F, core_thickness=M2_T_C, span=M2_L
        ),
        face=m2_face,
        load=50.0,
    )
    c = _capacity(wide, ortho_core, strength_basis, ortho_core_strength, requirement)
    # P_core = 2 * b * t_c * tau = 2 * 1.0 * 0.020 * 1.0e6 = 40000 N
    assert c.core_shear_limit == pytest.approx(2 * (2 * M2_B) * M2_T_C * 1.0e6, rel=1e-12)
    assert c.core_shear_limit == pytest.approx(40000.0, rel=1e-12)
    assert M2_E_F == 70.0e9 and M2_RHO_F == 2700.0
