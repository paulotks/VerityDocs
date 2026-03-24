from pathlib import Path

import pytest

from veritydocs.scaffold.generator import init_project


@pytest.fixture()
def sample_project(tmp_path: Path) -> Path:
    init_project(tmp_path, "Teste", "pt-BR", "software", [])
    return tmp_path
