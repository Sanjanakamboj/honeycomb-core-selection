"""AB-AE plus regression and determinism for the combined Milestone 4 screen."""

from __future__ import annotations

import runpy
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from sandwich_panel import (
    CANDIDATE_CORES,
    CoreCompressionProperties,
    CoreShearDirection,
    DeflectionRequirement,
    FaceStrength,
    LimitingConstraint,
    LocalFailureMode,
    LocalPatchLoad,
    LocalScreenBasis,
    RetentionStatus,
    SandwichConstraint,
    StrengthBasis,
    StudyBasis,
    assess_candidate_design,
    assess_sandwich_design,
    build_design_table,
    build_sandwich_table,
    core_depth_wrinkling_sweep,
    evaluate_candidates,
    get_core,
    get_core_compression,
    get_core_strength,
)

CORE_DEPTHS = [0.005, 0.010, 0.015, 0.020, 0.025]
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "local_failure_screen.py"


def _design(basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
            requirement, local_basis, direction="L"):
    return assess_sandwich_design(
        basis, ortho_core, ortho_core_strength, core_compression, direction,
        strength_basis, requirement, local_basis,
    )


# -- AB. local governing mode computed from margins ------------------------


def test_local_governing_mode_is_the_minimum_margin(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
    requirement, local_basis,
):
    a = _design(basis, ortho_core, ortho_core_strength, core_compression,
                strength_basis, requirement, local_basis)
    assert a.local.governing_local_margin == min(
        a.local.wrinkling_margin, a.local.core_compression_margin
    )
    expected = (
        LocalFailureMode.WRINKLING
        if a.local.wrinkling_margin <= a.local.core_compression_margin
        else LocalFailureMode.CORE_COMPRESSION
    )
    assert a.local.governing_local_mode is expected


def test_local_governing_mode_switches_when_the_crush_allowable_moves(
    basis, ortho_core, ortho_core_strength, strength_basis, requirement, local_basis
):
    """Neither mode is hard-coded: sweep the crush allowable so each governs."""
    seen = set()
    for sigma_c in (2.0e5, 2.0e6, 2.0e8, 2.0e12):
        record = CoreCompressionProperties(
            name="TEST-CORE", compression_strength=sigma_c, compression_modulus=500.0e6
        )
        a = _design(basis, ortho_core, ortho_core_strength, record,
                    strength_basis, requirement, local_basis)
        assert a.local.governing_local_margin == min(
            a.local.wrinkling_margin, a.local.core_compression_margin
        )
        seen.add(a.local.governing_local_mode)
    assert seen == {LocalFailureMode.WRINKLING, LocalFailureMode.CORE_COMPRESSION}


def test_local_governing_mode_never_reports_a_global_or_deferred_mode(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
    requirement, local_basis,
):
    a = _design(basis, ortho_core, ortho_core_strength, core_compression,
                strength_basis, requirement, local_basis)
    assert a.local.governing_local_mode in tuple(LocalFailureMode)
    assert len(list(LocalFailureMode)) == 2  # wrinkling + core compression, nothing else


# -- indentation is deferred, not faked ------------------------------------


def test_no_indentation_margin_is_reported(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
    requirement, local_basis,
):
    """Indentation is deferred; no duplicate margin may masquerade as a new mode."""
    a = _design(basis, ortho_core, ortho_core_strength, core_compression,
                strength_basis, requirement, local_basis)
    for banned in (
        "indentation_margin",
        "indentation_pass",
        "indentation_allowable",
        "local_indentation_margin",
        "contact_pressure_margin",
    ):
        assert not hasattr(a.local, banned)
    assert not any("indent" in name.lower() for name in LocalFailureMode.__members__)


def test_patch_pressure_is_a_single_quantity_not_two_named_ones(patch_load):
    # The contact pressure and the local core compressive stress are the SAME
    # number in this model - which is exactly why there is only one margin.
    assert patch_load.pressure == patch_load.force / patch_load.patch_area


