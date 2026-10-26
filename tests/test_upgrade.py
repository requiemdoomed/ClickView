import json
import pytest
from clipview.backup import decode_backup, write_backup
from clipview.store import Store
from clipview.privacy import looks_sensitive


@pytest.fixture
def store():
    s = Store()
    yield s
    s.close()


def record(body="example", **values):
    return dict(body=body, category="Notes", pinned=False, copied=1700000000, **values)


def test_backup_roundtrip(store, tmp_path):
    i = store.add("नमस्ते\n  indented")
    store.update(i, pinned=True, category="Notes")
    path = tmp_path / "backup.json"
    write_backup(path, store.search())
    raw = path.read_text(encoding="utf-8")
    records = decode_backup(raw)
    assert records[0]["pinned"] is True
    assert records[0]["body"] == "नमस्ते\n  indented"
    other = Store()
    try:
        assert other.import_records(records) == (1, 0)
        assert other.search()[0]["copied"] == records[0]["copied"]
    finally:
        other.close()


def test_import_keeps_existing_metadata(store):
    i = store.add("example")
    store.update(i, pinned=True, category="Original")
    assert store.import_records([record()]) == (0, 1)
    assert store.search()[0]["category"] == "Original"


@pytest.mark.parametrize(
    "change",
    [
        {"pinned": "false"},
        {"copied": float("nan")},
        {"copied": True},
        {"category": "x" * 81},
        {"body": " "},
        {"body": "x" * 100001},
    ],
)
def test_invalid_backup_rejected(store, change):
    row = record()
    row.update(change)
    with pytest.raises(ValueError):
        store.import_records([record("valid first"), row])
    assert not store.search()


def test_invalid_version():
    for version in [True, 2, "1"]:
        with pytest.raises(ValueError):
            decode_backup(
                json.dumps(dict(format="clipview", version=version, clips=[]))
            )


def test_import_transaction_rollback(store, monkeypatch):
    original = store.execute

    def broken(sql, params=(), fetch=False):
        if sql.startswith("INSERT") and params[1] == "fail":
            raise RuntimeError("database interrupted")
        return original(sql, params, fetch)

    monkeypatch.setattr(store, "execute", broken)
    with pytest.raises(RuntimeError):
        store.import_records([record("good"), record("fail")])
    assert not store.search()
    monkeypatch.setattr(store, "execute", original)
    assert store.add("recovered")


def test_edit_preserves_date_and_rejects_duplicate(store):
    a = store.add("a")
    b = store.add("b")
    date = store.search("a")[0]["copied"]
    store.update(a, pinned=True, category="Edited", body="changed")
    assert store.search("changed")[0]["copied"] == date
    with pytest.raises(ValueError):
        store.update(b, pinned=True, category="Bad", body="changed")
    assert store.search("b")[0]["category"] == "Unsorted"


def test_retention_preserves_pins(store):
    records = [record("old"), record("pinned")]
    records[1]["pinned"] = True
    store.import_records(records)
    store.add("new")
    store.expire(30)
    assert {r["body"] for r in store.search()} == {"pinned", "new"}


def test_sort_oldest(store):
    store.import_records(
        [
            record("first"),
            dict(body="last", category="Notes", pinned=False, copied=1800000000),
        ]
    )
    assert store.search(order="oldest")[0]["body"] == "first"
    assert store.search()[0]["body"] == "last"


def test_duplicate_backup():
    with pytest.raises(ValueError):
        decode_backup(
            json.dumps(dict(format="clipview", version=1, clips=[record(), record()]))
        )


@pytest.mark.parametrize(
    "text",
    [
        "-----BEGIN PRIVATE KEY-----",
        "ghp_" + "x" * 36,
        "AKIA" + "A" * 16,
        "sk-" + "x" * 40,
    ],
)
def test_secret_formats(text):
    assert looks_sensitive(text)


@pytest.mark.parametrize(
    "text",
    ["SELECT * FROM notes", "My class starts at 9", "sk-short", "github_pat_short"],
)
def test_ordinary_text(text):
    assert not looks_sensitive(text)
