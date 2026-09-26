"""
scripts/fetch_c2c12.py OSF discovery and listing, against a fake OSF API.

The fake mirrors the layout seen on osf.io/ysaq2 (checked 2026-09-25):
project -> experiment components titled "090303-C2C12P15-FGF2,BMP2" ->
one component per sequence titled "exp1_F0001 Data", TIFFs loose in its
osfstorage root, plus annotation components with no TIFFs. No network.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "fetch_c2c12", os.path.join(os.path.dirname(__file__), "..", "scripts", "fetch_c2c12.py"))
fc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fc)

API = fc.OSF_API


def _node(nid, title):
    return {"id": nid, "attributes": {"title": title}}


def _provider(nid):
    return {"attributes": {"name": "osfstorage"},
            "relationships": {"files": {"links": {"related": {"href": f"{API}/nodes/{nid}/files/osfstorage/"}}}}}


def _file(name):
    return {"attributes": {"kind": "file", "name": name, "materialized_path": f"/{name}", "size": 10},
            "links": {"download": f"https://osf.io/download/{name}/"}}


def _fake_osf():
    children = {
        "root": [_node("e1", "090303-C2C12P15-FGF2,BMP2"), _node("e2", "090318-C2C12P7-FGF2,BMP2")],
        "e1": [_node("s11", "exp1_F0001 Data"), _node("s12", "exp1_F0002 Data"), _node("a1", "Annotation_Human")],
        "e2": [_node("s21", "exp1_F0001 Data")],
    }
    files = {
        "root": [_file("Download Instructions.txt")],
        "s11": [_file(f"exp1_F0001-{i:05d}.tif") for i in range(1, 4)],
        "s12": [_file(f"exp1_F0002-{i:05d}.tif") for i in range(1, 4)],
        "s21": [_file(f"exp1_F0001-{i:05d}.tif") for i in range(1, 4)],
        "a1": [_file("exp1_F0001.xml")],
    }

    def pages(url):
        path = url.removeprefix(f"{API}/nodes/")
        nid, rest = path.split("/", 1)
        if rest == "children/":
            return iter(children.get(nid, []))
        if rest == "files/":
            return iter([_provider(nid)])
        if rest.startswith("files/osfstorage/"):
            return iter(files.get(nid, []))
        raise AssertionError(url)

    return pages


def test_discover_finds_sequences_two_component_levels_down(tmp_path, monkeypatch):
    monkeypatch.setattr(fc, "_pages", _fake_osf())
    inv = fc.discover(str(tmp_path / "inv.json"), node="root")
    assert inv["mode"] == "tiff_folders"
    assert sorted(tf["path"] for tf in inv["tiff_folders"]) == [
        "/090303-C2C12P15-FGF2,BMP2/exp1_F0001 Data",
        "/090303-C2C12P15-FGF2,BMP2/exp1_F0002 Data",
        "/090318-C2C12P7-FGF2,BMP2/exp1_F0001 Data",
    ]
    seqs = fc._collect_sequences_from_inventory(inv)
    ids = sorted(f"c2c12_{s['experiment']}_{fc.slug(s['leaf'])}" for s in seqs)
    # the same sequence name in two experiments stays two sequences
    assert ids == ["c2c12_090303_exp1_F0001_Data", "c2c12_090303_exp1_F0002_Data", "c2c12_090318_exp1_F0001_Data"]
    assert {fc.parse_condition(s["leaf"]) for s in seqs} == {"unknown"}  # names don't state the condition


def test_list_full_sorts_by_name_and_relists_on_duplicates(monkeypatch):
    calls = []
    good = [_file("a-00001.tif"), _file("a-00002.tif")]
    bad = [_file("a-00001.tif"), _file("a-00001.tif")]

    def pages(url):
        calls.append(url)
        return iter(bad if len(calls) == 1 else good)

    monkeypatch.setattr(fc, "_pages", pages)
    assert [e["name"] for e in fc._list_full(f"{API}/nodes/s/files/osfstorage/")] == ["a-00001.tif", "a-00002.tif"]
    assert len(calls) == 2 and all(u.endswith("?sort=name") for u in calls)

    monkeypatch.setattr(fc, "_pages", lambda url: iter(bad))
    with pytest.raises(RuntimeError, match="duplicate"):
        fc._list_full(f"{API}/nodes/s/files/osfstorage/")