def test_no_crimping_or_buckling_mode_is_reported():
    for banned in ("crimping", "crimp", "buckling", "dimpling", "intracell"):
        assert not any(banned in n.lower() for n in LocalFailureMode.__members__)
        assert not any(banned in n.lower() for n in SandwichConstraint.__members__)


# -- AC. local feasibility iff all local checks pass -----------------------


@pytest.mark.parametrize(
    "wrinkling_ok,crush_ok,expected",
    [(True, True, True), (False, True, False), (True, False, False), (False, False, False)],
)
def test_local_feasible_is_the_and_of_both_local_checks(
    basis, ortho_core, ortho_core_strength, strength_basis, requirement,
    wrinkling_model, wrinkling_ok, crush_ok, expected,
):
    from sandwich_panel import evaluate_candidate

    r = evaluate_candidate(basis, ortho_core, "L")
    # Pick E_c to put the wrinkling stress just above / just below the demand.
    scale = 1.5 if wrinkling_ok else 0.5
    e_c = (scale * r.max_face_stress / wrinkling_model.coefficient) ** 3 / (
        basis.face.youngs_modulus * r.effective_shear_modulus
    )
    patch = LocalPatchLoad.square(force=100.0, side=0.025)  # 160 kPa
    sigma_c = 1.5 * patch.pressure if crush_ok else 0.5 * patch.pressure
    record = CoreCompressionProperties(
        name="TEST-CORE", compression_strength=sigma_c, compression_modulus=e_c
    )
    a = _design(
        basis, ortho_core, ortho_core_strength, record, strength_basis, requirement,
        LocalScreenBasis(wrinkling_model=wrinkling_model, patch_load=patch),
    )
    assert a.local.wrinkling_pass is wrinkling_ok
    assert a.local.core_compression_pass is crush_ok
    assert a.local_failure_feasible is expected
    assert a.local_failure_feasible == (
        a.local.wrinkling_pass and a.local.core_compression_pass
    )


# -- AD. overall feasibility requires all three families -------------------


def test_overall_feasible_requires_deflection_global_and_local(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
    requirement, local_basis,
):
    a = _design(basis, ortho_core, ortho_core_strength, core_compression,
                strength_basis, requirement, local_basis)
    assert a.deflection_feasible is True
    assert a.global_strength_feasible is True
    assert a.local_failure_feasible is True
    assert a.overall_feasible is True
    assert a.overall_feasible == (
        a.deflection_feasible and a.global_strength_feasible and a.local_failure_feasible
    )
    assert a.retention is RetentionStatus.RETAINED


def test_deflection_failure_alone_rejects_globally(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis, local_basis
):
    a = _design(basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
                DeflectionRequirement(maximum_total_deflection=1.0e-4), local_basis)
    assert (a.deflection_feasible, a.global_strength_feasible, a.local_failure_feasible) == (
        False, True, True
    )
    assert a.overall_feasible is False
    assert a.retention is RetentionStatus.REJECTED_GLOBAL
    assert "deflection" in a.retention_reason


def test_global_strength_failure_alone_rejects_globally(
    basis, ortho_core, ortho_core_strength, core_compression, requirement, local_basis
):
    weak = StrengthBasis(face_strength=FaceStrength(name="weak", yield_strength=1.0e6))
    a = _design(basis, ortho_core, ortho_core_strength, core_compression, weak,
                requirement, local_basis)
    assert (a.deflection_feasible, a.global_strength_feasible, a.local_failure_feasible) == (
        True, False, True
    )
    assert a.retention is RetentionStatus.REJECTED_GLOBAL
    assert "face_yield" in a.retention_reason


def test_local_failure_alone_rejects_locally(
    basis, ortho_core, ortho_core_strength, strength_basis, requirement, wrinkling_model
):
    crushable = CoreCompressionProperties(
        name="TEST-CORE", compression_strength=1.0e4, compression_modulus=500.0e6
    )
    a = _design(
        basis, ortho_core, ortho_core_strength, crushable, strength_basis, requirement,
        LocalScreenBasis(
            wrinkling_model=wrinkling_model,
            patch_load=LocalPatchLoad.square(force=100.0, side=0.025),
        ),
    )
    assert (a.deflection_feasible, a.global_strength_feasible, a.local_failure_feasible) == (
        True, True, False
    )
    assert a.retention is RetentionStatus.REJECTED_LOCAL
    assert "core_compression" in a.retention_reason


