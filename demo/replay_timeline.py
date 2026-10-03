"""
demo/replay_timeline.py — the app's Flask Timeline tab (cultureQC_upgrade_specv4.md
§2B.3, B1). Reads the precomputed replays in demo/replays/*.json, written by
scripts/export_demo_replays.py from real held-out C2C12 sequences; never the
cache, never a model. Per visit: confluency with its FOV-noise band, the
per-visit anomaly flag, the quality gate (REIMAGE), and the passage forecast
once it has been made. No classifier (demoted, configs/qc.yaml), no SPC or
trend charts.
"""

from __future__ import annotations

import glob
import html
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from culture.profiles import get_profile
from culture.rules import RULES_VERSION
from demo.theme import ACCENT, BG_CARD, BORDER, TEXT_PRIMARY, TEXT_SECONDARY

REPLAY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "replays")
ORDER = ["normal_1", "normal_2", "contamination", "stall", "dimming"]
LABELS = {
    "normal_1": "Normal flask 1",
    "normal_2": "Normal flask 2",
    "contamination": "Contamination onset (exaggerated-scale stress test)",
    "stall": "Growth slowdown",
    "dimming": "Lamp dimming",
}
FLAG_COLOR = "#ef4444"
REIMAGE_COLOR = "#f59e0b"
ONSET_COLOR = "#a78bfa"
SETUP_PROFILE = "c2c12_ker2018"     # the replays' imaging setup (Ker et al. 2018); uncalibrated unless validated


def passage_note(flagged: bool) -> str:
    """Why a passage at the target would not be recommended on its own, under the current rules."""
    if not get_profile(SETUP_PROFILE).calibrated:
        return (f" **Passage goes to a person:** this imaging setup has no calibration profile, so under "
                f"{RULES_VERSION} a passage at the target is sent to human review, not recommended."
                + (" The anomaly check also flagged the visit this forecast was made at." if flagged else ""))
    if flagged:
        return (f" **Passage held:** the anomaly check flagged the visit this forecast was made at, so under "
                f"{RULES_VERSION} a passage is sent to human review, not recommended.")
    return ""


def load_replays(replay_dir: str = REPLAY_DIR) -> dict[str, dict]:
    docs = {}
    for path in glob.glob(os.path.join(replay_dir, "*.json")):
        with open(path) as f:
            doc = json.load(f)
        docs[doc["scenario"]] = doc
    return {k: docs[k] for k in ORDER if k in docs} | {k: v for k, v in docs.items() if k not in ORDER}


def choices(replays: dict[str, dict]) -> list[tuple[str, str]]:
    return [(LABELS.get(k, k), k) for k in replays]


def plot(doc: dict) -> "plt.Figure":
    plt.close("all")
    v = pd.DataFrame(doc["visits"])
    fc = doc["forecast"]
    fig, ax = plt.subplots(figsize=(9, 4.0), dpi=140)
    fig.patch.set_facecolor(BG_CARD)
    ax.set_facecolor(BG_CARD)

    ax.fill_between(v.hours, v.confluency_mean - v.noise_se, v.confluency_mean + v.noise_se, color=ACCENT,
                    alpha=0.18, linewidth=0, label="FOV sampling noise (±1 SE of 3 FOVs)")
    ax.plot(v.hours, v.confluency_mean, "-", color=ACCENT, linewidth=1.4, alpha=0.8)
    ok = v[v.quality_pass]
    ax.scatter(ok.hours, ok.confluency_mean, s=36, color=ACCENT, zorder=3, label="Visit (3 FOVs)")
    bad = v[~v.quality_pass]
    if len(bad):
        ax.scatter(bad.hours, bad.confluency_mean, marker="x", s=60, color=REIMAGE_COLOR, linewidth=1.8, zorder=4,
                   label="REIMAGE (quality gate fail; not in the trend)")
    flagged = v[v.anomaly_flag.fillna(False).astype(bool)]
    if len(flagged):
        ax.scatter(flagged.hours, flagged.confluency_mean, s=150, facecolor="none", edgecolor=FLAG_COLOR,
                   linewidth=1.6, zorder=5, label="Anomaly flag")

    if doc.get("fault"):
        ax.axvline(doc["fault"]["onset_hours"], color=ONSET_COLOR, linestyle="--", linewidth=1.1,
                   label=f"Simulated fault onset ({doc['fault']['onset_hours']:.0f} h)")

    ax.axhline(fc["target_pct"], color=TEXT_SECONDARY, linestyle=":", linewidth=1.0,
               label=f"Target {fc['target_pct']:.0f}%")
    if fc["status"] == "predicted":
        curve = fc["fit_curve"]
        ax.plot(curve["hours"], curve["mean"], "--", color=TEXT_PRIMARY, linewidth=1.0, alpha=0.7,
                label=f"Growth fit at {fc['made_at_hours']:.0f} h")
        if fc.get("interval_hours"):
            lo, hi = fc["interval_hours"]
            ax.axvspan(lo, hi, color=TEXT_PRIMARY, alpha=0.08, linewidth=0, label="Forecast 90% interval")
        ax.axvline(fc["t_star_hours"], color=TEXT_PRIMARY, linewidth=1.0, alpha=0.8)

    ax.set_xlabel("Hours since first visit", color=TEXT_SECONDARY)
    ax.set_ylabel("Confluency (%, Cellpose-SAM)", color=TEXT_SECONDARY)
    ax.set_ylim(0, max(100.0, float((v.confluency_mean + v.noise_se).max()) + 5))
    ax.tick_params(colors=TEXT_SECONDARY)
    for spine in ax.spines.values():
        spine.set_color(BORDER)
    ax.grid(True, color=BORDER, linewidth=0.6, alpha=0.6)
    leg = ax.legend(loc="upper left", fontsize=7, frameon=False)
    for t in leg.get_texts():
        t.set_color(TEXT_SECONDARY)
    fig.tight_layout()
    return fig


