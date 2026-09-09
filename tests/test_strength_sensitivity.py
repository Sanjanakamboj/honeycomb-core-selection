"""AD-AN, AP, AQ: load scaling, core-depth capacity, regression and determinism."""

from __future__ import annotations

import runpy
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from sandwich_panel import (
    CANDIDATE_CORES,
    CoreShearDirection,
    LimitingConstraint,
    StudyBasis,
    assess_candidate_design,
    build_design_table,
    build_trade_table,
    core_depth_capacity_sweep,
    evaluate_candidates,
    get_core,
    get_core_strength,
    load_sensitivity_sweep,
    pareto_front_by_capacity,
)

LOADS = [25.0, 50.0, 100.0, 500.0, 1000.0, 2000.0, 3000.0]
CORE_DEPTHS = [0.005, 0.010, 0.015, 0.020, 0.025]
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "core_strength_screen.py"


def _at(basis, load):
    return StudyBasis(
        geometry=basis.geometry,
        face=basis.face,
        load=load,
        shear_correction_factor=basis.shear_correction_factor,
    )


# -- AD-AI. load scaling ---------------------------------------------------


def test_all_demands_scale_linearly_with_load(
    basis, ortho_core, ortho_core_strength, strength_basis, requirement
):
    # AD, AE, AF, AG, AH.
    one = assess_candidate_design(
        _at(basis, 50.0), ortho_core, ortho_core_strength, "L", strength_basis, requirement
    )
    four = assess_candidate_design(
        _at(basis, 200.0), ortho_core, ortho_core_strength, "L", strength_basis, requirement
    )
    assert four.strength.face_stress == pytest.approx(4 * one.strength.face_stress, rel=1e-12)
    assert four.strength.core_shear_stress == pytest.approx(
        4 * one.strength.core_shear_stress, rel=1e-12
    )
    assert four.result.bending_deflection == pytest.approx(
        4 * one.result.bending_deflection, rel=1e-12
    )
    assert four.result.shear_deflection == pytest.approx(
        4 * one.result.shear_deflection, rel=1e-12
    )
    assert four.result.total_deflection == pytest.approx(
        4 * one.result.total_deflection, rel=1e-12
    )


def test_demand_ratios_double_when_the_load_doubles(
    basis, ortho_core, ortho_core_strength, strength_basis, requirement
):
    # AI. MS = allowable/demand - 1, so (MS + 1) halves when the demand doubles.
    one = assess_candidate_design(
        _at(basis, 50.0), ortho_core, ortho_core_strength, "L", strength_basis, requirement
    )
    two = assess_candidate_design(
        _at(basis, 100.0), ortho_core, ortho_core_strength, "L", strength_basis, requirement
    )
    assert (two.strength.face_margin + 1.0) == pytest.approx(
        (one.strength.face_margin + 1.0) / 2.0, rel=1e-12
    )
    assert (two.strength.core_shear_margin + 1.0) == pytest.approx(
        (one.strength.core_shear_margin + 1.0) / 2.0, rel=1e-12
    )


def test_load_capacities_do_not_depend_on_the_evaluation_load(
    basis, ortho_core, ortho_core_strength, strength_basis, requirement
):
    caps = [
        assess_candidate_design(
            _at(basis, p), ortho_core, ortho_core_strength, "L", strength_basis, requirement
        ).capacity
        for p in LOADS
    ]
    for c in caps[1:]:
        assert c.face_limit == pytest.approx(caps[0].face_limit, rel=1e-12)
        assert c.core_shear_limit == pytest.approx(caps[0].core_shear_limit, rel=1e-12)
        assert c.deflection_limit == pytest.approx(caps[0].deflection_limit, rel=1e-12)
        assert c.governing_constraint is caps[0].governing_constraint


def test_load_sweep_shape_and_monotonicity(basis, strength_basis, requirement):
    rows = load_sensitivity_sweep(
        basis, get_core("HC-AL-45"), get_core_strength("HC-AL-45"), LOADS,
        strength_basis, requirement,
    )
    assert len(rows) == 2 * len(LOADS)
    for direction in (CoreShearDirection.L, CoreShearDirection.W):
        sub = [r for r in rows if r.direction is direction]
        assert all(b.total_deflection > a.total_deflection for a, b in zip(sub, sub[1:]))
        assert all(b.face_stress > a.face_stress for a, b in zip(sub, sub[1:]))
        assert all(b.face_margin < a.face_margin for a, b in zip(sub, sub[1:]))
        assert all(b.core_shear_margin < a.core_shear_margin for a, b in zip(sub, sub[1:]))


