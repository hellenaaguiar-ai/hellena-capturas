"""Processamento por IA: so o TEXTO transcrito e enviado, nunca o audio.

Usa a OpenAI com function calling (saida estruturada por schema), para nao
depender de "pedir markdown e torcer para vir certo".
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .ai_client import call_structured_tool, coerce_str_list

POSSIBLE_USES = [
    "Second Brain",
    "Investigação",
    "Ideia de conteúdo",
    "Tarefa/lembrete",
    "História",
    "Tese",
    "Princípio",
    "Modelo mental",
    "Apenas arquivar",
]

CONFIDENCE_LEVELS = ["baixa", "media", "alta"]

SYSTEM_PROMPT = """\
Voce processa transcricoes de pensamentos falados em voz alta por uma pessoa \
capturando pensamentos no dia a dia (leitura, reflexao, rotina, terapia, \
trabalho). O texto que voce recebe e a transcricao bruta de um unico audio.

Nem toda gravacao e uma "ideia": pode ser uma reflexao sem aplicacao pratica, \
uma tarefa para o futuro, uma mudanca de opiniao/percepcao sobre algo, uma \
pergunta em aberto, uma observacao sobre um livro/pessoa/situacao, entre \
outras coisas. Identifique o que a gravacao realmente e, sem forcar um \
enquadramento de "ideia" quando nao for isso. Exemplos de classification \
(essa lista NAO e fechada, use a que melhor descrever o conteudo real): \
"reflexao", "reflexao-livro", "ideia-de-conteudo", "tarefa-futura", \
"mudanca-de-pensamento", "nota-terapia", "observacao-comportamento", \
"pergunta", "principio", "modelo-mental", "historia", "tese", "indefinido".

Regras obrigatorias, sem excecao:
- Nao invente crencas que a pessoa nao expressou.
- Nao complete ideias que nao foram ditas.
- Nao transforme inferencias em fatos: se voce esta deduzindo algo que nao foi \
dito explicitamente, isso vai em "evidence_and_connections" marcado como \
possibilidade, nunca na sintese como se fosse afirmado.
- Nao "melhore" o pensamento mudando seu sentido.
- Nao remova contradicoes relevantes presentes na fala.
- Preserve o vocabulario e a intencao original.
- Voce pode limpar vicios de transcricao (hesitacoes tipo "e", "tipo", "entao", \
repeticoes, palavras cortadas) no campo cleaned_transcript, mas sem reescrever \
frases nem trocar palavras por sinonimos "melhores".
- Se nao houver base para preencher um campo (ex: nenhuma entidade citada, \
nenhuma pergunta em aberto), deixe-o vazio. Nao invente conteudo para nao \
deixar um campo vazio.
- Se a classificacao ou o assunto estiver ambiguo, use confidence "baixa" e \
explique a ambiguidade em uncertainty_notes, em vez de forcar uma classificacao \
confiante.
- book_title so pode conter o titulo de um livro quando a gravacao for de fato \
sobre esse livro e o titulo tiver sido dito ou estiver inequivocamente presente \
na propria transcricao. Nao deduza o titulo por personagem, trama, autora ou \
contexto externo. Se houver qualquer ambiguidade, use string vazia e \
book_title_confidence "baixa".

