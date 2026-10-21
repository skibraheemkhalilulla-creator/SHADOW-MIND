"""Local SQLite persistence for ShadowIntelX IQ."""

from __future__ import annotations

import json
import math
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any


DB_PATH = Path(os.environ.get("SHADOWINTELX_DB_PATH", str(Path(__file__).with_name("shadowintelx.sqlite3"))))


@contextmanager
def _connect(db_path: str | Path = DB_PATH):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(db_path: str | Path = DB_PATH, legacy_scores_path: str | Path | None = None) -> None:
    """Create the schema and import the legacy leaderboard once, if present."""
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                display_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                xp INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0),
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY,
                attempt_key TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                arena TEXT NOT NULL,
                skill TEXT NOT NULL,
                level TEXT NOT NULL,
                score REAL NOT NULL CHECK (score >= 0 AND score <= max_score),
                max_score REAL NOT NULL CHECK (max_score > 0),
                accuracy REAL NOT NULL CHECK (accuracy >= 0 AND accuracy <= 100),
                duration_seconds REAL NOT NULL DEFAULT 0 CHECK (duration_seconds >= 0),
                xp_earned INTEGER NOT NULL DEFAULT 0 CHECK (xp_earned >= 0),
                details_json TEXT NOT NULL DEFAULT '{}',
                completed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS attempts_user_date_idx ON attempts(user_id, completed_at);
            CREATE INDEX IF NOT EXISTS attempts_user_skill_idx ON attempts(user_id, skill, completed_at);
            CREATE TABLE IF NOT EXISTS high_scores (
                id INTEGER PRIMARY KEY,
                player TEXT NOT NULL COLLATE NOCASE,
                arena TEXT NOT NULL,
                level TEXT NOT NULL,
                score REAL NOT NULL,
                unit TEXT NOT NULL,
                updated TEXT NOT NULL,
                UNIQUE(player COLLATE NOCASE, arena, level)
            );
            CREATE TABLE IF NOT EXISTS mission_claims (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mission_key TEXT NOT NULL,
                period_key TEXT NOT NULL,
                xp_earned INTEGER NOT NULL CHECK (xp_earned >= 0),
                claimed_at TEXT NOT NULL,
                UNIQUE(user_id, mission_key, period_key)
            );
            CREATE TABLE IF NOT EXISTS badges (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                badge_key TEXT NOT NULL,
                label TEXT NOT NULL,
                earned_at TEXT NOT NULL,
                UNIQUE(user_id, badge_key)
            );
            """
        )
        migration_key = "legacy_high_scores_imported_v1"
        migrated = conn.execute("SELECT 1 FROM schema_meta WHERE key = ?", (migration_key,)).fetchone()
        if migrated:
            return
        if legacy_scores_path is not None:
            try:
                rows = json.loads(Path(legacy_scores_path).read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError, TypeError):
                rows = []
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    try:
                        player = " ".join(str(row["player"]).split())[:24] or "Player"
                        arena = str(row["arena"])[:80]
                        level = str(row["level"])[:40]
                        score = float(row["score"])
                        unit = str(row.get("unit", "points"))[:40]
                        updated = str(row.get("updated", datetime.now().date().isoformat()))[:20]
                        if not math.isfinite(score):
                            continue
                    except (KeyError, TypeError, ValueError):
                        continue
                    conn.execute(
                        """INSERT INTO high_scores(player, arena, level, score, unit, updated)
                           VALUES (?, ?, ?, ?, ?, ?)
                           ON CONFLICT(player COLLATE NOCASE, arena, level) DO UPDATE SET
                             score=excluded.score, unit=excluded.unit, updated=excluded.updated
                           WHERE excluded.score > high_scores.score""",
                        (player, arena, level, score, unit, updated),
                    )
        conn.execute("INSERT INTO schema_meta(key, value) VALUES (?, ?)", (migration_key, "done"))


def normalize_name(display_name: str | None) -> str:
    return " ".join(str(display_name or "").split())[:32] or "Guest"


def get_or_create_user(display_name: str, db_path: str | Path = DB_PATH) -> dict[str, Any]:
    name = normalize_name(display_name)
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO users(display_name, created_at) VALUES (?, ?) ON CONFLICT(display_name) DO NOTHING",
            (name, datetime.now().astimezone().isoformat(timespec="seconds")),
        )
        row = conn.execute("SELECT id, display_name, xp, created_at FROM users WHERE display_name = ? COLLATE NOCASE", (name,)).fetchone()
        return dict(row)


def get_user_xp(user_id: int, db_path: str | Path = DB_PATH) -> int:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT xp FROM users WHERE id = ?", (int(user_id),)).fetchone()
        return int(row["xp"]) if row else 0


def _award_automatic_badges(conn: sqlite3.Connection, user_id: int, now: str) -> None:
    attempt_count = conn.execute("SELECT COUNT(*) AS n FROM attempts WHERE user_id = ?", (user_id,)).fetchone()["n"]
    skill_rows = conn.execute("SELECT skill, details_json FROM attempts WHERE user_id = ?", (user_id,)).fetchall()
    distinct_skills = set()
    for row in skill_rows:
        if row["skill"] in {"logic", "maths", "memory", "focus", "verbal", "interview"}:
            distinct_skills.add(row["skill"])
        if row["skill"] == "boss":
            try:
                details = json.loads(row["details_json"])
            except (ValueError, TypeError):
                details = {}
            for stage in details.get("stages", []) if isinstance(details, dict) else []:
                if isinstance(stage, dict) and stage.get("skill") in {"logic", "maths", "memory", "focus", "verbal", "interview"}:
                    distinct_skills.add(stage["skill"])
    possible = []
    if attempt_count >= 1:
        possible.append(("first_attempt", "First Step"))
    if attempt_count >= 10:
        possible.append(("ten_attempts", "Consistent Practice"))
    if len(distinct_skills) >= 4:
        possible.append(("skill_explorer", "Skill Explorer"))
    for key, label in possible:
        conn.execute(
            "INSERT INTO badges(user_id, badge_key, label, earned_at) VALUES (?, ?, ?, ?) ON CONFLICT(user_id, badge_key) DO NOTHING",
            (user_id, key, label, now),
        )


def record_attempt(
    user_id: int,
    attempt_key: str,
    arena: str,
    skill: str,
    level: str,
    score: float,
    max_score: float,
    duration_seconds: float = 0,
    xp_earned: int = 0,
    details: dict[str, Any] | None = None,
    completed_at: str | None = None,
    db_path: str | Path = DB_PATH,
) -> bool:
    """Save one completed attempt and its XP atomically; duplicate keys award nothing."""
    key_value = str(attempt_key or "").strip()[:128]
    arena_value, skill_value, level_value = str(arena or "").strip(), str(skill or "").strip(), str(level or "").strip()
    if not key_value or not arena_value or not skill_value or not level_value:
        raise ValueError("attempt key, arena, skill, and level are required")
    score_value, max_value = float(score), float(max_score)
    duration_value, xp_value = float(duration_seconds), int(xp_earned)
    if not math.isfinite(score_value) or not math.isfinite(max_value) or max_value <= 0 or score_value < 0 or score_value > max_value:
        raise ValueError("score must be finite and between zero and a positive max_score")
    if not math.isfinite(duration_value) or duration_value < 0 or xp_value < 0:
        raise ValueError("duration and XP must be non-negative")
    accuracy = min(100.0, max(0.0, score_value / max_value * 100))
    timestamp = completed_at or datetime.now().astimezone().isoformat(timespec="seconds")
    details_text = json.dumps(details or {}, ensure_ascii=False, separators=(",", ":"))
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO attempts(
                   attempt_key, user_id, arena, skill, level, score, max_score, accuracy,
                   duration_seconds, xp_earned, details_json, completed_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(attempt_key) DO NOTHING""",
            (key_value, int(user_id), arena_value[:100], skill_value[:30], level_value[:40],
             score_value, max_value, accuracy, duration_value, xp_value, details_text, timestamp),
        )
        if cursor.rowcount == 0:
            return False
        conn.execute("UPDATE users SET xp = xp + ? WHERE id = ?", (xp_value, int(user_id)))
        _award_automatic_badges(conn, int(user_id), timestamp)
        if str(arena).casefold() == "mind boss battle":
            conn.execute(
                "INSERT INTO badges(user_id, badge_key, label, earned_at) VALUES (?, 'boss_finisher', 'Mind Boss Finisher', ?) ON CONFLICT(user_id, badge_key) DO NOTHING",
                (int(user_id), timestamp),
            )
        return True