def test_load_sweep_crosses_the_deflection_limit_before_face_yield(basis, strength_basis, requirement):
    rows = load_sensitivity_sweep(
        basis, get_core("HC-AL-45"), get_core_strength("HC-AL-45"), LOADS,
        strength_basis, requirement,
    )
    lrows = [r for r in rows if r.direction is CoreShearDirection.L]
    first_defl_fail = next(r.load for r in lrows if not r.deflection_feasible)
    first_strength_fail = next(r.load for r in lrows if not r.strength_feasible)
    assert first_defl_fail < first_strength_fail
    # Core shear never governs anywhere in this range.
    assert all(r.core_shear_margin > 0.0 for r in rows)
    assert all(r.governing_constraint is LimitingConstraint.DEFLECTION for r in rows)


def test_load_sweep_rejects_empty_inputs(basis, strength_basis, requirement):
    core, cs = get_core("HC-AL-45"), get_core_strength("HC-AL-45")
    with pytest.raises(ValueError):
        load_sensitivity_sweep(basis, core, cs, [], strength_basis, requirement)
    with pytest.raises(ValueError):
        load_sensitivity_sweep(basis, core, cs, LOADS, strength_basis, requirement, directions=[])


# -- AJ-AN. core depth ------------------------------------------------------


@pytest.fixture
def depth_rows(basis, strength_basis, requirement):
    return core_depth_capacity_sweep(
        basis, get_core("HC-AL-45"), get_core_strength("HC-AL-45"), CORE_DEPTHS,
        strength_basis, requirement,
    )


def test_thicker_core_increases_EI(depth_rows):
    # AJ.
    assert all(b.flexural_rigidity > a.flexural_rigidity for a, b in zip(depth_rows, depth_rows[1:]))


def test_thicker_core_increases_mass(depth_rows):
    # AK. m_A = 2.16 + 45 * t_c
    assert all(b.areal_mass > a.areal_mass for a, b in zip(depth_rows, depth_rows[1:]))
    for row in depth_rows:
        assert row.areal_mass == pytest.approx(2.16 + 45.0 * row.core_thickness, rel=1e-12)


def test_thicker_core_raises_the_face_yield_load_limit(depth_rows):
    # AL.
    assert all(b.face_limit > a.face_limit for a, b in zip(depth_rows, depth_rows[1:]))


def test_thicker_core_raises_the_core_shear_load_limit(depth_rows):
    # AM. P_core = 2 b t_c tau, exactly linear in t_c.
    assert all(
        b.core_shear_limit_L > a.core_shear_limit_L for a, b in zip(depth_rows, depth_rows[1:])
    )
    assert all(
        b.core_shear_limit_W > a.core_shear_limit_W for a, b in zip(depth_rows, depth_rows[1:])
    )
    for row in depth_rows:
        assert row.core_shear_limit_L == pytest.approx(
            2 * 0.5 * row.core_thickness * 1.60e6, rel=1e-12
        )


def test_thicker_core_raises_the_deflection_load_limit(depth_rows):
    # AN.
    assert all(
        b.deflection_limit_L > a.deflection_limit_L for a, b in zip(depth_rows, depth_rows[1:])
    )
    assert all(
        b.deflection_limit_W > a.deflection_limit_W for a, b in zip(depth_rows, depth_rows[1:])
    )


def test_thicker_core_raises_the_overall_preliminary_limit(depth_rows):
    assert all(
        b.preliminary_limit_L > a.preliminary_limit_L for a, b in zip(depth_rows, depth_rows[1:])
    )
    assert all(
        b.preliminary_limit_W > a.preliminary_limit_W for a, b in zip(depth_rows, depth_rows[1:])
    )


def test_deflection_limit_grows_faster_than_the_strength_limits(depth_rows):
    # EI ~ t_c^2 drives the deflection limit; the strength limits go as ~t_c.
    first, last = depth_rows[0], depth_rows[-1]
    defl_growth = last.deflection_limit_L / first.deflection_limit_L
    face_growth = last.face_limit / first.face_limit
    core_growth = last.core_shear_limit_L / first.core_shear_limit_L
    assert defl_growth > face_growth
    assert core_growth == pytest.approx(CORE_DEPTHS[-1] / CORE_DEPTHS[0], rel=1e-12)


def test_deflection_still_governs_across_the_whole_core_depth_range(depth_rows):
    for row in depth_rows:
        assert row.governing_constraint_L is LimitingConstraint.DEFLECTION
        assert row.governing_constraint_W is LimitingConstraint.DEFLECTION
        assert row.preliminary_limit_L == pytest.approx(row.deflection_limit_L, rel=1e-15)


def test_core_depth_sweep_does_not_mutate_the_basis(basis, strength_basis, requirement):
    before = basis.geometry.core_thickness
    core_depth_capacity_sweep(
        basis, get_core("HC-AL-45"), get_core_strength("HC-AL-45"), CORE_DEPTHS,
        strength_basis, requirement,
    )
    assert basis.geometry.core_thickness == before


def test_core_depth_sweep_rejects_empty_input(basis, strength_basis, requirement):
    with pytest.raises(ValueError):
        core_depth_capacity_sweep(
            basis, get_core("HC-AL-45"), get_core_strength("HC-AL-45"), [],
            strength_basis, requirement,
        )


