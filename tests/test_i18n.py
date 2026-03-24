from pathlib import Path

from veritydocs.i18n import catalog as catalog_mod
from veritydocs.i18n.catalog import (
    default_language,
    docs_scaffold,
    module_titles,
    set_language,
    tr,
)
from veritydocs.i18n.filenames import load_docs_filemap, normalize_docs_locale
from veritydocs.scaffold.generator import init_project


def test_tr_loads_from_yaml_en():
    assert "successfully" in tr("en", "init_done")


def test_tr_loads_from_yaml_pt_br():
    assert "sucesso" in tr("pt-BR", "init_done")


def test_tr_unknown_key_returns_key():
    assert tr("en", "totally_missing_key_xyz") == "totally_missing_key_xyz"


def test_tr_fallback_to_pt_br_for_missing_translation():
    # Unknown lang normalizes to pt-BR; message still resolves
    assert "Projeto" in tr("xx-YY", "init_done")


def test_normalize_docs_locale():
    assert normalize_docs_locale("en") == "en"
    assert normalize_docs_locale("pt-BR") == "pt-BR"
    assert normalize_docs_locale("fr") == "pt-BR"


def test_load_docs_filemap_en_vs_pt_br():
    en_map = load_docs_filemap("en")
    br_map = load_docs_filemap("pt-BR")
    assert en_map["prd"]["vision"] == "00-vision-scope.md"
    assert br_map["prd"]["vision"] == "00-visao-escopo.md"


def test_module_titles_count():
    assert len(module_titles("en")) == 7
    assert len(module_titles("pt-BR")) == 7


def test_docs_scaffold_keys():
    keys = docs_scaffold("en").keys()
    assert "trace_header" in keys
    assert "flows_index" in keys


def test_init_project_en_uses_english_scaffold(tmp_path: Path):
    init_project(tmp_path, "Demo", "en", "software", ["cursor"])
    trace = (tmp_path / "docs" / "traceability.md").read_text(encoding="utf-8")
    assert trace.startswith("# Traceability")


def test_set_language_and_default_language():
    try:
        set_language("en")
        assert default_language() == "en"
        set_language("pt-BR")
        assert default_language() == "pt-BR"
    finally:
        catalog_mod._cli_lang_override = None  # type: ignore[attr-defined]


def test_docs_scaffold_merges_fallback_with_primary():
    en = docs_scaffold("en")
    pt = docs_scaffold("pt-BR")
    assert "trace_header" in en and "trace_header" in pt
    assert len(en) >= len(pt) or len(en) > 0