def test_retention_reason_lists_every_failing_screen(
    basis, ortho_core, ortho_core_strength, wrinkling_model
):
    weak_face = StrengthBasis(face_strength=FaceStrength(name="weak", yield_strength=1.0e6))
    crushable = CoreCompressionProperties(
        name="TEST-CORE", compression_strength=1.0e4, compression_modulus=500.0e6
    )
    a = _design(
        basis, ortho_core, ortho_core_strength, crushable, weak_face,
        DeflectionRequirement(maximum_total_deflection=1.0e-4),
        LocalScreenBasis(
            wrinkling_model=wrinkling_model,
            patch_load=LocalPatchLoad.square(force=100.0, side=0.025),
        ),
    )
    for expected in ("deflection", "face_yield", "core_compression"):
        assert expected in a.retention_reason


# -- AE. unlike margins are never blended ----------------------------------


def test_margins_of_three_different_families_are_never_blended(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
    requirement, local_basis,
):
    a = _design(basis, ortho_core, ortho_core_strength, core_compression,
                strength_basis, requirement, local_basis)
    assert abs(a.design.deflection.margin) < 1.0  # metres
    assert a.design.strength.governing_margin > 1.0  # dimensionless
    assert a.local.governing_local_margin > 1.0  # dimensionless
    for banned in (
        "combined_margin", "total_margin", "overall_margin", "margin", "min_margin"
    ):
        assert not hasattr(a, banned)


def test_local_patch_capacity_is_not_folded_into_the_global_capacity(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
    requirement, local_basis,
):
    """Different load cases: the crush force must not enter the central-load limit."""
    a = _design(basis, ortho_core, ortho_core_strength, core_compression,
                strength_basis, requirement, local_basis)
    c = a.capacity
    assert c.sandwich_limit == min(
        c.deflection_limit, c.face_limit, c.core_shear_limit, c.wrinkling_limit
    )
    assert c.sandwich_limit != a.local.core_crush_force_limit
    for banned in ("crush_limit", "core_crush_force_limit", "local_limit"):
        assert not hasattr(c, banned)


def test_sandwich_constraint_never_includes_core_compression():
    assert "CORE_COMPRESSION" not in SandwichConstraint.__members__
    assert set(SandwichConstraint) == {
        SandwichConstraint.DEFLECTION,
        SandwichConstraint.FACE_YIELD,
        SandwichConstraint.CORE_SHEAR,
        SandwichConstraint.WRINKLING,
    }


def test_sandwich_constraint_extends_the_milestone3_set_compatibly():
    # The Milestone 3 enum is untouched; shared members carry identical values.
    assert len(list(LimitingConstraint)) == 3
    for member in LimitingConstraint:
        assert member.value in {c.value for c in SandwichConstraint}
    assert SandwichConstraint.DEFLECTION == LimitingConstraint.DEFLECTION.value


# -- global capacity with wrinkling ----------------------------------------


def test_sandwich_limit_is_the_minimum_of_four(basis, strength_basis, requirement, local_basis):
    for a in build_sandwich_table(basis, strength_basis, requirement, local_basis):
        c = a.capacity
        limits = {
            SandwichConstraint.DEFLECTION: c.deflection_limit,
            SandwichConstraint.FACE_YIELD: c.face_limit,
            SandwichConstraint.CORE_SHEAR: c.core_shear_limit,
            SandwichConstraint.WRINKLING: c.wrinkling_limit,
        }
        assert c.sandwich_limit == pytest.approx(min(limits.values()), rel=1e-15)
        assert limits[c.governing_constraint] == pytest.approx(c.sandwich_limit, rel=1e-15)