# -- dominance on (mass down, capacity up) --------------------------------


def test_capacity_pareto_front_is_consistent(basis, strength_basis, requirement):
    table = build_design_table(basis, strength_basis, requirement)
    front = pareto_front_by_capacity(table)
    assert front
    from sandwich_panel import is_dominated_by_capacity

    for a in front:
        assert not is_dominated_by_capacity(a, table)
    for a in table:
        if a not in front:
            assert is_dominated_by_capacity(a, table)


def test_lightest_and_highest_capacity_are_never_dominated(basis, strength_basis, requirement):
    from sandwich_panel import is_dominated_by_capacity

    table = build_design_table(basis, strength_basis, requirement)
    lightest = min(table, key=lambda a: a.result.areal_mass)
    strongest = max(table, key=lambda a: a.capacity.preliminary_limit)
    assert not is_dominated_by_capacity(lightest, table)
    assert not is_dominated_by_capacity(strongest, table)


# -- AP. Milestone 2 results unchanged by the Milestone 3 layer ------------


def test_milestone2_candidate_results_are_unchanged(basis, strength_basis, requirement):
    m2 = evaluate_candidates(basis, CANDIDATE_CORES)
    m3 = [a.result for a in build_design_table(basis, strength_basis, requirement)]
    assert len(m2) == len(m3)
    for a, b in zip(m2, m3):
        assert asdict(a) == asdict(b)


def test_milestone2_deflection_assessments_are_unchanged(basis, strength_basis, requirement):
    from sandwich_panel import DeflectionRequirement

    req = DeflectionRequirement(maximum_total_deflection=1.5e-3)
    m2 = build_trade_table(basis, CANDIDATE_CORES, requirement=req)
    m3 = build_design_table(basis, strength_basis, req)
    assert len(m2) == len(m3)
    for row, a in zip(m2, m3):
        assert asdict(row.assessment) == asdict(a.deflection)


# -- AQ. determinism -------------------------------------------------------


def test_strength_assessment_is_deterministic(
    basis, ortho_core, ortho_core_strength, strength_basis, requirement
):
    def snap():
        a = assess_candidate_design(
            basis, ortho_core, ortho_core_strength, "L", strength_basis, requirement
        )
        return (asdict(a.strength), asdict(a.capacity), asdict(a.deflection))

    first = snap()
    for _ in range(5):
        assert snap() == first


def test_design_table_is_deterministic(basis, strength_basis, requirement):
    def snap():
        return [
            (
                a.label,
                a.result.areal_mass,
                a.strength.face_margin,
                a.strength.core_shear_margin,
                a.capacity.preliminary_limit,
                str(a.capacity.governing_constraint),
                a.overall_feasible,
            )
            for a in build_design_table(basis, strength_basis, requirement)
        ]

    first = snap()
    for _ in range(5):
        assert snap() == first


def test_sweeps_are_deterministic(basis, strength_basis, requirement):
    def snap():
        return [
            (r.core_thickness, r.face_limit, r.preliminary_limit_L, r.preliminary_limit_W)
            for r in core_depth_capacity_sweep(
                basis, get_core("HC-AL-45"), get_core_strength("HC-AL-45"), CORE_DEPTHS,
                strength_basis, requirement,
            )
        ]

    first = snap()
    for _ in range(3):
        assert snap() == first


# -- example smoke test ----------------------------------------------------


def _run_example(capsys):
    saved = sys.argv[:]
    sys.argv = [str(EXAMPLE)]
    try:
        runpy.run_path(str(EXAMPLE), run_name="__main__")
    finally:
        sys.argv = saved
    return capsys.readouterr().out


def test_strength_example_runs(capsys):
    out = _run_example(capsys)
    for heading in (
        "STUDY BASIS",
        "BASELINE DEMAND",
        "50 N CANDIDATE SCREEN",
        "ALLOWABLE LOAD TRADE",
        "DIRECTIONAL STRENGTH PENALTY",
        "LOAD SENSITIVITY",
        "CORE-DEPTH + STRENGTH TRADE",
        "LOAD-CAPACITY / MASS INTERPRETATION",
    ):
        assert heading in out
    assert "ILLUSTRATIVE" in out
    assert "Candidates retained for later crushing, wrinkling" in out


def test_strength_example_never_declares_a_selection(capsys):
    out = _run_example(capsys).upper()
    for banned in ("SELECTED CORE", "RECOMMENDED CORE", "WINNER", "WE RECOMMEND", "BEST CORE"):
        assert banned not in out


def test_strength_example_does_not_claim_deferred_failure_modes(capsys):
    out = _run_example(capsys).lower()
    # These may only appear as explicitly deferred items, never as computed checks.
    for term in ("crushing", "wrinkling", "indentation"):
        assert "deferred" in out or "retained for later" in out
        assert f"{term} margin" not in out
        assert f"ms_{term}" not in out
