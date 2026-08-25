"""Validate the shipped Home Assistant config-flow translations."""

from __future__ import annotations

import json
from pathlib import Path


TRANSLATIONS = Path(__file__).parents[1] / "custom_components" / "zeal" / "translations"
STRINGS = TRANSLATIONS.parent / "strings.json"
EXPECTED_LANGUAGES = {"da", "de", "en", "es", "fi", "fr", "it", "nb", "nl", "sv"}


def _leaf_paths(value: object, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    """Return every scalar JSON path below a nested object."""
    if isinstance(value, dict):
        paths: set[tuple[str, ...]] = set()
        for key, child in value.items():
            paths.update(_leaf_paths(child, (*prefix, key)))
        return paths
    return {prefix}


def test_translations_match_english_schema_and_are_nonempty() -> None:
    """Every supported language must contain the complete English schema."""
    language_files = {path.stem: path for path in TRANSLATIONS.glob("*.json")}
    assert set(language_files) == EXPECTED_LANGUAGES

    english = json.loads(language_files["en"].read_text(encoding="utf-8"))
    assert json.loads(STRINGS.read_text(encoding="utf-8")) == english
    expected_paths = _leaf_paths(english)

    for language, path in sorted(language_files.items()):
        translated = json.loads(path.read_text(encoding="utf-8"))
        assert _leaf_paths(translated) == expected_paths, language

        for leaf_path in expected_paths:
            value: object = translated
            for key in leaf_path:
                assert isinstance(value, dict)
                value = value[key]
            assert isinstance(value, str) and value.strip(), (language, leaf_path)
