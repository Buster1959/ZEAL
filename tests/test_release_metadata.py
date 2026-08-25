"""Validate files required to package and publish ZEAL."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "custom_components" / "zeal" / "manifest.json"


def test_manifest_and_hacs_identity_are_consistent() -> None:
    """The Home Assistant and HACS manifests must describe the same integration."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))

    assert manifest["domain"] == "zeal"
    assert manifest["name"] == hacs["name"] == "ZEAL HVAC System"
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert manifest["integration_type"] == "helper"
    assert manifest["iot_class"] == "local_push"
    assert manifest["config_flow"] is True
    assert manifest["documentation"] == "https://github.com/Buster1959/ZEAL"
    assert manifest["issue_tracker"] == "https://github.com/Buster1959/ZEAL/issues"


def test_manifest_keys_use_hassfest_order() -> None:
    """Hassfest requires domain/name first and every remaining key sorted."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    keys = list(manifest)
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])


def test_hacs_and_hassfest_workflows_cover_release_events() -> None:
    """Both repository validators must run for changes and manual checks."""
    workflows = ROOT / ".github" / "workflows"
    hacs = (workflows / "hacs.yml").read_text(encoding="utf-8")
    hassfest = (workflows / "hassfest.yml").read_text(encoding="utf-8")

    for workflow in (hacs, hassfest):
        assert "push:" in workflow
        assert "pull_request:" in workflow
        assert "workflow_dispatch:" in workflow
        assert "actions/checkout@" in workflow
    assert "hacs/action@main" in hacs
    assert "category: integration" in hacs
    assert "home-assistant/actions/hassfest@master" in hassfest
