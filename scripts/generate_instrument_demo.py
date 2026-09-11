"""Regenerate the recorded Huh7 viewer from actual model outputs.

Run from the repository root with .venv/bin/python scripts/generate_instrument_demo.py.
This takes several minutes on CPU; it never edits the original sample audit chain.
"""
import base64
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import torch
    from culture.pipeline import analyze
    from culture.records import _canonical_json
    torch.set_num_threads(2)
    details = {}
    source = ROOT / 'site/assets/pipeline-output/Huh7_contaminated_field.png'
    with tempfile.TemporaryDirectory() as temp:
        record = analyze(str(source), cell_line='Huh7', image_ref=source.name,
                         log_path=str(Path(temp) / 'events.jsonl'), details=details)
    target = ROOT / 'site/public/instrument'
    target.mkdir(parents=True, exist_ok=True)
    visuals = {}
    for key, uri in details['visuals'].items():
        (target / f'{key}.png').write_bytes(base64.b64decode(uri.split(',')[1]))
        visuals[key] = f'/instrument/{key}.png'
    payload = dict(visuals=visuals, record=record, confluency_pct=record['confluency_pct'],
                   record_canonical=_canonical_json({k:v for k,v in record.items() if k != 'record_hash'}))
    (target / 'demo.json').write_text(json.dumps(payload))
    print('Saved actual Huh7 inference artifacts and a new standalone record.')


if __name__ == '__main__':
    main()
