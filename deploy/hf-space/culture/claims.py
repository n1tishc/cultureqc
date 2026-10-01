"""
Claims policy checker (cultureQC_upgrade_specv4.md §12, incl. the v3.2
additions). tests/test_claims.py runs it over everything a viewer reads:
README, the app's UI strings, the rationale templates, the detectability
matrix, and the demo JSONs.

Three rule kinds:
  forbid          the phrase may not appear at all
  unless_negated  allowed only when negated just before it ("cannot detect
                  mycoplasma", "not Part 11 compliant")
  needs_context   allowed only with a qualifier nearby (98% needs "synthetic",
                  a passage-prediction number needs "n = 5")

Not automatable, checked by hand at freeze: presenting precomputed outputs as
live; implying BioFlow lacks audit trails in paraphrase.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

NEGATION = re.compile(r"\b(not|no|never|cannot|can't|can not|doesn't|does not|isn't|is not|aren't|without|nor)\b",
                      re.I)
NEGATION_LOOKBACK = 45
CONTEXT_WINDOW = 200


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: str
    kind: str                  # forbid | unless_negated | needs_context
    context: str | None = None


RULES = [
    Rule("mycoplasma status", r"mycoplasma[- ](detected|positive|negative|free)", "forbid"),
    Rule("mycoplasma detection", r"\b(detects?|detected|detecting|identif(?:y|ies|ied)|confirms?|confirmed)\b"
         r"[^.\n]{0,30}\bmycoplasma", "unless_negated"),
    Rule("mycoplasma risk", r"mycoplasma[- ]risk", "forbid"),
    Rule("real-time contamination", r"\b(real[- ]?time|live)\b[^.\n]{0,20}\bcontamination", "unless_negated"),
    Rule("replaces testing", r"\breplac\w*\b[^.\n]{0,40}\b(sterility|pcr|compendial)", "unless_negated"),
    Rule("compliance claim", r"part\s*11[- ]compliant|\bgmp[- ]validated", "unless_negated"),
    Rule("vendor integration", r"\bintegrat\w*\b[^.\n]{0,25}\b(bioflow|momentum|green button go|robocell)",
         "unless_negated"),
    Rule("vendor lacks audit", r"\b(bioflow|celltrio)\b[^.\n]{0,30}\b(lacks?|has no|have no)\b[^.\n]{0,20}audit",
         "forbid"),
    Rule("synthetic headline", r"\b98\s?%|\b2\.34\s?pp", "needs_context", r"synthetic"),
    Rule("fault number provenance", r"\b(AUROC|recall|detection rate)\b[^.\n]{0,40}\d", "needs_context",
         r"simulated|synthetic"),
    Rule("stall or drift detection", r"\b(detects?|detected|detecting|flags?|catch(?:es)?|catching)\b[^.\n]{0,30}"
         r"\b(growth stalls?|stalls?|slowdowns?|instrument drift)\b", "unless_negated"),
    Rule("trend monitoring", r"\b(monitor\w*|trend\w*|track\w*)\b[^.\n]{0,20}\b(anomaly scores?|class probabilit\w*)",
         "unless_negated"),
    Rule("passage number", r"\b(passage|time to target|target crossing|crossing)\b[^.\n]{0,80}\b\d+(\.\d+)?\s?h\b",
         "needs_context", r"n\s?=\s?5"),
    Rule("quarantine decision", r"\bquarantine", "forbid"),
    Rule("latency claim", r"\b\d+(\.\d+)?\s?(s|sec|seconds|min|minutes?)\b[^.\n]{0,30}\bper (image|visit|fov|frame)\b"
         r"|\b(a|one) minute per (image|visit|frame)", "needs_context", r"V9|live_latency"),
    Rule("cell doubling time", r"cell doubling time", "unless_negated"),
    # rules_v0.4 renamed the action hold -> continue; "passage held" stays. A quoted `hold` is allowed
    # only where the rename is explained (continue nearby).
    Rule("hold as an action", r"[\"'`]hold[\"'`]|\b(recommends?|recommended|action is|rules say|rules return)\s+\**hold\b",
         "needs_context", r"\bcontinue\b"),
    # The confluency score tracks density, not the reading's error (results/confidence_vs_error.md).
    Rule("confluency score as probability",
         r"\b(confluency|measurement|reading)\s+confidence\b[^.\n]{0,40}\b(probabilit\w*|calibrat\w*)"
         r"|\b(probabilit\w*|calibrated)\b[^.\n]{0,20}\b(confluency|measurement|reading)\s+confidence\b"
         r"|\bconfidence\b[^.\n]{0,15}\bthat the (reading|confluency|number) is (right|correct)", "forbid"),
    # A bare hash chain misses a full rewrite and a deleted tail (docs/audit_mapping.md, "The chain").
    Rule("chain overclaim", r"\bbreaks?\b[^.\n]{0,25}\bevery\b[^.\n]{0,15}\blinks?\b|tamper[- ]?proof", "forbid"),
]


def violations(text: str, source: str = "") -> list[str]:
    out = []
    for rule in RULES:
        for m in re.finditer(rule.pattern, text, re.I):
            if rule.kind == "unless_negated":
                if NEGATION.search(text[max(0, m.start() - NEGATION_LOOKBACK):m.start()]):
                    continue
            elif rule.kind == "needs_context":
                window = text[max(0, m.start() - CONTEXT_WINDOW):m.end() + CONTEXT_WINDOW]
                if re.search(rule.context, window, re.I):
                    continue
            line = text.count("\n", 0, m.start()) + 1
            out.append(f"{source}:{line}: [{rule.name}] {m.group(0)!r}")
    return out


def python_strings(path: str) -> str:
    """Every string literal in a module (UI text, templates, f-string parts),
    one per line, without comments or identifiers."""
    with open(path) as f:
        tree = ast.parse(f.read())
    return "\n".join(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str))
