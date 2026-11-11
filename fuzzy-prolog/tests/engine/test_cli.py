from __future__ import annotations

from pathlib import Path

import pytest

from fuzzyprolog.cli import main

from .conftest import FAMILLE


@pytest.fixture
def famille_file(tmp_path: Path) -> Path:
    path = tmp_path / "famille.pl"
    path.write_text(FAMILLE, encoding="utf-8")
    return path


def test_queries_from_the_command_line(
    capsys: pytest.CaptureFixture[str], famille_file: Path
) -> None:
    code = main([str(famille_file), "-q", "grand_parent(X, Y).", "-q", "fils(X, nobody)."])
    out = capsys.readouterr().out
    assert code == 0
    assert "X = ali, Y = youssef (1.00)" in out and "non." in out


def test_explain_limit_and_options(capsys: pytest.CaptureFixture[str], famille_file: Path) -> None:
    code = main(
        [
            str(famille_file),
            "-q",
            "ancetre(aicha, X).",
            "--max",
            "2",
            "--explain",
            "--tnorm",
            "product",
            "--lambda-cut",
            "0.1",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0 and "limite de 2" in out and "clause l." in out


def test_errors_give_exit_code_1(
    capsys: pytest.CaptureFixture[str], famille_file: Path, tmp_path: Path
) -> None:
    assert main([str(tmp_path / "absent.pl"), "-q", "a."]) == 1
    assert "introuvable" in capsys.readouterr().err
    assert main([str(famille_file), "-q", "inconnu(x)."]) == 1
    assert "Prédicat inconnu" in capsys.readouterr().err
    assert main([str(famille_file), "--no-prelude", "-q", "app(a, [a])."]) == 1
    assert "Prédicat inconnu" in capsys.readouterr().err
    bad = tmp_path / "bad.pl"
    bad.write_text("p(a) :- .", encoding="utf-8")
    assert main([str(bad), "-q", "p(a)."]) == 1


def test_repl(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], famille_file: Path
) -> None:
    lines = iter(["fils(X, ali).", "", "inconnu(a).", "halt."])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(lines))
    assert main([str(famille_file)]) == 0
    captured = capsys.readouterr()
    assert "X = mohamed (1.00)" in captured.out and "Prédicat inconnu" in captured.err
