from veritydocs.intake.classifier import classify_requirement
from veritydocs.intake.interview import is_complete
from veritydocs.intake.similarity import find_similar


def test_classifier_defaults_to_func():
    assert classify_requirement("enviar email ao concluir demanda") == "FUNC"


def test_similarity_detects_overlap():
    matches = find_similar("enviar email quando concluir", ["enviar email quando concluir tarefa"])
    assert matches


def test_interview_completeness():
    ok = is_complete(
        {
            "descricao": "x",
            "ator": "y",
            "regra": "z",
            "criterio_aceite": "a",
            "escopo": "MVP",
        }
    )
    assert ok
