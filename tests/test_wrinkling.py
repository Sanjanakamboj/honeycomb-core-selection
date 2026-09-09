"""Q-AA: wrinkling model validation, screening stress, scaling identities and load limit."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    CANDIDATE_CORES,
    CoreCompressionProperties,
    CoreShearDirection,
    FaceMaterial,
    StudyBasis,
    WrinklingModel,
    assess_local_failure,
    build_sandwich_table,
    evaluate_candidate,
    get_core,
    get_core_compression,
    wrinkling_margin,
    wrinkling_screening_stress,
)

E_F = 70.0e9
E_C = 500.0e6
C_WR = 0.5
SIGMA_WR_L = C_WR * (E_F * E_C * 50.0e6) ** (1 / 3)
SIGMA_WR_W = C_WR * (E_F * E_C * 20.0e6) ** (1 / 3)
SIGMA_FACE_50N = 4.6850973860e6


# -- Q. model validation ---------------------------------------------------


@pytest.mark.parametrize("bad", [0.0, -0.5, math.nan, math.inf, -math.inf])
def test_wrinkling_model_rejects_bad_coefficient(bad):
    with pytest.raises(ValueError):
        WrinklingModel(coefficient=bad)


def test_wrinkling_coefficient_has_no_default():
    # The coefficient must be supplied explicitly: no empirical constant may hide
    # inside the package.
    with pytest.raises(TypeError):
        WrinklingModel()  # type: ignore[call-arg]


def test_wrinkling_model_is_immutable(wrinkling_model):
    with pytest.raises(Exception):
        wrinkling_model.coefficient = 1.0  # type: ignore[misc]


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_screening_stress_validates_every_modulus(wrinkling_model, bad):
    for kwargs in (
        {"face_modulus": bad, "core_compression_modulus": E_C, "core_shear_modulus": 50e6},
        {"face_modulus": E_F, "core_compression_modulus": bad, "core_shear_modulus": 50e6},
        {"face_modulus": E_F, "core_compression_modulus": E_C, "core_shear_modulus": bad},
    ):
        with pytest.raises(ValueError):
            wrinkling_screening_stress(wrinkling_model, **kwargs)


def test_screening_stress_rejects_a_non_model():
    with pytest.raises(TypeError):
        wrinkling_screening_stress(0.5, E_F, E_C, 50e6)  # type: ignore[arg-type]


# -- R. screening-stress hand calculation ----------------------------------


def test_screening_stress_hand_calc(wrinkling_model):
    # 0.5 * (70e9 * 500e6 * 50e6)^(1/3) = 0.5 * (1.75e27)^(1/3)
    value = wrinkling_screening_stress(wrinkling_model, E_F, E_C, 50.0e6)
    assert value == pytest.approx(0.5 * (1.75e27) ** (1 / 3), rel=1e-12)
    assert value == pytest.approx(6.0256e8, rel=1e-4)
    assert value == pytest.approx(SIGMA_WR_L, rel=1e-15)


def test_model_method_matches_the_free_function(wrinkling_model):
    assert wrinkling_model.screening_stress(E_F, E_C, 50.0e6) == wrinkling_screening_stress(
        wrinkling_model, E_F, E_C, 50.0e6
    )


def test_screening_stress_is_linear_in_the_coefficient():
    a = wrinkling_screening_stress(WrinklingModel(coefficient=0.5), E_F, E_C, 50e6)
    b = wrinkling_screening_stress(WrinklingModel(coefficient=1.0), E_F, E_C, 50e6)
    assert b == pytest.approx(2 * a, rel=1e-12)


# -- S / T / U. cube-root scaling in each modulus --------------------------


def test_face_modulus_cube_root_scaling(wrinkling_model):
    # S. Doubling E_f multiplies sigma_wr by 2^(1/3).
    a = wrinkling_screening_stress(wrinkling_model, E_F, E_C, 50e6)
    b = wrinkling_screening_stress(wrinkling_model, 8 * E_F, E_C, 50e6)
    assert b == pytest.approx(2.0 * a, rel=1e-12)  # 8^(1/3) = 2
    c = wrinkling_screening_stress(wrinkling_model, 2 * E_F, E_C, 50e6)
    assert c == pytest.approx(2 ** (1 / 3) * a, rel=1e-12)


def test_core_compression_modulus_cube_root_scaling(wrinkling_model):
    # T.
    a = wrinkling_screening_stress(wrinkling_model, E_F, E_C, 50e6)
    b = wrinkling_screening_stress(wrinkling_model, E_F, 27 * E_C, 50e6)
    assert b == pytest.approx(3.0 * a, rel=1e-12)  # 27^(1/3) = 3


def test_core_shear_modulus_cube_root_scaling(wrinkling_model):
    # U.
    a = wrinkling_screening_stress(wrinkling_model, E_F, E_C, 50e6)
    b = wrinkling_screening_stress(wrinkling_model, E_F, E_C, 64 * 50e6)
    assert b == pytest.approx(4.0 * a, rel=1e-12)  # 64^(1/3) = 4


# -- V. L/W ratio identity --------------------------------------------------


def test_L_over_W_screening_stress_ratio_is_the_cube_root_of_the_modulus_ratio(
    basis, ortho_core, core_compression, local_basis
):
    al = assess_local_failure(
        evaluate_candidate(basis, ortho_core, "L"),
        basis.face.youngs_modulus, core_compression, local_basis,
    )
    aw = assess_local_failure(
        evaluate_candidate(basis, ortho_core, "W"),
        basis.face.youngs_modulus, core_compression, local_basis,
    )
    ratio = al.wrinkling_screening_stress / aw.wrinkling_screening_stress
    assert ratio == pytest.approx((50.0 / 20.0) ** (1 / 3), rel=1e-12)
    assert ratio == pytest.approx(1.35720880, rel=1e-6)


def test_ratio_identity_holds_for_every_candidate(basis, strength_basis, requirement, local_basis):
    table = build_sandwich_table(basis, strength_basis, requirement, local_basis)
    l_rows = {a.result.core_name: a for a in table if a.result.direction is CoreShearDirection.L}
    w_rows = {a.result.core_name: a for a in table if a.result.direction is CoreShearDirection.W}
    for core in CANDIDATE_CORES:
        ratio = (
            l_rows[core.name].local.wrinkling_screening_stress
            / w_rows[core.name].local.wrinkling_screening_stress
        )
        expected = (core.shear_modulus_L / core.shear_modulus_W) ** (1 / 3)
        assert ratio == pytest.approx(expected, rel=1e-12)


def test_W_is_always_the_lower_wrinkling_stress(basis, strength_basis, requirement, local_basis):
    # Lower G_W -> lower screening stress -> lower margin.
    table = build_sandwich_table(basis, strength_basis, requirement, local_basis)
    l_rows = {a.result.core_name: a for a in table if a.result.direction is CoreShearDirection.L}
    w_rows = {a.result.core_name: a for a in table if a.result.direction is CoreShearDirection.W}
    for name in l_rows:
        assert w_rows[name].local.wrinkling_screening_stress < l_rows[name].local.wrinkling_screening_stress
        assert w_rows[name].local.wrinkling_margin < l_rows[name].local.wrinkling_margin


# -- W. wrinkling margin hand calculation ----------------------------------


def test_wrinkling_margin_hand_calc(basis, ortho_core, core_compression, local_basis):
    a = assess_local_failure(
        evaluate_candidate(basis, ortho_core, "L"),
        basis.face.youngs_modulus, core_compression, local_basis,
    )
    # demand is the EXISTING global beam-theory face stress, not a new field
    assert a.face_stress == pytest.approx(SIGMA_FACE_50N, rel=1e-6)
    assert a.wrinkling_margin == pytest.approx(SIGMA_WR_L / SIGMA_FACE_50N - 1.0, rel=1e-6)
    assert a.wrinkling_pass is True


def test_wrinkling_margin_helper_hand_calc():
    assert wrinkling_margin(100.0, 250.0) == pytest.approx(1.5, rel=1e-15)


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_wrinkling_margin_validates_inputs(bad):
    with pytest.raises(ValueError):
        wrinkling_margin(bad, 100.0)
    with pytest.raises(ValueError):
        wrinkling_margin(100.0, bad)


def test_wrinkling_demand_is_the_same_face_stress_as_face_yield(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis, requirement, local_basis
):
    from sandwich_panel import assess_sandwich_design

    a = assess_sandwich_design(
        basis, ortho_core, ortho_core_strength, core_compression, "L",
        strength_basis, requirement, local_basis,
    )
    assert a.local.face_stress == a.design.strength.face_stress


# -- X. exact-boundary PASS -------------------------------------------------


def test_wrinkling_exact_boundary_passes():
    """Exactly reaching the screening stress PASSES.

    Tested on the margin function, where the boundary can be represented exactly.
    Reconstructing a boundary E_c through the assessment cannot round-trip
    exactly - a cube root followed by a cube lands a few ULP off - so that path is
    checked as a near-boundary case below instead of pretending to be exact.
    """
    for value in (1.0, 4.6850973860e6, 6.0256e8):
        assert wrinkling_margin(value, value) == pytest.approx(0.0, abs=1e-15)
        assert wrinkling_margin(value, value) >= 0.0


def test_wrinkling_near_boundary_behaviour_through_the_assessment(
    basis, ortho_core, local_basis
):
    r = evaluate_candidate(basis, ortho_core, "L")
    target = r.max_face_stress

    def assess_with_screening_stress(scale):
        # Choose E_c so that sigma_wr lands at `scale` x the face stress demand:
        #   C * (E_f * E_c * G)^(1/3) = scale * sigma
        e_c = (scale * target / local_basis.wrinkling_model.coefficient) ** 3 / (
            basis.face.youngs_modulus * r.effective_shear_modulus
        )
        record = CoreCompressionProperties(
            name="TEST-CORE", compression_strength=2.0e6, compression_modulus=e_c
        )
        return assess_local_failure(r, basis.face.youngs_modulus, record, local_basis)

    at = assess_with_screening_stress(1.0)
    assert at.wrinkling_screening_stress == pytest.approx(target, rel=1e-12)
    assert at.wrinkling_margin == pytest.approx(0.0, abs=1e-12)

    assert assess_with_screening_stress(1.001).wrinkling_pass is True
    assert assess_with_screening_stress(0.999).wrinkling_pass is False


# -- Y. fail case -----------------------------------------------------------


def test_wrinkling_fail_case(basis, ortho_core, local_basis):
    r = evaluate_candidate(basis, ortho_core, "L")
    target = 0.5 * r.max_face_stress
    e_c = (target / local_basis.wrinkling_model.coefficient) ** 3 / (
        basis.face.youngs_modulus * r.effective_shear_modulus
    )
    weak = CoreCompressionProperties(
        name="TEST-CORE", compression_strength=2.0e6, compression_modulus=e_c
    )
    a = assess_local_failure(r, basis.face.youngs_modulus, weak, local_basis)
    assert a.wrinkling_margin == pytest.approx(-0.5, rel=1e-9)
    assert a.wrinkling_pass is False
    assert a.local_failure_feasible is False


# -- Z. wrinkling load-limit hand calculation ------------------------------


def test_wrinkling_load_limit_hand_calc(
    basis, ortho_core, ortho_core_strength, core_compression, strength_basis, requirement, local_basis
):
    from sandwich_panel import assess_sandwich_design

    a = assess_sandwich_design(
        basis, ortho_core, ortho_core_strength, core_compression, "L",
        strength_basis, requirement, local_basis,
    )
    # P_wr = P_ref * sigma_wr / sigma_face(P_ref) = 50 * sigma_wr / 4.6850974e6
    assert a.capacity.wrinkling_limit == pytest.approx(
        50.0 * SIGMA_WR_L / SIGMA_FACE_50N, rel=1e-6
    )
    assert a.capacity.wrinkling_limit == pytest.approx(6430.7, rel=1e-4)


def test_wrinkling_limit_is_independent_of_the_reference_load(
    m2_geometry, m2_face, ortho_core, ortho_core_strength, core_compression,
    strength_basis, requirement, local_basis,
):
    from sandwich_panel import assess_sandwich_design

    limits = []
    for p in (10.0, 50.0, 900.0):
        b = StudyBasis(geometry=m2_geometry, face=m2_face, load=p)
        limits.append(
            assess_sandwich_design(
                b, ortho_core, ortho_core_strength, core_compression, "L",
                strength_basis, requirement, local_basis,
            ).capacity.wrinkling_limit
        )
    for value in limits[1:]:
        assert value == pytest.approx(limits[0], rel=1e-12)


# -- AA. returned limit gives zero margin ----------------------------------


def test_wrinkling_limit_gives_zero_margin_at_that_load(
    m2_geometry, m2_face, ortho_core, ortho_core_strength, core_compression,
    strength_basis, requirement, local_basis,
):
    from sandwich_panel import assess_sandwich_design

    base = StudyBasis(geometry=m2_geometry, face=m2_face, load=50.0)
    limit = assess_sandwich_design(
        base, ortho_core, ortho_core_strength, core_compression, "L",
        strength_basis, requirement, local_basis,
    ).capacity.wrinkling_limit

    at_limit = assess_sandwich_design(
        StudyBasis(geometry=m2_geometry, face=m2_face, load=limit),
        ortho_core, ortho_core_strength, core_compression, "L",
        strength_basis, requirement, local_basis,
    )
    assert at_limit.local.wrinkling_margin == pytest.approx(0.0, abs=1e-12)
    assert at_limit.local.wrinkling_pass is True

    above = assess_sandwich_design(
        StudyBasis(geometry=m2_geometry, face=m2_face, load=1.001 * limit),
        ortho_core, ortho_core_strength, core_compression, "L",
        strength_basis, requirement, local_basis,
    )
    assert above.local.wrinkling_pass is False


# -- wrinkling vs face yield -----------------------------------------------


def test_wrinkling_can_be_more_restrictive_than_face_yield(
    basis, strength_basis, requirement, local_basis
):
    """The Milestone 4 sandwich-specific insight, verified against the real database.

    For the low-compression-modulus aramid-equivalent core in the soft W shear
    direction, the wrinkling load limit falls BELOW the face-yield limit.
    """
    table = build_sandwich_table(basis, strength_basis, requirement, local_basis)
    below = [a.label for a in table if a.capacity.wrinkling_limit < a.capacity.face_limit]
    assert below == ["HC-AR-48 [W]"]
    aramid_w = next(a for a in table if a.label == "HC-AR-48 [W]")
    assert aramid_w.capacity.wrinkling_limit < aramid_w.capacity.face_limit
    # ...and it is driven by the low compression modulus, not by shear alone.
    assert get_core_compression("HC-AR-48").compression_modulus < get_core_compression(
        "HC-AL-45"
    ).compression_modulus
    assert get_core("HC-AR-48").shear_modulus_W > get_core("HC-AL-45").shear_modulus_W


def test_wrinkling_never_governs_the_global_limit_at_this_geometry(
    basis, strength_basis, requirement, local_basis
):
    # Reported as found: deflection still governs everywhere.
    table = build_sandwich_table(basis, strength_basis, requirement, local_basis)
    for a in table:
        assert a.capacity.wrinkling_limit > a.capacity.deflection_limit


def test_face_material_modulus_feeds_the_wrinkling_screen(
    m2_geometry, ortho_core, core_compression, local_basis
):
    stiff = StudyBasis(
        geometry=m2_geometry,
        face=FaceMaterial(name="stiff", youngs_modulus=8 * 70.0e9, density=2700.0),
        load=50.0,
    )
    soft = StudyBasis(
        geometry=m2_geometry,
        face=FaceMaterial(name="soft", youngs_modulus=70.0e9, density=2700.0),
        load=50.0,
    )
    a = assess_local_failure(
        evaluate_candidate(stiff, ortho_core, "L"),
        stiff.face.youngs_modulus, core_compression, local_basis,
    )
    b = assess_local_failure(
        evaluate_candidate(soft, ortho_core, "L"),
        soft.face.youngs_modulus, core_compression, local_basis,
    )
    assert a.wrinkling_screening_stress == pytest.approx(
        2.0 * b.wrinkling_screening_stress, rel=1e-12
    )
