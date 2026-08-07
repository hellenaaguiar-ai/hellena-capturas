"""Processamento por IA dos modos desktop (reuniao, terapia e aula).

Mesmas regras de autoria do modo ideia: nao inventar, nao completar, nao
transformar inferencia em fato. O modo terapia tem uma regra extra: nao
diagnosticar nem interpretar psicologicamente alem do que foi dito.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .ai_client import call_structured_tool, coerce_str_list

CONFIDENCE_LEVELS = ["baixa", "media", "alta"]

COMMON_RULES = """\
Regras obrigatorias, sem excecao:
- Nao invente informacao que nao foi dita por nenhum dos dois lados.
- Nao complete ideias que nao foram ditas.
- Nao transforme inferencias em fatos.
- Preserve o vocabulario e a intencao original de cada pessoa.
- Se nao houver base para preencher um campo, deixe-o vazio - nao invente \
conteudo so para nao deixar um campo vazio.
- Se algo estiver ambiguo, use confidence "baixa" e explique em \
uncertainty_notes."""

# ---------------------------------------------------------------------------
# Reuniao / aula
# ---------------------------------------------------------------------------

MEETING_SYSTEM_PROMPT = f"""\
Voce processa a transcricao de uma reuniao ou aula, ja dividida em duas \
trilhas: o que a pessoa dona do computador disse (microfone) e o que as \
outras pessoas/o audio do computador reproduziu (sistema). O texto de \
entrada ja vem rotulado indicando qual trecho e de qual trilha.

{COMMON_RULES}
- Decisoes e itens de acao so entram nas listas correspondentes se foram \
efetivamente ditos como decisao/acao, nao inferidos por voce.
- Distinga com cuidado "participants" de "people_mentioned" - sao coisas \
diferentes e misturar as duas e um erro grave:
  - "participants": so pessoas que REALMENTE estavam na chamada, falando. \
Voce so tem evidencia direta disso quando a propria transcricao mostra a \
pessoa sendo endereçada diretamente (ex: "obrigada, Ana", "Ana, pode \
falar?") ou se identificando. NAO inclua alguem aqui so porque o nome foi \
dito em algum momento - isso e "people_mentioned".
  - "people_mentioned": nomes de pessoas citadas na conversa como \
referencia, exemplo, terceiro, concorrente, etc - pessoas de quem se fala, \
nao com quem se fala. A grande maioria dos nomes citados numa reuniao de \
consultoria/mentoria cai aqui, nao em "participants".
  - Se voce nao tem certeza se alguem realmente participou ou so foi \
citado, coloque em "people_mentioned" (o mais conservador) e explique a \
duvida em uncertainty_notes - nunca "promova" um nome pra participants \
por suposicao."""

MEETING_TOOL_SCHEMA = {
    "name": "structure_meeting_capture",
    "description": "Estrutura a transcricao de uma reuniao/aula em resumo, decisoes e acoes.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Titulo curto da reuniao/aula (ate 80 caracteres)."},
            "summary": {"type": "string", "description": "Resumo fiel do que foi discutido, 3 a 6 frases."},
            "decisions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Decisoes explicitamente tomadas. Vazio se nenhuma.",
            },
            "action_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Itens de acao explicitamente combinados. Vazio se nenhum.",
            },
            "participants": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Pessoas que REALMENTE participaram da chamada (falaram, foram endereçadas "
                    "diretamente, se identificaram) - nao qualquer nome citado. Vazio se nao for "
                    "possivel identificar com confianca quem estava na chamada."
                ),
            },
            "people_mentioned": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Nomes de pessoas citadas/referenciadas durante a conversa (exemplo, "
                    "referencia, terceiro) que NAO participaram da propria chamada. Vazio se nenhuma."
                ),
            },
            "open_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Perguntas levantadas e nao respondidas na reuniao.",
            },
            "confidence": {"type": "string", "enum": CONFIDENCE_LEVELS},
            "uncertainty_notes": {"type": "string", "description": "String vazia se nao houver ambiguidade."},
        },
        "required": [
            "title",
            "summary",
            "decisions",
            "action_items",
            "participants",
            "people_mentioned",
            "open_questions",
            "confidence",
            "uncertainty_notes",
        ],
    },
}


@dataclass
class ProcessedMeeting:
    title: str
    summary: str
    decisions: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    people_mentioned: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    confidence: str = "baixa"
    uncertainty_notes: str = ""


def process_meeting_transcript(labeled_text: str, api_key: str, model: str) -> ProcessedMeeting:
    data = call_structured_tool(
        system_prompt=MEETING_SYSTEM_PROMPT,
        tool_schema=MEETING_TOOL_SCHEMA,
        user_content=f"Transcricao da reuniao/aula:\n\n{labeled_text}",
        api_key=api_key,
        model=model,
    )
    return ProcessedMeeting(
        title=data["title"],
        summary=data["summary"],
        decisions=coerce_str_list(data.get("decisions", [])),
        action_items=coerce_str_list(data.get("action_items", [])),
        participants=coerce_str_list(data.get("participants", [])),
        people_mentioned=coerce_str_list(data.get("people_mentioned", [])),
        open_questions=coerce_str_list(data.get("open_questions", [])),
        confidence=data.get("confidence", "baixa"),
        uncertainty_notes=data.get("uncertainty_notes", ""),
    )


# ---------------------------------------------------------------------------
# Terapia
# ---------------------------------------------------------------------------

THERAPY_SYSTEM_PROMPT = f"""\
Voce processa a transcricao de uma sessao de terapia, ja dividida em duas \
trilhas: o que a cliente disse (microfone) e o que o(a) terapeuta disse \
(audio do sistema). O texto de entrada ja vem rotulado indicando qual \
trecho e de qual trilha.

