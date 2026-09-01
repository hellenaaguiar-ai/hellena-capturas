import json
from pathlib import Path

from voice_capture.cloud_transcribe import DiarizedTranscript, SpeakerSegment
from voice_capture.config import Config
from voice_capture.desktop_ai import ProcessedMeeting
from voice_capture.meeting_pipeline import (
    _align_local_words,
    _needs_portuguese_retranscription,
    parse_mobile_meeting_date,
    process_mobile_meeting,
)
from voice_capture.state import StateStore
from voice_capture.transcribe import TimedTranscriptResult, TimedWord


def _config(tmp_path: Path) -> Config:
    vault = tmp_path / "vault"
    return Config(
        inbox_dir=tmp_path / "VoiceCaptures" / "Inbox",
        vault_inbox_dir=vault / "Inbox" / "Voz",
        data_dir=tmp_path / "data",
        whisper_model="small",
        whisper_language="pt",
        extraction_model="gpt-test",
        openai_api_key="openai-test",
        audio_retention_days=30,
        vault_meeting_dir=vault / "Reuniões",
        vault_therapy_dir=vault / "Terapia",
        vault_class_dir=vault / "Aulas",
        vault_reflection_dir=vault / "Reflexões",
        meeting_inbox_dir=tmp_path / "VoiceCaptures" / "Reuniões",
        speaker_reference_path=tmp_path / "Hellena.m4a",
    )


def test_parses_shortcut_date_format(tmp_path: Path):
    path = tmp_path / "REUNIÃO - Eduarda Bochi- 14_08_2026, 12_00.m4a"
    path.write_bytes(b"audio")
    date = parse_mobile_meeting_date(path)
    assert (date.year, date.month, date.day, date.hour, date.minute) == (2026, 8, 14, 12, 0)


def test_detects_excessive_english_in_portuguese_meeting():
    bad = " ".join(["the team will have to make this work"] * 8)
    good = "A equipe vai organizar o trabalho e revisar as decisões da reunião."

    assert _needs_portuguese_retranscription(bad) is True
    assert _needs_portuguese_retranscription(good) is False


def test_aligns_local_portuguese_words_to_cloud_speakers_and_normalizes_hellena():
    diarized = DiarizedTranscript(
        "english text",
        [
            SpeakerSegment("A", 0, 2, "english"),
            SpeakerSegment("B", 2, 4, "text"),
        ],
        {},
    )
    local = TimedTranscriptResult(
        words=[
            TimedWord(0.2, 0.6, " Olá"),
            TimedWord(0.7, 1.1, ", Helena"),
            TimedWord(2.2, 2.6, " Tudo"),
            TimedWord(2.7, 3.1, " bem?"),
        ],
        language="pt",
        duration_seconds=4,
    )

    result = _align_local_words(diarized, local)

    assert [segment.speaker for segment in result.segments] == ["A", "B"]
    assert [segment.text for segment in result.segments] == ["Olá, Hellena", "Tudo bem?"]
    assert result.raw["source"] == "local-portuguese-aligned-to-cloud-diarization"


def test_processes_mobile_meeting_with_diarization_and_preserves_raw(tmp_path: Path):
    config = _config(tmp_path)
    config.ensure_dirs()
    config.speaker_reference_path.write_bytes(b"voice")
    audio = config.resolved_meeting_inbox_dir / "REUNIÃO - Eduarda- 14_08_2026, 12_00.m4a"
    audio.write_bytes(b"meeting audio")
    calls = []

    def fake_cloud(path, **kwargs):
        calls.append((path, kwargs))
        return DiarizedTranscript(
            "Bom dia. Oi.",
            [
                SpeakerSegment("Hellena", 0, 1, "Bom dia."),
                SpeakerSegment("A", 1, 2, "Oi."),
            ],
            {"text": "Bom dia. Oi.", "segments": [
                {"speaker": "Hellena", "start": 0, "end": 1, "text": "Bom dia."},
                {"speaker": "A", "start": 1, "end": 2, "text": "Oi."},
            ]},
        )

    def fake_process(text, api_key, model):
        assert "Hellena: Bom dia." in text
        assert "A: Oi." in text
        return ProcessedMeeting(title="Reunião com Eduarda", summary="Conversa inicial.")

    state = StateStore(config.state_file)
    assert process_mobile_meeting(audio, config, state, fake_cloud, fake_process) == "done"
    assert calls[0][1]["known_speaker_name"] == "Hellena"
    assert calls[0][1]["speaker_reference_path"] == config.speaker_reference_path
    item = next(iter(state.all_items().values()))
    assert Path(item.audio_archive_path).exists()
    assert Path(item.transcript_raw_path).read_text(encoding="utf-8").startswith("[00:00] Hellena")
    json_path = Path(item.transcript_raw_path).with_suffix(".diarized.json")
    assert json.loads(json_path.read_text(encoding="utf-8"))["segments"][1]["speaker"] == "A"
    note = Path(item.note_path).read_text(encoding="utf-8")
    assert "source: mobile-meeting" in note
    assert "## Transcrição por falante" in note


