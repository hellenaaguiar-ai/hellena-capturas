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
# Reflexao (diario de bordo - so microfone, uma pessoa falando sozinha)
# ---------------------------------------------------------------------------

REFLECTION_SYSTEM_PROMPT = f"""\
Voce processa a transcricao de uma reflexao/desabafo falado em voz alta -
uma unica pessoa pensando em voz alta, sem interlocutor (so a trilha do
microfone). Pode ser um desabafo, uma percepcao sobre si mesma, uma
mudanca de opiniao, uma observacao comportamental - mais proximo de uma
entrada de diario do que de uma "ideia" objetiva.

{COMMON_RULES}
- Voce NAO diagnostica, NAO interpreta psicologicamente e NAO da opiniao \
clinica sobre o que foi dito - mesma regra do modo terapia. Apenas \
organiza e sintetiza o que a pessoa disse.
- Preserve o tom emocional expresso na fala (frustracao, alivio, duvida, \
etc.) na sintese - nao neutralize nem "objetifique" o que foi dito.
- "insights" sao percepcoes que a propria pessoa expressou (ex: "percebi \
que..."), nunca uma interpretacao sua do que ela "realmente" quis dizer."""

REFLECTION_TOOL_SCHEMA = {
    "name": "structure_reflection_capture",
    "description": "Estrutura uma reflexao/desabafo falado em sintese (com tom emocional preservado), temas e percepcoes, sem interpretacao clinica.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Titulo curto (ate 80 caracteres), descritivo do tema central."},
            "synthesis": {
                "type": "string",
                "description": (
                    "Sintese fiel do que foi dito, 3 a 6 frases, preservando o tom emocional "
                    "expresso - sem interpretacao clinica nem neutralizar o que foi sentido."
                ),
            },
            "themes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Temas abordados na fala, citados explicitamente.",
            },
            "insights": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Percepcoes que a propria pessoa expressou durante a fala. Vazio se nenhuma.",
            },
            "confidence": {"type": "string", "enum": CONFIDENCE_LEVELS},
            "uncertainty_notes": {"type": "string", "description": "String vazia se nao houver ambiguidade."},
        },
        "required": ["title", "synthesis", "themes", "insights", "confidence", "uncertainty_notes"],
    },
}


@dataclass
class ProcessedReflection:
    title: str
    synthesis: str
    themes: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    confidence: str = "baixa"
    uncertainty_notes: str = ""


def process_reflection_transcript(text: str, api_key: str, model: str) -> ProcessedReflection:
    data = call_structured_tool(
        system_prompt=REFLECTION_SYSTEM_PROMPT,
        tool_schema=REFLECTION_TOOL_SCHEMA,
        user_content=f"Transcricao da reflexao:\n\n{text}",
        api_key=api_key,
        model=model,
    )
    return ProcessedReflection(
        title=data["title"],
        synthesis=data["synthesis"],
        themes=coerce_str_list(data.get("themes", [])),
        insights=coerce_str_list(data.get("insights", [])),
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
"realmente" quis dizer.
- Esta e uma captura privada para consulta, nao um gerenciador de tarefas. \
Nao transforme sugestoes, possibilidades ou temas da conversa em tarefas.
- Destaque perguntas, observacoes e formulacoes relevantes do(a) terapeuta \
em therapist_highlights, preservando que vieram do(a) terapeuta.
- revisit_topics registra assuntos que podem ser retomados ou observados, \
sem linguagem prescritiva e sem checkboxes.
- Examine obrigatoriamente AS DUAS trilhas. Se a trilha do(a) terapeuta \
contiver fala compreensivel, therapist_highlights nao pode ficar vazio.
- Os campos sao mutuamente distintos: themes contem apenas nomes curtos de \
assuntos; important_points contem fatos ou momentos centrais; insights contem \
percepcoes formuladas pela cliente; therapist_highlights contem contribuicoes \
do(a) terapeuta; revisit_topics contem fios que podem ser retomados.
- Nao despeje insights, frases longas ou observacoes do terapeuta em themes.
- Extraia o que estiver sustentado pela transcricao. Ser conservador significa \
nao inventar, nao ignorar evidencias explicitas e devolver campos vazios.
- O nome da cliente e Hellena, com dois L. Use Hellena quando estiver se \
referindo a cliente. Nao altere o nome de terceiras pessoas que realmente se \
chamem Helena."""

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
                "minItems": 1,
                "maxItems": 10,
                "items": {"type": "string"},
                "description": "De 5 a 10 nomes curtos de assuntos abordados; sem frases, insights ou interpretacoes.",
            },
            "insights": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {"type": "string"},
                "description": "De 3 a 8 percepcoes que a cliente formulou sobre si ou sua vida, preferencialmente em primeira pessoa. Nao duplicar em themes.",
            },
            "important_points": {
                "type": "array",
                "minItems": 1,
                "maxItems": 10,
                "items": {"type": "string"},
                "description": "De 5 a 10 fatos, tensoes ou momentos concretos centrais da conversa; nao sao temas genericos nem tarefas.",
            },
            "therapist_highlights": {
                "type": "array",
                "minItems": 1,
                "maxItems": 10,
                "items": {"type": "string"},
                "description": "De 4 a 10 perguntas, observacoes ou formulacoes relevantes ditas pelo(a) terapeuta, em itens separados. Obrigatorio quando houver fala compreensivel na trilha do sistema.",
            },
            "revisit_topics": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {"type": "string"},
                "description": "De 2 a 6 fios da conversa que podem ser retomados ou observados; sem verbos de ordem, checkboxes ou compromissos inventados.",
            },
            "confidence": {"type": "string", "enum": CONFIDENCE_LEVELS},
            "uncertainty_notes": {"type": "string", "description": "String vazia se nao houver ambiguidade."},
        },
        "required": [
            "title",
            "session_summary",
            "themes",
            "insights",
            "important_points",
            "therapist_highlights",
            "revisit_topics",
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
    important_points: list[str] = field(default_factory=list)
    therapist_highlights: list[str] = field(default_factory=list)
    revisit_topics: list[str] = field(default_factory=list)
    confidence: str = "baixa"
    uncertainty_notes: str = ""


def process_therapy_transcript(labeled_text: str, api_key: str, model: str) -> ProcessedTherapy:
    data = call_structured_tool(
        system_prompt=THERAPY_SYSTEM_PROMPT,
        tool_schema=THERAPY_TOOL_SCHEMA,
        user_content=f"Transcricao da sessao:\n\n{labeled_text}",
        api_key=api_key,
        model=model,
        max_tokens=4096,
    )
    return ProcessedTherapy(
        title=data["title"],
        session_summary=data["session_summary"],
        themes=coerce_str_list(data.get("themes", [])),
        insights=coerce_str_list(data.get("insights", [])),
        important_points=coerce_str_list(data.get("important_points", [])),
        therapist_highlights=coerce_str_list(data.get("therapist_highlights", [])),
        revisit_topics=coerce_str_list(data.get("revisit_topics", [])),
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
