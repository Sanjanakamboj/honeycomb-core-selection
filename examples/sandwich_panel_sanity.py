"""Representative solar-panel-substrate sanity case (Milestone 1).

ALL MATERIAL AND GEOMETRY VALUES BELOW ARE ILLUSTRATIVE PLACEHOLDERS.
They are chosen to be plausible for a spacecraft solar-panel substrate; they are
not sourced from a datasheet and are not a design baseline.

The transverse central point load is a STIFFNESS DEMONSTRATION load only. It is
not a launch, qualification, deployment or handling load case.

Run with:

    python examples/sandwich_panel_sanity.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):  # allow running without installing the package
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sandwich_panel import (  # noqa: E402
    CoreMaterial,
    FaceMaterial,
    SandwichGeometry,
    SandwichPanel,
    core_depth_sweep,
    core_shear_modulus_sweep,
    face_thickness_sweep,
)

MM = 1.0e-3
MPA = 1.0e6
GPA = 1.0e9

# --- illustrative inputs -------------------------------------------------

GEOMETRY = SandwichGeometry(
    width=0.500,  # b   [m]
    face_thickness=0.4 * MM,  # t_f [m]
    core_thickness=20.0 * MM,  # t_c [m]
    span=1.500,  # L   [m]
)

FACE = FaceMaterial(
    name="Illustrative aluminium-like face sheet (not a datasheet value)",
    youngs_modulus=70.0 * GPA,  # E_f   [Pa]
    density=2700.0,  # rho_f [kg/m^3]
)

CORE = CoreMaterial(
    name="Illustrative low-density honeycomb-equivalent core (not a datasheet value)",
    density=32.0,  # rho_c [kg/m^3]
    shear_modulus=40.0 * MPA,  # G_c   [Pa], effective transverse shear
)

LOAD = 50.0  # P [N], stiffness demonstration only


def _rule(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> None:
    panel = SandwichPanel(geometry=GEOMETRY, face=FACE, core=CORE)
    geom = panel.geometry
    sec = panel.section()
    mass = panel.mass()
    res = panel.central_point_load(LOAD)

    print("=" * 72)
    print("SANDWICH PANEL SANITY CASE - illustrative solar-panel substrate")
    print("Milestone 1: verified mechanics only. No core selection is implied.")
    print("=" * 72)

    _rule("GEOMETRY")
    print(f"  span                L   = {geom.span:.4f} m")
    print(f"  width               b   = {geom.width:.4f} m")
    print(f"  face thickness      t_f = {geom.face_thickness * 1e3:.4f} mm")
    print(f"  core thickness      t_c = {geom.core_thickness * 1e3:.4f} mm")
    print(f"  total thickness     h   = {geom.total_thickness * 1e3:.4f} mm")

    _rule("MATERIALS (illustrative)")
    print(f"  face    : {FACE.name}")
    print(f"    E_f   = {FACE.youngs_modulus / GPA:.3f} GPa")
    print(f"    rho_f = {FACE.density:.1f} kg/m^3")
    print(f"  core    : {CORE.name}")
    print(f"    G_c   = {CORE.shear_modulus / MPA:.3f} MPa (effective transverse shear)")
    print(f"    rho_c = {CORE.density:.1f} kg/m^3")
    print("  core normal-stress bending stiffness: NEGLECTED (shear layer only)")

    _rule("SECTION")
    print(f"  computed neutral axis        z_na  = {sec.neutral_axis_z:.6e} m (mid-plane = 0)")
    print(f"  face centroid offset         z_f   = {sec.face_centroid_offset * 1e3:.4f} mm")
    print(f"  face local I (b t_f^3 / 12)        = {sec.face_local_second_moment:.6e} m^4")
    print(f"  face parallel-axis term            = {sec.face_parallel_axis_term:.6e} m^4")
    print(f"  I_faces exact                      = {sec.faces_second_moment:.6e} m^4")
    print(f"  I_faces thin-face approximation    = {sec.faces_second_moment_thin_face:.6e} m^4")
    print(
        f"  relative approximation error       = {sec.faces_thin_face_relative_error:.3e} "
        f"({sec.faces_thin_face_relative_error * 100:.4f} %)"
    )
    print(f"  flexural rigidity            EI    = {sec.flexural_rigidity:.6e} N m^2")
    print(f"  per unit width               EI/b  = {sec.flexural_rigidity_per_width:.6e} N m")

    _rule("MASS")
    print(f"  face areal mass  (2 rho_f t_f)     = {mass.face_areal_mass:.4f} kg/m^2")
    print(f"  core areal mass  (rho_c t_c)       = {mass.core_areal_mass:.4f} kg/m^2")
    print(f"  total areal mass m_A               = {mass.total_areal_mass:.4f} kg/m^2")
    print(f"  face mass fraction                 = {mass.face_mass_fraction * 100:.2f} %")
    print(f"  plan area (b L)                    = {mass.plan_area:.4f} m^2")
    print(f"  total strip mass                   = {mass.total_mass:.4f} kg")
    print("  (bare faces + core only: no adhesive, inserts, edge close-outs or doublers)")

    _rule("LOAD RESPONSE - simply supported strip, central point load")
    print("  stiffness demonstration load; NOT a qualification load case")
    print(f"  load                     P         = {res.load:.4f} N")
    print(f"  shear correction factor  kappa     = {res.shear_correction_factor:.4f}")
    print(f"  max bending moment       M_max     = {res.max_bending_moment:.6f} N m")
    print(f"  max shear force          V_max     = {res.max_shear_force:.6f} N")
    print(f"  max face stress (outer surface)    = {res.max_face_stress / MPA:.4f} MPa")
    print(f"  avg core shear stress              = {res.avg_core_shear_stress / 1e3:.4f} kPa")
    print(f"  bending deflection       delta_b   = {res.bending_deflection * 1e3:.4f} mm")
    print(f"  shear deflection         delta_s   = {res.shear_deflection * 1e3:.4f} mm")
    print(f"  total deflection         delta     = {res.total_deflection * 1e3:.4f} mm")
    print(f"  shear fraction     delta_s / delta = {res.shear_deflection_fraction:.4f}")

    _rule("SENSITIVITY - core depth (b, t_f, E_f, L fixed)")
    print(f"  {'t_c [mm]':>9} {'h [mm]':>9} {'EI [N m^2]':>13} {'EI/EI_0':>9} "
          f"{'m_A [kg/m2]':>12} {'m_A/m_A0':>9} {'delta [mm]':>11}")
    for row in core_depth_sweep(panel, [5 * MM, 10 * MM, 15 * MM, 20 * MM, 25 * MM], LOAD):
        print(
            f"  {row.core_thickness * 1e3:9.2f} {row.total_thickness * 1e3:9.2f} "
            f"{row.flexural_rigidity:13.4e} {row.flexural_rigidity_ratio:9.3f} "
            f"{row.areal_mass:12.4f} {row.areal_mass_ratio:9.3f} "
            f"{row.total_deflection * 1e3:11.4f}"
        )
    print("  -> large EI gain for a modest areal-mass increase: the core-depth leverage.")
    print("  -> growth is NOT an exact square law: t_f is finite, so z_f = t_c/2 + t_f/2.")

    _rule("SENSITIVITY - face thickness (t_c, b, L fixed)")
    print(f"  {'t_f [mm]':>9} {'EI [N m^2]':>13} {'m_A [kg/m2]':>12} "
          f"{'sigma_f [MPa]':>14} {'delta [mm]':>11}")
    for frow in face_thickness_sweep(
        panel, [0.2 * MM, 0.3 * MM, 0.4 * MM, 0.5 * MM, 0.6 * MM], LOAD
    ):
        print(
            f"  {frow.face_thickness * 1e3:9.2f} {frow.flexural_rigidity:13.4e} "
            f"{frow.areal_mass:12.4f} {frow.max_face_stress / MPA:14.4f} "
            f"{frow.total_deflection * 1e3:11.4f}"
        )
    print("  -> face thickness buys stiffness and stress margin, but pays directly in mass.")

    _rule("SENSITIVITY - effective core shear modulus (geometry fixed)")
    print(f"  {'G_c [MPa]':>10} {'delta_b [mm]':>13} {'delta_s [mm]':>13} "
          f"{'delta [mm]':>11} {'shear frac':>11}")
    for grow in core_shear_modulus_sweep(
        panel, [10 * MPA, 20 * MPA, 40 * MPA, 80 * MPA, 160 * MPA], LOAD
    ):
        print(
            f"  {grow.core_shear_modulus / MPA:10.1f} {grow.bending_deflection * 1e3:13.4f} "
            f"{grow.shear_deflection * 1e3:13.4f} {grow.total_deflection * 1e3:11.4f} "
            f"{grow.shear_deflection_fraction:11.4f}"
        )
    print("  -> delta_b is invariant with G_c; delta_s scales as 1/G_c.")
    print("  -> a bending-stiff sandwich can still be core-shear-sensitive.")

    print()
    print("=" * 72)
    print("Milestone 1 establishes the verified sandwich-panel mechanics only.")
    print("Candidate honeycomb materials and final core selection are deferred.")
    print("No failure criteria, buckling, thermal or vibration assessment is included.")
    print("=" * 72)


if __name__ == "__main__":
    main()
