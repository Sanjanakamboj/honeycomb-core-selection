"""Generate the STM-10 portfolio figures deterministically.

Writes four PNGs into this directory. Reuses the package APIs only - every number
plotted is recomputed from the model, never hard-coded.

    ALL PLOTTED CANDIDATE PROPERTIES AND BOTH REQUIREMENT LINES ARE ILLUSTRATIVE.

Run with:

    python figures/make_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from sandwich_panel import (  # noqa: E402
    CANDIDATE_CORES,
    CoreShearDirection,
    DeflectionRequirement,
    FaceMaterial,
    FrequencyRequirement,
    ILLUSTRATIVE_FACE_STRENGTH,
    LocalPatchLoad,
    LocalScreenBasis,
    PreliminaryScreens,
    SandwichGeometry,
    StrengthBasis,
    StudyBasis,
    WrinklingModel,
    assess_integrated_design,
    build_integrated_table,
    get_core,
    get_core_compression,
    get_core_strength,
    select_preliminary_core,
)

MM = 1.0e-3
MPA = 1.0e6
GPA = 1.0e9
HERE = Path(__file__).resolve().parent

# Deterministic, non-interactive styling.
plt.rcParams.update({
    "figure.dpi": 140,
    "savefig.dpi": 140,
    "font.size": 9,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
    "svg.hashsalt": "stm10",
})
# Strip the timestamp so repeated runs are byte-identical.
PNG_METADATA = {"Software": None}

# Candidates cluster tightly in areal mass (3.06 and 3.12 kg/m^2 are only
# 0.06 apart), so per-point text labels collide no matter how they are offset.
# Colour therefore identifies the CANDIDATE and marker shape the ORIENTATION -
# unambiguous and collision-free.
CANDIDATE_COLOUR = {
    "HC-AL-30": "#2166ac",
    "HC-AL-45": "#4393c3",
    "HC-AR-48": "#7fbf7b",
    "HC-AL-60": "#f4a582",
    "HC-AL-80": "#b2182b",
}
L_MARKER, W_MARKER = "o", "^"
SELECTED = dict(marker="o", s=300, facecolors="none", edgecolors="#111111",
                linewidths=2.2, linestyle="--", zorder=5)
REQ_LINE = dict(color="#b2182b", linestyle="--", linewidth=1.3, zorder=1)


def _scatter_candidates(ax, y_of):
    """Plot all ten configurations, coloured by candidate, shaped by orientation."""
    for a in TABLE:
        is_l = a.result.direction is CoreShearDirection.L
        ax.scatter(
            a.areal_mass, y_of(a),
            marker=L_MARKER if is_l else W_MARKER, s=78,
            c=CANDIDATE_COLOUR[a.result.core_name],
            edgecolors="black", linewidths=0.6, zorder=3,
        )


def _candidate_legend(ax, loc):
    """Two-part legend: candidate colours, then orientation shapes."""
    from matplotlib.lines import Line2D

    handles = [
        Line2D([], [], marker="s", linestyle="none", markersize=8,
               markerfacecolor=CANDIDATE_COLOUR[name], markeredgecolor="black",
               markeredgewidth=0.5,
               label=f"{name}  ({density:.0f} kg/m$^3$)")
        for name, density in [(c.name, c.density) for c in CANDIDATE_CORES]
    ] + [
        Line2D([], [], marker=L_MARKER, linestyle="none", markersize=8,
               markerfacecolor="white", markeredgecolor="black",
               label="L orientation (ribbon)"),
        Line2D([], [], marker=W_MARKER, linestyle="none", markersize=8,
               markerfacecolor="white", markeredgecolor="black",
               label="W orientation (transverse)"),
        Line2D([], [], marker="o", linestyle="none", markersize=12,
               markerfacecolor="none", markeredgecolor="#111111", markeredgewidth=1.8,
               label="preliminary selection"),
    ]
    ax.legend(handles=handles, loc=loc, fontsize=7.5, framealpha=0.95,
              handletextpad=0.6, labelspacing=0.4)

GEOMETRY = SandwichGeometry(
    width=0.500, face_thickness=0.4 * MM, core_thickness=20.0 * MM, span=1.500
)
FACE = FaceMaterial(name="Illustrative aluminium-like face sheet",
                    youngs_modulus=70.0 * GPA, density=2700.0)
BASIS = StudyBasis(geometry=GEOMETRY, face=FACE, load=50.0)
SCREENS = PreliminaryScreens(
    deflection=DeflectionRequirement(maximum_total_deflection=GEOMETRY.span / 1000.0),
    strength=StrengthBasis(face_strength=ILLUSTRATIVE_FACE_STRENGTH),
    local=LocalScreenBasis(
        wrinkling_model=WrinklingModel(coefficient=0.5, source_note="illustrative"),
        patch_load=LocalPatchLoad.square(force=100.0, side=25.0 * MM),
    ),
    frequency=FrequencyRequirement(minimum_frequency_hz=25.0),
)

TABLE = build_integrated_table(BASIS, SCREENS)
SELECTION = select_preliminary_core(TABLE)
L_ROWS = [a for a in TABLE if a.result.direction is CoreShearDirection.L]
W_ROWS = [a for a in TABLE if a.result.direction is CoreShearDirection.W]


def _save(fig, name: str) -> None:
    path = HERE / name
    fig.savefig(path, bbox_inches="tight", metadata=PNG_METADATA)
    plt.close(fig)
    print(f"  wrote {path.relative_to(HERE.parent)}")


def figure_1_mass_vs_deflection() -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.5))
    limit = SCREENS.deflection.maximum_total_deflection * 1e3

    ax.axhline(limit, **REQ_LINE)
    ax.text(2.63, limit - 0.012, f"illustrative limit  span/1000 = {limit:.1f} mm",
            ha="left", va="top", fontsize=8, color="#b2182b")

    _scatter_candidates(ax, lambda a: a.result.total_deflection * 1e3)
    ax.scatter([SELECTION.areal_mass], [SELECTION.total_deflection * 1e3], **SELECTED)

    ax.set_xlabel("panel areal mass  $m_A$  [kg/m$^2$]")
    ax.set_ylabel("total deflection at 50 N  $\\delta$  [mm]")
    ax.set_title("Static stiffness trade: heavier, shear-stiffer cores deflect less\n"
                 "(every configuration passes the illustrative limit)", fontsize=10)
    ax.set_xlim(2.6, 4.35)
    ax.set_ylim(1.18, 1.53)
    _candidate_legend(ax, "upper right")
    _save(fig, "fig1_mass_vs_deflection.png")


def figure_2_mass_vs_frequency() -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.5))
    limit = SCREENS.frequency.minimum_frequency_hz

    ax.axhline(limit, **REQ_LINE)
    ax.text(2.63, limit + 0.2, f"illustrative requirement  $f_1 \\geq$ {limit:.0f} Hz",
            ha="left", va="bottom", fontsize=8, color="#b2182b")

    _scatter_candidates(ax, lambda a: a.modal.frequency)
    ax.scatter([SELECTION.areal_mass], [SELECTION.first_mode_frequency], **SELECTED)

    ax.set_xlabel("panel areal mass  $m_A$  [kg/m$^2$]")
    ax.set_ylabel("fundamental frequency  $f_1$  [Hz]")
    ax.set_title("Modal trade: the LIGHTEST core gives the HIGHEST frequency\n"
                 "(despite having the lowest core shear modulus)", fontsize=10)
    ax.set_xlim(2.6, 4.35)
    ax.set_ylim(24.5, 32.4)
    _candidate_legend(ax, "upper right")
    _save(fig, "fig2_mass_vs_frequency.png")


def figure_3_utilisations() -> None:
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    labels = [a.label for a in TABLE]
    x = range(len(labels))
    width = 0.27

    defl = [a.utilisation.deflection for a in TABLE]
    modal = [a.utilisation.frequency for a in TABLE]
    wrink = [a.utilisation.wrinkling for a in TABLE]

    ax.bar([i - width for i in x], defl, width, label="static deflection",
           color="#1b6ca8", edgecolor="black", linewidth=0.4)
    ax.bar(list(x), modal, width, label="modal frequency",
           color="#e08214", edgecolor="black", linewidth=0.4)
    ax.bar([i + width for i in x], wrink, width, label="face wrinkling",
           color="#7fbf7b", edgecolor="black", linewidth=0.4)

    ax.axhline(1.0, color="#b2182b", linestyle="--", linewidth=1.4, zorder=3)
    ax.text(len(labels) - 0.4, 1.02, "utilisation = 1  (screen limit)",
            ha="right", va="bottom", fontsize=8, color="#b2182b")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("utilisation  =  demand / capacity  [-]")
    ax.set_ylim(0, 1.16)
    ax.set_title("Which screen is closest to critical\n"
                 "(face yield $\\leq$ 0.018 and core shear $\\leq$ 0.005 omitted: far from critical)",
                 fontsize=10)
    ax.legend(loc="upper left", fontsize=8, ncol=3, framealpha=0.95)
    _save(fig, "fig3_screen_utilisations.png")


def figure_4_core_thickness_trade() -> None:
    core = get_core("HC-AL-45")
    strength = get_core_strength("HC-AL-45")
    compression = get_core_compression("HC-AL-45")
    thicknesses = [5, 10, 15, 20, 25, 30]

    data = {}
    for direction in ("L", "W"):
        rows = []
        for t_c in thicknesses:
            local = StudyBasis(
                geometry=SandwichGeometry(
                    width=GEOMETRY.width, face_thickness=GEOMETRY.face_thickness,
                    core_thickness=t_c * MM, span=GEOMETRY.span),
                face=FACE, load=BASIS.load,
            )
            rows.append(assess_integrated_design(
                local, core, strength, compression, direction, SCREENS))
        data[direction] = rows

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(6.4, 5.6), sharex=True,
        gridspec_kw={"height_ratios": [1, 1.25], "hspace": 0.12},
    )

    ax_top.plot(thicknesses, [a.areal_mass for a in data["L"]],
                marker="s", color="#4d4d4d", linewidth=1.6, label="areal mass")
    ax_top.set_ylabel("areal mass  $m_A$  [kg/m$^2$]")
    ax_top.set_ylim(2.2, 3.7)
    ax_top.legend(loc="upper left", fontsize=8)
    ax_top.set_title("Core-depth trade (HC-AL-45): depth buys frequency cheaply\n"
                     "mass grows linearly, $f_1$ grows because $EI \\sim t_c^2$", fontsize=10)

    ax_bot.plot(thicknesses, [a.modal.frequency for a in data["L"]],
                marker="o", color="#1b6ca8", linewidth=1.6, label="$f_1$, L orientation")
    ax_bot.plot(thicknesses, [a.modal.frequency for a in data["W"]],
                marker="^", color="#e08214", linewidth=1.6, linestyle="--",
                label="$f_1$, W orientation")
    limit = SCREENS.frequency.minimum_frequency_hz
    ax_bot.axhline(limit, **REQ_LINE)
    ax_bot.text(30, limit - 1.2, f"illustrative requirement  $f_1 \\geq$ {limit:.0f} Hz",
                ha="right", va="top", fontsize=8, color="#b2182b")
    ax_bot.set_xlabel("core thickness  $t_c$  [mm]")
    ax_bot.set_ylabel("fundamental frequency  $f_1$  [Hz]")
    ax_bot.set_xticks(thicknesses)
    ax_bot.set_ylim(5, 45)
    ax_bot.legend(loc="upper left", fontsize=8)
    _save(fig, "fig4_core_thickness_trade.png")


def main() -> None:
    print("Generating STM-10 portfolio figures (all values illustrative)...")
    figure_1_mass_vs_deflection()
    figure_2_mass_vs_frequency()
    figure_3_utilisations()
    figure_4_core_thickness_trade()
    print("Done.")


if __name__ == "__main__":
    main()
