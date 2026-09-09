"""Y-AH: sensitivity, determinism and load scaling through the trade layer."""

from __future__ import annotations

import runpy
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from sandwich_panel import (
    CANDIDATE_CORES,
    DeflectionRequirement,
    StudyBasis,
    build_trade_table,
    core_density_sweep,
    core_depth_directional_sweep,
    core_shear_modulus_sweep_at_fixed_density,
    evaluate_candidate,
    get_core,
)

from .conftest import M2_DELTA_B, M2_EI, M2_P

DENSITIES = [25.0, 40.0, 60.0, 80.0, 100.0]
SHEAR_MODULI = [10.0e6, 20.0e6, 40.0e6, 80.0e6, 160.0e6]
CORE_DEPTHS = [0.005, 0.010, 0.015, 0.020, 0.025]

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "core_candidate_trade.py"


# -- Y / Z. density sensitivity -------------------------------------------


def test_density_changes_areal_mass_linearly(basis):
    # Y. m_A = 2.16 + rho_c * 0.020
    rows = core_density_sweep(basis, DENSITIES, 40.0e6)
    assert len(rows) == len(DENSITIES)
    for row, rho in zip(rows, DENSITIES):
        assert row.core_density == rho
        assert row.areal_mass == pytest.approx(2.16 + rho * 0.020, rel=1e-12)
    # Exact linearity: equal density steps give equal mass steps.
    doubled = core_density_sweep(basis, [30.0, 60.0], 40.0e6)
    assert doubled[1].core_areal_mass == pytest.approx(2 * doubled[0].core_areal_mass, rel=1e-12)


def test_density_does_not_change_any_stiffness_quantity(basis):
    # Z.
    rows = core_density_sweep(basis, DENSITIES, 40.0e6)
    ref = rows[0]
    for row in rows:
        assert row.flexural_rigidity == ref.flexural_rigidity  # bit-for-bit
        assert row.bending_deflection == ref.bending_deflection
        assert row.shear_deflection == ref.shear_deflection
        assert row.total_deflection == ref.total_deflection
        assert row.shear_fraction == ref.shear_fraction
    assert ref.flexural_rigidity == pytest.approx(M2_EI, rel=1e-9)
    assert ref.bending_deflection == pytest.approx(M2_DELTA_B, rel=1e-6)


def test_density_sweep_rejects_empty_input(basis):
    with pytest.raises(ValueError):
        core_density_sweep(basis, [], 40.0e6)


# -- AA / AB / AC. shear-modulus sensitivity ------------------------------


def test_shear_modulus_does_not_change_mass(basis):
    # AA.
    rows = core_shear_modulus_sweep_at_fixed_density(basis, SHEAR_MODULI, 45.0)
    ref = rows[0]
    for row in rows:
        assert row.areal_mass == ref.areal_mass  # bit-for-bit
        assert row.core_areal_mass == ref.core_areal_mass
        assert row.total_mass == ref.total_mass
    assert ref.areal_mass == pytest.approx(2.16 + 45.0 * 0.020, rel=1e-12)


def test_shear_modulus_does_not_change_EI_or_bending_deflection(basis):
    # AB.
    rows = core_shear_modulus_sweep_at_fixed_density(basis, SHEAR_MODULI, 45.0)
    ref = rows[0]
    for row in rows:
        assert row.flexural_rigidity == ref.flexural_rigidity  # bit-for-bit
        assert row.bending_deflection == ref.bending_deflection


def test_shear_deflection_scales_as_inverse_G(basis):
    # AC. delta_s = 1875 / G for this basis.
    rows = core_shear_modulus_sweep_at_fixed_density(basis, SHEAR_MODULI, 45.0)
    for row in rows:
        assert row.shear_deflection == pytest.approx(1875.0 / row.effective_shear_modulus, rel=1e-12)
    for a, b in zip(rows, rows[1:]):
        factor = b.effective_shear_modulus / a.effective_shear_modulus
        assert b.shear_deflection == pytest.approx(a.shear_deflection / factor, rel=1e-12)


