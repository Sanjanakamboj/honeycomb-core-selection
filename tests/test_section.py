"""C, D, E, F, G, H, I, J, K - section properties and flexural rigidity."""

from __future__ import annotations

import pytest

from sandwich_panel import FaceMaterial, SandwichGeometry, SandwichPanel, section_properties

from .conftest import B, E_F, L, T_C, T_F

# Independent hand arithmetic for the reference case.
Z_F = 0.015 / 2 + 0.0005 / 2  # 0.00775 m
A_F = 0.40 * 0.0005  # 2.0e-4 m^2
I_LOCAL = 0.40 * 0.0005**3 / 12  # 4.1666666...e-12 m^4
I_PARALLEL = A_F * Z_F**2  # 1.20125e-8 m^4
I_FACE = I_LOCAL + I_PARALLEL  # 1.2016666...e-8 m^4
I_TOTAL = 2 * I_FACE  # 2.4033333...e-8 m^4
EI = 70.0e9 * I_TOTAL  # 1682.3333... N m^2


def test_neutral_axis_is_exactly_at_midplane_for_symmetric_layup(panel):
    # C. Computed, not assumed: modulus-weighted first moment must vanish.
    assert panel.section().neutral_axis_z == pytest.approx(0.0, abs=1e-18)


def test_neutral_axis_stays_at_midplane_when_a_core_modulus_is_supplied(geometry, face, core):
    # A symmetric layup is symmetric regardless of the core modulus.
    p = SandwichPanel(geometry=geometry, face=face, core=core, core_modulus=1.0e8)
    assert p.section().neutral_axis_z == pytest.approx(0.0, abs=1e-18)


def test_outer_fibre_distance_is_half_total_thickness(panel):
    assert panel.section().outer_fibre_distance == pytest.approx(0.008, abs=1e-15)


def test_face_centroid_offset(panel):
    # D.
    assert panel.section().face_centroid_offset == pytest.approx(0.00775, abs=1e-15)


def test_face_local_second_moment_hand_calc(panel):
    # E. b t_f^3 / 12 = 0.4 * 1.25e-10 / 12
    assert panel.section().face_local_second_moment == pytest.approx(4.1666666666667e-12, rel=1e-12)


def test_face_parallel_axis_term_hand_calc(panel):
    # F. (b t_f) z_f^2 = 2.0e-4 * 0.00775^2 = 1.20125e-8
    assert panel.section().face_parallel_axis_term == pytest.approx(1.20125e-8, rel=1e-12)


def test_single_face_second_moment_hand_calc(panel):
    assert panel.section().face_second_moment == pytest.approx(I_FACE, rel=1e-12)


def test_total_face_second_moment_hand_calc(panel):
    # G.
    assert panel.section().faces_second_moment == pytest.approx(I_TOTAL, rel=1e-12)
    assert panel.section().faces_second_moment == pytest.approx(2.40333333333e-8, rel=1e-10)


def test_exact_second_moment_exceeds_thin_face_approximation(panel):
    # H. The approximation drops the positive local terms, so it under-predicts.
    sec = panel.section()
    assert sec.faces_second_moment > sec.faces_second_moment_thin_face
    assert sec.faces_second_moment_thin_face == pytest.approx(2 * 1.20125e-8, rel=1e-12)


def test_thin_face_approximation_error_equals_local_term_share(panel):
    # H. The whole discrepancy is exactly the two dropped b t_f^3 / 12 terms.
    sec = panel.section()
    expected = -(2 * I_LOCAL) / I_TOTAL
    assert sec.faces_thin_face_relative_error == pytest.approx(expected, rel=1e-12)
    assert abs(sec.faces_thin_face_relative_error) < 1e-3  # thin faces: well under 0.1 %


def test_thin_face_error_grows_as_faces_get_thicker(panel):
    thin = panel.with_geometry(face_thickness=0.0002).section()
    thick = panel.with_geometry(face_thickness=0.0020).section()
    assert abs(thick.faces_thin_face_relative_error) > abs(thin.faces_thin_face_relative_error)


def test_flexural_rigidity_hand_calc(panel):
    assert panel.section().flexural_rigidity == pytest.approx(EI, rel=1e-12)
    assert panel.section().flexural_rigidity == pytest.approx(1682.33333333, rel=1e-9)


def test_flexural_rigidity_per_width(panel):
    sec = panel.section()
    assert sec.flexural_rigidity_per_width == pytest.approx(EI / 0.40, rel=1e-12)


