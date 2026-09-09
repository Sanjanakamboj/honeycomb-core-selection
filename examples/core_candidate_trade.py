"""Milestone 2: candidate honeycomb-core mass / shear-stiffness trade.

ALL CANDIDATE CORE PROPERTIES ARE ILLUSTRATIVE HONEYCOMB-EQUIVALENT VALUES.
They are representative engineering-study inputs, not manufacturer datasheet
values, not design allowables and not qualification data. See
``src/sandwich_panel/core_database.py``.

The deflection limit applied below is an ILLUSTRATIVE preliminary stiffness
screen, not a qualification limit. The transverse point load is a stiffness
demonstration load, not a launch or qualification load case.

No core is selected here. Milestone 2 establishes the trade framework; strength,
stability, thermal and manufacturing screening - and therefore any actual
selection - are deferred.

Run with:

    python examples/core_candidate_trade.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):  # allow running without installing the package
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sandwich_panel import (  # noqa: E402
    CANDIDATE_CORES,
    CoreShearDirection,
    DeflectionRequirement,
    FaceMaterial,
    SandwichGeometry,
    StudyBasis,
    build_trade_table,
    core_density_sweep,
    core_depth_directional_sweep,
    core_shear_modulus_sweep_at_fixed_density,
    evaluate_candidates,
    get_core,
    pareto_front,
)

MM = 1.0e-3
MPA = 1.0e6
GPA = 1.0e9

# --- common study basis: the Milestone 1 representative panel, unchanged ----

GEOMETRY = SandwichGeometry(
    width=0.500,  # b   [m]
    face_thickness=0.4 * MM,  # t_f [m]
    core_thickness=20.0 * MM,  # t_c [m]
    span=1.500,  # L   [m]
)

FACE = FaceMaterial(
    name="Illustrative aluminium-like face sheet (not a datasheet value)",
    youngs_modulus=70.0 * GPA,
    density=2700.0,
)

LOAD = 50.0  # P [N], stiffness demonstration only

BASIS = StudyBasis(geometry=GEOMETRY, face=FACE, load=LOAD)

# Illustrative preliminary stiffness screen. Chosen by CONVENTION as span/1000,
# a common precision-structure deflection guideline - deliberately not a number
# reverse-engineered from the candidate results to manufacture a winner.
DEFLECTION_LIMIT = GEOMETRY.span / 1000.0  # 1.5 mm
REQUIREMENT = DeflectionRequirement(
    maximum_total_deflection=DEFLECTION_LIMIT,
    label="illustrative panel deflection limit = span/1000 (preliminary stiffness screen only)",
)


def _rule(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def _direction_table(rows) -> None:
    print(
        f"  {'candidate':<10}{'rho':>6}{'G_eff':>8}{'m_A':>8}{'delta':>9}"
        f"{'shear':>8}{'margin':>9}  {'screen':<6}"
    )
    print(
        f"  {'':<10}{'kg/m3':>6}{'MPa':>8}{'kg/m2':>8}{'mm':>9}{'frac %':>8}{'mm':>9}"
    )
    for row in rows:
        r = row.result
        a = row.assessment
        print(
            f"  {r.core_name:<10}{r.core_density:>6.0f}"
            f"{r.effective_shear_modulus / MPA:>8.1f}{r.areal_mass:>8.3f}"
            f"{r.total_deflection * 1e3:>9.4f}{r.shear_fraction * 100:>8.2f}"
            f"{a.margin * 1e3:>9.4f}  {'PASS' if a.feasible else 'FAIL':<6}"
        )


def main() -> None:
    print("=" * 78)
    print("CANDIDATE HONEYCOMB-CORE TRADE - Milestone 2")
    print("Milestone 2 compares candidate-core mass and shear-stiffness behaviour")
    print("under a common sandwich geometry. Strength-based core selection is")
    print("intentionally deferred. NO CORE IS SELECTED HERE.")
    print("=" * 78)

    _rule("STUDY BASIS (identical for every candidate)")
    print(f"  span                L   = {GEOMETRY.span:.4f} m")
    print(f"  width               b   = {GEOMETRY.width:.4f} m")
    print(f"  face thickness      t_f = {GEOMETRY.face_thickness * 1e3:.4f} mm")
    print(f"  core thickness      t_c = {GEOMETRY.core_thickness * 1e3:.4f} mm")
    print(f"  total thickness     h   = {GEOMETRY.total_thickness * 1e3:.4f} mm")
    print(f"  face material           : {FACE.name}")
    print(f"    E_f   = {FACE.youngs_modulus / GPA:.1f} GPa   rho_f = {FACE.density:.0f} kg/m^3")
    print(f"  face areal mass (2 rho_f t_f)  = {2 * FACE.density * GEOMETRY.face_thickness:.4f} kg/m^2")
    print(f"  transverse central point load P = {LOAD:.2f} N  (stiffness demonstration only)")
    print(f"  {REQUIREMENT.label}")
    print(f"    delta_allowable = {DEFLECTION_LIMIT * 1e3:.4f} mm")
    print("    convention: PASS when delta_total <= delta_allowable;")
    print("                margin = delta_allowable - delta_total")

    _rule("CANDIDATE DATABASE (ILLUSTRATIVE HONEYCOMB-EQUIVALENT VALUES)")
    print("  Not manufacturer data. Not allowables. Not qualification data.")
    print()
    print(f"  {'candidate':<10}{'rho':>7}{'G_L':>8}{'G_W':>8}{'G_L/G_W':>9}  family")
    print(f"  {'':<10}{'kg/m3':>7}{'MPa':>8}{'MPa':>8}{'-':>9}")
    for core in CANDIDATE_CORES:
        print(
            f"  {core.name:<10}{core.density:>7.0f}{core.shear_modulus_L / MPA:>8.1f}"
            f"{core.shear_modulus_W / MPA:>8.1f}{core.directional_shear_ratio:>9.2f}"
            f"  {core.family}"
        )

    table = build_trade_table(BASIS, CANDIDATE_CORES, requirement=REQUIREMENT)
    l_rows = [row for row in table if row.result.direction is CoreShearDirection.L]
    w_rows = [row for row in table if row.result.direction is CoreShearDirection.W]

    ei = l_rows[0].result.flexural_rigidity
    delta_b = l_rows[0].result.bending_deflection
    print()
    print(f"  EI is identical for every candidate : {ei:.4e} N m^2")
    print(f"  bending deflection likewise         : {delta_b * 1e3:.4f} mm")
    print("  (faces carry the bending stiffness; the core carries only shear)")

    _rule("L-DIRECTION RESULTS (ribbon / longitudinal - stiffer)")
    _direction_table(l_rows)

    _rule("W-DIRECTION RESULTS (transverse / expansion - softer)")
    _direction_table(w_rows)

    _rule("DIRECTIONAL PENALTY")
    print("  identity check: delta_s,W / delta_s,L == G_L / G_W (same geometry and load)")
    print(f"  {'candidate':<10}{'G_L/G_W':>10}{'ds_W/ds_L':>12}"
          f"{'ds_L [mm]':>12}{'ds_W [mm]':>12}{'d_tot W-L':>12}")
    for core in CANDIDATE_CORES:
        rl = next(r.result for r in l_rows if r.result.core_name == core.name)
        rw = next(r.result for r in w_rows if r.result.core_name == core.name)
        print(
            f"  {core.name:<10}{core.directional_shear_ratio:>10.4f}"
            f"{rw.shear_deflection / rl.shear_deflection:>12.4f}"
            f"{rl.shear_deflection * 1e3:>12.4f}{rw.shear_deflection * 1e3:>12.4f}"
            f"{(rw.total_deflection - rl.total_deflection) * 1e3:>12.4f}"
        )
    print("  -> orienting the panel across the ribbon direction costs real stiffness;")
    print("     the L/W choice must be a deliberate design decision, never a default.")

    _rule("SHEAR-STIFFNESS-TO-DENSITY INDICATOR (first-order only)")
    print("  G_eff / rho_c [m^2/s^2] - a coarse screening indicator, NOT an")
    print("  optimisation index and NOT a ranking on its own.")
    print(f"  {'candidate':<10}{'L [m2/s2]':>14}{'W [m2/s2]':>14}")
    for core in CANDIDATE_CORES:
        print(
            f"  {core.name:<10}{core.specific_shear_stiffness('L'):>14.4e}"
            f"{core.specific_shear_stiffness('W'):>14.4e}"
        )

    _rule("MASS-STIFFNESS INTERPRETATION")
    all_results = evaluate_candidates(BASIS, CANDIDATE_CORES)
    lightest = min(CANDIDATE_CORES, key=lambda c: c.density)
    stiffest = max(CANDIDATE_CORES, key=lambda c: c.shear_modulus_L)
    best_index = max(CANDIDATE_CORES, key=lambda c: c.specific_shear_stiffness("L"))
    lowest_l = min((r.result for r in l_rows), key=lambda r: r.total_deflection)
    lowest_w = min((r.result for r in w_rows), key=lambda r: r.total_deflection)
    print(f"  lightest core                       : {lightest.name} "
          f"({lightest.density:.0f} kg/m^3)")
    print(f"  stiffest core in shear (G_L)        : {stiffest.name} "
          f"({stiffest.shear_modulus_L / MPA:.0f} MPa)")
    print(f"  lowest total deflection, L          : {lowest_l.core_name} "
          f"({lowest_l.total_deflection * 1e3:.4f} mm)")
    print(f"  lowest total deflection, W          : {lowest_w.core_name} "
          f"({lowest_w.total_deflection * 1e3:.4f} mm)")
    print(f"  best G_L/rho_c indicator            : {best_index.name} "
          f"({best_index.specific_shear_stiffness('L'):.4e} m^2/s^2)")

    n_pass = sum(1 for row in table if row.assessment.feasible)
    print()
    print(f"  stiffness screen: {n_pass}/{len(table)} candidate-direction combinations "
          f"meet the {DEFLECTION_LIMIT * 1e3:.2f} mm limit.")
    if n_pass == len(table):
        print("  At this core depth the screen does NOT discriminate: the response is")
        print("  bending-dominated, so every candidate passes. That is reported as found;")
        print("  the data was not tuned to manufacture a mixed outcome. See the core-depth")
        print("  sweep below for where this limit actually bites.")
    elif n_pass == 0:
        print("  No candidate meets the limit at this geometry.")
    else:
        print("  The screen separates candidates at this geometry.")

    front = pareto_front(all_results)
    print()
    print("  Non-dominated on (areal mass, total deflection) - screening aid only,")
    print("  not optimisation and not a selection:")
    for r in front:
        print(f"    {r.label:<16} m_A = {r.areal_mass:6.3f} kg/m^2   "
              f"delta = {r.total_deflection * 1e3:.4f} mm")
    dominated = [r for r in all_results if r not in front]
    for r in dominated:
        print(f"    (dominated: {r.label:<16} m_A = {r.areal_mass:6.3f} kg/m^2   "
              f"delta = {r.total_deflection * 1e3:.4f} mm)")

    _rule("SENSITIVITY - core density at fixed G (G = 40 MPa, L)")
    print(f"  {'rho [kg/m3]':>12}{'m_A [kg/m2]':>13}{'EI [N m^2]':>13}"
          f"{'delta_b [mm]':>14}{'delta [mm]':>12}")
    for r in core_density_sweep(BASIS, [25.0, 40.0, 60.0, 80.0, 100.0], 40.0 * MPA):
        print(f"  {r.core_density:>12.0f}{r.areal_mass:>13.4f}{r.flexural_rigidity:>13.4e}"
              f"{r.bending_deflection * 1e3:>14.4f}{r.total_deflection * 1e3:>12.4f}")
    print("  -> density moves mass only. Stiffness inputs are cleanly separated.")

    _rule("SENSITIVITY - core shear modulus at fixed density (rho = 45 kg/m3, L)")
    print(f"  {'G [MPa]':>9}{'m_A [kg/m2]':>13}{'delta_b [mm]':>14}"
          f"{'delta_s [mm]':>14}{'delta [mm]':>12}{'shear %':>10}")
    for r in core_shear_modulus_sweep_at_fixed_density(
        BASIS, [10.0 * MPA, 20.0 * MPA, 40.0 * MPA, 80.0 * MPA, 160.0 * MPA], 45.0
    ):
        print(f"  {r.effective_shear_modulus / MPA:>9.0f}{r.areal_mass:>13.4f}"
              f"{r.bending_deflection * 1e3:>14.4f}{r.shear_deflection * 1e3:>14.4f}"
              f"{r.total_deflection * 1e3:>12.4f}{r.shear_fraction * 100:>10.2f}")
    print("  -> mass and EI unmoved; delta_s scales as 1/G and the total approaches")
    print("     the bending-only floor as G grows.")

    _rule("CORE-DEPTH TRADE (HC-AL-45, both directions)")
    print(f"  {'t_c [mm]':>9}{'EI [N m^2]':>13}{'m_A [kg/m2]':>13}{'d_b [mm]':>11}"
          f"{'ds_L [mm]':>11}{'ds_W [mm]':>11}{'tot_L [mm]':>12}{'tot_W [mm]':>12}")
    for row in core_depth_directional_sweep(
        BASIS, get_core("HC-AL-45"), [5 * MM, 10 * MM, 15 * MM, 20 * MM, 25 * MM]
    ):
        print(
            f"  {row.core_thickness * 1e3:>9.1f}{row.flexural_rigidity:>13.4e}"
            f"{row.areal_mass:>13.4f}{row.bending_deflection * 1e3:>11.4f}"
            f"{row.shear_deflection_L * 1e3:>11.4f}{row.shear_deflection_W * 1e3:>11.4f}"
            f"{row.total_deflection_L * 1e3:>12.4f}{row.total_deflection_W * 1e3:>12.4f}"
        )
    print("  -> core depth acts on THREE things at once: it raises EI steeply through")
    print("     face separation, adds core mass linearly, AND increases the core shear")
    print("     area A_s = b t_c, so the shear deflection falls too. Core depth is not")
    print("     optimised here.")

    print()
    print("=" * 78)
    print("Candidates retained for later strength/failure screening.")
    print("No core is selected. No strength, stability, thermal or manufacturing")
    print("criterion has been applied. Face stress and core shear stress are reported")
    print("elsewhere as demand diagnostics only - no allowables exist in this model.")
    print("=" * 78)


if __name__ == "__main__":
    main()
