from voice_capture.ai_client import coerce_str_list


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
