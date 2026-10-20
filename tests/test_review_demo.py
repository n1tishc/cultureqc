import importlib.util
import json
from pathlib import Path

import jsonschema

from culture.records import verify_chain

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("site_build_data", ROOT / "site/assets/build_data.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def test_illustrative_review_is_reproducible_and_preserves_source(tmp_path):
    source = ROOT / "demo/examples/examples.json"
    before = source.read_bytes()
    examples = json.loads(before)
    records = examples["changes"] + [item["record"] for item in examples["examples"]]
    reading = next(item["record"] for item in examples["examples"] if item["id"] == "evican_ht29")
    demo = BUILD.build_review_demo(records, reading)
    assert demo == BUILD.build_review_demo(records, reading)
    assert source.read_bytes() == before
    shipped = json.loads((ROOT / "site/src/data.json").read_text())["examples"]
    assert shipped["review_demo"] == demo
    by_id = {item["id"]: item["record"] for item in shipped["items"] + shipped["changes"]}
    original = [by_id[identity] for identity in shipped["chain_order"]]
    assert [item["canonical"] for item in original] == [BUILD.canonical(record) for record in records]
    assert [item["record_hash"] for item in original] == [record["record_hash"] for record in records]
    event = json.loads(demo["record"]["canonical"])
    event["record_hash"] = demo["record"]["record_hash"]
    jsonschema.validate(event, json.loads((ROOT / "culture/schema.json").read_text()),
                        format_checker=jsonschema.FormatChecker())
    assert event["reviews_record_id"] == reading["record_id"]
    assert event["reviews_record_hash"] == reading["record_hash"]
    assert event["final_action"] == "human_review"
    assert event["host_signature_ref"] is None
    assert "Illustrative" in event["reviewer"]["name"]
    assert event["signature_meaning"] == "review"
    log = tmp_path / "extension.jsonl"
    log.write_text("".join(json.dumps(record) + "\n" for record in records + [event]))
    assert verify_chain(log, checkpoint=demo["checkpoint"]).ok


def test_current_and_historical_identities_are_distinct():
    from culture.records import SCHEMA_VERSION
    from culture.rules import RULES_VERSION

    data = json.loads((ROOT / "site/src/data.json").read_text())
    assert data["meta"]["schema"] == SCHEMA_VERSION
    assert data["meta"]["rules"] == RULES_VERSION
    for item in data["examples"]["items"]:
        record = json.loads(item["record"]["canonical"])
        assert record["schema_version"] == "0.4"
        assert record["decided_by"] == item["rules"] == "rules_v0.5"
