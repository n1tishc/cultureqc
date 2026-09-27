"""B8 (cultureQC_upgrade_specv4.md §2B.7): every number in the README's
provenance table ("Results and where they come from") appears in the results
file that row cites, so the README cannot drift from the scripts' output."""

import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def provenance_rows() -> list[list[str]]:
    with open(os.path.join(REPO, "README.md")) as f:
        text = f.read()
    section = text.split("## Results and where they come from", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 4 and cells[0] not in ("Result", "---"):
            rows.append(cells)
    return rows


def test_table_is_there():
    rows = provenance_rows()
    assert len(rows) >= 10
    for result, number, provenance, source in rows:
        assert provenance and re.search(r"synthetic|real|simulated", provenance), result
        assert re.fullmatch(r"`results/[\w.]+`", source), source


def test_every_number_is_in_its_source():
    missing = []
    for result, number, _, source in provenance_rows():
        with open(os.path.join(REPO, source.strip("`"))) as f:
            src = f.read()
        for n in NUMBER.findall(number):
            if not re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", src):
                missing.append(f"{result}: {n} not in {source}")
    assert not missing, "\n".join(missing)
