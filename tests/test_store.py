import pytest
from clipview.store import Store
from clipview.privacy import allowed


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.sqlite3")
    yield s
    s.close()


def test_five_copy_search_restore(store):
    snippets = [
        "git status",
        "Meeting at 10",
        "SELECT * FROM notes;",
        "print(42)",
        "Study chapter 4",
    ]
    for text in snippets:
        store.add(text)
    assert len(store.search()) == 5
    assert store.search("select")[0]["body"] == snippets[2]


def test_exact_whitespace_unicode_and_literal_search(store):
    text = "  नमस्ते\n100%_ ' OR 1=1 --  "
    store.add(text)
    assert store.search("%_")[0]["body"] == text
    assert store.search("absent") == []


def test_dedupe_preserves_metadata(store):
    i = store.add("hello")
    store.update(i, pinned=True, category="Work")
    assert store.add("hello") == i
    assert len(store.search()) == 1
    assert store.search(category="Work", pinned=True)[0]["pinned"] == 1


def test_clear_preserves_pins(store):
    i = store.add("keep")
    store.update(i, pinned=True, category="Work")
    store.add("remove")
    store.clear()
    assert len(store.search()) == 1
    store.clear(True)
    assert store.search() == []


def test_delete(store):
    i = store.add("delete me")
    store.delete(i)
    assert not store.search()


def test_validation(store):
    assert store.add("  ") == None
    with pytest.raises(ValueError):
        store.add("x" * 100001)
    i = store.add("a")
    with pytest.raises(ValueError):
        store.update(i, pinned=False, category="x" * 81)


def test_reopen(tmp_path):
    path = tmp_path / "history.db"
    s = Store(path)
    s.add("lasting")
    s.close()
    s = Store(path)
    assert s.search()[0]["body"] == "lasting"
    s.close()


@pytest.mark.parametrize(
    "app,paused,expected",
    [
        (None, False, False),
        ("Bitwarden.exe", False, False),
        ("Editor", True, False),
        ("Editor", False, True),
    ],
)
def test_capture_policy(app, paused, expected):
    assert allowed(app, paused=paused) == expected


def test_retention(store):
    for i in range(2002):
        store.add(str(i))
    assert len(store.search()) == 2000
    assert not store.search("nonexistent")
    assert all(c["body"] not in ("0", "1") for c in store.search())