def test_total_deflection_approaches_the_bending_only_limit_as_G_grows(basis):
    rows = core_shear_modulus_sweep_at_fixed_density(
        basis, [10.0e6, 1.0e8, 1.0e10, 1.0e12], 45.0
    )
    assert all(b.total_deflection < a.total_deflection for a, b in zip(rows, rows[1:]))
    assert all(r.total_deflection > r.bending_deflection for r in rows)
    assert rows[-1].total_deflection == pytest.approx(rows[-1].bending_deflection, rel=1e-5)
    assert rows[-1].shear_fraction < 1e-5


def test_shear_modulus_sweep_rejects_empty_input(basis):
    with pytest.raises(ValueError):
        core_shear_modulus_sweep_at_fixed_density(basis, [], 45.0)


# -- AD / AE / AF. core-depth trade ---------------------------------------


def test_core_depth_increases_EI(basis):
    # AD.
    rows = core_depth_directional_sweep(basis, get_core("HC-AL-45"), CORE_DEPTHS)
    assert len(rows) == len(CORE_DEPTHS)
    assert all(b.flexural_rigidity > a.flexural_rigidity for a, b in zip(rows, rows[1:]))


def test_core_depth_increases_areal_mass(basis):
    # AE. m_A = 2.16 + 45 * t_c for HC-AL-45.
    rows = core_depth_directional_sweep(basis, get_core("HC-AL-45"), CORE_DEPTHS)
    assert all(b.areal_mass > a.areal_mass for a, b in zip(rows, rows[1:]))
    for row in rows:
        assert row.areal_mass == pytest.approx(2.16 + 45.0 * row.core_thickness, rel=1e-12)


def test_core_depth_reduces_shear_deflection_in_both_directions(basis):
    # AF. A_s = b t_c grows with core depth, so delta_s falls.
    rows = core_depth_directional_sweep(basis, get_core("HC-AL-45"), CORE_DEPTHS)
    assert all(b.shear_deflection_L < a.shear_deflection_L for a, b in zip(rows, rows[1:]))
    assert all(b.shear_deflection_W < a.shear_deflection_W for a, b in zip(rows, rows[1:]))
    assert all(b.total_deflection_L < a.total_deflection_L for a, b in zip(rows, rows[1:]))
    assert all(b.total_deflection_W < a.total_deflection_W for a, b in zip(rows, rows[1:]))


def test_core_depth_sweep_keeps_the_directional_identity(basis):
    core = get_core("HC-AL-45")
    for row in core_depth_directional_sweep(basis, core, CORE_DEPTHS):
        assert row.shear_deflection_W / row.shear_deflection_L == pytest.approx(
            core.directional_shear_ratio, rel=1e-12
        )
        assert row.total_deflection_L == pytest.approx(
            row.bending_deflection + row.shear_deflection_L, rel=1e-15
        )
        assert row.total_deflection_W == pytest.approx(
            row.bending_deflection + row.shear_deflection_W, rel=1e-15
        )


def test_core_depth_total_thickness_hand_calc(basis):
    rows = core_depth_directional_sweep(basis, get_core("HC-AL-45"), [0.010])
    # h = 2 * 0.0004 + 0.010 = 0.0108 m
    assert rows[0].total_thickness == pytest.approx(0.0108, abs=1e-15)


def test_core_depth_sweep_does_not_mutate_the_basis(basis):
    before = basis.geometry.core_thickness
    core_depth_directional_sweep(basis, get_core("HC-AL-45"), CORE_DEPTHS)
    assert basis.geometry.core_thickness == before


def test_core_depth_sweep_rejects_empty_input(basis):
    with pytest.raises(ValueError):
        core_depth_directional_sweep(basis, get_core("HC-AL-45"), [])


# -- AG. determinism ------------------------------------------------------


def test_candidate_results_are_deterministic(basis, ortho_core):
    first = asdict(evaluate_candidate(basis, ortho_core, "L"))
    for _ in range(5):
        assert asdict(evaluate_candidate(basis, ortho_core, "L")) == first


def test_trade_table_is_deterministic(basis):
    req = DeflectionRequirement(maximum_total_deflection=1.5e-3)

    def snapshot():
        return [
            (row.result.label, row.result.areal_mass, row.result.total_deflection, row.feasible)
            for row in build_trade_table(basis, CANDIDATE_CORES, requirement=req)
        ]

    first = snapshot()
    for _ in range(5):
        assert snapshot() == first


