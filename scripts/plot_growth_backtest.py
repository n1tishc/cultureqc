"""
V3 plot: predicted vs actual target crossing from A1's rows
(results/growth_backtest.csv; no refit). Target − 10 cut, held-out fleet.
50% is the only spec target the held-out sequences cross; 30% and 40% are
the added, not-in-spec targets.

Usage:
    python scripts/plot_growth_backtest.py
"""

from __future__ import annotations

import os

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    d = pd.read_csv(os.path.join(REPO, "results", "growth_backtest.csv"))
    d = d[(d.cut == "target-10") & (d.outcome == "predicted")]
    settings = [("with_repositioning", 1, "1 crop"), ("with_repositioning", 3, "3 crops"),
                ("without_repositioning", 1, "full frame (ceiling)")]
    cads = sorted(d.cadence_h.unique())
    fig, axes = plt.subplots(1, len(cads), figsize=(11, 4.5), sharex=True, sharey=True)
    markers = {30.0: "^", 40.0: "s", 50.0: "o"}
    colors = {"1 crop": "tab:blue", "3 crops": "tab:orange", "full frame (ceiling)": "tab:green"}
    for ax, cad in zip(axes, cads):
        for rep, nf, lab in settings:
            s = d[(d.cadence_h == cad) & (d.repositioning == rep) & (d.n_fov == nf)]
            for tgt, g in s.groupby("target_pct"):
                ax.errorbar(g.true_hours, g.predicted_hours,
                            yerr=[(g.predicted_hours - g.interval_lo).clip(lower=0).fillna(0),
                                  (g.interval_hi - g.predicted_hours).clip(lower=0).fillna(0)],
                            fmt=markers[tgt], color=colors[lab], ms=5 if tgt == 50 else 3.5,
                            alpha=1.0 if tgt == 50 else 0.45, elinewidth=0.6, capsize=0,
                            label=f"{lab}, {tgt:g}%{'' if tgt == 50 else ' (not in spec)'}")
        lim = [15, 115]
        ax.plot(lim, lim, "k-", lw=0.6)
        ax.fill_between(lim, [x - 12 for x in lim], [x + 12 for x in lim], color="grey", alpha=0.12, lw=0,
                        label="±12 h (V3 error limit)")
        ax.set(xlim=lim, ylim=lim, title=f"held-out, {cad:g} h cadence, target − 10 cut",
               xlabel="actual crossing (h, full-frame Cellpose-SAM)", ylabel="predicted crossing (h)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=4, fontsize=7)
    fig.tight_layout(rect=(0, 0.16, 1, 1))
    fig.savefig(os.path.join(REPO, "results", "growth_backtest_v3.png"), dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