def test_sandwich_limit_never_exceeds_the_milestone3_limit(
    basis, strength_basis, requirement, local_basis
):
    # Adding a constraint can only reduce (or hold) the capacity.
    m3 = {a.label: a for a in build_design_table(basis, strength_basis, requirement)}
    for a in build_sandwich_table(basis, strength_basis, requirement, local_basis):
        assert a.capacity.sandwich_limit <= m3[a.label].capacity.preliminary_limit


def test_wrinkling_can_become_the_governing_global_constraint(
    basis, ortho_core, ortho_core_strength, strength_basis, wrinkling_model
):
    """Not hard-coded: a very low core compression modulus makes wrinkling govern."""
    loose = DeflectionRequirement(maximum_total_deflection=1.0)  # never governs
    floppy = CoreCompressionProperties(
        name="TEST-CORE", compression_strength=2.0e6, compression_modulus=1.0e5
    )
    a = _design(
        basis, ortho_core, ortho_core_strength, floppy, strength_basis, loose,
        LocalScreenBasis(
            wrinkling_model=wrinkling_model,
            patch_load=LocalPatchLoad.square(force=100.0, side=0.025),
        ),
    )
    assert a.capacity.governing_constraint is SandwichConstraint.WRINKLING
    assert a.capacity.sandwich_limit == pytest.approx(a.capacity.wrinkling_limit, rel=1e-15)


def test_capacity_to_areal_mass_hand_calc(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
    requirement, local_basis,
):
    a = _design(basis, ortho_core, ortho_core_strength, core_compression,
                strength_basis, requirement, local_basis)
    # areal mass = 2*2700*0.0004 + 40*0.020 = 2.96 kg/m^2
    assert a.capacity.areal_mass == pytest.approx(2.96, rel=1e-12)
    assert a.capacity.capacity_to_areal_mass == pytest.approx(
        a.capacity.sandwich_limit / 2.96, rel=1e-12
    )


# -- table shape and validation --------------------------------------------


def test_sandwich_table_shape_and_order(basis, strength_basis, requirement, local_basis):
    table = build_sandwich_table(basis, strength_basis, requirement, local_basis)
    n = len(CANDIDATE_CORES)
    assert len(table) == 2 * n
    assert all(a.result.direction is CoreShearDirection.L for a in table[:n])
    assert all(a.result.direction is CoreShearDirection.W for a in table[n:])
    assert [a.result.core_name for a in table[:n]] == [c.name for c in CANDIDATE_CORES]


def test_sandwich_table_rejects_empty_inputs(basis, strength_basis, requirement, local_basis):
    with pytest.raises(ValueError):
        build_sandwich_table(basis, strength_basis, requirement, local_basis, cores=[])
    with pytest.raises(ValueError):
        build_sandwich_table(basis, strength_basis, requirement, local_basis, directions=[])


def test_sandwich_table_rejects_a_missing_compression_record(
    basis, strength_basis, requirement, local_basis
):
    with pytest.raises(KeyError):
        build_sandwich_table(
            basis, strength_basis, requirement, local_basis,
            compressions=[
                CoreCompressionProperties(
                    name="SOMETHING-ELSE", compression_strength=2e6, compression_modulus=5e8
                )
            ],
        )


def test_mismatched_compression_record_rejected(
    basis, ortho_core, ortho_core_strength, strength_basis, requirement, local_basis
):
    wrong = CoreCompressionProperties(
        name="SOMETHING-ELSE", compression_strength=2e6, compression_modulus=5e8
    )
    with pytest.raises(ValueError):
        _design(basis, ortho_core, ortho_core_strength, wrong, strength_basis,
                requirement, local_basis)


def test_local_screen_basis_type_checks(wrinkling_model, patch_load):
    with pytest.raises(TypeError):
        LocalScreenBasis(wrinkling_model=0.5, patch_load=patch_load)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        LocalScreenBasis(wrinkling_model=wrinkling_model, patch_load=0.5)  # type: ignore[arg-type]


# -- core depth + wrinkling ------------------------------------------------


@pytest.fixture
def depth_rows(basis, strength_basis, requirement, local_basis):
    return core_depth_wrinkling_sweep(
        basis, get_core("HC-AL-45"), get_core_strength("HC-AL-45"),
        get_core_compression("HC-AL-45"), CORE_DEPTHS,
        strength_basis, requirement, local_basis, directions=["L"],
    )