def forecast_text(doc: dict) -> str:
    fc, bt = doc["forecast"], doc["forecast"]["backtest"]
    backtest = (f"backtest: n = {bt['n_sequences']} sequences, {fc['target_pct']:.0f}% target; median absolute "
                f"error {bt['median_abs_error_h']:.1f} h, 90% interval covered the recorded crossing in "
                f"{bt['interval_covers']}; {bt['source']}")
    made_at = next((v for v in doc["visits"] if v["visit"] == fc.get("made_at_visit")), None)
    held = passage_note(made_at is not None and bool(made_at.get("anomaly_flag")))
    if fc["status"] == "suppressed_fault":
        return (f"**Passage forecast:** not shown. The growth fit made at {fc['made_at_hours']:.0f} h, after the "
                f"simulated fault's onset, is {fc['suppressed_reason']}, so no crossing time is given.{held} "
                f"({backtest})")
    if fc["status"] != "predicted":
        return f"**Passage forecast:** none for this flask. ({backtest})"
    lo_hi = (f", 90% interval {fc['interval_hours'][0]:.0f}–{fc['interval_hours'][1]:.0f} h"
             if fc.get("interval_hours") else ", no interval (too few bootstrap crossings)")
    text = (f"**Passage forecast** (made once, at the first visit reaching {fc['cut_pct']:.0f}%, "
            f"{fc['made_at_hours']:.0f} h): reaches {fc['target_pct']:.0f}% at {fc['t_star_hours']:.0f} h{lo_hi} "
            f"({backtest}).")
    if doc.get("recorded_crossing_hours") is not None:
        text += (f" Recorded full-frame crossing: {doc['recorded_crossing_hours']:.0f} h. "
                 f"{fc['target_pct']:.0f}% here is as Cellpose-SAM measures it, which reads about 8 pp low (V1).")
    if held:
        text += held + " The forecast is the growth fit only, not an action."
    return text


def summary_md(doc: dict) -> str:
    s = doc["summary"]
    lines = [f"**{html.escape(LABELS.get(doc['scenario'], doc['scenario']))}** · held-out sequence "
             f"`{doc['stream_id']}` · {s['n_visits']} visits, about every "
             f"{doc['replay_params']['mean_interval_hours']:.0f} h, {doc['replay_params']['n_fov']} FOVs each", "",
             doc["caption"], ""]
    lines += [f"- {n}" for n in doc["notes"]]
    if doc.get("fault"):
        flags = s["anomaly_flags_after_onset"]
        first = s["first_flag_after_onset_visit"]
        lines += ["", f"After onset: anomaly flag on {flags} of {s['n_post_onset_visits']} visits"
                  + (f" (first at post-onset visit {first})" if first else "")
                  + f"; REIMAGE on {s['reimage_after_onset']} of {s['n_post_onset_visits']}."]
    lines += ["", forecast_text(doc)]
    return "\n".join(lines)


def table(doc: dict) -> pd.DataFrame:
    rows = []
    for v in doc["visits"]:
        flag = v["anomaly_flag"]
        row = {
            "Visit": v["visit"] + 1,
            "Hours": f"{v['hours']:.1f}",
            "Confluency (%)": f"{v['confluency_mean']:.1f} ± {v['noise_se']:.1f}",
            "Quality gate": "pass" if v["quality_pass"] else "REIMAGE: " + ", ".join(v["quality_reasons"]),
            "Anomaly score / threshold": ("n/a" if v["anomaly_score"] is None
                                          else f"{v['anomaly_score']:.3f} / {v['anomaly_threshold']:.3f} "
                                               f"({v['anomaly_bin']}%)"),
            "Anomaly flag": "n/a" if flag is None else ("FLAG" if flag else "—"),
        }
        if doc.get("fault"):
            row["After onset"] = "yes" if v["post_onset"] else "no"
        rows.append(row)
    return pd.DataFrame(rows)


def table_html(doc: dict) -> str:
    """table() as an HTML table in the Detectability tab's style (Gradio's
    Dataframe ignores the dark theme)."""
    df = table(doc)
    head = "".join(f"<th>{html.escape(c)}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(x))}</td>" for x in row) + "</tr>"
                   for row in df.itertuples(index=False))
    return (f'<table class="detect-table replay-table"><thead><tr>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table>")


def render(scenario: str, replays: dict[str, dict] | None = None):
    replays = load_replays() if replays is None else replays
    doc = replays[scenario]
    return plot(doc), summary_md(doc), table_html(doc)
