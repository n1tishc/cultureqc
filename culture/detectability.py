"""
Detectability matrix (cultureQC_upgrade_specv4.md §2B.5, B4): what cultureQC
can and cannot detect at the tested imaging setup, each row backed by a
Phase A check or marked "not tested". The content lives in
configs/detectability.yaml; this module loads it, hashes it for records, and
renders it for the app.
"""

from __future__ import annotations

import html
import os

import yaml

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "configs", "detectability.yaml")
COLUMNS = [("issue", "Issue"), ("detectable_here", "Detectable here?"), ("evidence", "Evidence"),
           ("confirm_with", "Confirm with")]


def load(path: str = DEFAULT_PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def config_hash(path: str = DEFAULT_PATH) -> str:
    """SHA-256 of the file's raw bytes, for records' config_hashes (same
    convention as quality.config_hash())."""
    from culture.records import hash_file
    return hash_file(path)


def to_html(matrix: dict | None = None, path: str = DEFAULT_PATH) -> str:
    m = load(path) if matrix is None else matrix
    head = "".join(f"<th>{label}</th>" for _, label in COLUMNS)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(r[k]))}</td>" for k, _ in COLUMNS) + "</tr>"
                   for r in m["rows"])
    return (f'<table class="detect-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
            f'<p class="detect-note"><b>Tested setup:</b> {html.escape(m["tested_setup"])}</p>'
            f'<p class="detect-note"><b>Provenance:</b> {html.escape(m["provenance_note"])}</p>'
            f'<p class="detect-note detect-hash">configs/detectability.yaml · SHA-256 '
            f'{config_hash(path)[:16]}… (recorded in every analysis record)</p>')