def test_retry_reuses_cloud_transcript(tmp_path: Path):
    config = _config(tmp_path)
    config.ensure_dirs()
    audio = config.resolved_meeting_inbox_dir / "REUNIÃO - Teste- 14_08_2026, 12_00.m4a"
    audio.write_bytes(b"meeting audio")
    cloud_calls = 0

    def fake_cloud(path, **kwargs):
        nonlocal cloud_calls
        cloud_calls += 1
        return DiarizedTranscript("Oi", [SpeakerSegment("A", 0, 1, "Oi")], {
            "text": "Oi", "segments": [{"speaker": "A", "start": 0, "end": 1, "text": "Oi"}]
        })

    process_calls = 0

    def flaky_process(text, api_key, model):
        nonlocal process_calls
        process_calls += 1
        if process_calls == 1:
            raise RuntimeError("temporary")
        return ProcessedMeeting(title="Teste", summary="Ok")

    state = StateStore(config.state_file)
    assert process_mobile_meeting(audio, config, state, fake_cloud, flaky_process) == "error"
    assert process_mobile_meeting(audio, config, state, fake_cloud, flaky_process) == "done"
    assert cloud_calls == 1


def test_token_limited_summary_falls_back_to_complete_transcript_note(tmp_path: Path):
    config = _config(tmp_path)
    config.ensure_dirs()
    audio = config.resolved_meeting_inbox_dir / "REUNIÃO - Renato Mussa- 17_08_2026, 12_00.m4a"
    audio.write_bytes(b"meeting audio")

    def fake_cloud(path, **kwargs):
        return DiarizedTranscript(
            "Oi",
            [SpeakerSegment("Hellena", 0, 1, "Oi")],
            {"text": "Oi", "segments": [{"speaker": "Hellena", "start": 0, "end": 1, "text": "Oi"}]},
        )

    def token_limited_process(text, api_key, model):
        raise RuntimeError(
            "Resposta da OpenAI interrompida pelo limite de tokens; "
            "a captura nao sera salva como se estivesse completa."
        )

    state = StateStore(config.state_file)
    result = process_mobile_meeting(audio, config, state, fake_cloud, token_limited_process)

    assert result == "done"
    item = next(iter(state.all_items().values()))
    note = Path(item.note_path).read_text(encoding="utf-8")
    assert "# Reunião com Renato Mussa" in note
    assert "## Transcrição por falante\n[00:00] Hellena: Oi" in note
    assert "nenhum conteúdo foi inferido" in note


def test_force_reprocess_replaces_completed_note_without_duplicate(tmp_path: Path):
    config = _config(tmp_path)
    config.ensure_dirs()
    audio = config.resolved_meeting_inbox_dir / "REUNIÃO - Renato Mussa- 17_08_2026, 12_00.m4a"
    audio.write_bytes(b"meeting audio")
    cloud_calls = 0

    def fake_cloud(path, **kwargs):
        nonlocal cloud_calls
        cloud_calls += 1
        return DiarizedTranscript(
            "Oi",
            [SpeakerSegment("Hellena", 0, 1, "Oi")],
            {"text": "Oi", "segments": [{"speaker": "Hellena", "start": 0, "end": 1, "text": "Oi"}]},
        )

    summaries = iter(["Resumo incompleto.", "Resumo completo."])

    def fake_process(text, api_key, model):
        return ProcessedMeeting(title="Reunião com Renato Mussa", summary=next(summaries))

    state = StateStore(config.state_file)
    assert process_mobile_meeting(audio, config, state, fake_cloud, fake_process) == "done"
    first_item = next(iter(state.all_items().values()))
    first_path = Path(first_item.note_path)
    assert "Resumo incompleto." in first_path.read_text(encoding="utf-8")

    assert process_mobile_meeting(audio, config, state, fake_cloud, fake_process, force=True) == "done"
    second_item = next(iter(state.all_items().values()))

    assert Path(second_item.note_path) == first_path
    assert "Resumo completo." in first_path.read_text(encoding="utf-8")
    assert len(list(config.vault_meeting_dir.glob("*.md"))) == 1
    assert cloud_calls == 1
