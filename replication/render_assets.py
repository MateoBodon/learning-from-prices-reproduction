#!/usr/bin/env python3
"""Render the four reported figures and four supporting tables.

Tables 2 and 3 are assembled from exact formulas and generated result files.
Table 1 is assembled from the separately labeled source-custody record; those
recorded source checks are not rerun by this repository.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_analysis as ra

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
TAB = ROOT / "tables"
FIG.mkdir(exist_ok=True)
TAB.mkdir(exist_ok=True)
mpl.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "figure.dpi": 160,
        "savefig.dpi": 300,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
    }
)
BLUE = "#1d4ed8"
RED = "#b91c1c"
GOLD = "#b45309"
GREEN = "#047857"
GRAY = "#64748b"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def figure1():
    sys.set_int_max_str_digits(0)
    d = json.load(open(ROOT / "results/stability_grid.json"))
    z = np.zeros((9, 9), int)
    for r in d["cells"]:
        if r["asymptotic"] == "UNSTABLE":
            z[r["j"] + 4, r["i"] + 4] += 1
    fig, ax = plt.subplots(figsize=(5.8, 4.3))
    im = ax.imshow(z, origin="lower", cmap="RdYlBu_r", vmin=0, vmax=100)
    for y in range(9):
        for x in range(9):
            red, green, blue, _ = im.cmap(im.norm(z[y, x]))
            luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            ax.text(
                x,
                y,
                str(z[y, x]),
                ha="center",
                va="center",
                fontsize=8,
                color="white" if luminance < 0.45 else "#111827",
            )
    ax.set_xticks(range(9), range(-4, 5))
    ax.set_yticks(range(9), range(-4, 5))
    ax.set_xlabel(r"signal-variance exponent $i$")
    ax.set_ylabel(r"noise-variance exponent $j$")
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("count out of 100")
    save(fig, "Fig1_stability_regions")


def figure2():
    d = json.load(open(ROOT / "results/stability_grid.json"))
    cells = d["source_sweep"]["cells"]
    phis = np.arange(1, 101) / 100
    ks = [1, 2, 3, 10, 99, 100]
    colors = [RED, "#7c3aed", GOLD, GREEN, BLUE, GRAY]
    styles = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1))]
    markers = ["o", "s", "^", "D", "v", "P"]
    fig, ax = plt.subplots(figsize=(6.8, 4.1))
    for k, col, style, marker in zip(ks, colors, styles, markers):
        vals = [
            10 ** row["errors"][str(k)]["log10_absolute"]
            if row["errors"][str(k)]["log10_absolute"] is not None
            else 1e-18
            for row in cells
        ]
        ax.plot(
            phis,
            np.maximum(vals, 1e-18),
            label=f"K={k}",
            color=col,
            ls=style,
            lw=1.55,
            marker=marker,
            markevery=10,
            ms=3.2,
        )
    ax.axvspan(0.06, 0.44, color=RED, alpha=0.09)
    ax.text(
        0.25,
        2.8e3,
        "asymptotically unstable",
        color=RED,
        fontsize=8,
        ha="center",
    )
    ax.axvline(0.60, color=GREEN, ls="--", lw=1.2)
    ax.text(0.61, 4e-1, r"displayed $h=0.60$", color=GREEN, fontsize=8)
    ax.set_yscale("log")
    ax.set_ylim(1e-18, 1e4)
    ax.set_xlabel(r"partial-revelation weight $h$")
    ax.set_ylabel("relative coefficient error")
    ax.legend(ncol=3, frameon=False, loc="lower left")
    save(fig, "Fig2_finite_iteration_error")


def figure3():
    t = 152 / 125
    fig, axs = plt.subplots(
        1, 2, figsize=(7.2, 3.5), gridspec_kw={"width_ratios": [1.15, 1]}
    )
    ax = axs[0]
    xs = np.linspace(-5.4, 2.3, 600)
    ys = -xs / t
    ys[np.abs(xs + t) < 0.045] = np.nan
    ax.plot(xs, ys, color=BLUE, lw=2, label=r"$w'=-w/t$")
    ax.axvline(-t, color=RED, ls="--", label=r"pole $w=-t$")
    ax.axvline(1, color=GRAY, ls=":", label=r"chart infinity $w=1$")
    ax.scatter([-t], [1], s=42, facecolors="white", edgecolors=RED, lw=1.3, zorder=4)
    ax.annotate(
        "pole",
        (-t, 1),
        xytext=(4, 5),
        textcoords="offset points",
        fontsize=7,
        color=RED,
    )
    for m in range(2, 6):
        x = (-t) ** m
        ax.scatter([x], [-x / t], s=28, color=GOLD, zorder=3)
        ax.annotate(
            f"preimage {m - 1}",
            (x, -x / t),
            xytext=(3, 4),
            textcoords="offset points",
            fontsize=7,
        )
    ax.axhline(0, color="#cbd5e1", lw=0.8)
    ax.axvline(0, color="#cbd5e1", lw=0.8)
    ax.set_xlim(-5.4, 2.3)
    ax.set_ylim(-2.1, 4.6)
    ax.set_xlabel(r"current coordinate $w$")
    ax.set_ylabel(r"next coordinate $w'$")
    ax.legend(frameon=False, loc="upper left")
    ax = axs[1]
    n = np.arange(0, 21)
    w0 = -250 / 581
    for tt, col, style, marker, lab in [
        (1.216, BLUE, "-", "o", "t>1: contraction"),
        (1.0, GOLD, "--", "s", "t=1: two-cycle"),
        (0.82, RED, "-.", "^", "t<1: expansion"),
    ]:
        ax.plot(
            n,
            np.abs(w0 * (-1 / tt) ** n),
            marker=marker,
            ms=2.8,
            lw=1.5,
            ls=style,
            color=col,
            label=lab,
        )
    ax.set_yscale("log")
    ax.set_xlabel("reduced updates")
    ax.set_ylabel(r"$|w_K|$")
    ax.legend(frameon=False)
    save(fig, "Fig3_pole_geometry")


def figure4():
    pp = ra.private_float_path(True)[:20]
    lp = ra.private_float_path(False)[:20]
    start = tuple(map(float, ra.private_ce_start()))
    pp = [start] + pp
    lp = [start] + lp
    k = np.arange(21)
    fig, axs = plt.subplots(1, 2, figsize=(8.0, 3.6))
    axs[0].plot(k, [v[2] for v in pp], color=BLUE, lw=1.8, label="article/updater-H")
    axs[0].plot(k, [v[2] for v in lp], color=RED, lw=1.8, ls="--", label="deposited-D")
    axs[0].axhline(float(ra.private_root(True)[2]), color=BLUE, alpha=0.35)
    axs[0].axhline(float(ra.private_root(False)[2]), color=RED, alpha=0.35)
    axs[0].set_xlabel("map applications K")
    axs[0].set_ylabel(r"mean-supply loading $q_K$")
    axs[0].legend(frameon=False)
    xs = np.linspace(0.5, 1.5, 101)
    for idx, col, style, lab in [
        (1, GOLD, "-", "K=1"),
        (10, GREEN, "--", "K=10"),
        (20, GRAY, "-.", "K=20"),
    ]:
        gap = [
            abs(
                (lp[idx][0] + lp[idx][1] * x + lp[idx][2] + lp[idx][3])
                - (pp[idx][0] + pp[idx][1] * x + pp[idx][2] + pp[idx][3])
            )
            for x in xs
        ]
        axs[1].plot(xs, gap, color=col, ls=style, lw=1.7, label=lab)
    axs[1].axhline(
        float(ra.F(5000, 116781)),
        color=RED,
        ls=":",
        lw=1.4,
        label="fixed-point raw gap",
    )
    axs[1].set_xlabel("realization x")
    axs[1].set_ylabel("absolute price-function gap")
    axs[1].legend(frameon=False)
    save(fig, "Fig4_private_map_paths")


def write_table(name, header, rows, align=None):
    align = align or ("l" * len(header))
    with (TAB / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows([header, *rows])
    lines = [
        r"\begin{tabular}{" + align + "}",
        r"\toprule",
        " & ".join(header) + r" \\",
        r"\midrule",
    ]
    lines += [" & ".join(map(str, row)) + r" \\" for row in rows]
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / f"{name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def tables():
    custody = json.load(open(ROOT / "provenance/recorded_source_checks.json"))
    write_table(
        "table1_source_custody",
        ["Check", "Result", "Bound"],
        custody["table_rows"],
        r"@{}p{.32\textwidth}p{.36\textwidth}p{.21\textwidth}@{}",
    )

    article_root = ra.private_root(True)
    deposited_root = ra.private_root(False)
    mean_supply_residual = article_root[2] - deposited_root[2]
    fixed_gap = ra.F(125000, 3544233)
    first_gap = ra.F(125000, 751233)
    normalized_amplification = first_gap / fixed_gap
    raw_amplification = ra.F(15000, 59843) / ra.F(5000, 116781)
    root_text = "$(" + ",".join(str(value) for value in article_root) + ")$"
    write_table(
        "table2_private_identities",
        ["Object", "Exact value", "Decimal"],
        [
            ["Article/updater-$H$ root", root_text, "--"],
            [
                "Deposited-$D$ mean-supply loading",
                f"${deposited_root[2]}$",
                f"{float(deposited_root[2]):.6f}",
            ],
            [
                "Mean-supply residual",
                f"${mean_supply_residual}$",
                f"{float(mean_supply_residual):.6f}",
            ],
            [
                "Fixed gap (fixed-$H$ norm)",
                f"${fixed_gap}$",
                f"{100 * float(fixed_gap):.6f}\\%",
            ],
            [
                "First-update gap (time-1 $H$ norm)",
                f"${first_gap}$",
                f"{100 * float(first_gap):.6f}\\%",
            ],
            [
                "Normalized amplification",
                f"${normalized_amplification}$",
                f"{float(normalized_amplification):.6f}",
            ],
            [
                "Raw-gap amplification",
                f"${raw_amplification}$",
                f"{float(raw_amplification):.6f}",
            ],
        ],
        r"@{}p{.31\textwidth}p{.46\textwidth}p{.13\textwidth}@{}",
    )

    stability = json.load(open(ROOT / "results/stability_grid.json"))
    horizon = json.load(open(ROOT / "results/finite_horizon_sensitivity.json"))
    pole_guard = json.load(open(ROOT / "results/finite_pole_certificate.json"))
    stable_cells = [row for row in stability["cells"] if row["asymptotic"] == "STABLE"]
    closest = max(stable_cells, key=lambda row: row["epsilon"]["decimal"])
    displayed = next(
        row for row in stability["source_sweep"]["cells"] if row["phi_index"] == 60
    )
    source_counts = stability["source_sweep"]["counts"]
    counts = stability["counts"]
    partial_horizon = horizon["branches"]["partial_revelation_benchmark"][
        "persistent_entry"
    ]["0.01"]["coefficient"]
    private_horizons = {
        horizon["branches"][branch]["persistent_entry"]["0.01"]["coefficient"]
        for branch in ("article_updater_H", "deposited_D")
    }
    if len(private_horizons) != 1:
        raise AssertionError("private-branch horizon mismatch")
    private_horizon = private_horizons.pop()
    checked = (
        pole_guard["deposited_sweep_cells_checked"]
        + pole_guard["prespecified_grid_cells_checked"]
    )
    write_table(
        "table3_stability_horizon",
        ["Diagnostic", "Exact/result", "Interpretation"],
        [
            [
                "Deposited sweep",
                f"{source_counts['UNSTABLE']}/100 unstable",
                r"$h=0.06,\ldots,0.44$",
            ],
            [
                "Prespecified variance grid",
                f"{counts['UNSTABLE']:,}/8,100 unstable",
                f"{counts['STABLE']:,} stable",
            ],
            [
                "Closest grid cell",
                f"$\\epsilon={closest['epsilon']['rational']}$",
                f"margin $1/{closest['epsilon']['denominator']}$",
            ],
            [
                r"Displayed $h=0.60$",
                f"$\\epsilon={displayed['epsilon']['rational']}$",
                "stable",
            ],
            [
                r"Benchmark 1\% persistent horizon",
                f"K={partial_horizon}",
                "partial coefficient error",
            ],
            [
                r"Private 1\% persistent horizon",
                f"K={private_horizon}",
                "both coefficient systems",
            ],
            [
                "Exact all-horizon partial-orbit check",
                f"{pole_guard['exact_finite_poles']} finite poles",
                f"{checked:,} prespecified cells",
            ],
            [
                "Exact boundary cells",
                str(counts["BOUNDARY"]),
                "no boundary value assigned to a class",
            ],
        ],
        r"@{}p{.32\textwidth}p{.31\textwidth}p{.27\textwidth}@{}",
    )
    rows = [
        [
            "Previously established results",
            "equilibrium equations; recurrence; authors' convergence boundary",
            "no novelty claim",
        ],
        [
            "Implementation consistency",
            "deposited-$D$ denominator; exact roots; market-clearing discrepancy",
            "not a general correction of the paper",
        ],
        [
            "Finite iteration",
            "prespecified counts, horizons, and pole margins",
            "no tuned thresholds or starts",
        ],
        [
            "Bounded source agreement",
            "MATLAB objects 10--11 and coefficients",
            "no independent objects 1--9 reproduction",
        ],
        [
            "Source distribution",
            "public citation and custody hashes; independent code",
            "no third-party source files redistributed",
        ],
    ]
    write_table(
        "table4_claim_boundary", ["Category", "Included", "Excluded"], rows, "lll"
    )
    lines = (
        [
            r"\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{.19\textwidth}XX@{}}",
            r"\toprule",
            r"Category & Included & Excluded \\",
            r"\midrule",
        ]
        + [" & ".join(row) + r" \\" for row in rows]
        + [r"\bottomrule", r"\end{tabularx}"]
    )
    (TAB / "table4_claim_boundary.tex").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main():
    figure1()
    figure2()
    figure3()
    figure4()
    tables()
    files = sorted(
        [
            p.relative_to(ROOT).as_posix()
            for p in list(FIG.glob("*")) + list(TAB.glob("*"))
        ]
    )
    print(
        json.dumps(
            {"status": "PASS", "figure_files": 8, "table_files": 8, "files": files},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
