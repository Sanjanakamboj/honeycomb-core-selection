"""L-S: candidate trade results, and T-X: the deflection requirement."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    CANDIDATE_CORES,
    CoreShearDirection,
    DeflectionRequirement,
    FaceMaterial,
    OrthotropicCoreMaterial,
    StudyBasis,
    build_trade_table,
    evaluate_candidate,
    evaluate_candidates,
    is_dominated,
    pareto_front,
)

from .conftest import (
    M2_DELTA_B,
    M2_EI,
    M2_FACE_AREAL_MASS,
    M2_P,
    M2_SHEAR_AREA,
    M2_T_C,
)


# -- study basis validation -----------------------------------------------


@pytest.mark.parametrize("bad", [0.0, -50.0, math.nan, math.inf])
def test_study_basis_rejects_invalid_load(m2_geometry, m2_face, bad):
    with pytest.raises(ValueError):
        StudyBasis(geometry=m2_geometry, face=m2_face, load=bad)


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan])
def test_study_basis_rejects_invalid_kappa(m2_geometry, m2_face, bad):
    with pytest.raises(ValueError):
        StudyBasis(
            geometry=m2_geometry, face=m2_face, load=50.0, shear_correction_factor=bad
        )


def test_study_basis_type_checks(m2_geometry, m2_face):
    with pytest.raises(TypeError):
        StudyBasis(geometry="nope", face=m2_face, load=50.0)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        StudyBasis(geometry=m2_geometry, face="nope", load=50.0)  # type: ignore[arg-type]


def test_evaluate_candidate_rejects_a_non_orthotropic_core(basis, core):
    with pytest.raises(TypeError):
        evaluate_candidate(basis, core, "L")  # Milestone 1 CoreMaterial


def test_evaluate_candidate_rejects_a_bad_direction(basis, ortho_core):
    with pytest.raises(ValueError):
        evaluate_candidate(basis, ortho_core, "LW")


def test_evaluate_candidates_rejects_empty_inputs(basis):
    with pytest.raises(ValueError):
        evaluate_candidates(basis, [])
    with pytest.raises(ValueError):
        evaluate_candidates(basis, CANDIDATE_CORES, directions=[])


# -- L / M. face-dominated invariance across candidates -------------------


def test_same_EI_across_every_candidate_and_direction(basis):
    # L. The core carries no bending normal stiffness, so EI cannot move.
    results = evaluate_candidates(basis, CANDIDATE_CORES)
    reference = results[0].flexural_rigidity
    for r in results:
        assert r.flexural_rigidity == reference  # bit-for-bit
    assert reference == pytest.approx(M2_EI, rel=1e-9)


def test_same_bending_deflection_across_every_candidate_and_direction(basis):
    # M.
    results = evaluate_candidates(basis, CANDIDATE_CORES)
    reference = results[0].bending_deflection
    for r in results:
        assert r.bending_deflection == reference  # bit-for-bit
    assert reference == pytest.approx(M2_DELTA_B, rel=1e-6)


def test_same_face_stress_across_every_candidate(basis):
    # Face stress is a geometry/load quantity here, so it cannot move either.
    results = evaluate_candidates(basis, CANDIDATE_CORES)
    assert len({r.max_face_stress for r in results}) == 1


def test_same_core_shear_stress_across_every_candidate(basis):
    # tau = V / (b t_c) depends on geometry and load only, not on G or rho.
    results = evaluate_candidates(basis, CANDIDATE_CORES)
    assert len({r.avg_core_shear_stress for r in results}) == 1
    # V_max = 50/2 = 25 N ; A_s = 0.010 m^2 -> 2500 Pa
    assert results[0].avg_core_shear_stress == pytest.approx(2500.0, rel=1e-12)


# -- N. mass moves only with core density ---------------------------------


def test_total_areal_mass_changes_only_with_core_density(basis):
    results = evaluate_candidates(basis, CANDIDATE_CORES)
    for r in results:
        assert r.face_areal_mass == pytest.approx(M2_FACE_AREAL_MASS, rel=1e-12)
        # m_A = 2.16 + rho_c * 0.020
        assert r.core_areal_mass == pytest.approx(r.core_density * M2_T_C, rel=1e-12)
        assert r.areal_mass == pytest.approx(M2_FACE_AREAL_MASS + r.core_density * 0.020, rel=1e-12)


def test_areal_mass_is_identical_between_L_and_W(basis):
    # Direction changes stiffness, never mass.
    for core in CANDIDATE_CORES:
        rl = evaluate_candidate(basis, core, "L")
        rw = evaluate_candidate(basis, core, "W")
        assert rl.areal_mass == rw.areal_mass
        assert rl.total_mass == rw.total_mass


def test_areal_mass_hand_calc_for_one_candidate(basis, ortho_core):
    # 2*2700*0.0004 + 40*0.020 = 2.16 + 0.80 = 2.96 kg/m^2
    r = evaluate_candidate(basis, ortho_core, "L")
    assert r.areal_mass == pytest.approx(2.96, rel=1e-12)
    assert r.core_mass_fraction == pytest.approx(0.80 / 2.96, rel=1e-12)


# -- S. panel mass consistency --------------------------------------------


def test_panel_mass_consistency(basis):
    # plan area = 0.5 * 1.5 = 0.75 m^2
    for r in evaluate_candidates(basis, CANDIDATE_CORES):
        assert r.total_mass == pytest.approx(r.areal_mass * 0.75, rel=1e-12)
        assert r.face_areal_mass + r.core_areal_mass == pytest.approx(r.areal_mass, rel=1e-15)


# -- O. shear deflection moves only with the selected G -------------------


def test_shear_deflection_hand_calc(basis, ortho_core):
    # delta_s = P L / (4 kappa G A_s) = 50*1.5/(4*G*0.010) = 1875 / G
    rl = evaluate_candidate(basis, ortho_core, "L")
    rw = evaluate_candidate(basis, ortho_core, "W")
    assert rl.shear_deflection == pytest.approx(1875.0 / 50.0e6, rel=1e-12)
    assert rw.shear_deflection == pytest.approx(1875.0 / 20.0e6, rel=1e-12)
    assert rl.effective_shear_modulus == 50.0e6
    assert rw.effective_shear_modulus == 20.0e6
    assert M2_SHEAR_AREA == 0.010


def test_shear_deflection_depends_only_on_the_selected_modulus(basis):
    # Two cores with different densities but the SAME G_L must give the same
    # shear deflection.
    a = OrthotropicCoreMaterial(name="a", density=30.0, shear_modulus_L=40e6, shear_modulus_W=9e6)
    b = OrthotropicCoreMaterial(name="b", density=90.0, shear_modulus_L=40e6, shear_modulus_W=1e6)
    ra = evaluate_candidate(basis, a, "L")
    rb = evaluate_candidate(basis, b, "L")
    assert ra.shear_deflection == rb.shear_deflection
    assert ra.total_deflection == rb.total_deflection
    assert ra.areal_mass != rb.areal_mass


# -- P. directional identity ----------------------------------------------


def test_W_over_L_shear_deflection_ratio_equals_G_L_over_G_W(basis):
    for core in CANDIDATE_CORES:
        rl = evaluate_candidate(basis, core, "L")
        rw = evaluate_candidate(basis, core, "W")
        assert rw.shear_deflection / rl.shear_deflection == pytest.approx(
            core.directional_shear_ratio, rel=1e-12
        )


def test_W_is_always_the_softer_direction(basis):
    for core in CANDIDATE_CORES:
        rl = evaluate_candidate(basis, core, "L")
        rw = evaluate_candidate(basis, core, "W")
        assert rw.shear_deflection > rl.shear_deflection
        assert rw.total_deflection > rl.total_deflection
        assert rw.shear_fraction > rl.shear_fraction


# -- Q / R. deflection identity and bounded shear fraction ----------------


def test_total_deflection_identity(basis):
    # Q.
    for r in evaluate_candidates(basis, CANDIDATE_CORES):
        assert r.total_deflection == pytest.approx(
            r.bending_deflection + r.shear_deflection, rel=1e-15
        )


def test_shear_fraction_bounded_and_consistent(basis):
    # R.
    for r in evaluate_candidates(basis, CANDIDATE_CORES):
        assert 0.0 < r.shear_fraction < 1.0
        assert r.shear_fraction == pytest.approx(
            r.shear_deflection / r.total_deflection, rel=1e-15
        )


def test_specific_shear_stiffness_indicator_hand_calc(basis, ortho_core):
    r = evaluate_candidate(basis, ortho_core, "L")
    assert r.specific_shear_stiffness == pytest.approx(50.0e6 / 40.0, rel=1e-15)


def test_result_carries_direction_and_label(basis, ortho_core):
    r = evaluate_candidate(basis, ortho_core, "W")
    assert r.direction is CoreShearDirection.W
    assert r.label == "TEST-CORE [W]"
    assert r.core_thickness == pytest.approx(M2_T_C)


def test_evaluate_candidates_ordering_is_direction_major(basis):
    results = evaluate_candidates(basis, CANDIDATE_CORES)
    n = len(CANDIDATE_CORES)
    assert len(results) == 2 * n
    assert all(r.direction is CoreShearDirection.L for r in results[:n])
    assert all(r.direction is CoreShearDirection.W for r in results[n:])
    assert [r.core_name for r in results[:n]] == [c.name for c in CANDIDATE_CORES]


# -- T-X. deflection requirement ------------------------------------------


@pytest.mark.parametrize("bad", [0.0, -1.0e-3, math.nan, math.inf, -math.inf])
def test_requirement_validation(bad):
    # W.
    with pytest.raises(ValueError):
        DeflectionRequirement(maximum_total_deflection=bad)


def test_requirement_pass_case():
    # T.
    a = DeflectionRequirement(maximum_total_deflection=1.5e-3).assess(1.2535e-3)
    assert a.feasible is True
    assert a.margin > 0.0
    assert a.normalised_margin > 0.0


def test_requirement_exact_boundary_passes():
    # U. The convention is `actual <= allowable`, so equality PASSES.
    limit = 1.5e-3
    a = DeflectionRequirement(maximum_total_deflection=limit).assess(limit)
    assert a.feasible is True
    assert a.margin == pytest.approx(0.0, abs=1e-18)
    assert a.normalised_margin == pytest.approx(0.0, abs=1e-15)


def test_requirement_fail_case():
    # V.
    a = DeflectionRequirement(maximum_total_deflection=1.0e-3).assess(1.2535e-3)
    assert a.feasible is False
    assert a.margin < 0.0
    assert a.normalised_margin < 0.0


def test_margin_identity():
    # X.
    limit, actual = 1.5e-3, 1.2535e-3
    a = DeflectionRequirement(maximum_total_deflection=limit).assess(actual)
    assert a.margin == pytest.approx(limit - actual, rel=1e-15)
    assert a.normalised_margin == pytest.approx(limit / actual - 1.0, rel=1e-15)
    assert a.allowable_deflection == limit
    assert a.total_deflection == actual


@pytest.mark.parametrize("bad", [0.0, -1.0e-3, math.nan])
def test_requirement_rejects_invalid_deflection_input(bad):
    with pytest.raises(ValueError):
        DeflectionRequirement(maximum_total_deflection=1.5e-3).assess(bad)


def test_requirement_label_is_carried_through():
    req = DeflectionRequirement(maximum_total_deflection=1.5e-3, label="illustrative limit")
    assert "illustrative" in req.label


# -- trade table ----------------------------------------------------------


def test_trade_table_shape_and_order(basis):
    req = DeflectionRequirement(maximum_total_deflection=1.5e-3)
    table = build_trade_table(basis, CANDIDATE_CORES, requirement=req)
    assert len(table) == 2 * len(CANDIDATE_CORES)
    for row in table:
        assert row.assessment is not None
        assert row.feasible == row.assessment.feasible
        assert row.margin == row.assessment.margin
        assert row.assessment.total_deflection == row.result.total_deflection


def test_trade_table_without_a_requirement_leaves_feasibility_unknown(basis):
    table = build_trade_table(basis, CANDIDATE_CORES)
    for row in table:
        assert row.assessment is None
        assert row.feasible is None
        assert row.margin is None


def test_trade_table_reports_mixed_outcomes_when_the_limit_bites(basis):
    # A tight limit must be able to separate L from W for the softest core.
    softest = min(CANDIDATE_CORES, key=lambda c: c.shear_modulus_W)
    rl = evaluate_candidate(basis, softest, "L")
    rw = evaluate_candidate(basis, softest, "W")
    limit = 0.5 * (rl.total_deflection + rw.total_deflection)
    req = DeflectionRequirement(maximum_total_deflection=limit)
    assert req.assess(rl.total_deflection).feasible is True
    assert req.assess(rw.total_deflection).feasible is False


# -- preliminary dominance ------------------------------------------------


def test_pareto_front_excludes_a_dominated_candidate(basis):
    results = evaluate_candidates(basis, CANDIDATE_CORES, directions=["L"])
    front = pareto_front(results)
    assert front  # never empty
    for r in front:
        assert not is_dominated(r, results)
    for r in results:
        if r not in front:
            assert is_dominated(r, results)


def test_dominance_requires_no_worse_on_both_and_better_on_one(basis):
    results = evaluate_candidates(basis, CANDIDATE_CORES, directions=["L"])
    for r in results:
        if is_dominated(r, results):
            assert any(
                o.areal_mass <= r.areal_mass
                and o.total_deflection <= r.total_deflection
                and (o.areal_mass < r.areal_mass or o.total_deflection < r.total_deflection)
                for o in results
                if o is not r
            )


def test_a_candidate_never_dominates_itself(basis, ortho_core):
    r = evaluate_candidate(basis, ortho_core, "L")
    assert is_dominated(r, [r]) is False


def test_the_lightest_candidate_is_never_dominated(basis):
    results = evaluate_candidates(basis, CANDIDATE_CORES, directions=["L"])
    lightest = min(results, key=lambda r: r.areal_mass)
    assert not is_dominated(lightest, results)


def test_the_lowest_deflection_candidate_is_never_dominated(basis):
    results = evaluate_candidates(basis, CANDIDATE_CORES, directions=["L"])
    stiffest = min(results, key=lambda r: r.total_deflection)
    assert not is_dominated(stiffest, results)


def test_pareto_front_preserves_input_order(basis):
    results = evaluate_candidates(basis, CANDIDATE_CORES, directions=["L"])
    front = pareto_front(results)
    assert [r.core_name for r in front] == [
        r.core_name for r in results if r in front
    ]


def test_face_material_does_not_affect_the_candidate_ranking_axes(m2_geometry, ortho_core):
    # Changing the face modulus moves EI and bending deflection for everyone
    # equally; it must not change which core is lighter.
    stiff_face = FaceMaterial(name="stiff", youngs_modulus=140.0e9, density=2700.0)
    b2 = StudyBasis(geometry=m2_geometry, face=stiff_face, load=M2_P)
    r = evaluate_candidate(b2, ortho_core, "L")
    assert r.flexural_rigidity == pytest.approx(2 * M2_EI, rel=1e-9)
    assert r.areal_mass == pytest.approx(2.96, rel=1e-12)