def test_ei_scales_linearly_with_face_modulus(geometry, core):
    # I.
    base = SandwichPanel(
        geometry=geometry,
        face=FaceMaterial(name="a", youngs_modulus=E_F, density=2700.0),
        core=core,
    )
    doubled = SandwichPanel(
        geometry=geometry,
        face=FaceMaterial(name="b", youngs_modulus=2 * E_F, density=2700.0),
        core=core,
    )
    assert doubled.flexural_rigidity == pytest.approx(2.0 * base.flexural_rigidity, rel=1e-12)


def test_ei_scales_linearly_with_width(panel):
    # J.
    wide = panel.with_geometry(width=3 * B)
    assert wide.flexural_rigidity == pytest.approx(3.0 * panel.flexural_rigidity, rel=1e-12)


def test_ei_grows_monotonically_with_core_thickness(panel):
    # K.
    values = [
        panel.with_geometry(core_thickness=t).flexural_rigidity
        for t in (0.005, 0.010, 0.015, 0.020, 0.025)
    ]
    assert all(b > a for a, b in zip(values, values[1:]))


def test_ei_growth_approaches_but_is_not_exactly_a_square_law(panel):
    # K. Doubling the core depth multiplies EI by slightly less than 4 because
    # z_f = t_c/2 + t_f/2 with a finite face thickness (and by more than 1).
    ei_10 = panel.with_geometry(core_thickness=0.010).flexural_rigidity
    ei_20 = panel.with_geometry(core_thickness=0.020).flexural_rigidity
    ratio = ei_20 / ei_10
    assert 3.5 < ratio < 4.0


def test_section_properties_function_matches_panel(geometry, face, panel):
    direct = section_properties(geometry, face)
    assert direct.flexural_rigidity == panel.section().flexural_rigidity


def test_core_modulus_adds_bending_stiffness_only_when_supplied(geometry, face, core):
    without = SandwichPanel(geometry=geometry, face=face, core=core).section()
    with_core = SandwichPanel(
        geometry=geometry, face=face, core=core, core_modulus=1.0e8
    ).section()
    assert without.core_modulus is None
    assert with_core.flexural_rigidity > without.flexural_rigidity
    # Stress is still reported on the faces-only second moment in Milestone 1.
    assert with_core.second_moment_for_stress == pytest.approx(without.faces_second_moment)


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_invalid_core_modulus_rejected(geometry, face, core, bad):
    with pytest.raises(ValueError):
        SandwichPanel(geometry=geometry, face=face, core=core, core_modulus=bad)


def test_ei_is_independent_of_span(panel):
    assert panel.with_geometry(span=2 * L).flexural_rigidity == pytest.approx(
        panel.flexural_rigidity, rel=1e-15
    )


def test_unknown_geometry_field_rejected(panel):
    with pytest.raises(ValueError):
        panel.with_geometry(thickness=0.01)


def test_geometry_type_is_checked(face, core):
    with pytest.raises(TypeError):
        SandwichPanel(geometry="not a geometry", face=face, core=core)  # type: ignore[arg-type]


def test_material_types_are_checked(geometry, face, core):
    with pytest.raises(TypeError):
        SandwichPanel(geometry=geometry, face=core, core=core)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        SandwichPanel(geometry=geometry, face=face, core=face)  # type: ignore[arg-type]


def test_section_of_a_thin_face_panel_is_close_to_the_classic_approximation():
    # Sanity: for very thin faces the exact and approximate forms converge.
    g = SandwichGeometry(width=1.0, face_thickness=1.0e-5, core_thickness=0.02, span=1.0)
    f = FaceMaterial(name="thin", youngs_modulus=70.0e9, density=2700.0)
    sec = section_properties(g, f)
    assert abs(sec.faces_thin_face_relative_error) < 1e-6


def test_second_moment_for_stress_is_the_faces_only_value(panel):
    sec = panel.section()
    assert sec.second_moment_for_stress == sec.faces_second_moment


def test_core_second_moment_reported_but_bending_inactive_by_default(panel):
    sec = panel.section()
    # b t_c^3 / 12 = 0.4 * 0.015^3 / 12
    assert sec.core_second_moment == pytest.approx(0.4 * 0.015**3 / 12, rel=1e-12)
    assert sec.flexural_rigidity == pytest.approx(70.0e9 * sec.faces_second_moment, rel=1e-15)


def test_face_thickness_zero_area_face_rejected_upstream():
    with pytest.raises(ValueError):
        SandwichGeometry(width=T_C, face_thickness=0.0, core_thickness=T_C, span=T_F)
