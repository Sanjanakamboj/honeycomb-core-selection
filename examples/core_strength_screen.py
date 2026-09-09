"""Milestone 3: first-order face-yield and core-shear screening of the candidate cores.

ALL STRENGTH VALUES ARE ILLUSTRATIVE.
Face yield strength and core shear strengths are representative engineering-study
inputs: not manufacturer allowables, not design allowables, not qualification
data. See ``src/sandwich_panel/strength_database.py``.

The deflection limit is the Milestone 2 illustrative preliminary stiffness screen
(span/1000). The point load is a stiffness/strength demonstration load, not a
launch or qualification load case.

Only two strength checks exist here, because only two are supported by the
current beam-strip mechanics: face longitudinal normal stress, and AVERAGE
effective core shear stress. Crushing, wrinkling, crimping, indentation, inserts
and adhesive failure are deferred, not approximated.

No core is selected.

Run with:

    python examples/core_strength_screen.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):  # allow running without installing the package
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sandwich_panel import (  # noqa: E402
    CANDIDATE_CORES,
    CANDIDATE_CORE_STRENGTHS,
    ILLUSTRATIVE_FACE_STRENGTH,
    CoreShearDirection,
    DeflectionRequirement,
    FaceMaterial,
    SandwichGeometry,
    StrengthBasis,
    StudyBasis,
    build_design_table,
    core_depth_capacity_sweep,
    get_core,
    get_core_strength,
    load_sensitivity_sweep,
    pareto_front_by_capacity,
)

MM = 1.0e-3
KPA = 1.0e3
MPA = 1.0e6
GPA = 1.0e9

# --- common study basis: unchanged from Milestones 1-2 ---------------------

GEOMETRY = SandwichGeometry(
    width=0.500, face_thickness=0.4 * MM, core_thickness=20.0 * MM, span=1.500
)
FACE = FaceMaterial(
    name="Illustrative aluminium-like face sheet (not a datasheet value)",
    youngs_modulus=70.0 * GPA,
    density=2700.0,
)
LOAD = 50.0  # P [N]
BASIS = StudyBasis(geometry=GEOMETRY, face=FACE, load=LOAD)

# Design factor kept explicit and visible rather than folded into material data.
FACE_DESIGN_FACTOR = 1.0
STRENGTH = StrengthBasis(
    face_strength=ILLUSTRATIVE_FACE_STRENGTH, face_design_factor=FACE_DESIGN_FACTOR
)

DEFLECTION_LIMIT = GEOMETRY.span / 1000.0  # 1.5 mm, as established in Milestone 2
REQUIREMENT = DeflectionRequirement(
    maximum_total_deflection=DEFLECTION_LIMIT,
    label="illustrative panel deflection limit = span/1000 (preliminary stiffness screen only)",
)


def _rule(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> None:
    print("=" * 84)
    print("CANDIDATE CORE STRENGTH SCREEN - Milestone 3")
    print("Milestone 3 adds first-order face-yield and average core-shear screening only.")
    print("Crushing, wrinkling, local indentation, inserts and other sandwich-specific")
    print("failure modes remain intentionally deferred. NO CORE IS SELECTED HERE.")
    print("-" * 84)
    print("ALL STRENGTH VALUES BELOW ARE ILLUSTRATIVE STRENGTH INPUTS -")
    print("NOT MANUFACTURER ALLOWABLES, not design allowables, not qualification data.")
    print("=" * 84)

    _rule("STUDY BASIS")
    print(f"  span L = {GEOMETRY.span:.4f} m    width b = {GEOMETRY.width:.4f} m")
    print(f"  face thickness t_f = {GEOMETRY.face_thickness * 1e3:.4f} mm    "
          f"core thickness t_c = {GEOMETRY.core_thickness * 1e3:.4f} mm")
    print(f"  total thickness h = {GEOMETRY.total_thickness * 1e3:.4f} mm")
    print(f"  face: E_f = {FACE.youngs_modulus / GPA:.1f} GPa, rho_f = {FACE.density:.0f} kg/m^3")
    print(f"  face strength record : {ILLUSTRATIVE_FACE_STRENGTH.name}")
    print(f"    illustrative face-sheet yield strength = "
          f"{ILLUSTRATIVE_FACE_STRENGTH.yield_strength / MPA:.1f} MPa")
    print(f"    face design factor (explicit)          = {FACE_DESIGN_FACTOR:.2f}")
    print(f"    sigma_face_allowable = yield / factor  = "
          f"{STRENGTH.face_allowable_stress / MPA:.1f} MPa")
    print(f"  transverse central point load P = {LOAD:.2f} N")
    print(f"  {REQUIREMENT.label}")
    print(f"    delta_allowable = {DEFLECTION_LIMIT * 1e3:.4f} mm")
    print("  margin conventions:")
    print("    face   : MS = sigma_allowable / sigma_demand - 1   (dimensionless)")
    print("    core   : MS = tau_allowable   / tau_demand   - 1   (dimensionless)")
    print("    deflection margin is a LENGTH and is never combined numerically with these")

    table = build_design_table(BASIS, STRENGTH, REQUIREMENT)
    l_rows = [a for a in table if a.result.direction is CoreShearDirection.L]
    w_rows = [a for a in table if a.result.direction is CoreShearDirection.W]
    ref = l_rows[0]

    _rule("BASELINE DEMAND (identical for every candidate at P = 50 N)")
    print(f"  face stress       sigma_face,max = {ref.strength.face_stress / MPA:.4f} MPa")
    print(f"  core shear stress tau_core (avg) = {ref.strength.core_shear_stress / KPA:.4f} kPa")
    print(f"  bending deflection delta_b       = {ref.result.bending_deflection * 1e3:.4f} mm")
    print("  (face stress and core shear stress depend on geometry and load only,")
    print("   so they are the same for every candidate core)")

    _rule("50 N CANDIDATE SCREEN")
    print(f"  {'candidate':<14}{'m_A':>7}{'delta':>8}{'d-marg':>8}{'defl':>6}"
          f"{'MS_face':>9}{'face':>6}{'MS_core':>10}{'core':>6}{'STR':>6}{'OVERALL':>9}")
    print(f"  {'':<14}{'kg/m2':>7}{'mm':>8}{'mm':>8}{'':>6}{'[-]':>9}{'':>6}{'[-]':>10}")
    for a in table:
        print(
            f"  {a.label:<14}{a.result.areal_mass:>7.3f}"
            f"{a.result.total_deflection * 1e3:>8.4f}{a.deflection.margin * 1e3:>8.4f}"
            f"{'PASS' if a.deflection_feasible else 'FAIL':>6}"
            f"{a.strength.face_margin:>9.2f}{'PASS' if a.strength.face_pass else 'FAIL':>6}"
            f"{a.strength.core_shear_margin:>10.2f}"
            f"{'PASS' if a.strength.core_shear_pass else 'FAIL':>6}"
            f"{'PASS' if a.strength_feasible else 'FAIL':>6}"
            f"{'PASS' if a.overall_feasible else 'FAIL':>9}"
        )
    n_defl = sum(1 for a in table if a.deflection_feasible)
    n_str = sum(1 for a in table if a.strength_feasible)
    n_all = sum(1 for a in table if a.overall_feasible)
    print(f"  deflection {n_defl}/{len(table)} PASS   strength {n_str}/{len(table)} PASS   "
          f"overall {n_all}/{len(table)} PASS")
    print("  -> At 50 N every candidate passes both screens, with strength margins two to")
    print("     three ORDERS OF MAGNITUDE clear. The strength screen does not discriminate")
    print("     the candidate set at this load. Reported as found: the illustrative")
    print("     strengths were NOT reduced to manufacture a failure.")

    _rule("ALLOWABLE LOAD TRADE (preliminary central-point-load limits)")
    print(f"  {'candidate':<14}{'m_A':>7}{'P_defl':>9}{'P_face':>10}{'P_core':>11}"
          f"{'P_prelim':>10}  {'governing':<12}{'P/m_A':>10}")
    print(f"  {'':<14}{'kg/m2':>7}{'N':>9}{'N':>10}{'N':>11}{'N':>10}  {'':<12}{'N m2/kg':>10}")
    for a in table:
        c = a.capacity
        print(
            f"  {a.label:<14}{c.areal_mass:>7.3f}{c.deflection_limit:>9.2f}"
            f"{c.face_limit:>10.1f}{c.core_shear_limit:>11.0f}{c.preliminary_limit:>10.2f}"
            f"  {str(c.governing_constraint):<12}{c.capacity_to_areal_mass:>10.2f}"
        )
    print("  -> DEFLECTION governs every candidate in both directions. The face limit is")
    print(f"     ~{ref.capacity.face_limit / ref.capacity.deflection_limit:.0f}x the deflection limit and the core-shear limit is "
          f"{min(a.capacity.core_shear_limit / a.capacity.deflection_limit for a in table):.0f}-"
          f"{max(a.capacity.core_shear_limit / a.capacity.deflection_limit for a in table):.0f}x it.")
    print("     This panel is stiffness-critical, not strength-critical.")

    _rule("DIRECTIONAL STRENGTH PENALTY")
    print("  identity check: P_core,L / P_core,W == tau_L / tau_W (same geometry)")
    print(f"  {'candidate':<10}{'tau_L':>8}{'tau_W':>8}{'tau_L/tau_W':>13}"
          f"{'P_core,L':>11}{'P_core,W':>11}{'ratio':>9}{'P_prelim L/W':>14}")
    print(f"  {'':<10}{'MPa':>8}{'MPa':>8}{'[-]':>13}{'N':>11}{'N':>11}{'[-]':>9}{'[-]':>14}")
    for core in CANDIDATE_CORES:
        st = get_core_strength(core.name)
        al = next(a for a in l_rows if a.result.core_name == core.name)
        aw = next(a for a in w_rows if a.result.core_name == core.name)
        print(
            f"  {core.name:<10}{st.shear_strength_L / MPA:>8.2f}{st.shear_strength_W / MPA:>8.2f}"
            f"{st.directional_strength_ratio:>13.4f}"
            f"{al.capacity.core_shear_limit:>11.0f}{aw.capacity.core_shear_limit:>11.0f}"
            f"{al.capacity.core_shear_limit / aw.capacity.core_shear_limit:>9.4f}"
            f"{al.capacity.preliminary_limit / aw.capacity.preliminary_limit:>14.4f}"
        )
    print("  -> The directional strength penalty is real (1.64-1.71x) but never governs")
    print("     here; the L/W penalty that DOES bite is the stiffness one from Milestone 2.")

    _rule("LOAD SENSITIVITY (HC-AL-45, both directions)")
    print("  Loads far above the deflection limit are shown only to locate the face-yield")
    print("  crossing within the model. They are not proposed design loads.")
    print(f"  {'dir':>4}{'P [N]':>9}{'delta [mm]':>12}{'defl':>6}{'sigma [MPa]':>13}"
          f"{'MS_face':>10}{'tau [kPa]':>11}{'MS_core':>11}{'STR':>6}{'OVERALL':>9}"
          f"  {'governing':<12}")
    for row in load_sensitivity_sweep(
        BASIS, get_core("HC-AL-45"), get_core_strength("HC-AL-45"),
        [25.0, 50.0, 100.0, 500.0, 1000.0, 2000.0, 3000.0], STRENGTH, REQUIREMENT,
    ):
        print(
            f"  {row.direction.value:>4}{row.load:>9.0f}{row.total_deflection * 1e3:>12.4f}"
            f"{'PASS' if row.deflection_feasible else 'FAIL':>6}"
            f"{row.face_stress / MPA:>13.4f}{row.face_margin:>10.3f}"
            f"{row.core_shear_stress / KPA:>11.2f}{row.core_shear_margin:>11.2f}"
            f"{'PASS' if row.strength_feasible else 'FAIL':>6}"
            f"{'PASS' if row.overall_feasible else 'FAIL':>9}"
            f"  {str(row.governing_constraint):<12}"
        )
    print("  -> Every demand is exactly linear in P, so deflection fails first (just above")
    print("     ~56-60 N) and face yield only at ~2.9 kN. Core shear never becomes critical")
    print("     anywhere in this range.")

    _rule("CORE-DEPTH + STRENGTH TRADE (HC-AL-45, both directions)")
    print(f"  {'t_c':>6}{'m_A':>8}{'EI':>12}{'P_face':>10}{'P_defl,L':>10}{'P_defl,W':>10}"
          f"{'P_core,L':>10}{'P_core,W':>10}{'P_lim,L':>9}{'P_lim,W':>9}  {'gov L/W':<12}")
    print(f"  {'mm':>6}{'kg/m2':>8}{'N m^2':>12}{'N':>10}{'N':>10}{'N':>10}"
          f"{'N':>10}{'N':>10}{'N':>9}{'N':>9}")
    for row in core_depth_capacity_sweep(
        BASIS, get_core("HC-AL-45"), get_core_strength("HC-AL-45"),
        [5 * MM, 10 * MM, 15 * MM, 20 * MM, 25 * MM], STRENGTH, REQUIREMENT,
    ):
        print(
            f"  {row.core_thickness * 1e3:>6.1f}{row.areal_mass:>8.3f}"
            f"{row.flexural_rigidity:>12.4e}{row.face_limit:>10.1f}"
            f"{row.deflection_limit_L:>10.2f}{row.deflection_limit_W:>10.2f}"
            f"{row.core_shear_limit_L:>10.0f}{row.core_shear_limit_W:>10.0f}"
            f"{row.preliminary_limit_L:>9.2f}{row.preliminary_limit_W:>9.2f}"
            f"  {str(row.governing_constraint_L)}/{str(row.governing_constraint_W)}"
        )
    print("  -> Core depth raises all three capacities at once: EI (hence the deflection")
    print("     limit) roughly with t_c^2, and both the face and core-shear limits roughly")
    print("     with t_c. Core mass grows linearly. Deflection still governs throughout,")
    print("     because it grows from the lowest starting point. t_c is NOT optimised here.")

    _rule("LOAD-CAPACITY / MASS INTERPRETATION")
    lightest = min(table, key=lambda a: a.result.areal_mass)
    highest = max(table, key=lambda a: a.capacity.preliminary_limit)
    best_indicator = max(table, key=lambda a: a.capacity.capacity_to_areal_mass)
    print(f"  lightest candidate                      : {lightest.label} "
          f"({lightest.result.areal_mass:.3f} kg/m^2)")
    print(f"  highest preliminary load capacity       : {highest.label} "
          f"({highest.capacity.preliminary_limit:.2f} N, governed by "
          f"{highest.capacity.governing_constraint})")
    print(f"  best preliminary load-capacity/mass      : {best_indicator.label} "
          f"({best_indicator.capacity.capacity_to_areal_mass:.2f} N m^2/kg)")
    print("  (the last is a `preliminary load-capacity-to-areal-mass indicator`, a coarse")
    print("   screening diagnostic - NOT a universal optimisation metric)")

    front = pareto_front_by_capacity(table)
    print()
    print("  Non-dominated on (lower areal mass, higher preliminary capacity):")
    for a in front:
        print(f"    {a.label:<14} m_A = {a.result.areal_mass:6.3f} kg/m^2   "
              f"P_prelim = {a.capacity.preliminary_limit:6.2f} N")
    print(f"  ({len(table) - len(front)} of {len(table)} combinations are dominated on these two axes.)")
    print("  Screening aid only - not optimisation, not a selection.")

    print()
    print("=" * 84)
    print("Candidates retained for later crushing, wrinkling and practical-design screening.")
    print("No core is selected. Only face longitudinal stress and AVERAGE effective core")
    print("shear stress have been screened; both margins are preliminary, not certification")
    print("margins, and every strength value used here is illustrative.")
    print("=" * 84)


if __name__ == "__main__":
    main()