def test_identical_bases_give_identical_results(m2_geometry, m2_face, ortho_core):
    a = StudyBasis(geometry=m2_geometry, face=m2_face, load=M2_P)
    b = StudyBasis(geometry=m2_geometry, face=m2_face, load=M2_P)
    assert a == b
    assert asdict(evaluate_candidate(a, ortho_core, "W")) == asdict(
        evaluate_candidate(b, ortho_core, "W")
    )


def test_sweeps_are_deterministic(basis):
    def snap(rows):
        return [(r.core_density, r.effective_shear_modulus, r.total_deflection) for r in rows]

    first = snap(core_density_sweep(basis, DENSITIES, 40.0e6))
    for _ in range(3):
        assert snap(core_density_sweep(basis, DENSITIES, 40.0e6)) == first


# -- AH. load scaling ------------------------------------------------------


def test_all_demand_quantities_scale_linearly_with_load(m2_geometry, m2_face, ortho_core):
    one = StudyBasis(geometry=m2_geometry, face=m2_face, load=M2_P)
    three = StudyBasis(geometry=m2_geometry, face=m2_face, load=3 * M2_P)
    a = evaluate_candidate(one, ortho_core, "L")
    b = evaluate_candidate(three, ortho_core, "L")
    for field in (
        "bending_deflection",
        "shear_deflection",
        "total_deflection",
        "max_face_stress",
        "avg_core_shear_stress",
    ):
        assert getattr(b, field) == pytest.approx(3 * getattr(a, field), rel=1e-12)


def test_load_does_not_change_mass_stiffness_or_shear_fraction(m2_geometry, m2_face, ortho_core):
    one = StudyBasis(geometry=m2_geometry, face=m2_face, load=M2_P)
    three = StudyBasis(geometry=m2_geometry, face=m2_face, load=3 * M2_P)
    a = evaluate_candidate(one, ortho_core, "L")
    b = evaluate_candidate(three, ortho_core, "L")
    assert b.areal_mass == a.areal_mass
    assert b.total_mass == a.total_mass
    assert b.flexural_rigidity == a.flexural_rigidity
    assert b.shear_fraction == pytest.approx(a.shear_fraction, rel=1e-12)


def test_kappa_scales_shear_deflection_through_the_trade_layer(m2_geometry, m2_face, ortho_core):
    base = StudyBasis(geometry=m2_geometry, face=m2_face, load=M2_P)
    halved = StudyBasis(
        geometry=m2_geometry, face=m2_face, load=M2_P, shear_correction_factor=0.5
    )
    a = evaluate_candidate(base, ortho_core, "L")
    b = evaluate_candidate(halved, ortho_core, "L")
    assert b.bending_deflection == a.bending_deflection
    assert b.shear_deflection == pytest.approx(2 * a.shear_deflection, rel=1e-12)


# -- example smoke test ----------------------------------------------------


def test_trade_example_runs(capsys):
    saved = sys.argv[:]
    sys.argv = [str(EXAMPLE)]
    try:
        runpy.run_path(str(EXAMPLE), run_name="__main__")
    finally:
        sys.argv = saved
    out = capsys.readouterr().out
    for heading in (
        "STUDY BASIS",
        "CANDIDATE DATABASE",
        "L-DIRECTION RESULTS",
        "W-DIRECTION RESULTS",
        "DIRECTIONAL PENALTY",
        "MASS-STIFFNESS INTERPRETATION",
        "CORE-DEPTH TRADE",
    ):
        assert heading in out
    assert "ILLUSTRATIVE" in out
    assert "Candidates retained for later strength/failure screening." in out


def test_trade_example_never_declares_a_selection(capsys):
    saved = sys.argv[:]
    sys.argv = [str(EXAMPLE)]
    try:
        runpy.run_path(str(EXAMPLE), run_name="__main__")
    finally:
        sys.argv = saved
    out = capsys.readouterr().out.upper()
    for banned in ("SELECTED CORE", "RECOMMENDED CORE", "WINNER", "WE RECOMMEND", "BEST CORE"):
        assert banned not in out
