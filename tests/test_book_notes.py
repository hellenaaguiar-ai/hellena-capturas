from datetime import datetime

import pytest

from voice_capture.book_notes import AmbiguousBookNoteError, append_spoken_capture, find_book_note


def test_appends_literal_transcript_and_preserves_highlights(tmp_path):
    books = tmp_path / "📚 Livros"
    books.mkdir()
    note = books / "A Empregada - Freida McFadden.md"
    note.write_text(
        '---\ntype: book\ntitle: "A Empregada"\n---\n\n# A Empregada\n\n'
        '## Destaques\n\n> "um grifo"\n\n## Insights\n\n_Ainda não há reflexões gravadas._\n',
        encoding="utf-8",
    )

    result = append_spoken_capture(
        books,
        "A Empregada",
        "Eu fiquei com raiva dessa cena, mas ainda não sei explicar por quê.",
        datetime(2026, 8, 12, 16, 30),
    )

    content = result.read_text(encoding="utf-8")
    assert '> "um grifo"' in content
    assert "Eu fiquei com raiva dessa cena, mas ainda não sei explicar por quê." in content
    assert "_Ainda não há reflexões gravadas._" not in content
    assert "Síntese" not in content


def test_creates_minimal_book_note_without_empty_fields(tmp_path):
    books = tmp_path / "📚 Livros"

    note = append_spoken_capture(
        books,
        "O Livro Exato",
        "Minha fala original.",
        datetime(2026, 8, 12, 16, 30),
    )

    content = note.read_text(encoding="utf-8")
    assert note.name == "O Livro Exato.md"
    assert 'title: "O Livro Exato"' in content
    assert "Minha fala original." in content
    assert "author:" not in content
    assert "Destaques" not in content


def test_ambiguous_existing_notes_are_not_selected(tmp_path):
    books = tmp_path / "📚 Livros"
    books.mkdir()
    (books / "Livro - Autora A.md").write_text("# Livro\n", encoding="utf-8")
    nested = books / "Livro - Autora B"
    nested.mkdir()
    (nested / "Livro - Autora B.md").write_text("# Livro\n", encoding="utf-8")

    with pytest.raises(AmbiguousBookNoteError):
        find_book_note(books, "Livro")
