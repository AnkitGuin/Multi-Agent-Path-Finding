"""Authentic-baseline provenance must survive platform line-ending changes."""
import hashlib
import json
from pathlib import Path


def test_vendored_pibt_matches_recorded_unmodified_upstream_files():
    directory = Path(__file__).resolve().parents[1]/"third_party/pypibt"
    manifest = json.loads((directory/"UPSTREAM.json").read_text())
    assert manifest["revision"] == "a3c97f60413c6619a29a5022969896bc54877edc"
    assert manifest["modifications"] == "none"
    for name, expected in manifest["files_lf_sha256"].items():
        assert hashlib.sha256((directory/name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected
    assert "Copyright 2023 Keisuke Okumura" in (directory/"LICENCE.txt").read_text()
