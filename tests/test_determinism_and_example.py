"""AB. Determinism, plus an end-to-end smoke test of the sanity example."""

from __future__ import annotations

import runpy
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from sandwich_panel import SandwichPanel

from .conftest import P

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sandwich_panel_sanity.py"


def test_section_properties_are_deterministic(panel):
    first = asdict(panel.section())
    for _ in range(5):
        assert asdict(panel.section()) == first


def test_mass_properties_are_deterministic(panel):
    first = asdict(panel.mass())
    for _ in range(5):
        assert asdict(panel.mass()) == first


def test_load_response_is_deterministic(panel):
    first = asdict(panel.central_point_load(P))
    for _ in range(5):
        assert asdict(panel.central_point_load(P)) == first


def test_identical_panels_give_identical_results(geometry, face, core):
    a = SandwichPanel(geometry=geometry, face=face, core=core)
    b = SandwichPanel(geometry=geometry, face=face, core=core)
    assert a == b
    assert asdict(a.central_point_load(P)) == asdict(b.central_point_load(P))


def test_sanity_example_runs(capsys):
    saved = sys.argv[:]
    sys.argv = [str(EXAMPLE)]
    try:
        runpy.run_path(str(EXAMPLE), run_name="__main__")
    finally:
        sys.argv = saved
    out = capsys.readouterr().out
    for heading in ("GEOMETRY", "MATERIALS", "SECTION", "MASS", "LOAD RESPONSE", "SENSITIVITY"):
        assert heading in out
    assert "illustrative" in out.lower()
    assert "final core selection" in out.lower()


def test_example_case_reproduces_expected_headline_numbers():
    """Independent hand check of the example case published in the README.

    b = 0.5 m, t_f = 0.4 mm, t_c = 20 mm, L = 1.5 m,
    E_f = 70 GPa, rho_f = 2700, G_c = 40 MPa, rho_c = 32, P = 50 N.

        z_f      = 0.010 + 0.0002 = 0.0102 m
        I_total  = 2 * (0.5*0.0004^3/12 + 0.5*0.0004*0.0102^2) = 4.1621333e-8 m^4
        EI       = 70e9 * 4.1621333e-8                          = 2913.4933 N m^2
        m_A      = 2*2700*0.0004 + 32*0.020                     = 2.80 kg/m^2
        delta_b  = 50*1.5^3/(48*2913.4933)                      = 1.2066700e-3 m
        delta_s  = 50*1.5/(4*40e6*0.5*0.020)                     = 4.6875e-5 m
        sigma_f  = (50*1.5/4)*0.0104/4.1621333e-8               = 4.6850974e6 Pa
        tau_c    = 25/0.010                                      = 2500 Pa
    """
    from sandwich_panel import CoreMaterial, FaceMaterial, SandwichGeometry

    panel = SandwichPanel(
        geometry=SandwichGeometry(
            width=0.5, face_thickness=0.0004, core_thickness=0.020, span=1.5
        ),
        face=FaceMaterial(name="illustrative", youngs_modulus=70.0e9, density=2700.0),
        core=CoreMaterial(name="illustrative", density=32.0, shear_modulus=40.0e6),
    )
    sec = panel.section()
    res = panel.central_point_load(50.0)

    assert sec.faces_second_moment == pytest.approx(4.1621333333e-8, rel=1e-9)
    assert sec.flexural_rigidity == pytest.approx(2913.49333333, rel=1e-9)
    assert panel.areal_mass == pytest.approx(2.80, rel=1e-12)
    assert panel.mass().total_mass == pytest.approx(2.80 * 0.5 * 1.5, rel=1e-12)
    assert res.max_bending_moment == pytest.approx(18.75, rel=1e-12)
    assert res.max_shear_force == pytest.approx(25.0, rel=1e-12)
    assert res.bending_deflection == pytest.approx(1.2066700e-3, rel=1e-6)
    assert res.shear_deflection == pytest.approx(4.6875e-5, rel=1e-12)
    assert res.total_deflection == pytest.approx(1.2535450e-3, rel=1e-6)
    assert res.max_face_stress == pytest.approx(4.6850974e6, rel=1e-6)
    assert res.avg_core_shear_stress == pytest.approx(2500.0, rel=1e-12)
    assert res.shear_deflection_fraction == pytest.approx(0.0373940, rel=1e-4)
