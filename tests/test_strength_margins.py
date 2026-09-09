"""G-N: face and core shear margins, governing mode, combined feasibility."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    FaceStrength,
    LimitingConstraint,
    OrthotropicCoreStrength,
    StrengthBasis,
    assess_candidate_design,
    assess_strength,
    core_shear_margin,
    evaluate_candidate,
    face_stress_margin,
)

from .conftest import M3_SIGMA_AT_50N, M3_TAU_AT_50N


# -- margin helpers --------------------------------------------------------


def test_margin_helper_hand_calc():
    # MS = allowable / demand - 1
    assert face_stress_margin(100.0, 250.0) == pytest.approx(1.5, rel=1e-15)
    assert core_shear_margin(2500.0, 1.0e6) == pytest.approx(399.0, rel=1e-15)


def test_margin_helper_boundary_is_zero():
    assert face_stress_margin(123.4, 123.4) == pytest.approx(0.0, abs=1e-15)
    assert core_shear_margin(2500.0, 2500.0) == pytest.approx(0.0, abs=1e-15)


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_margin_helpers_validate_inputs(bad):
    with pytest.raises(ValueError):
        face_stress_margin(bad, 100.0)
    with pytest.raises(ValueError):
        face_stress_margin(100.0, bad)
    with pytest.raises(ValueError):
        core_shear_margin(bad, 100.0)
    with pytest.raises(ValueError):
        core_shear_margin(100.0, bad)


# -- G. face margin hand calculation --------------------------------------


def test_face_margin_hand_calc(basis, ortho_core, strength_basis, ortho_core_strength):
    r = evaluate_candidate(basis, ortho_core, "L")
    a = assess_strength(r, strength_basis, ortho_core_strength)
    # sigma at 50 N = 0.375 * 0.0104 / I_faces * 50 = 4.6850974 MPa
    assert a.face_stress == pytest.approx(M3_SIGMA_AT_50N, rel=1e-12)
    assert a.face_stress == pytest.approx(4.6850974e6, rel=1e-6)
    assert a.face_allowable == pytest.approx(270.0e6, rel=1e-15)
    assert a.face_margin == pytest.approx(270.0e6 / M3_SIGMA_AT_50N - 1.0, rel=1e-12)
    assert a.face_margin == pytest.approx(56.6296, rel=1e-4)
    assert a.face_pass is True


def test_face_margin_scales_with_design_factor(basis, ortho_core, face_strength, ortho_core_strength):
    r = evaluate_candidate(basis, ortho_core, "L")
    one = assess_strength(r, StrengthBasis(face_strength=face_strength), ortho_core_strength)
    two = assess_strength(
        r, StrengthBasis(face_strength=face_strength, face_design_factor=2.0), ortho_core_strength
    )
    assert two.face_allowable == pytest.approx(one.face_allowable / 2.0, rel=1e-15)
    assert (two.face_margin + 1.0) == pytest.approx((one.face_margin + 1.0) / 2.0, rel=1e-12)


# -- H. face exact-boundary PASS ------------------------------------------


def test_face_exact_boundary_passes(basis, ortho_core, ortho_core_strength):
    r = evaluate_candidate(basis, ortho_core, "L")
    sb = StrengthBasis(
        face_strength=FaceStrength(name="boundary", yield_strength=r.max_face_stress)
    )
    a = assess_strength(r, sb, ortho_core_strength)
    assert a.face_margin == pytest.approx(0.0, abs=1e-15)
    assert a.face_pass is True


# -- I. face fail case ----------------------------------------------------


def test_face_fail_case(basis, ortho_core, ortho_core_strength):
    r = evaluate_candidate(basis, ortho_core, "L")
    sb = StrengthBasis(
        face_strength=FaceStrength(name="weak", yield_strength=0.99 * r.max_face_stress)
    )
    a = assess_strength(r, sb, ortho_core_strength)
    assert a.face_margin < 0.0
    assert a.face_margin == pytest.approx(-0.01, rel=1e-9)
    assert a.face_pass is False
    assert a.strength_feasible is False


# -- J. core shear margin hand calculation --------------------------------


def test_core_shear_margin_hand_calc(basis, ortho_core, strength_basis, ortho_core_strength):
    rl = evaluate_candidate(basis, ortho_core, "L")
    rw = evaluate_candidate(basis, ortho_core, "W")
    al = assess_strength(rl, strength_basis, ortho_core_strength)
    aw = assess_strength(rw, strength_basis, ortho_core_strength)
    # tau at 50 N = (50/2) / (0.5 * 0.020) = 2500 Pa
    assert al.core_shear_stress == pytest.approx(M3_TAU_AT_50N, rel=1e-12)
    assert al.core_shear_stress == pytest.approx(2500.0, rel=1e-12)
    # L: 1.0e6 / 2500 - 1 = 399 ; W: 0.4e6 / 2500 - 1 = 159
    assert al.core_shear_allowable == 1.0e6
    assert al.core_shear_margin == pytest.approx(399.0, rel=1e-12)
    assert aw.core_shear_allowable == 0.4e6
    assert aw.core_shear_margin == pytest.approx(159.0, rel=1e-12)
    assert al.core_shear_pass and aw.core_shear_pass


def test_core_margin_uses_the_selected_direction(basis, ortho_core, strength_basis, ortho_core_strength):
    al = assess_strength(
        evaluate_candidate(basis, ortho_core, "L"), strength_basis, ortho_core_strength
    )
    aw = assess_strength(
        evaluate_candidate(basis, ortho_core, "W"), strength_basis, ortho_core_strength
    )
    assert al.core_shear_margin > aw.core_shear_margin
    assert (al.core_shear_margin + 1.0) / (aw.core_shear_margin + 1.0) == pytest.approx(
        ortho_core_strength.directional_strength_ratio, rel=1e-12
    )


# -- K. core exact-boundary PASS ------------------------------------------


def test_core_exact_boundary_passes(basis, ortho_core, strength_basis):
    r = evaluate_candidate(basis, ortho_core, "L")
    cs = OrthotropicCoreStrength(
        name="boundary",
        shear_strength_L=r.avg_core_shear_stress,
        shear_strength_W=r.avg_core_shear_stress,
    )
    a = assess_strength(r, strength_basis, cs)
    assert a.core_shear_margin == pytest.approx(0.0, abs=1e-15)
    assert a.core_shear_pass is True
    assert a.strength_feasible is True


# -- L. core fail case ----------------------------------------------------


def test_core_fail_case(basis, ortho_core, strength_basis):
    r = evaluate_candidate(basis, ortho_core, "L")
    cs = OrthotropicCoreStrength(
        name="weak",
        shear_strength_L=0.5 * r.avg_core_shear_stress,
        shear_strength_W=0.5 * r.avg_core_shear_stress,
    )
    a = assess_strength(r, strength_basis, cs)
    assert a.core_shear_margin == pytest.approx(-0.5, rel=1e-12)
    assert a.core_shear_pass is False
    assert a.strength_feasible is False


# -- M. governing mode is the minimum margin, computed not assumed --------


def test_governing_mode_is_face_when_face_margin_is_smaller(
    basis, ortho_core, strength_basis, ortho_core_strength
):
    r = evaluate_candidate(basis, ortho_core, "L")
    a = assess_strength(r, strength_basis, ortho_core_strength)
    assert a.face_margin < a.core_shear_margin
    assert a.governing_mode is LimitingConstraint.FACE_YIELD
    assert a.governing_margin == a.face_margin


def test_governing_mode_is_core_when_core_margin_is_smaller(basis, ortho_core, strength_basis):
    r = evaluate_candidate(basis, ortho_core, "L")
    # tau_allow = 1.2 * demand -> MS_core = 0.2, far below the face margin.
    cs = OrthotropicCoreStrength(
        name="soft",
        shear_strength_L=1.2 * r.avg_core_shear_stress,
        shear_strength_W=1.2 * r.avg_core_shear_stress,
    )
    a = assess_strength(r, strength_basis, cs)
    assert a.core_shear_margin < a.face_margin
    assert a.governing_mode is LimitingConstraint.CORE_SHEAR
    assert a.governing_margin == pytest.approx(0.2, rel=1e-12)


def test_governing_margin_is_always_the_minimum(basis, ortho_core, strength_basis):
    r = evaluate_candidate(basis, ortho_core, "L")
    for factor in (0.5, 1.0, 1.2, 10.0, 1000.0, 1.0e6):
        cs = OrthotropicCoreStrength(
            name="sweep",
            shear_strength_L=factor * r.avg_core_shear_stress,
            shear_strength_W=factor * r.avg_core_shear_stress,
        )
        a = assess_strength(r, strength_basis, cs)
        assert a.governing_margin == min(a.face_margin, a.core_shear_margin)
        expected = (
            LimitingConstraint.FACE_YIELD
            if a.face_margin <= a.core_shear_margin
            else LimitingConstraint.CORE_SHEAR
        )
        assert a.governing_mode is expected


def test_governing_mode_is_never_deflection(basis, ortho_core, strength_basis, ortho_core_strength):
    # The strength assessment must not reach outside its own two modes.
    a = assess_strength(
        evaluate_candidate(basis, ortho_core, "L"), strength_basis, ortho_core_strength
    )
    assert a.governing_mode in (LimitingConstraint.FACE_YIELD, LimitingConstraint.CORE_SHEAR)


# -- N. strength feasible iff both pass -----------------------------------


@pytest.mark.parametrize(
    "face_factor,core_factor,expected",
    [
        (2.0, 2.0, True),
        (1.0, 1.0, True),  # both exactly at the boundary
        (0.9, 2.0, False),
        (2.0, 0.9, False),
        (0.9, 0.9, False),
    ],
)
def test_strength_feasible_is_the_and_of_both_checks(
    basis, ortho_core, face_factor, core_factor, expected
):
    r = evaluate_candidate(basis, ortho_core, "L")
    sb = StrengthBasis(
        face_strength=FaceStrength(
            name="tuned", yield_strength=face_factor * r.max_face_stress
        )
    )
    cs = OrthotropicCoreStrength(
        name="tuned",
        shear_strength_L=core_factor * r.avg_core_shear_stress,
        shear_strength_W=core_factor * r.avg_core_shear_stress,
    )
    a = assess_strength(r, sb, cs)
    assert a.strength_feasible is expected
    assert a.strength_feasible == (a.face_pass and a.core_shear_pass)


# -- combined assessment keeps stiffness and strength separate ------------


def test_overall_feasible_is_the_and_of_deflection_and_strength(
    basis, ortho_core, ortho_core_strength, strength_basis, requirement
):
    a = assess_candidate_design(
        basis, ortho_core, ortho_core_strength, "L", strength_basis, requirement
    )
    assert a.overall_feasible == (a.deflection_feasible and a.strength_feasible)
    assert a.deflection_feasible is True
    assert a.strength_feasible is True
    assert a.overall_feasible is True


def test_deflection_failure_alone_fails_the_overall_screen(
    basis, ortho_core, ortho_core_strength, strength_basis
):
    from sandwich_panel import DeflectionRequirement

    tight = DeflectionRequirement(maximum_total_deflection=1.0e-4)
    a = assess_candidate_design(
        basis, ortho_core, ortho_core_strength, "L", strength_basis, tight
    )
    assert a.deflection_feasible is False
    assert a.strength_feasible is True
    assert a.overall_feasible is False


def test_strength_failure_alone_fails_the_overall_screen(
    basis, ortho_core, ortho_core_strength, requirement
):
    weak = StrengthBasis(face_strength=FaceStrength(name="weak", yield_strength=1.0e6))
    a = assess_candidate_design(
        basis, ortho_core, ortho_core_strength, "L", weak, requirement
    )
    assert a.deflection_feasible is True
    assert a.strength_feasible is False
    assert a.overall_feasible is False


def test_margins_of_different_units_are_never_combined(
    basis, ortho_core, ortho_core_strength, strength_basis, requirement
):
    # The deflection margin is a length; the strength margins are dimensionless.
    # There must be no attribute offering a single blended number.
    a = assess_candidate_design(
        basis, ortho_core, ortho_core_strength, "L", strength_basis, requirement
    )
    assert a.deflection.margin == pytest.approx(1.5e-3 - a.result.total_deflection, rel=1e-12)
    assert abs(a.deflection.margin) < 1.0  # metres
    assert a.strength.governing_margin > 1.0  # dimensionless
    for banned in ("combined_margin", "total_margin", "overall_margin", "margin"):
        assert not hasattr(a, banned)


def test_assess_strength_type_checks(basis, ortho_core, strength_basis, ortho_core_strength):
    r = evaluate_candidate(basis, ortho_core, "L")
    with pytest.raises(TypeError):
        assess_strength(r, "nope", ortho_core_strength)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        assess_strength(r, strength_basis, "nope")  # type: ignore[arg-type]


def test_mismatched_strength_record_rejected(
    basis, ortho_core, strength_basis, requirement
):
    from sandwich_panel import OrthotropicCoreStrength as OCS

    wrong = OCS(name="SOMETHING-ELSE", shear_strength_L=1.0e6, shear_strength_W=0.4e6)
    with pytest.raises(ValueError):
        assess_candidate_design(basis, ortho_core, wrong, "L", strength_basis, requirement)