def test_screening_stress_does_not_move_with_core_depth(depth_rows):
    # Under this convention sigma_wr depends only on material moduli.
    assert len({r.wrinkling_screening_stress for r in depth_rows}) == 1


def test_face_stress_demand_falls_with_core_depth(depth_rows):
    assert all(b.face_stress < a.face_stress for a, b in zip(depth_rows, depth_rows[1:]))


def test_wrinkling_margin_improves_with_core_depth(depth_rows):
    # Not because the allowable rises, but because the demand falls.
    assert all(
        b.wrinkling_margin > a.wrinkling_margin for a, b in zip(depth_rows, depth_rows[1:])
    )
    assert all(
        b.wrinkling_limit > a.wrinkling_limit for a, b in zip(depth_rows, depth_rows[1:])
    )


def test_core_depth_sweep_reports_both_directions(basis, strength_basis, requirement, local_basis):
    rows = core_depth_wrinkling_sweep(
        basis, get_core("HC-AL-45"), get_core_strength("HC-AL-45"),
        get_core_compression("HC-AL-45"), CORE_DEPTHS,
        strength_basis, requirement, local_basis,
    )
    assert len(rows) == 2 * len(CORE_DEPTHS)
    l_rows = [r for r in rows if r.direction is CoreShearDirection.L]
    w_rows = [r for r in rows if r.direction is CoreShearDirection.W]
    for a, b in zip(l_rows, w_rows):
        assert b.wrinkling_screening_stress < a.wrinkling_screening_stress
        assert b.face_stress == a.face_stress  # demand is direction-independent


def test_core_depth_sweep_does_not_mutate_the_basis(
    basis, strength_basis, requirement, local_basis
):
    before = basis.geometry.core_thickness
    core_depth_wrinkling_sweep(
        basis, get_core("HC-AL-45"), get_core_strength("HC-AL-45"),
        get_core_compression("HC-AL-45"), CORE_DEPTHS,
        strength_basis, requirement, local_basis,
    )
    assert basis.geometry.core_thickness == before


def test_core_depth_sweep_rejects_empty_inputs(basis, strength_basis, requirement, local_basis):
    args = (basis, get_core("HC-AL-45"), get_core_strength("HC-AL-45"),
            get_core_compression("HC-AL-45"))
    with pytest.raises(ValueError):
        core_depth_wrinkling_sweep(*args, [], strength_basis, requirement, local_basis)
    with pytest.raises(ValueError):
        core_depth_wrinkling_sweep(
            *args, CORE_DEPTHS, strength_basis, requirement, local_basis, directions=[]
        )


# -- regression: Milestones 1-3 unchanged through the Milestone 4 layer ----


def test_milestone2_candidate_results_are_unchanged(
    basis, strength_basis, requirement, local_basis
):
    m2 = evaluate_candidates(basis, CANDIDATE_CORES)
    m4 = [a.result for a in build_sandwich_table(basis, strength_basis, requirement, local_basis)]
    assert len(m2) == len(m4)
    for a, b in zip(m2, m4):
        assert asdict(a) == asdict(b)


def test_milestone3_assessments_are_unchanged(basis, strength_basis, requirement, local_basis):
    m3 = build_design_table(basis, strength_basis, requirement)
    m4 = build_sandwich_table(basis, strength_basis, requirement, local_basis)
    assert len(m3) == len(m4)
    for a, b in zip(m3, m4):
        assert asdict(a.deflection) == asdict(b.design.deflection)
        assert asdict(a.strength) == asdict(b.design.strength)
        assert asdict(a.capacity) == asdict(b.design.capacity)


def test_milestone3_capacity_fields_survive_on_the_milestone4_capacity(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
    requirement, local_basis,
):
    m3 = assess_candidate_design(
        basis, ortho_core, ortho_core_strength, "L", strength_basis, requirement
    )
    m4 = _design(basis, ortho_core, ortho_core_strength, core_compression,
                 strength_basis, requirement, local_basis)
    assert m4.capacity.deflection_limit == m3.capacity.deflection_limit
    assert m4.capacity.face_limit == m3.capacity.face_limit
    assert m4.capacity.core_shear_limit == m3.capacity.core_shear_limit
    assert m4.capacity.areal_mass == m3.capacity.areal_mass


