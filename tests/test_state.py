from voice_capture.state import ItemState, STATUS_DONE, STATUS_PENDING, StateStore


def test_state_roundtrip(tmp_path):
    state_file = tmp_path / "state.json"
    store = StateStore(state_file)
    store.upsert("abc123", ItemState(source_filename="x.m4a", first_seen_at="2026-01-01T00:00:00"))
    store.save()

    reloaded = StateStore(state_file)
    item = reloaded.get("abc123")
    assert item is not None
    assert item.source_filename == "x.m4a"
    assert item.status == STATUS_PENDING


def test_is_done(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.upsert(
        "hash1",
        ItemState(source_filename="a.m4a", first_seen_at="t", status=STATUS_DONE),
    )
    assert store.is_done("hash1") is True
    assert store.is_done("hash-nao-existe") is False


def test_errors_filters_only_error_status(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.upsert("h1", ItemState(source_filename="a", first_seen_at="t", status="error", error="boom"))
    store.upsert("h2", ItemState(source_filename="b", first_seen_at="t", status=STATUS_DONE))
    errors = store.errors()
    assert list(errors.keys()) == ["h1"]
