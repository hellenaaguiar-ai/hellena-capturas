"""Helper compartilhado para chamadas estruturadas (tool use) a Claude API.
Usado tanto pelo processamento de ideias (mobile) quanto pelo de reuniao e
terapia (desktop) - so o texto ja transcrito trafega, nunca audio."""
from __future__ import annotations

import re

_ITEM_TAG_RE = re.compile(r"<item>(.*?)</item>", re.DOTALL)


def coerce_str_list(value: object) -> list[str]:
    """Bug real ja visto em producao: apesar do schema pedir array de
    strings, o modelo as vezes devolve uma UNICA STRING representando a
    lista com tags tipo "<item>primeiro</item>\\n<item>segundo</item>" em
    vez de um array de verdade. Sem essa checagem, o resto do codigo
    iterava direto sobre essa string (`for i in items`), o que em Python
    itera CARACTER por CARACTER - a nota saia com um item de lista por
    letra. Aceita lista normalmente; se vier string, tenta separar pelas
    tags <item>; se nao achar nenhuma, trata a string inteira como um
    unico item (nunca descarta conteudo)."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        matches = _ITEM_TAG_RE.findall(value)
        if matches:
            return [m.strip() for m in matches if m.strip()]
        stripped = value.strip()
        return [stripped] if stripped else []
    return []


def call_structured_tool(
    system_prompt: str,
    tool_schema: dict,
    user_content: str,
    api_key: str,
    model: str,
    max_tokens: int = 2048,
) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_schema["name"]},
        messages=[{"role": "user", "content": user_content}],
    )
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            "Resposta da Claude interrompida pelo limite de tokens; "
            "a captura nao sera salva como se estivesse completa."
        )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    return tool_use.input