{COMMON_RULES}
- Voce NAO diagnostica, NAO interpreta psicologicamente e NAO da opiniao \
clinica. Apenas organiza o que foi dito.
- "insights" sao percepcoes que a propria cliente expressou durante a \
sessao (ex: "percebi que..."), nunca uma interpretacao sua do que ela \
"realmente" quis dizer."""

THERAPY_TOOL_SCHEMA = {
    "name": "structure_therapy_capture",
    "description": "Estrutura a transcricao de uma sessao de terapia em sintese, temas e encaminhamentos, sem interpretacao clinica.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Titulo curto da sessao (ate 80 caracteres), ex: tema central."},
            "session_summary": {
                "type": "string",
                "description": "Sintese fiel do que foi conversado, 3 a 6 frases, sem interpretacao clinica.",
            },
            "themes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Temas abordados na sessao, citados explicitamente.",
            },
            "insights": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Percepcoes que a propria cliente expressou durante a sessao. Vazio se nenhuma.",
            },
            "follow_ups": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Encaminhamentos ou tarefas combinadas explicitamente na sessao. Vazio se nenhum.",
            },
            "confidence": {"type": "string", "enum": CONFIDENCE_LEVELS},
            "uncertainty_notes": {"type": "string", "description": "String vazia se nao houver ambiguidade."},
        },
        "required": [
            "title",
            "session_summary",
            "themes",
            "insights",
            "follow_ups",
            "confidence",
            "uncertainty_notes",
        ],
    },
}


@dataclass
class ProcessedTherapy:
    title: str
    session_summary: str
    themes: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    confidence: str = "baixa"
    uncertainty_notes: str = ""


def process_therapy_transcript(labeled_text: str, api_key: str, model: str) -> ProcessedTherapy:
    data = call_structured_tool(
        system_prompt=THERAPY_SYSTEM_PROMPT,
        tool_schema=THERAPY_TOOL_SCHEMA,
        user_content=f"Transcricao da sessao:\n\n{labeled_text}",
        api_key=api_key,
        model=model,
    )
    return ProcessedTherapy(
        title=data["title"],
        session_summary=data["session_summary"],
        themes=coerce_str_list(data.get("themes", [])),
        insights=coerce_str_list(data.get("insights", [])),
        follow_ups=coerce_str_list(data.get("follow_ups", [])),
        confidence=data.get("confidence", "baixa"),
        uncertainty_notes=data.get("uncertainty_notes", ""),
    )


# ---------------------------------------------------------------------------
# Aula
# ---------------------------------------------------------------------------

CLASS_SYSTEM_PROMPT = f"""\
Voce processa a transcricao do audio de uma aula/curso (Hotmart, YouTube, \
curso gravado, etc.) - uma unica trilha, so o audio da aula, sem \
microfone (quem gravou estava so assistindo, nao falando).

{COMMON_RULES}"""

CLASS_TOOL_SCHEMA = {
    "name": "structure_class_capture",
    "description": "Estrutura a transcricao de uma aula em resumo e topicos abordados.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Titulo curto da aula (ate 80 caracteres)."},
            "summary": {"type": "string", "description": "Resumo fiel do conteudo da aula, 3 a 6 frases."},
            "topics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topicos/assuntos abordados na aula, na ordem em que apareceram.",
            },
            "key_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Pontos/afirmacoes importantes destacados na aula. Vazio se nenhum se destacou.",
            },
            "confidence": {"type": "string", "enum": CONFIDENCE_LEVELS},
            "uncertainty_notes": {"type": "string", "description": "String vazia se nao houver ambiguidade."},
        },
        "required": ["title", "summary", "topics", "key_points", "confidence", "uncertainty_notes"],
    },
}


@dataclass
class ProcessedClass:
    title: str
    summary: str
    topics: list[str] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)
    confidence: str = "baixa"
    uncertainty_notes: str = ""


def process_class_transcript(text: str, api_key: str, model: str) -> ProcessedClass:
    data = call_structured_tool(
        system_prompt=CLASS_SYSTEM_PROMPT,
        tool_schema=CLASS_TOOL_SCHEMA,
        user_content=f"Transcricao da aula:\n\n{text}",
        api_key=api_key,
        model=model,
    )
    return ProcessedClass(
        title=data["title"],
        summary=data["summary"],
        topics=coerce_str_list(data.get("topics", [])),
        key_points=coerce_str_list(data.get("key_points", [])),
        confidence=data.get("confidence", "baixa"),
        uncertainty_notes=data.get("uncertainty_notes", ""),
    )