possible_uses so pode conter itens desta lista fixa (pode ser uma lista vazia \
se nada se aplicar claramente):
""" + ", ".join(f'"{u}"' for u in POSSIBLE_USES)

TOOL_SCHEMA = {
    "name": "structure_voice_capture",
    "description": "Estrutura uma transcricao de pensamento falado em campos fieis ao que foi dito.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Titulo provisorio curto (ate 80 caracteres), descritivo, sem inventar interpretacao.",
            },
            "synthesis": {
                "type": "string",
                "description": "2 a 5 frases resumindo fielmente o que foi dito, sem adicionar interpretacao nao expressa.",
            },
            "cleaned_transcript": {
                "type": "string",
                "description": "Transcricao com vicios de fala removidos, sem reescrever frases ou trocar palavras.",
            },
            "entities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Pessoas, livros, personagens, conceitos citados explicitamente. Vazio se nenhum.",
            },
            "evidence_and_connections": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Conexoes ou inferencias possiveis, marcadas como possibilidade, nao como fato.",
            },
            "open_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Perguntas em aberto levantadas pela fala. Vazio se nenhuma.",
            },
            "possible_uses": {
                "type": "array",
                "items": {"type": "string", "enum": POSSIBLE_USES},
                "description": "Subconjunto da lista fixa de usos possiveis. Pode ser vazio.",
            },
            "classification": {
                "type": "string",
                "description": (
                    "O que esta gravacao realmente e - nem toda gravacao e uma ideia. "
                    "Melhor palpite, em poucas palavras (ex: 'reflexao', 'reflexao-livro', "
                    "'ideia-de-conteudo', 'tarefa-futura', 'mudanca-de-pensamento', "
                    "'nota-terapia', 'observacao-comportamento', 'pergunta', 'principio', "
                    "'modelo-mental', 'historia', 'tese', 'indefinido'). Lista nao fechada: "
                    "use outra categoria se descrever melhor o conteudo real."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": CONFIDENCE_LEVELS,
                "description": "Confianca na classificacao/estruturacao acima.",
            },
            "related_topics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags curtas de topico extraidas do proprio texto (nao do restante do vault).",
            },
            "uncertainty_notes": {
                "type": "string",
                "description": "Explicacao do que esta ambiguo, se confidence for baixa. String vazia se nao houver.",
            },
            "book_title": {
                "type": "string",
                "description": "Titulo explicito e inequivoco do livro sobre o qual a pessoa fala. String vazia se nao estiver claro.",
            },
            "book_title_confidence": {
                "type": "string",
                "enum": CONFIDENCE_LEVELS,
                "description": "Alta somente quando o titulo do livro estiver explicito e inequivoco na transcricao.",
            },
        },
        "required": [
            "title",
            "synthesis",
            "cleaned_transcript",
            "entities",
            "evidence_and_connections",
            "open_questions",
            "possible_uses",
            "classification",
            "confidence",
            "related_topics",
            "uncertainty_notes",
            "book_title",
            "book_title_confidence",
        ],
    },
}


@dataclass
class ProcessedCapture:
    title: str
    synthesis: str
    cleaned_transcript: str
    entities: list[str] = field(default_factory=list)
    evidence_and_connections: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    possible_uses: list[str] = field(default_factory=list)
    classification: str = "indefinido"
    confidence: str = "baixa"
    related_topics: list[str] = field(default_factory=list)
    uncertainty_notes: str = ""
    book_title: str = ""
    book_title_confidence: str = "baixa"


def process_transcript(raw_text: str, api_key: str, model: str) -> ProcessedCapture:
    data = call_structured_tool(
        system_prompt=SYSTEM_PROMPT,
        tool_schema=TOOL_SCHEMA,
        user_content=f"Transcricao bruta a estruturar:\n\n{raw_text}",
        api_key=api_key,
        model=model,
    )
    return ProcessedCapture(
        title=data["title"],
        synthesis=data["synthesis"],
        cleaned_transcript=data["cleaned_transcript"],
        entities=coerce_str_list(data.get("entities", [])),
        evidence_and_connections=coerce_str_list(data.get("evidence_and_connections", [])),
        open_questions=coerce_str_list(data.get("open_questions", [])),
        possible_uses=coerce_str_list(data.get("possible_uses", [])),
        classification=data.get("classification", "indefinido"),
        confidence=data.get("confidence", "baixa"),
        related_topics=coerce_str_list(data.get("related_topics", [])),
        uncertainty_notes=data.get("uncertainty_notes", ""),
        book_title=data.get("book_title", "").strip(),
        book_title_confidence=data.get("book_title_confidence", "baixa"),
    )