def list_attempts(user_id: int, db_path: str | Path = DB_PATH, limit: int | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM attempts WHERE user_id = ? ORDER BY completed_at ASC, id ASC"
    params: tuple[Any, ...] = (int(user_id),)
    if limit is not None:
        query = "SELECT * FROM (SELECT * FROM attempts WHERE user_id = ? ORDER BY completed_at DESC, id DESC LIMIT ?) ORDER BY completed_at ASC, id ASC"
        params = (int(user_id), max(0, int(limit)))
    with _connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["details"] = json.loads(item.pop("details_json"))
        except (ValueError, TypeError):
            item["details"] = {}
        result.append(item)
    return result


def upsert_high_score(player: str, arena: str, level: str, score: float, unit: str = "points", db_path: str | Path = DB_PATH) -> dict[str, Any]:
    name = " ".join(str(player).split())[:24] or "Player"
    value = float(score)
    if not math.isfinite(value):
        raise ValueError("score must be a finite number")
    updated = datetime.now().date().isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO high_scores(player, arena, level, score, unit, updated)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(player COLLATE NOCASE, arena, level) DO UPDATE SET
                 score=excluded.score, unit=excluded.unit, updated=excluded.updated
               WHERE excluded.score > high_scores.score""",
            (name, str(arena)[:80], str(level)[:40], value, str(unit)[:40], updated),
        )
        row = conn.execute(
            "SELECT player, arena, level, score, unit, updated FROM high_scores WHERE player = ? COLLATE NOCASE AND arena = ? AND level = ?",
            (name, str(arena)[:80], str(level)[:40]),
        ).fetchone()
        return dict(row)


def list_high_scores(db_path: str | Path = DB_PATH) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT player, arena, level, score, unit, updated FROM high_scores ORDER BY score DESC, player COLLATE NOCASE").fetchall()
    return [dict(row) for row in rows]


def claim_mission(user_id: int, mission_key: str, period_key: str, xp_earned: int, db_path: str | Path = DB_PATH) -> bool:
    xp_value = max(0, int(xp_earned))
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO mission_claims(user_id, mission_key, period_key, xp_earned, claimed_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id, mission_key, period_key) DO NOTHING",
            (int(user_id), str(mission_key), str(period_key), xp_value, timestamp),
        )
        if cursor.rowcount == 0:
            return False
        conn.execute("UPDATE users SET xp = xp + ? WHERE id = ?", (xp_value, int(user_id)))
        conn.execute(
            "INSERT INTO badges(user_id, badge_key, label, earned_at) VALUES (?, ?, ?, ?) ON CONFLICT(user_id, badge_key) DO NOTHING",
            (int(user_id), f"mission_{mission_key}", "Mission Complete", timestamp),
        )
        return True


def list_mission_claims(user_id: int, db_path: str | Path = DB_PATH) -> set[tuple[str, str]]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT mission_key, period_key FROM mission_claims WHERE user_id = ?", (int(user_id),)).fetchall()
    return {(row["mission_key"], row["period_key"]) for row in rows}


def list_badges(user_id: int, db_path: str | Path = DB_PATH) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT badge_key, label, earned_at FROM badges WHERE user_id = ? ORDER BY earned_at ASC, id ASC", (int(user_id),)).fetchall()
    return [dict(row) for row in rows]


def award_badge(user_id: int, badge_key: str, label: str, db_path: str | Path = DB_PATH) -> bool:
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO badges(user_id, badge_key, label, earned_at) VALUES (?, ?, ?, ?) ON CONFLICT(user_id, badge_key) DO NOTHING",
            (int(user_id), str(badge_key), str(label)[:80], datetime.now().astimezone().isoformat(timespec="seconds")),
        )
        return cursor.rowcount == 1
