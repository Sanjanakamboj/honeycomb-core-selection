"""AA-AL: candidate integration, feasibility logic and the preliminary selection."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from sandwich_panel import (
    CANDIDATE_CORES,
    SELECTION_BASIS,
    CoreShearDirection,
    DeflectionRequirement,
    FaceStrength,
    FrequencyRequirement,
    PreliminaryScreens,
    StrengthBasis,
    build_integrated_table,
    build_sandwich_table,
    core_names,
    evaluate_candidates,
    select_preliminary_core,
)

from .conftest import M2_P


# -- AA / AB. EI invariance -------------------------------------------------


def test_same_EI_across_every_candidate(basis, screens):
    table = build_integrated_table(basis, screens)
    assert len({a.result.flexural_rigidity for a in table}) == 1


def test_EI_matches_the_milestone1_reference(basis, screens):
    table = build_integrated_table(basis, screens)
    assert table[0].result.flexural_rigidity == pytest.approx(2913.4933333, rel=1e-9)


def test_same_bending_only_frequency_across_L_and_W(basis, screens):
    table = build_integrated_table(basis, screens)
    by_core: dict[str, set[float]] = {}
    for a in table:
        by_core.setdefault(a.result.core_name, set()).add(a.modal.bending_only_frequency)
    for values in by_core.values():
        assert len(values) == 1  # bit-for-bit identical between L and W


# -- AC. candidate mass unchanged from Milestone 2 --------------------------


def test_candidate_masses_match_milestone2(basis, screens):
    m2 = {r.label: r.areal_mass for r in evaluate_candidates(basis, CANDIDATE_CORES)}
    for a in build_integrated_table(basis, screens):
        assert a.areal_mass == m2[a.label]
    assert sorted({round(v, 3) for v in m2.values()}) == [2.76, 3.06, 3.12, 3.36, 3.76]


# -- AD. static results unchanged from Milestones 2-4 -----------------------


def test_all_static_results_are_identical_to_milestones_2_to_4(basis, screens):
    m4 = build_sandwich_table(
        basis, screens.strength, screens.deflection, screens.local
    )
    m5 = build_integrated_table(basis, screens)
    assert len(m4) == len(m5)
    for a, b in zip(m4, m5):
        assert asdict(a.result) == asdict(b.result)
        assert asdict(a.design.deflection) == asdict(b.sandwich.design.deflection)
        assert asdict(a.design.strength) == asdict(b.sandwich.design.strength)
        assert asdict(a.design.capacity) == asdict(b.sandwich.design.capacity)
        assert asdict(a.local) == asdict(b.sandwich.local)
        assert asdict(a.capacity) == asdict(b.sandwich.capacity)


def test_static_load_response_is_still_the_50N_case(basis, screens):
    assert basis.load == M2_P
    table = build_integrated_table(basis, screens)
    assert table[0].result.total_deflection == pytest.approx(1.3004e-3, rel=1e-4)


# -- AE. integrated feasibility AND logic -----------------------------------


def test_overall_feasible_is_the_and_of_all_four(basis, screens):
    for a in build_integrated_table(basis, screens):
        assert a.overall_feasible == (
            a.deflection_feasible
            and a.global_strength_feasible
            and a.local_failure_feasible
            and a.modal_feasible
        )
        assert a.static_feasible == (
            a.deflection_feasible and a.global_strength_feasible and a.local_failure_feasible
        )


@pytest.mark.parametrize("screen", ["deflection", "strength", "frequency"])
def test_each_screen_can_fail_the_overall_result_alone(basis, screens, screen):
    if screen == "deflection":
        variant = screens.with_deflection(DeflectionRequirement(maximum_total_deflection=1.0e-4))
    elif screen == "frequency":
        variant = screens.with_frequency(FrequencyRequirement(minimum_frequency_hz=1000.0))
    else:
        variant = PreliminaryScreens(
            deflection=screens.deflection,
            strength=StrengthBasis(face_strength=FaceStrength(name="weak", yield_strength=1.0e6)),
            local=screens.local,
            frequency=screens.frequency,
        )
    table = build_integrated_table(basis, variant)
    assert all(not a.overall_feasible for a in table)
    for a in table:
        assert screen.replace("strength", "face_yield") in a.failing_screens


def test_failing_screens_lists_every_failure(basis, screens):
    variant = screens.with_deflection(
        DeflectionRequirement(maximum_total_deflection=1.0e-4)
    ).with_frequency(FrequencyRequirement(minimum_frequency_hz=1000.0))
    a = build_integrated_table(basis, variant)[0]
    assert "deflection" in a.failing_screens
    assert "frequency" in a.failing_screens


def test_all_configurations_pass_at_the_canonical_basis(basis, screens):
    table = build_integrated_table(basis, screens)
    assert all(a.overall_feasible for a in table)
    assert len(table) == 10


# -- AF. no dimensional blending --------------------------------------------


def test_the_four_margin_families_are_never_blended(basis, screens):
    a = build_integrated_table(basis, screens)[0]
    assert abs(a.sandwich.design.deflection.margin) < 1.0  # metres
    assert a.sandwich.design.strength.governing_margin > 1.0  # dimensionless
    assert a.sandwich.local.governing_local_margin > 1.0  # dimensionless
    assert a.modal.margin_hz > 1.0  # hertz
    for banned in ("combined_margin", "total_margin", "overall_margin", "margin", "min_margin"):
        assert not hasattr(a, banned)


def test_utilisations_are_dimensionless_and_comparable(basis, screens):
    for a in build_integrated_table(basis, screens):
        u = a.utilisation
        for name, value in u.global_screens.items():
            assert 0.0 < value <= 1.0, name  # every screen passes here
        assert 0.0 < u.core_compression_local_patch <= 1.0


def test_utilisation_hand_calcs(basis, screens):
    a = build_integrated_table(basis, screens)[0]
    u, s = a.utilisation, a.sandwich
    assert u.deflection == pytest.approx(
        s.result.total_deflection / screens.deflection.maximum_total_deflection, rel=1e-12
    )
    assert u.face_yield == pytest.approx(
        s.design.strength.face_stress / s.design.strength.face_allowable, rel=1e-12
    )
    assert u.core_shear == pytest.approx(
        s.design.strength.core_shear_stress / s.design.strength.core_shear_allowable, rel=1e-12
    )
    assert u.wrinkling == pytest.approx(
        s.local.face_stress / s.local.wrinkling_screening_stress, rel=1e-12
    )
    assert u.frequency == pytest.approx(
        screens.frequency.minimum_frequency_hz / a.modal.frequency, rel=1e-12
    )
    assert u.core_compression_local_patch == pytest.approx(
        s.local.local_core_compression_stress / s.local.core_compression_allowable, rel=1e-12
    )


def test_utilisation_below_one_iff_the_screen_passes(basis, screens):
    tight = screens.with_frequency(FrequencyRequirement(minimum_frequency_hz=30.0))
    for a in build_integrated_table(basis, tight):
        assert (a.utilisation.frequency <= 1.0) == a.modal_feasible


def test_closest_global_screen_is_the_largest_utilisation(basis, screens):
    for a in build_integrated_table(basis, screens):
        u = a.utilisation
        assert u.closest_global_utilisation == max(u.global_screens.values())
        assert u.global_screens[u.closest_global_screen] == u.closest_global_utilisation


def test_local_patch_utilisation_is_excluded_from_the_global_comparison(basis, screens):
    for a in build_integrated_table(basis, screens):
        assert "core_compression" not in a.utilisation.global_screens
        assert len(a.utilisation.global_screens) == 5


def test_frequency_becomes_the_closest_screen_for_the_heaviest_cores(basis, screens):
    """A real result: for heavy cores the modal screen overtakes deflection."""
    table = build_integrated_table(basis, screens)
    closest = {a.label: a.utilisation.closest_global_screen for a in table}
    assert closest["HC-AL-80 [L]"] == "frequency"
    assert closest["HC-AL-80 [W]"] == "frequency"
    assert closest["HC-AL-30 [L]"] == "deflection"


# -- AG. deterministic ordering ---------------------------------------------


def test_table_ordering_is_deterministic_and_direction_major(basis, screens):
    table = build_integrated_table(basis, screens)
    n = len(CANDIDATE_CORES)
    assert len(table) == 2 * n
    assert all(a.result.direction is CoreShearDirection.L for a in table[:n])
    assert all(a.result.direction is CoreShearDirection.W for a in table[n:])
    assert [a.result.core_name for a in table[:n]] == list(core_names())
    labels = [a.label for a in table]
    for _ in range(3):
        assert [a.label for a in build_integrated_table(basis, screens)] == labels


def test_table_rejects_empty_inputs(basis, screens):
    with pytest.raises(ValueError):
        build_integrated_table(basis, screens, cores=[])
    with pytest.raises(ValueError):
        build_integrated_table(basis, screens, directions=[])


def test_screens_type_checks(requirement, strength_basis, local_basis, frequency_requirement):
    with pytest.raises(TypeError):
        PreliminaryScreens(
            deflection="nope", strength=strength_basis,
            local=local_basis, frequency=frequency_requirement,
        )
    with pytest.raises(TypeError):
        PreliminaryScreens(
            deflection=requirement, strength=strength_basis,
            local=local_basis, frequency="nope",
        )


# -- AH-AK. selection --------------------------------------------------------


def test_selection_is_deterministic(basis, screens):
    table = build_integrated_table(basis, screens)
    first = select_preliminary_core(table)
    for _ in range(5):
        assert asdict(select_preliminary_core(build_integrated_table(basis, screens))) == asdict(first)


def test_selection_picks_the_minimum_areal_mass_feasible_configuration(basis, screens):
    # AJ.
    table = build_integrated_table(basis, screens)
    selection = select_preliminary_core(table)
    feasible = [a for a in table if a.overall_feasible]
    assert selection is not None
    assert selection.areal_mass == min(a.areal_mass for a in feasible)
    assert selection.candidate == "HC-AL-30"
    assert selection.direction is CoreShearDirection.L
    assert selection.feasible_configuration_count == len(feasible)


def test_selection_only_considers_feasible_configurations(basis, screens):
    # AI. Make the lightest core infeasible on frequency and it must not be chosen.
    table = build_integrated_table(basis, screens)
    lightest = min(table, key=lambda a: a.areal_mass)
    just_above = lightest.modal.frequency * 1.0001
    variant = screens.with_frequency(FrequencyRequirement(minimum_frequency_hz=just_above))
    new_table = build_integrated_table(basis, variant)
    selection = select_preliminary_core(new_table)
    if selection is not None:
        assert selection.label != lightest.label
        assert all(
            a.overall_feasible for a in new_table if a.label == selection.label
        )


def test_selection_tie_break_prefers_the_larger_frequency_margin(basis, screens):
    # AK. L and W of the same candidate share an areal mass; L has the higher
    # frequency, so the mass tie must break toward L.
    table = build_integrated_table(basis, screens)
    selection = select_preliminary_core(table)
    l_row = next(a for a in table if a.label == "HC-AL-30 [L]")
    w_row = next(a for a in table if a.label == "HC-AL-30 [W]")
    assert l_row.areal_mass == w_row.areal_mass  # exact tie on the primary key
    assert l_row.modal.margin_hz > w_row.modal.margin_hz
    assert selection.direction is CoreShearDirection.L


def test_selection_tie_break_is_stable_for_identical_configurations(basis, screens):
    table = build_integrated_table(basis, screens)
    doubled = table + table  # exact duplicates
    assert select_preliminary_core(doubled).label == select_preliminary_core(table).label


# -- AL. no-selection case ---------------------------------------------------


def test_no_feasible_configuration_returns_none(basis, screens):
    impossible = screens.with_frequency(FrequencyRequirement(minimum_frequency_hz=1000.0))
    table = build_integrated_table(basis, impossible)
    assert all(not a.overall_feasible for a in table)
    assert select_preliminary_core(table) is None


def test_no_feasible_configuration_on_a_tight_deflection_limit(basis, screens):
    impossible = screens.with_deflection(DeflectionRequirement(maximum_total_deflection=1.0e-4))
    assert select_preliminary_core(build_integrated_table(basis, impossible)) is None


def test_empty_input_returns_none():
    assert select_preliminary_core([]) is None


# -- selection reporting ------------------------------------------------------


def test_selection_reports_the_stated_basis(basis, screens):
    selection = select_preliminary_core(build_integrated_table(basis, screens))
    assert selection.selection_basis == SELECTION_BASIS
    assert "minimum areal mass" in selection.selection_basis
    assert "optimum" not in selection.selection_basis.lower()
    assert "optimal" not in selection.selection_basis.lower()


def test_selection_carries_the_full_feasibility_record(basis, screens):
    selection = select_preliminary_core(build_integrated_table(basis, screens))
    assert selection.deflection_feasible is True
    assert selection.global_strength_feasible is True
    assert selection.local_failure_feasible is True
    assert selection.modal_feasible is True
    assert selection.first_mode_frequency == pytest.approx(31.100, rel=1e-3)
    assert selection.frequency_margin_hz == pytest.approx(6.100, rel=1e-3)
    assert selection.areal_mass == pytest.approx(2.760, rel=1e-12)
    assert selection.total_panel_mass == pytest.approx(2.760 * 0.75, rel=1e-12)
    assert selection.closest_global_screen == "deflection"
    assert 0.0 < selection.closest_global_utilisation <= 1.0
    assert selection.label == "HC-AL-30 [L]"


def test_the_lightest_core_also_has_the_highest_frequency(basis, screens):
    """The Milestone 5 headline: mass beats shear stiffness for frequency."""
    table = build_integrated_table(basis, screens)
    lightest = min(table, key=lambda a: a.areal_mass)
    highest_f = max(table, key=lambda a: a.modal.frequency)
    assert lightest.label == highest_f.label == "HC-AL-30 [L]"
    # ...even though it has the LOWEST shear modulus of the set.
    assert lightest.modal.effective_shear_modulus == min(
        a.modal.effective_shear_modulus for a in table if a.result.direction is CoreShearDirection.L
    )
