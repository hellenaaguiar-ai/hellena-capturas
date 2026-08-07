"""Monta o Markdown das notas de reuniao, terapia e aula (modos desktop)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .desktop_ai import ProcessedClass, ProcessedMeeting, ProcessedTherapy
from .markdown_writer import CONFIDENCE_DISPLAY, build_filename  # reaproveita slugify/nome de arquivo


@dataclass
class DesktopNoteMeta:
    content_hash: str
    created_at: datetime
    recorded_at: datetime
    mic_audio_path: Optional[str]
    system_audio_path: Optional[str]
    transcription_model: str
    processing_model: str


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items) or "_Nenhum(a)._"


def _checklist_todo(items: list[str]) -> str:
    return "\n".join(f"- [ ] {i}" for i in items) or "_Nenhum item._"


def build_meeting_markdown(processed: ProcessedMeeting, mic_text: str, system_text: str, meta: DesktopNoteMeta) -> str:
    confidence_key = processed.confidence if processed.confidence in CONFIDENCE_DISPLAY else "baixa"
    needs_review = confidence_key == "baixa"

    frontmatter = "\n".join(
        [
            "---",
            "type: meeting-capture",
            f"id: {meta.content_hash[:16]}",
            f"created_at: {meta.created_at.isoformat()}",
            f"recorded_at: {meta.recorded_at.isoformat()}",
            "source: desktop-voice",
            "processing_status: done",
            f"confidence: {CONFIDENCE_DISPLAY[confidence_key]}",
            f"needs_review: {'true' if needs_review else 'false'}",
            f"participants: {_yaml_list(processed.participants)}",
            f"people_mentioned: {_yaml_list(processed.people_mentioned)}",
            f"audio_file_mic: {meta.mic_audio_path}",
            f"audio_file_system: {meta.system_audio_path or ''}",
            f"transcription_model: {meta.transcription_model}",
            f"processing_model: {meta.processing_model}",
            "---",
        ]
    )

    uncertainty_block = f"\n> ⚠️ {processed.uncertainty_notes}\n" if processed.uncertainty_notes else ""

    body = f"""
# {processed.title}
{uncertainty_block}
## Resumo
{processed.summary}

## Decisões
{_bullets(processed.decisions)}

## Itens de ação
{_checklist_todo(processed.action_items)}

## Perguntas em aberto
{_bullets(processed.open_questions)}

## Pessoas citadas (não participantes da chamada)
{_bullets(processed.people_mentioned)}

## Transcrição — você (microfone)
{mic_text or "_Sem áudio de microfone._"}

## Transcrição — outros participantes (áudio do sistema)
{system_text or "_Sem áudio do sistema capturado._"}
"""
    return frontmatter + "\n" + body.strip() + "\n"


def build_therapy_markdown(processed: ProcessedTherapy, mic_text: str, system_text: str, meta: DesktopNoteMeta) -> str:
    confidence_key = processed.confidence if processed.confidence in CONFIDENCE_DISPLAY else "baixa"
    needs_review = confidence_key == "baixa"

    frontmatter = "\n".join(
        [
            "---",
            "type: therapy-capture",
            f"id: {meta.content_hash[:16]}",
            f"created_at: {meta.created_at.isoformat()}",
            f"recorded_at: {meta.recorded_at.isoformat()}",
            "source: desktop-voice",
            "processing_status: done",
            f"confidence: {CONFIDENCE_DISPLAY[confidence_key]}",
            f"needs_review: {'true' if needs_review else 'false'}",
            f"themes: {_yaml_list(processed.themes)}",
            f"audio_file_mic: {meta.mic_audio_path}",
            f"audio_file_system: {meta.system_audio_path or ''}",
            f"transcription_model: {meta.transcription_model}",
            f"processing_model: {meta.processing_model}",
            "---",
        ]
    )

    uncertainty_block = f"\n> ⚠️ {processed.uncertainty_notes}\n" if processed.uncertainty_notes else ""

    body = f"""
# {processed.title}
{uncertainty_block}
## Síntese da sessão
{processed.session_summary}

## Temas abordados
{_bullets(processed.themes)}

## Percepções expressas na sessão
{_bullets(processed.insights)}

## Encaminhamentos
{_checklist_todo(processed.follow_ups)}

## Transcrição — você (microfone)
{mic_text or "_Sem áudio de microfone._"}

## Transcrição — terapeuta (áudio do sistema)
{system_text or "_Sem áudio do sistema capturado._"}
"""
    return frontmatter + "\n" + body.strip() + "\n"


def build_class_markdown(processed: ProcessedClass, class_text: str, meta: DesktopNoteMeta) -> str:
    confidence_key = processed.confidence if processed.confidence in CONFIDENCE_DISPLAY else "baixa"
    needs_review = confidence_key == "baixa"

    frontmatter = "\n".join(
        [
            "---",
            "type: class-capture",
            f"id: {meta.content_hash[:16]}",
            f"created_at: {meta.created_at.isoformat()}",
            f"recorded_at: {meta.recorded_at.isoformat()}",
            "source: desktop-voice",
            "processing_status: done",
            f"confidence: {CONFIDENCE_DISPLAY[confidence_key]}",
            f"needs_review: {'true' if needs_review else 'false'}",
            f"topics: {_yaml_list(processed.topics)}",
            f"audio_file: {meta.system_audio_path or ''}",
            f"transcription_model: {meta.transcription_model}",
            f"processing_model: {meta.processing_model}",
            "---",
        ]
    )

    uncertainty_block = f"\n> ⚠️ {processed.uncertainty_notes}\n" if processed.uncertainty_notes else ""

    body = f"""
# {processed.title}
{uncertainty_block}
## Resumo
{processed.summary}

## Tópicos abordados
{_bullets(processed.topics)}

## Pontos-chave
{_bullets(processed.key_points)}

## Transcrição da aula
{class_text or "_Sem áudio capturado._"}
"""
    return frontmatter + "\n" + body.strip() + "\n"


def _yaml_list(items: list[str]) -> str:
    if not items:
        return "[]"
    escaped = ", ".join(f'"{i}"' for i in items)
    return f"[{escaped}]"
