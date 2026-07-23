"""Helper compartilhado para chamadas estruturadas (tool use) a Claude API.
Usado tanto pelo processamento de ideias (mobile) quanto pelo de reuniao e
terapia (desktop) - so o texto ja transcrito trafega, nunca audio."""
from __future__ import annotations


def call_structured_tool(
    system_prompt: str,
    tool_schema: dict,
    user_content: str,
    api_key: str,
    model: str,
) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_prompt,
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_schema["name"]},
        messages=[{"role": "user", "content": user_content}],
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    return tool_use.input
