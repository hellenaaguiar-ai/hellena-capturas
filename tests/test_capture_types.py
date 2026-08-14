from pathlib import Path

from voice_capture.capture_types import CAPTURE_BOOK, CAPTURE_IDEA, CAPTURE_REFLECTION, detect_capture_type


def test_detects_mobile_prefixes_ignoring_accents_and_separators():
    assert detect_capture_type(Path("IDEIA__2026-08-12_15-30.m4a")) == CAPTURE_IDEA
    assert detect_capture_type(Path("Reflexão - 2026-08-12 15-31.m4a")) == CAPTURE_REFLECTION
    assert detect_capture_type(Path("PENSAMENTOS E REFLEXÕES__2026-08-12.m4a")) == CAPTURE_REFLECTION
    assert detect_capture_type(Path("Insight de livro__2026-08-12.m4a")) == CAPTURE_BOOK
    assert detect_capture_type(Path("Insights de livro - 2026-08-12.m4a")) == CAPTURE_BOOK
    assert detect_capture_type(Path("LIVRO - 2026-08-12.m4a")) == CAPTURE_BOOK
    assert detect_capture_type(Path("Captura de pensamento - 2026-08-12.m4a")) == CAPTURE_REFLECTION


def test_legacy_filename_remains_idea():
    assert detect_capture_type(Path("Gravação de Áudio 2026-08-12 às 02.05.24.m4a")) == CAPTURE_IDEA
