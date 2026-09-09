"""Milestone 4: sandwich-specific local failure screening of the candidate cores.

ALL VALUES ARE ILLUSTRATIVE. Core compression strengths and moduli, the face
strength, the core shear strengths, the wrinkling coefficient and the local patch
load are all representative engineering-study inputs: not manufacturer
allowables, not design allowables, not qualification data.

Two local modes are screened, and only two:

  * face wrinkling, via an explicitly illustrative screening convention
  * core through-thickness compression under a prescribed local patch

Local indentation is DEFERRED, not implemented, because with the current inputs a
distinct indentation margin would either duplicate the core compression check
exactly or require invented data. Shear crimping is deferred because the model has
no in-plane compressive load case. See src/sandwich_panel/local_failure.py.

No core is selected.

Run with:

    python examples/local_failure_screen.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):  # allow running without installing the package
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sandwich_panel import (  # noqa: E402
    CANDIDATE_CORES,
    ILLUSTRATIVE_FACE_STRENGTH,
    CoreShearDirection,
    DeflectionRequirement,
    FaceMaterial,
    LocalPatchLoad,
    LocalScreenBasis,
    RetentionStatus,
    SandwichGeometry,
    StrengthBasis,
    StudyBasis,
    WrinklingModel,
    build_sandwich_table,
    core_depth_wrinkling_sweep,
    get_core,
    get_core_compression,
    get_core_strength,
    local_patch_force_sweep,
    local_patch_size_sweep,
)

MM = 1.0e-3
KPA = 1.0e3
MPA = 1.0e6
GPA = 1.0e9

# --- study basis: unchanged from Milestones 1-3 ---------------------------

GEOMETRY = SandwichGeometry(
    width=0.500, face_thickness=0.4 * MM, core_thickness=20.0 * MM, span=1.500
)
FACE = FaceMaterial(
    name="Illustrative aluminium-like face sheet (not a datasheet value)",
    youngs_modulus=70.0 * GPA,
    density=2700.0,
)
LOAD = 50.0
BASIS = StudyBasis(geometry=GEOMETRY, face=FACE, load=LOAD)
STRENGTH = StrengthBasis(face_strength=ILLUSTRATIVE_FACE_STRENGTH, face_design_factor=1.0)
DEFLECTION_LIMIT = GEOMETRY.span / 1000.0
REQUIREMENT = DeflectionRequirement(
    maximum_total_deflection=DEFLECTION_LIMIT,
    label="illustrative panel deflection limit = span/1000 (preliminary stiffness screen only)",
)

# --- Milestone 4 local screen inputs --------------------------------------

# The coefficient is a REQUIRED explicit input: the package has no default, so no
# empirical constant can hide inside it. 0.5 is a commonly cited value for this
# analytical form, used here as an illustrative screening convention only.
WRINKLING = WrinklingModel(
    coefficient=0.5,
    source_note=(
        "ILLUSTRATIVE screening convention - NOT a validated allowable and not "
        "sourced to a standard. Published coefficients for this form vary by "
        "reference and by imperfection assumption."
    ),
    notes="sigma_wr,screen = C_wr * (E_f * E_c * G_eff)^(1/3)",
)

# Illustrative local hard-point patch load. Chosen as a round, transparent case,
# NOT sized to make any candidate fail - see the sweeps below for where the
# boundaries actually fall.
PATCH = LocalPatchLoad.square(force=100.0, side=25.0 * MM)
LOCAL = LocalScreenBasis(wrinkling_model=WRINKLING, patch_load=PATCH)


def _rule(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> None:
    print("=" * 96)
    print("SANDWICH LOCAL FAILURE SCREEN - Milestone 4")
    print("Screens face wrinkling and local core crushing on top of the Milestone 3")
    print("global screens. Local indentation and shear crimping are DEFERRED, with")
    print("reasons stated, not approximated. NO CORE IS SELECTED HERE.")
    print("-" * 96)
    print("ALL VALUES BELOW ARE ILLUSTRATIVE LOCAL-FAILURE INPUTS -")
    print("NOT MANUFACTURER ALLOWABLES, not design allowables, not qualification data.")
    print("=" * 96)

    table = build_sandwich_table(BASIS, STRENGTH, REQUIREMENT, LOCAL)
    l_rows = [a for a in table if a.result.direction is CoreShearDirection.L]
    w_rows = [a for a in table if a.result.direction is CoreShearDirection.W]
    ref = l_rows[0]

    _rule("STUDY BASIS")
    print(f"  GLOBAL: span L = {GEOMETRY.span:.3f} m, width b = {GEOMETRY.width:.3f} m, "
          f"t_f = {GEOMETRY.face_thickness * 1e3:.2f} mm, t_c = {GEOMETRY.core_thickness * 1e3:.1f} mm")
    print(f"    face: E_f = {FACE.youngs_modulus / GPA:.1f} GPa, "
          f"illustrative yield = {ILLUSTRATIVE_FACE_STRENGTH.yield_strength / MPA:.0f} MPa, "
          f"design factor = {STRENGTH.face_design_factor:.2f}")
    print(f"    central point load P = {LOAD:.1f} N   "
          f"(face stress = {ref.local.face_stress / MPA:.4f} MPa)")
    print(f"    {REQUIREMENT.label}: {DEFLECTION_LIMIT * 1e3:.3f} mm")
    print(f"  LOCAL: illustrative local hard-point patch load")
    print(f"    F_local = {PATCH.force:.1f} N over "
          f"{PATCH.patch_width * 1e3:.0f} x {PATCH.patch_length * 1e3:.0f} mm "
          f"= {PATCH.patch_area * 1e6:.0f} mm^2")
    print(f"    patch pressure = {PATCH.pressure / KPA:.1f} kPa")
    print("    this is a preliminary local core compression screen for a prescribed")
    print("    footprint - NOT an insert analysis")
    print(f"  WRINKLING CONVENTION: sigma_wr,screen = C_wr * (E_f * E_c * G_eff)^(1/3)")
    print(f"    C_wr = {WRINKLING.coefficient} (explicit required input; no default in the package)")
    print(f"    {WRINKLING.source_note}")
    print("  The global load case (P) and the local load case (F_local) are INDEPENDENT")
    print("  and their capacities are never combined.")

    _rule("CANDIDATE LOCAL PROPERTIES (illustrative)")
    print(f"  {'candidate':<10}{'rho':>6}{'E_c':>8}{'sigma_c':>10}"
          f"{'sigma_wr,L':>12}{'sigma_wr,W':>12}{'wr L/W':>9}{'(GL/GW)^1/3':>13}")
    print(f"  {'':<10}{'kg/m3':>6}{'MPa':>8}{'MPa':>10}{'MPa':>12}{'MPa':>12}{'[-]':>9}{'[-]':>13}")
    for core in CANDIDATE_CORES:
        cc = get_core_compression(core.name)
        al = next(a for a in l_rows if a.result.core_name == core.name)
        aw = next(a for a in w_rows if a.result.core_name == core.name)
        sl = al.local.wrinkling_screening_stress
        sw = aw.local.wrinkling_screening_stress
        print(f"  {core.name:<10}{core.density:>6.0f}{cc.compression_modulus / MPA:>8.0f}"
              f"{cc.compression_strength / MPA:>10.2f}{sl / MPA:>12.1f}{sw / MPA:>12.1f}"
              f"{sl / sw:>9.4f}{(core.shear_modulus_L / core.shear_modulus_W) ** (1/3):>13.4f}")
    print("  -> sigma_wr,L / sigma_wr,W == (G_L/G_W)^(1/3) exactly, as the model requires.")
    print("  -> HC-AR-48 has the LOWEST wrinkling stress despite mid-range density, because")
    print("     aramid paper's compression modulus is far below aluminium foil's and the")
    print("     screen goes as E_c^(1/3). That was not designed in.")

    _rule("GLOBAL SCREEN at 50 N (deflection + face yield + core shear + wrinkling)")
    print(f"  {'candidate':<14}{'delta':>8}{'defl':>6}{'MS_face':>9}{'MS_core':>10}"
          f"{'MS_wrink':>10}{'GLOBAL':>8}  {'governing':<12}")
    print(f"  {'':<14}{'mm':>8}{'':>6}{'[-]':>9}{'[-]':>10}{'[-]':>10}")
    for a in table:
        print(f"  {a.label:<14}{a.result.total_deflection * 1e3:>8.4f}"
              f"{'PASS' if a.deflection_feasible else 'FAIL':>6}"
              f"{a.design.strength.face_margin:>9.2f}"
              f"{a.design.strength.core_shear_margin:>10.2f}"
              f"{a.local.wrinkling_margin:>10.2f}"
              f"{'PASS' if a.deflection_feasible and a.global_strength_feasible and a.local.wrinkling_pass else 'FAIL':>8}"
              f"  {str(a.capacity.governing_constraint):<12}")

    _rule("LOCAL PATCH SCREEN (core through-thickness compression)")
    print("  Direction-independent: crushing does not involve the L/W shear moduli.")
    print(f"  {'candidate':<10}{'p_patch':>10}{'sigma_c':>10}{'MS_comp':>10}{'F_crush':>10}  {'screen':<6}")
    print(f"  {'':<10}{'kPa':>10}{'MPa':>10}{'[-]':>10}{'N':>10}")
    for a in l_rows:
        lf = a.local
        print(f"  {lf.candidate:<10}{lf.local_core_compression_stress / KPA:>10.1f}"
              f"{lf.core_compression_allowable / MPA:>10.2f}{lf.core_compression_margin:>10.2f}"
              f"{lf.core_crush_force_limit:>10.1f}"
              f"  {'PASS' if lf.core_compression_pass else 'FAIL':<6}")

    _rule("GLOBAL LOAD CAPACITY (central point load, now including wrinkling)")
    print(f"  {'candidate':<14}{'m_A':>7}{'P_defl':>9}{'P_face':>9}{'P_core':>10}"
          f"{'P_wrink':>10}{'P_sandwich':>12}  {'governing':<12}{'P/m_A':>9}")
    print(f"  {'':<14}{'kg/m2':>7}{'N':>9}{'N':>9}{'N':>10}{'N':>10}{'N':>12}  {'':<12}{'N m2/kg':>9}")
    for a in table:
        c = a.capacity
        print(f"  {a.label:<14}{c.areal_mass:>7.3f}{c.deflection_limit:>9.2f}"
              f"{c.face_limit:>9.1f}{c.core_shear_limit:>10.0f}{c.wrinkling_limit:>10.1f}"
              f"{c.sandwich_limit:>12.2f}  {str(c.governing_constraint):<12}"
              f"{c.capacity_to_areal_mass:>9.2f}")
    n_wr_below_face = sum(1 for a in table if a.capacity.wrinkling_limit < a.capacity.face_limit)
    print(f"  -> DEFLECTION still governs all {len(table)} cases; adding wrinkling did not change")
    print("     the governing global constraint anywhere.")
    print(f"  -> BUT wrinkling is the more restrictive STRENGTH mode in {n_wr_below_face} of "
          f"{len(table)} cases:")
    for a in table:
        if a.capacity.wrinkling_limit < a.capacity.face_limit:
            print(f"       {a.label}: P_wrinkling = {a.capacity.wrinkling_limit:.1f} N "
                  f"< P_face_yield = {a.capacity.face_limit:.1f} N")
    print("     That is the sandwich-specific insight: for a low-compression-modulus core in")
    print("     the soft shear direction, the face buckles locally before it yields.")

    _rule("LOCAL PATCH CAPACITY / MASS DIAGNOSTIC")
    print("  Crush force is a DIFFERENT load case from the global central load; the two")
    print("  capacities are never combined mathematically.")
    print(f"  {'candidate':<10}{'F_crush':>10}{'m_A':>8}{'F_crush/m_A':>14}")
    print(f"  {'':<10}{'N':>10}{'kg/m2':>8}{'N m2/kg':>14}")
    for a in l_rows:
        print(f"  {a.local.candidate:<10}{a.local.core_crush_force_limit:>10.1f}"
              f"{a.result.areal_mass:>8.3f}"
              f"{a.local.core_crush_force_limit / a.result.areal_mass:>14.1f}")
    print("  -> diagnostic only, not an optimisation metric.")

    _rule("LOCAL PATCH FORCE SENSITIVITY (HC-AL-30, weakest core in crushing, 25 mm patch)")
    print(f"  {'F_local':>9}{'pressure':>11}{'MS_comp':>10}  {'screen':<6}")
    print(f"  {'N':>9}{'kPa':>11}{'[-]':>10}")
    for row in local_patch_force_sweep(
        get_core_compression("HC-AL-30"), PATCH, [25.0, 50.0, 100.0, 200.0, 500.0, 1000.0]
    ):
        print(f"  {row.force:>9.0f}{row.pressure / KPA:>11.1f}{row.compression_margin:>10.3f}"
              f"  {'PASS' if row.compression_pass else 'FAIL':<6}")
    print(f"  -> pressure is exactly linear in force; the boundary is at F = "
          f"{get_core_compression('HC-AL-30').compression_strength * PATCH.patch_area:.1f} N.")

    _rule("PATCH-SIZE SENSITIVITY (HC-AL-30, F_local = 100 N, square patch)")
    print(f"  {'side':>7}{'area':>11}{'pressure':>11}{'MS_comp':>10}  {'screen':<6}")
    print(f"  {'mm':>7}{'mm^2':>11}{'kPa':>11}{'[-]':>10}")
    for row in local_patch_size_sweep(
        get_core_compression("HC-AL-30"), PATCH,
        [10 * MM, 15 * MM, 20 * MM, 25 * MM, 40 * MM, 50 * MM],
    ):
        print(f"  {row.patch_side * 1e3:>7.0f}{row.patch_area * 1e6:>11.1f}"
              f"{row.pressure / KPA:>11.1f}{row.compression_margin:>10.3f}"
              f"  {'PASS' if row.compression_pass else 'FAIL':<6}")
    print("  -> pressure goes exactly as 1/area, i.e. 1/side^2 for a square patch.")

    _rule("CORE-DEPTH + WRINKLING TRADE (HC-AL-45)")
    print(f"  {'dir':>4}{'t_c':>7}{'EI':>12}{'m_A':>8}{'sigma_face':>12}"
          f"{'sigma_wr':>11}{'MS_wrink':>10}{'P_wrink':>10}{'P_sandwich':>12}  {'governing':<12}")
    print(f"  {'':>4}{'mm':>7}{'N m^2':>12}{'kg/m2':>8}{'MPa':>12}{'MPa':>11}"
          f"{'[-]':>10}{'N':>10}{'N':>12}")
    for row in core_depth_wrinkling_sweep(
        BASIS, get_core("HC-AL-45"), get_core_strength("HC-AL-45"),
        get_core_compression("HC-AL-45"),
        [5 * MM, 10 * MM, 15 * MM, 20 * MM, 25 * MM],
        STRENGTH, REQUIREMENT, LOCAL,
    ):
        print(f"  {row.direction.value:>4}{row.core_thickness * 1e3:>7.1f}"
              f"{row.flexural_rigidity:>12.4e}{row.areal_mass:>8.3f}"
              f"{row.face_stress / MPA:>12.4f}{row.wrinkling_screening_stress / MPA:>11.1f}"
              f"{row.wrinkling_margin:>10.2f}{row.wrinkling_limit:>10.1f}"
              f"{row.sandwich_limit:>12.2f}  {str(row.governing_constraint):<12}")
    print("  -> sigma_wr does NOT move with core depth under this convention (it depends only")
    print("     on material moduli), but the face stress DEMAND falls steeply with depth, so")
    print("     the wrinkling margin improves anyway. Core depth is not optimised here.")

    _rule("CANDIDATE RETENTION")
    for a in table:
        print(f"  {a.label:<14}{str(a.retention):<18}{a.retention_reason}")
    retained = [a for a in table if a.retention is RetentionStatus.RETAINED]
    print(f"  {len(retained)}/{len(table)} candidate-direction combinations retained.")
    if len(retained) == len(table):
        print("  Every candidate survives every modelled screen at the illustrative load and")
        print("  patch. Local failure modes did NOT change which candidates remain viable at")
        print("  this baseline. Reported as found - the patch and coefficient were not sized")
        print("  to eliminate anyone. The sweeps above show where the boundaries actually are.")

    print()
    print("=" * 96)
    print("No final core is selected in Milestone 4; retained candidates proceed to practical")
    print("design and final trade screening.")
    print("Local indentation, shear crimping, detailed inserts/potting, fastener bearing,")
    print("adhesive failure, global buckling, thermal and vibration all remain deferred.")
    print("=" * 96)


if __name__ == "__main__":
    main()
