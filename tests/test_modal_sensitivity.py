"""AM-AV: modal sensitivity sweeps, requirement robustness and regression."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

from sandwich_panel import (
    CoreShearDirection,
    build_integrated_table,
    core_depth_modal_sweep,
    deflection_limit_sweep,
    frequency_requirement_sweep,
    get_core,
    modal_density_sweep,
    modal_face_thickness_sweep,
    modal_shear_modulus_sweep,
    select_preliminary_core,
)

MM = 1.0e-3
MPA = 1.0e6
DENSITIES = [25.0, 40.0, 60.0, 80.0, 100.0]
SHEAR_MODULI = [5 * MPA, 10 * MPA, 20 * MPA, 40 * MPA, 80 * MPA, 160 * MPA, 500 * MPA]
CORE_DEPTHS = [5 * MM, 10 * MM, 15 * MM, 20 * MM, 25 * MM, 30 * MM]
FACE_THICKNESSES = [0.2 * MM, 0.3 * MM, 0.4 * MM, 0.5 * MM, 0.6 * MM]
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "modal_core_selection.py"


# -- AM / AN. density ---------------------------------------------------------


@pytest.fixture
def density_rows(basis, frequency_requirement):
    return modal_density_sweep(basis, DENSITIES, 40 * MPA, frequency_requirement)


def test_density_increase_lowers_the_frequency(density_rows):
    # AM.
    assert all(b.frequency < a.frequency for a, b in zip(density_rows, density_rows[1:]))
    assert all(
        b.bending_only_frequency < a.bending_only_frequency
        for a, b in zip(density_rows, density_rows[1:])
    )


def test_density_increase_does_not_change_EI(density_rows):
    # AN.
    assert len({r.flexural_rigidity for r in density_rows}) == 1


def test_density_raises_distributed_mass_linearly(density_rows):
    for r in density_rows:
        # m_A = 2.16 + rho * 0.020 ; mu = m_A * 0.5
        assert r.areal_mass == pytest.approx(2.16 + r.core_density * 0.020, rel=1e-12)
        assert r.distributed_mass == pytest.approx(r.areal_mass * 0.5, rel=1e-12)


def test_frequency_follows_inverse_sqrt_of_distributed_mass(density_rows):
    a, b = density_rows[0], density_rows[-1]
    assert b.bending_only_frequency == pytest.approx(
        a.bending_only_frequency * (a.distributed_mass / b.distributed_mass) ** 0.5, rel=1e-12
    )


def test_density_sweep_rejects_empty_input(basis, frequency_requirement):
    with pytest.raises(ValueError):
        modal_density_sweep(basis, [], 40 * MPA, frequency_requirement)


# -- AO / AP. shear modulus ----------------------------------------------------


@pytest.fixture
def shear_rows(basis, frequency_requirement):
    return modal_shear_modulus_sweep(basis, SHEAR_MODULI, 45.0, frequency_requirement)


def test_shear_modulus_does_not_change_mass(shear_rows):
    # AO.
    assert len({r.areal_mass for r in shear_rows}) == 1
    assert len({r.distributed_mass for r in shear_rows}) == 1
    assert shear_rows[0].areal_mass == pytest.approx(2.16 + 45.0 * 0.020, rel=1e-12)


def test_shear_modulus_does_not_change_the_bending_only_frequency(shear_rows):
    # AP.
    assert len({r.bending_only_frequency for r in shear_rows}) == 1
    assert len({r.flexural_rigidity for r in shear_rows}) == 1


def test_shear_modulus_raises_the_corrected_frequency_monotonically(shear_rows):
    assert all(b.frequency > a.frequency for a, b in zip(shear_rows, shear_rows[1:]))


def test_high_shear_modulus_approaches_the_bending_only_asymptote(shear_rows):
    top = shear_rows[-1]
    assert top.frequency < top.bending_only_frequency
    assert top.frequency == pytest.approx(top.bending_only_frequency, rel=2e-3)
    for r in shear_rows:
        assert r.frequency <= r.bending_only_frequency


def test_shear_sweep_rejects_empty_input(basis, frequency_requirement):
    with pytest.raises(ValueError):
        modal_shear_modulus_sweep(basis, [], 45.0, frequency_requirement)


# -- AQ / AR / AS. core thickness ---------------------------------------------


@pytest.fixture
def depth_rows(basis, frequency_requirement):
    return core_depth_modal_sweep(
        basis, get_core("HC-AL-45"), CORE_DEPTHS, frequency_requirement, directions=["L"]
    )


def test_core_thickness_raises_EI(depth_rows):
    # AQ.
    assert all(b.flexural_rigidity > a.flexural_rigidity for a, b in zip(depth_rows, depth_rows[1:]))


def test_core_thickness_raises_mass(depth_rows):
    # AR.
    assert all(b.areal_mass > a.areal_mass for a, b in zip(depth_rows, depth_rows[1:]))
    for r in depth_rows:
        assert r.areal_mass == pytest.approx(2.16 + 45.0 * r.core_thickness, rel=1e-12)


def test_core_thickness_raises_the_frequency_over_this_range(depth_rows):
    # EI grows ~t_c^2 while mass grows only linearly, so bending wins - but this
    # is asserted from the computed model, not assumed.
    assert all(b.frequency > a.frequency for a, b in zip(depth_rows, depth_rows[1:]))
    assert depth_rows[0].frequency == pytest.approx(9.101, rel=1e-3)
    assert depth_rows[-1].frequency == pytest.approx(41.419, rel=1e-3)


def test_core_thickness_also_raises_the_shear_flexibility_ratio(depth_rows):
    # EI grows faster than A_s, so the shear penalty grows with depth too.
    assert all(
        b.shear_flexibility_ratio > a.shear_flexibility_ratio
        for a, b in zip(depth_rows, depth_rows[1:])
    )


def test_core_depth_row_matches_a_direct_recomputation(basis, frequency_requirement):
    # AS.
    from sandwich_panel import SandwichGeometry, StudyBasis, assess_core_modal

    core = get_core("HC-AL-45")
    for row in core_depth_modal_sweep(
        basis, core, [0.010, 0.025], frequency_requirement, directions=["L"]
    ):
        rebuilt = StudyBasis(
            geometry=SandwichGeometry(
                width=basis.geometry.width,
                face_thickness=basis.geometry.face_thickness,
                core_thickness=row.core_thickness,
                span=basis.geometry.span,
            ),
            face=basis.face,
            load=basis.load,
        )
        direct = assess_core_modal(rebuilt, core, "L", frequency_requirement)
        assert row.frequency == direct.frequency
        assert row.bending_only_frequency == direct.bending_only_frequency
        assert row.areal_mass == direct.areal_mass
        assert row.flexural_rigidity == direct.modal.flexural_rigidity


def test_core_depth_sweep_covers_both_directions(basis, frequency_requirement):
    rows = core_depth_modal_sweep(basis, get_core("HC-AL-45"), CORE_DEPTHS, frequency_requirement)
    assert len(rows) == 2 * len(CORE_DEPTHS)
    l_rows = [r for r in rows if r.direction is CoreShearDirection.L]
    w_rows = [r for r in rows if r.direction is CoreShearDirection.W]
    for a, b in zip(l_rows, w_rows):
        assert b.frequency < a.frequency
        assert b.bending_only_frequency == a.bending_only_frequency


def test_core_depth_sweep_does_not_mutate_the_basis(basis, frequency_requirement):
    before = basis.geometry.core_thickness
    core_depth_modal_sweep(basis, get_core("HC-AL-45"), CORE_DEPTHS, frequency_requirement)
    assert basis.geometry.core_thickness == before


def test_core_depth_sweep_rejects_empty_inputs(basis, frequency_requirement):
    with pytest.raises(ValueError):
        core_depth_modal_sweep(basis, get_core("HC-AL-45"), [], frequency_requirement)
    with pytest.raises(ValueError):
        core_depth_modal_sweep(
            basis, get_core("HC-AL-45"), CORE_DEPTHS, frequency_requirement, directions=[]
        )


# -- face thickness (reported, not assumed) -----------------------------------


def test_face_thickness_raises_both_EI_and_mass(basis, frequency_requirement):
    rows = modal_face_thickness_sweep(
        basis, FACE_THICKNESSES, get_core("HC-AL-45"), frequency_requirement
    )
    assert all(b.flexural_rigidity > a.flexural_rigidity for a, b in zip(rows, rows[1:]))
    assert all(b.areal_mass > a.areal_mass for a, b in zip(rows, rows[1:]))


def test_face_thickness_frequency_trend_is_monotonic_over_this_range(basis, frequency_requirement):
    # Stiffness wins over added mass here - computed, not assumed.
    rows = modal_face_thickness_sweep(
        basis, FACE_THICKNESSES, get_core("HC-AL-45"), frequency_requirement
    )
    assert all(b.frequency > a.frequency for a, b in zip(rows, rows[1:]))
    # The gain flattens: EI/mu tends to a constant once the faces dominate the mass.
    first_step = rows[1].frequency - rows[0].frequency
    last_step = rows[-1].frequency - rows[-2].frequency
    assert last_step < first_step


def test_face_thickness_sweep_rejects_empty_input(basis, frequency_requirement):
    with pytest.raises(ValueError):
        modal_face_thickness_sweep(basis, [], get_core("HC-AL-45"), frequency_requirement)


# -- AT. requirement sensitivity ----------------------------------------------


def test_raising_the_frequency_requirement_cannot_increase_the_feasible_count(basis, screens):
    rows = frequency_requirement_sweep(
        basis, screens, [5.0, 10.0, 15.0, 20.0, 25.0, 28.0, 30.0, 32.0]
    )
    counts = [r.feasible_count for r in rows]
    assert all(b <= a for a, b in zip(counts, counts[1:]))
    assert counts[0] == 10
    assert counts[-1] == 0


def test_the_requirement_sweep_locates_where_the_modal_screen_bites(basis, screens):
    rows = {r.required_frequency_hz: r for r in
            frequency_requirement_sweep(basis, screens, [25.0, 28.0, 30.0, 32.0])}
    assert rows[25.0].feasible_count == 10
    assert 0 < rows[30.0].feasible_count < 10
    assert rows[32.0].feasible_count == 0
    assert rows[32.0].lightest_feasible_label is None


def test_the_selection_is_stable_across_every_feasible_requirement(basis, screens):
    """The selection is not an artefact of the illustrative threshold."""
    rows = frequency_requirement_sweep(
        basis, screens, [5.0, 10.0, 15.0, 20.0, 25.0, 28.0, 30.0]
    )
    labels = {r.lightest_feasible_label for r in rows if r.feasible_count > 0}
    assert labels == {"HC-AL-30 [L]"}


def test_requirement_sweep_rejects_empty_input(basis, screens):
    with pytest.raises(ValueError):
        frequency_requirement_sweep(basis, screens, [])


# -- AU. static deflection-limit sensitivity ----------------------------------


def test_tightening_the_deflection_limit_cannot_increase_the_feasible_count(basis, screens):
    rows = deflection_limit_sweep(basis, screens, [500, 750, 1000, 1500, 2000])
    static = [r.static_feasible_count for r in rows]
    overall = [r.overall_feasible_count for r in rows]
    assert all(b <= a for a, b in zip(static, static[1:]))
    assert all(b <= a for a, b in zip(overall, overall[1:]))


def test_the_static_screen_is_brittle_between_span_1000_and_span_1500(basis, screens):
    rows = {r.span_divisor: r for r in
            deflection_limit_sweep(basis, screens, [1000, 1500])}
    assert rows[1000].static_feasible_count == 10
    assert rows[1500].static_feasible_count == 0
    assert rows[1500].selected_label is None


def test_the_selection_is_unchanged_wherever_anything_is_feasible(basis, screens):
    rows = deflection_limit_sweep(basis, screens, [500, 750, 1000, 1500, 2000])
    labels = {r.selected_label for r in rows if r.overall_feasible_count > 0}
    assert labels == {"HC-AL-30 [L]"}


def test_deflection_limit_sweep_does_not_redefine_the_canonical_limit(basis, screens):
    before = screens.deflection.maximum_total_deflection
    deflection_limit_sweep(basis, screens, [500, 2000])
    assert screens.deflection.maximum_total_deflection == before
    assert before == pytest.approx(1.5e-3, rel=1e-12)


def test_deflection_limit_sweep_rejects_empty_input(basis, screens):
    with pytest.raises(ValueError):
        deflection_limit_sweep(basis, screens, [])


# -- determinism ---------------------------------------------------------------


def test_sweeps_are_deterministic(basis, screens, frequency_requirement):
    def snap():
        return (
            [(r.swept_value, r.frequency) for r in
             modal_density_sweep(basis, DENSITIES, 40 * MPA, frequency_requirement)],
            [(r.core_thickness, r.frequency) for r in
             core_depth_modal_sweep(basis, get_core("HC-AL-45"), CORE_DEPTHS, frequency_requirement)],
            [(r.required_frequency_hz, r.feasible_count, r.lightest_feasible_label) for r in
             frequency_requirement_sweep(basis, screens, [20.0, 30.0])],
        )

    first = snap()
    for _ in range(3):
        assert snap() == first


# -- example smoke test --------------------------------------------------------


def _run_example(capsys):
    saved = sys.argv[:]
    sys.argv = [str(EXAMPLE)]
    try:
        runpy.run_path(str(EXAMPLE), run_name="__main__")
    finally:
        sys.argv = saved
    return capsys.readouterr().out


def test_modal_example_runs(capsys):
    out = _run_example(capsys)
    for heading in (
        "STUDY BASIS",
        "CANDIDATE MODAL TABLE",
        "INTEGRATED SCREEN",
        "DIRECTIONAL EFFECT",
        "CORE-DEPTH MODAL TRADE",
        "DENSITY SENSITIVITY",
        "SHEAR-MODULUS SENSITIVITY",
        "REQUIREMENT SENSITIVITY",
        "ILLUSTRATIVE PRELIMINARY CORE SELECTION",
    ):
        assert heading in out
    assert "ILLUSTRATIVE" in out
    assert "HC-AL-30" in out
    assert (
        "This selection is conditional on illustrative material properties and screening"
        in out
    )


def test_modal_example_never_claims_more_than_a_preliminary_selection(capsys):
    out = _run_example(capsys).upper()
    for banned in (
        "FINAL CORE", "QUALIFIED CORE", "FLIGHT-SELECTED", "CERTIFIED DESIGN",
        "MANUFACTURER RECOMMENDATION", "OPTIMIZED SOLUTION", "OPTIMISED SOLUTION",
    ):
        assert banned not in out
    assert "ILLUSTRATIVE PRELIMINARY CORE SELECTION" in out


def test_modal_example_states_the_data_policy(capsys):
    out = _run_example(capsys).lower()
    assert "illustrative" in out
    assert "not a launch-provider requirement" in out
    assert "sourced allowables" in out
