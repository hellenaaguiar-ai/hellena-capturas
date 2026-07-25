from datetime import datetime

from voice_capture.markdown_writer import NoteMeta, build_filename, build_markdown, slugify, write_note_atomic
from voice_capture.process_ai import ProcessedCapture


def make_processed(**overrides):
    base = dict(
        title="Vigilância romantizada como cuidado",
        synthesis="A pessoa observa que o personagem interpreta controle como cuidado.",
        cleaned_transcript="Esse personagem interpreta o controle do marido como cuidado.",
        entities=["marido"],
        evidence_and_connections=["Pode se conectar a discussões sobre vigilância romantizada."],
        open_questions=[],
        possible_uses=["Second Brain"],
        classification="reflexao-livro",
        confidence="media",
        related_topics=["vigilância", "cuidado"],
        uncertainty_notes="",
    )
    base.update(overrides)
    return ProcessedCapture(**base)


def make_meta():
    return NoteMeta(
        content_hash="a" * 64,
        created_at=datetime(2026, 7, 23, 22, 20),
        recorded_at=datetime(2026, 7, 23, 22, 14),
        audio_archive_path="data/audio_archive/aaaa.m4a",
        transcription_model="faster-whisper-small",
        processing_model="claude-sonnet-5",
    )


def test_slugify_removes_punctuation_keeps_spaces_and_accents():
    assert slugify("Vigilância é cuidado?!") == "Vigilância é cuidado"


def test_slugify_never_uses_hyphens():
    assert "-" not in slugify("Uma reflexão sobre livros e trauma")


def test_slugify_cuts_on_word_boundary():
    long_title = "Romances personagens que se exercitam apos trauma e minha interpretacao"
    result = slugify(long_title, max_len=40)
    assert len(result) <= 40
    assert all(word in long_title.split() for word in result.split())


def test_build_filename_uses_recorded_at_and_slug():
    filename = build_filename(datetime(2026, 7, 23, 22, 14), "Vigilância romantizada")
    assert filename == "2026-07-23 2214 - Vigilância romantizada.md"


def test_build_markdown_contains_frontmatter_and_sections():
    md = build_markdown(make_processed(), "transcricao bruta original", make_meta())

    assert "type: voice-capture" in md
    assert "confidence: média" in md
    assert "needs_review: false" in md
    assert "## Síntese" in md
    assert "## Transcrição limpa" in md
    assert "## Transcrição bruta" in md
    assert "transcricao bruta original" in md
    assert "- [x] Second Brain" in md
    assert "- [ ] Investigação" in md


def test_low_confidence_sets_needs_review_and_uncertainty_block():
    processed = make_processed(confidence="baixa", uncertainty_notes="Não ficou claro o contexto.")
    md = build_markdown(processed, "raw", make_meta())
    assert "needs_review: true" in md
    assert "⚠️ Não ficou claro o contexto." in md


def test_write_note_atomic_avoids_overwriting_existing_file(tmp_path):
    path1 = write_note_atomic(tmp_path, "nota.md", "conteudo 1")
    path2 = write_note_atomic(tmp_path, "nota.md", "conteudo 2")

    assert path1 != path2
    assert path1.read_text(encoding="utf-8") == "conteudo 1"
    assert path2.read_text(encoding="utf-8") == "conteudo 2"
    assert path2.name == "nota-2.md"
