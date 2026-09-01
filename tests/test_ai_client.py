from types import SimpleNamespace

from voice_capture.ai_client import call_structured_tool, coerce_str_list


def test_coerce_str_list_passthrough_for_real_list():
    assert coerce_str_list(["Ana", "Barbara"]) == ["Ana", "Barbara"]


def test_coerce_str_list_strips_and_drops_empty_items():
    assert coerce_str_list(["  Ana  ", "", "   ", "Barbara"]) == ["Ana", "Barbara"]


def test_coerce_str_list_extracts_item_tags_from_string():
    # Bug real: o modelo devolveu uma unica string com tags <item> em vez
    # de um array de verdade - sem a correcao, iterar isso gerava um
    # bullet por CARACTERE na nota.
    raw = "<item>Adotar conteúdo de opinião pessoal.</item>\n<item>Usar bastante o real test.</item>"
    assert coerce_str_list(raw) == [
        "Adotar conteúdo de opinião pessoal.",
        "Usar bastante o real test.",
    ]


def test_coerce_str_list_plain_string_without_tags_becomes_single_item():
    assert coerce_str_list("Só um item solto, sem tags.") == ["Só um item solto, sem tags."]


def test_coerce_str_list_empty_string_becomes_empty_list():
    assert coerce_str_list("") == []
    assert coerce_str_list("   ") == []


def test_coerce_str_list_unexpected_type_becomes_empty_list():
    assert coerce_str_list(None) == []
    assert coerce_str_list(42) == []


def _fake_openai_response(finish_reason: str, arguments: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(function=SimpleNamespace(arguments=arguments))
                    ]
                ),
            )
        ]
    )


def test_structured_extraction_sends_tool_schema_as_function_and_parses_arguments(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _fake_openai_response("tool_calls", '{"title": "Teste"}')

    class FakeOpenAI:
        def __init__(self, api_key):
            assert api_key == "key"
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)

    result = call_structured_tool(
        system_prompt="system",
        tool_schema={
            "name": "extract",
            "description": "Extrai campos",
            "input_schema": {"type": "object"},
        },
        user_content="content",
        api_key="key",
        model="gpt-4.1",
    )

    assert result == {"title": "Teste"}
    sent_tool = captured["tools"][0]
    assert sent_tool["function"]["name"] == "extract"
    assert sent_tool["function"]["parameters"] == {"type": "object"}
    assert captured["tool_choice"] == {"type": "function", "function": {"name": "extract"}}


def test_structured_extraction_raises_when_truncated_by_token_limit(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            return _fake_openai_response("length", "")

    class FakeOpenAI:
        def __init__(self, api_key):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)

    try:
        call_structured_tool(
            system_prompt="system",
            tool_schema={"name": "extract", "input_schema": {"type": "object"}},
            user_content="content",
            api_key="key",
            model="gpt-4.1",
        )
        assert False, "esperava RuntimeError por truncamento"
    except RuntimeError as exc:
        assert "limite de tokens" in str(exc)
