"""W-AC: strength database alignment, directional identities, cross-candidate invariance."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    CANDIDATE_CORES,
    CANDIDATE_CORE_STRENGTHS,
    ILLUSTRATIVE_FACE_STRENGTH,
    ILLUSTRATIVE_STRENGTH_NOTE,
    CoreShearDirection,
    OrthotropicCoreStrength,
    build_design_table,
    core_names,
    core_strength_names,
    get_core_strength,
)


# -- W / X / Y. database alignment ----------------------------------------


def test_every_elastic_candidate_has_a_matching_strength_record():
    # W.
    assert core_strength_names() == core_names()
    for core in CANDIDATE_CORES:
        assert get_core_strength(core.name).name == core.name


def test_no_extra_strength_only_candidate_exists():
    assert set(core_strength_names()) == set(core_names())
    assert len(CANDIDATE_CORE_STRENGTHS) == len(CANDIDATE_CORES)


def test_strength_database_order_is_deterministic_and_matches():
    # X.
    first = core_strength_names()
    for _ in range(5):
        assert core_strength_names() == first
    assert isinstance(CANDIDATE_CORE_STRENGTHS, tuple)
    assert list(core_strength_names()) == [c.name for c in CANDIDATE_CORES]


def test_strength_record_names_are_unique():
    # Y.
    names = core_strength_names()
    assert len(names) == len(set(names))


def test_no_duplicate_strength_records():
    signatures = {
        (s.name, s.shear_strength_L, s.shear_strength_W) for s in CANDIDATE_CORE_STRENGTHS
    }
    assert len(signatures) == len(CANDIDATE_CORE_STRENGTHS)


def test_all_strengths_positive_and_finite():
    # Z.
    for s in CANDIDATE_CORE_STRENGTHS:
        for value in (s.shear_strength_L, s.shear_strength_W):
            assert value > 0.0
            assert math.isfinite(value)
    assert ILLUSTRATIVE_FACE_STRENGTH.yield_strength > 0.0
    assert math.isfinite(ILLUSTRATIVE_FACE_STRENGTH.yield_strength)


def test_every_strength_record_carries_provenance():
    for s in CANDIDATE_CORE_STRENGTHS:
        assert s.source_note == ILLUSTRATIVE_STRENGTH_NOTE
        assert "ILLUSTRATIVE STRENGTH INPUT" in s.source_note
        assert "NOT MANUFACTURER ALLOWABLE" in s.source_note
        assert s.notes is not None and s.notes.strip()
    assert ILLUSTRATIVE_FACE_STRENGTH.source_note == ILLUSTRATIVE_STRENGTH_NOTE


def test_provenance_note_disclaims_allowables_and_qualification():
    note = ILLUSTRATIVE_STRENGTH_NOTE.lower()
    assert "not a design allowable" in note
    assert "not qualification data" in note


def test_face_strength_record_claims_no_alloy():
    # The elastic face material was never tied to a specific alloy, so the
    # strength record must not silently introduce one.
    text = f"{ILLUSTRATIVE_FACE_STRENGTH.name} {ILLUSTRATIVE_FACE_STRENGTH.notes}".lower()
    for alloy in ("6061", "7075", "2024", "5052", "t6", "t651"):
        assert alloy not in text


def test_no_ultimate_basis_is_supplied():
    # Milestone 3 uses ONE clearly defined allowable basis: yield.
    assert ILLUSTRATIVE_FACE_STRENGTH.ultimate_strength is None


def test_every_candidate_is_stronger_in_L_than_in_W():
    for s in CANDIDATE_CORE_STRENGTHS:
        assert s.shear_strength_L > s.shear_strength_W
        assert s.directional_strength_ratio > 1.0


def test_strength_ratios_are_in_a_plausible_band():
    for s in CANDIDATE_CORE_STRENGTHS:
        assert 1.4 <= s.directional_strength_ratio <= 2.2


def test_strength_broadly_tracks_density_within_the_aluminium_family():
    aluminium = [c for c in CANDIDATE_CORES if c.family == "aluminium-honeycomb-equivalent"]
    pairs = [(c.density, get_core_strength(c.name).shear_strength_L) for c in aluminium]
    pairs.sort()
    strengths = [s for _, s in pairs]
    assert strengths == sorted(strengths)


def test_the_aramid_candidate_is_weaker_than_its_density_peer():
    # Mirrors its lower shear stiffness: a different family, not just a heavier one.
    aramid = get_core_strength("HC-AR-48")
    aluminium = get_core_strength("HC-AL-45")
    assert aramid.shear_strength_L < aluminium.shear_strength_L


def test_get_core_strength_rejects_unknown_name():
    with pytest.raises(KeyError):
        get_core_strength("NO-SUCH-CORE")


def test_get_core_strength_is_exact_match_only():
    with pytest.raises(KeyError):
        get_core_strength("hc-al-30")


# -- AA. directional core-load ratio identity -----------------------------


def test_core_load_limit_ratio_equals_strength_ratio(basis, strength_basis, requirement):
    table = build_design_table(basis, strength_basis, requirement)
    l_rows = {a.result.core_name: a for a in table if a.result.direction is CoreShearDirection.L}
    w_rows = {a.result.core_name: a for a in table if a.result.direction is CoreShearDirection.W}
    for core in CANDIDATE_CORES:
        s = get_core_strength(core.name)
        ratio = l_rows[core.name].capacity.core_shear_limit / w_rows[core.name].capacity.core_shear_limit
        assert ratio == pytest.approx(s.directional_strength_ratio, rel=1e-12)


def test_core_load_limit_hand_calc_for_every_candidate(basis, strength_basis, requirement):
    # P_core = 2 * b * t_c * tau = 2 * 0.5 * 0.020 * tau = 0.02 * tau
    table = build_design_table(basis, strength_basis, requirement)
    for a in table:
        s = get_core_strength(a.result.core_name)
        expected = 0.02 * s.shear_strength(a.result.direction)
        assert a.capacity.core_shear_limit == pytest.approx(expected, rel=1e-12)


def test_W_capacity_is_never_above_L_capacity(basis, strength_basis, requirement):
    table = build_design_table(basis, strength_basis, requirement)
    l_rows = {a.result.core_name: a for a in table if a.result.direction is CoreShearDirection.L}
    w_rows = {a.result.core_name: a for a in table if a.result.direction is CoreShearDirection.W}
    for name in l_rows:
        assert w_rows[name].capacity.preliminary_limit <= l_rows[name].capacity.preliminary_limit
        assert w_rows[name].capacity.core_shear_limit < l_rows[name].capacity.core_shear_limit


# -- AB / AC. cross-candidate invariance ----------------------------------


def test_same_face_limit_across_all_candidates(basis, strength_basis, requirement):
    # AB. Face stress depends on geometry and load only, so the face limit cannot
    # depend on which core is fitted.
    table = build_design_table(basis, strength_basis, requirement)
    assert len({a.capacity.face_limit for a in table}) == 1


def test_same_face_stress_and_margin_across_all_candidates(basis, strength_basis, requirement):
    table = build_design_table(basis, strength_basis, requirement)
    assert len({a.strength.face_stress for a in table}) == 1
    assert len({a.strength.face_margin for a in table}) == 1


def test_same_core_shear_stress_across_all_candidates(basis, strength_basis, requirement):
    # The demand is geometry/load driven; only the allowable differs by candidate.
    table = build_design_table(basis, strength_basis, requirement)
    assert len({a.strength.core_shear_stress for a in table}) == 1
    # ...while the allowable differs for every candidate AND every direction.
    assert len({a.strength.core_shear_allowable for a in table}) == 2 * len(CANDIDATE_CORES)
    # so the core margin is the only strength quantity that varies across the table
    assert len({a.strength.core_shear_margin for a in table}) == 2 * len(CANDIDATE_CORES)


def test_same_bending_deflection_across_all_candidates(basis, strength_basis, requirement):
    # AC.
    table = build_design_table(basis, strength_basis, requirement)
    assert len({a.result.bending_deflection for a in table}) == 1
    assert len({a.result.flexural_rigidity for a in table}) == 1


def test_design_table_shape_and_order(basis, strength_basis, requirement):
    table = build_design_table(basis, strength_basis, requirement)
    n = len(CANDIDATE_CORES)
    assert len(table) == 2 * n
    assert all(a.result.direction is CoreShearDirection.L for a in table[:n])
    assert all(a.result.direction is CoreShearDirection.W for a in table[n:])
    assert [a.result.core_name for a in table[:n]] == list(core_names())


def test_design_table_rejects_empty_inputs(basis, strength_basis, requirement):
    with pytest.raises(ValueError):
        build_design_table(basis, strength_basis, requirement, cores=[])
    with pytest.raises(ValueError):
        build_design_table(basis, strength_basis, requirement, directions=[])


def test_design_table_rejects_a_core_without_a_strength_record(basis, strength_basis, requirement):
    with pytest.raises(KeyError):
        build_design_table(
            basis, strength_basis, requirement,
            strengths=[
                OrthotropicCoreStrength(
                    name="SOMETHING-ELSE", shear_strength_L=1.0e6, shear_strength_W=0.5e6
                )
            ],
        )
