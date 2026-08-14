import json
from pathlib import Path

import pytest

from voice_capture.cloud_transcribe import DiarizedTranscript, SpeakerSegment, transcribe_meeting_cloud


def test_labeled_text_preserves_speakers_and_timestamps():
    result = DiarizedTranscript(
        text="Oi. Olá.",
        segments=[
            SpeakerSegment("Hellena", 1.2, 2.0, "Oi."),
            SpeakerSegment("A", 65.0, 66.0, "Olá."),
        ],
        raw={},
    )
    assert result.labeled_text() == "[00:01] Hellena: Oi.\n[01:05] A: Olá."


def test_requires_openai_key_before_reading_audio(tmp_path: Path):
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        transcribe_meeting_cloud(tmp_path / "reuniao.m4a", api_key="")

