"""Opt-in integration against a disposable MySQL database, never a user's history."""

import os
import pytest
from clipview.store import Store


@pytest.mark.skipif(
    os.getenv("CLIPVIEW_TEST_MYSQL") != "1",
    reason="Disposable MySQL server not configured",
)
def test_mysql_roundtrip():
    s = Store(
        mysql=dict(
            host="127.0.0.1",
            user="clipview",
            password=os.environ["CLIPVIEW_TEST_PASSWORD"],
            database="clipview_test",
        )
    )
    try:
        s.clear(True)
        i = s.add("SELECT 你好 👋")
        s.update(i, pinned=True, category="Code")
        assert s.add("SELECT 你好 👋") == i
        assert s.search("你好", pinned=True)[0]["category"] == "Code"
        s.clear()
        assert len(s.search()) == 1
        s.clear(True)
        assert not s.search()
    finally:
        s.close()