# -- determinism -----------------------------------------------------------


def test_local_assessment_is_deterministic(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis,
    requirement, local_basis,
):
    def snap():
        a = _design(basis, ortho_core, ortho_core_strength, core_compression,
                    strength_basis, requirement, local_basis)
        return (asdict(a.local), asdict(a.capacity))

    first = snap()
    for _ in range(5):
        assert snap() == first


def test_sandwich_table_is_deterministic(basis, strength_basis, requirement, local_basis):
    def snap():
        return [
            (
                a.label,
                a.local.wrinkling_margin,
                a.local.core_compression_margin,
                a.capacity.sandwich_limit,
                str(a.capacity.governing_constraint),
                str(a.local.governing_local_mode),
                str(a.retention),
            )
            for a in build_sandwich_table(basis, strength_basis, requirement, local_basis)
        ]

    first = snap()
    for _ in range(5):
        assert snap() == first


def test_identical_bases_give_identical_results(
    m2_geometry, m2_face, ortho_core, ortho_core_strength, core_compression,
    strength_basis, requirement, local_basis,
):
    a = StudyBasis(geometry=m2_geometry, face=m2_face, load=50.0)
    b = StudyBasis(geometry=m2_geometry, face=m2_face, load=50.0)
    assert asdict(
        _design(a, ortho_core, ortho_core_strength, core_compression, strength_basis,
                requirement, local_basis).local
    ) == asdict(
        _design(b, ortho_core, ortho_core_strength, core_compression, strength_basis,
                requirement, local_basis).local
    )


# -- headline Milestone 4 outcome ------------------------------------------


def test_all_candidates_are_retained_at_the_canonical_basis(
    basis, strength_basis, requirement
):
    """Reported as found: local modes do not change viability at this baseline."""
    from sandwich_panel import WrinklingModel

    canonical = LocalScreenBasis(
        wrinkling_model=WrinklingModel(coefficient=0.5, source_note="illustrative"),
        patch_load=LocalPatchLoad.square(force=100.0, side=0.025),
    )
    table = build_sandwich_table(basis, strength_basis, requirement, canonical)
    assert all(a.retention is RetentionStatus.RETAINED for a in table)
    assert all(a.overall_feasible for a in table)


# -- example smoke test ----------------------------------------------------


def _run_example(capsys):
    saved = sys.argv[:]
    sys.argv = [str(EXAMPLE)]
    try:
        runpy.run_path(str(EXAMPLE), run_name="__main__")
    finally:
        sys.argv = saved
    return capsys.readouterr().out


def test_local_failure_example_runs(capsys):
    out = _run_example(capsys)
    for heading in (
        "STUDY BASIS",
        "CANDIDATE LOCAL PROPERTIES",
        "GLOBAL SCREEN",
        "LOCAL PATCH SCREEN",
        "GLOBAL LOAD CAPACITY",
        "LOCAL PATCH CAPACITY",
        "LOCAL PATCH FORCE SENSITIVITY",
        "PATCH-SIZE SENSITIVITY",
        "CORE-DEPTH + WRINKLING TRADE",
        "CANDIDATE RETENTION",
    ):
        assert heading in out
    assert "ILLUSTRATIVE" in out
    assert (
        "No final core is selected in Milestone 4; retained candidates proceed to practical"
        in out
    )


def test_local_failure_example_never_declares_a_selection(capsys):
    out = _run_example(capsys).upper()
    for banned in ("SELECTED CORE", "RECOMMENDED CORE", "WINNER", "WE RECOMMEND", "BEST CORE"):
        assert banned not in out


def test_local_failure_example_states_the_deferrals(capsys):
    out = _run_example(capsys).lower()
    assert "deferred" in out
    assert "indentation" in out
    assert "not an insert analysis" in out
