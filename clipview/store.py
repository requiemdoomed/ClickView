"""Transactional history repository for SQLite and MySQL."""

import hashlib
import sqlite3
import time
from contextlib import contextmanager
from .backup import MAX_BYTES, validate_records


class Store:
    def __init__(self, path=None, mysql=None):
        self.mysql = mysql is not None
        if self.mysql:
            import pymysql

            self.db = pymysql.connect(
                **mysql,
                charset="utf8mb4",
                autocommit=True,
                connect_timeout=3,
                read_timeout=3,
                write_timeout=3,
            )
        else:
            self.db = sqlite3.connect(
                str(path or ":memory:"), timeout=3, isolation_level=None
            )
            self.execute("PRAGMA secure_delete=ON")
        identity = (
            "BIGINT PRIMARY KEY AUTO_INCREMENT"
            if self.mysql
            else "INTEGER PRIMARY KEY AUTOINCREMENT"
        )
        self.execute(f"""CREATE TABLE IF NOT EXISTS clips (
            id {identity}, digest VARCHAR(64) NOT NULL UNIQUE,
            body {"MEDIUMTEXT" if self.mysql else "TEXT"} NOT NULL,
            category VARCHAR(80) NOT NULL DEFAULT 'Unsorted',
            pinned INTEGER NOT NULL DEFAULT 0, copied DOUBLE NOT NULL)""")

    def execute(self, sql, params=(), fetch=False):
        cursor = self.db.cursor()
        try:
            cursor.execute(sql.replace("?", "%s") if self.mysql else sql, params)
            return cursor.fetchall() if fetch else cursor.lastrowid
        finally:
            cursor.close()

    @contextmanager
    def transaction(self):
        if self.mysql:
            self.db.begin()
        else:
            self.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _prune(self):
        rows = self.execute(
            "SELECT id FROM clips WHERE pinned=0 ORDER BY copied DESC,id DESC LIMIT 2147483647 OFFSET 2000",
            fetch=True,
        )
        for row in rows:
            self.execute("DELETE FROM clips WHERE id=?", row)

    def add(self, text):
        if not isinstance(text, str) or not text.strip():
            return None
        if len(text.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Text exceeds the 100 KB limit.")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with self.transaction():
            existing = self.execute(
                "SELECT id FROM clips WHERE digest=?", (digest,), True
            )
            if existing:
                clip_id = existing[0][0]
                self.execute(
                    "UPDATE clips SET copied=? WHERE id=?", (time.time(), clip_id)
                )
            else:
                clip_id = self.execute(
                    "INSERT INTO clips(digest,body,copied) VALUES(?,?,?)",
                    (digest, text, time.time()),
                )
            self._prune()
        return clip_id

    def search(self, query="", category=None, pinned=False, order="newest"):
        rows = self.execute(
            "SELECT id,body,category,pinned,copied FROM clips ORDER BY pinned DESC,copied DESC,id DESC",
            fetch=True,
        )
        keys = ("id", "body", "category", "pinned", "copied")
        matches = [
            dict(zip(keys, row))
            for row in rows
            if query.casefold() in row[1].casefold()
            and (category is None or category == row[2])
            and (not pinned or row[3])
        ]
        if order == "oldest":
            matches.sort(key=lambda row: (not row["pinned"], row["copied"], row["id"]))
        return matches

    def update(self, clip_id, *, pinned, category, body=None):
        category = category.strip() or "Unsorted"
        if len(category) > 80:
            raise ValueError("Category must be 80 characters or fewer.")
        if body is not None and (
            not body.strip() or len(body.encode("utf-8")) > MAX_BYTES
        ):
            raise ValueError("Text must be nonempty and fit within 100 KB.")
        with self.transaction():
            if body is not None:
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                if self.execute(
                    "SELECT id FROM clips WHERE digest=? AND id<>?",
                    (digest, clip_id),
                    True,
                ):
                    raise ValueError(
                        "That text is already saved. Edit or delete the other snippet first."
                    )
                self.execute(
                    "UPDATE clips SET body=?,digest=? WHERE id=?",
                    (body, digest, clip_id),
                )
            self.execute(
                "UPDATE clips SET pinned=?,category=? WHERE id=?",
                (int(pinned), category, clip_id),
            )
            self._prune()

    def import_records(self, records):
        records = validate_records(records)
        added = skipped = 0
        with self.transaction():
            for row in records:
                digest = hashlib.sha256(row["body"].encode("utf-8")).hexdigest()
                if self.execute("SELECT id FROM clips WHERE digest=?", (digest,), True):
                    skipped += 1
                    continue
                self.execute(
                    "INSERT INTO clips(digest,body,category,pinned,copied) VALUES(?,?,?,?,?)",
                    (
                        digest,
                        row["body"],
                        row["category"],
                        int(row["pinned"]),
                        row["copied"],
                    ),
                )
                added += 1
            # Rejecting oversized merges instead of silently losing older history.
            count = self.execute(
                "SELECT COUNT(*) FROM clips WHERE pinned=0", fetch=True
            )[0][0]
            if count > 2000:
                raise ValueError(
                    "Import exceeds the 2,000 unpinned-snippet limit. Nothing was imported."
                )
        return added, skipped

    def expire(self, days):
        if type(days) is not int or not 0 <= days <= 3650:
            raise ValueError("Retention must be between 0 and 3,650 days.")
        if days:
            with self.transaction():
                self.execute(
                    "DELETE FROM clips WHERE pinned=0 AND copied<?",
                    (time.time() - days * 86400,),
                )

    def delete(self, clip_id):
        with self.transaction():
            self.execute("DELETE FROM clips WHERE id=?", (clip_id,))

    def clear(self, include_pinned=False):
        with self.transaction():
            self.execute(
                "DELETE FROM clips" + ("" if include_pinned else " WHERE pinned=0")
            )

    def close(self):
        self.db.close()
