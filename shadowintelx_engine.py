"""Explainable skill, adaptation, mission, and report logic."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from html import escape as html_escape
import math
from typing import Any, Iterable


SKILLS = {
    "logic": {"label": "Logic", "page": "IQ teller & logic", "action": "Solve a short reasoning set."},
    "maths": {"label": "Maths", "page": "Math speed arena", "action": "Complete a focused calculation sprint."},
    "memory": {"label": "Memory", "page": "Memory games", "action": "Replay a memory challenge and extend your recall."},
    "focus": {"label": "Focus", "page": "Focus arena", "action": "Run a timed focus challenge."},
    "verbal": {"label": "Verbal", "page": "Verbal arena", "action": "Practice a short communication round."},
    "interview": {"label": "Interview", "page": "Interview practice", "action": "Practice a structured role-based answer."},
}

LEVELS = ("Beginner", "Intermediate", "Advanced")
RANKS = ((0, "Initiate"), (100, "Apprentice"), (300, "Operative"), (600, "Specialist"), (1000, "Shadow Elite"), (2000, "Shadow Master"))
NAVIGATION_PAGES = (
    "Home", "Interview practice", "IQ teller & logic", "Math speed arena", "Memory games",
    "Verbal arena", "Focus arena", "High scores", "Progress & results", "Skill DNA & Shadow Coach",
    "Shadow Missions", "Mind Boss Battles", "Performance Intelligence",
)


def rank_for_xp(xp: int) -> dict[str, Any]:
    points = max(0, int(xp))
    index = max(i for i, (threshold, _) in enumerate(RANKS) if points >= threshold)
    threshold, label = RANKS[index]
    if index + 1 < len(RANKS):
        next_threshold, next_label = RANKS[index + 1]
        progress = (points - threshold) / (next_threshold - threshold)
        next_xp = next_threshold - points
    else:
        next_threshold, next_label = threshold, label
        progress, next_xp = 1.0, 0
    return {"name": label, "xp": points, "threshold": threshold, "next_rank": next_label, "next_xp": next_xp, "progress": min(1.0, max(0.0, progress))}


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _accuracy(attempt: dict[str, Any]) -> float:
    try:
        value = float(attempt.get("accuracy", 0))
    except (TypeError, ValueError):
        return 0.0
    return min(100.0, max(0.0, value))


def _skill_events(attempts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    events = []
    for attempt in attempts:
        skill = str(attempt.get("skill", "")).casefold()
        if skill in SKILLS:
            events.append(attempt)
            continue
        details = attempt.get("details") or {}
        if skill == "boss" and isinstance(details, dict):
            for index, stage in enumerate(details.get("stages", [])):
                if not isinstance(stage, dict) or str(stage.get("skill", "")).casefold() not in SKILLS:
                    continue
                virtual = dict(attempt)
                virtual["skill"] = str(stage["skill"]).casefold()
                virtual["accuracy"] = stage.get("accuracy", 0)
                virtual["level"] = stage.get("level", attempt.get("level", "Beginner"))
                virtual["id"] = int(attempt.get("id", 0)) * 100 + index
                events.append(virtual)
    return events


def build_skill_profile(attempts: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attempt in _skill_events(attempts):
        skill = str(attempt.get("skill", "")).casefold()
        if skill in SKILLS:
            grouped[skill].append(attempt)
    profile = {}
    for key, definition in SKILLS.items():
        rows = sorted(grouped.get(key, []), key=lambda item: (str(item.get("completed_at", "")), int(item.get("id", 0))))
        if not rows:
            profile[key] = {"key": key, "label": definition["label"], "page": definition["page"], "accuracy": None, "attempts": 0, "recent_accuracy": None, "trend": None}
            continue
        scores = [_accuracy(row) for row in rows]
        recent = scores[-5:]
        prior = scores[-10:-5]
        recent_average = sum(recent) / len(recent)
        prior_average = sum(prior) / len(prior) if prior else None
        trend = round(recent_average - prior_average, 1) if prior_average is not None else None
        profile[key] = {
            "key": key,
            "label": definition["label"],
            "page": definition["page"],
            "accuracy": round(sum(scores) / len(scores), 1),
            "attempts": len(scores),
            "recent_accuracy": round(recent_average, 1),
            "trend": trend,
            "latest_at": rows[-1].get("completed_at"),
        }
    return profile


def skill_radar_svg(profile: dict[str, dict[str, Any]]) -> str:
    """Return an accessible radar chart; missing skills remain explicitly unplotted."""
    width, height, cx, cy, radius = 420, 390, 210, 184, 122
    keys = list(SKILLS)
    points = []
    labels = []
    axes = []
    measured = []
    for index, key in enumerate(keys):
        angle = math.radians(-90 + index * 60)
        dx, dy = math.cos(angle), math.sin(angle)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + dx * radius:.1f}" y2="{cy + dy * radius:.1f}" class="axis"/>')
        definition = profile.get(key, {})
        accuracy = definition.get("accuracy")
        label = SKILLS[key]["label"]
        label_value = f"{label} {accuracy:g}%" if accuracy is not None else f"{label}, no saved attempts"
        if accuracy is not None:
            value_radius = radius * min(100.0, max(0.0, float(accuracy))) / 100
            points.append(f"{cx + dx * value_radius:.1f},{cy + dy * value_radius:.1f}")
            measured.append((cx + dx * value_radius, cy + dy * value_radius))
        label_x, label_y = cx + dx * (radius + 31), cy + dy * (radius + 31)
        anchor = "middle" if abs(dx) < .25 else ("start" if dx > 0 else "end")
        labels.append(f'<text x="{label_x:.1f}" y="{label_y + 4:.1f}" text-anchor="{anchor}" class="label">{html_escape(label_value)}</text>')
    grids = []
    for scale in (.2, .4, .6, .8, 1.0):
        coords = []
        for index in range(6):
            angle = math.radians(-90 + index * 60)
            coords.append(f"{cx + math.cos(angle) * radius * scale:.1f},{cy + math.sin(angle) * radius * scale:.1f}")
        grids.append(f'<polygon points="{" ".join(coords)}" class="grid"/>')
    value_shape = ""
    if len(points) == len(keys):
        value_shape = f'<polygon points="{" ".join(points)}" class="profile"/>'
    point_circles = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" class="point"/>' for x, y in measured)
    values = ", ".join(labelspec for labelspec in [
        f"{SKILLS[key]['label']} {profile[key]['accuracy']:g}%" if profile.get(key, {}).get("accuracy") is not None else f"{SKILLS[key]['label']} no saved attempts"
        for key in keys
    ])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Skill DNA radar: {html_escape(values)}">'
        '<style>.grid{fill:none;stroke:#ff43552c;stroke-width:1}.axis{stroke:#ff43552b;stroke-width:1}.profile{fill:#ff43552b;stroke:#ff536f;stroke-width:2.5;stroke-linejoin:round}.point{fill:#ff7a68;stroke:#fff0f1;stroke-width:1.2}.label{fill:#eadde0;font:12px Arial,sans-serif}</style>'
        f'<title>Skill DNA based on saved practice results</title>{"".join(grids)}{"".join(axes)}{value_shape}{point_circles}{"".join(labels)}</svg>'
    )


def recommend_difficulty(attempts: Iterable[dict[str, Any]], skill: str, default: str = "Beginner") -> dict[str, Any]:
    valid_default = default if default in LEVELS else "Beginner"
    rows = [row for row in _skill_events(attempts) if str(row.get("skill", "")).casefold() == skill.casefold()]
    rows.sort(key=lambda item: (str(item.get("completed_at", "")), int(item.get("id", 0))))
    recent = rows[-5:]
    if not recent:
        return {"level": valid_default, "reason": "No saved results for this skill yet. Start at your selected level."}
    recent_avg = sum(_accuracy(row) for row in recent) / len(recent)
    last_level = str(recent[-1].get("level", valid_default))
    current_index = LEVELS.index(last_level) if last_level in LEVELS else LEVELS.index(valid_default)
    if len(recent) >= 3 and recent_avg >= 85 and current_index < len(LEVELS) - 1:
        level = LEVELS[current_index + 1]
        reason = f"Your last {len(recent)} saved rounds averaged {recent_avg:.0f}% of their scoring rubric, so the next level is suggested."
    elif len(recent) >= 2 and recent_avg < 50 and current_index > 0:
        level = LEVELS[current_index - 1]
        reason = f"Your last {len(recent)} saved rounds averaged {recent_avg:.0f}% of their scoring rubric; a lower level can help reinforce the fundamentals."
    else:
        level = last_level if last_level in LEVELS else valid_default
        reason = f"Your last {len(recent)} saved rounds averaged {recent_avg:.0f}% of their scoring rubric; continue at this level and build consistency."
    return {"level": level, "reason": reason}


def coach_recommendation(attempts: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    rows = list(attempts)
    profile = build_skill_profile(rows)
    practiced = [item for item in profile.values() if item["attempts"]]
    if not practiced:
        return None
    weakest = min(practiced, key=lambda item: (item["recent_accuracy"], item["attempts"]))
    strongest = max(practiced, key=lambda item: (item["recent_accuracy"], item["attempts"]))
    recent_rows = [row for row in _skill_events(rows) if str(row.get("skill", "")).casefold() == weakest["key"]]
    recent_rows.sort(key=lambda item: (str(item.get("completed_at", "")), int(item.get("id", 0))))
    sample_size = min(5, len(recent_rows))
    return {
        "skill": weakest["key"],
        "label": weakest["label"],
        "page": weakest["page"],
        "accuracy": weakest["recent_accuracy"],
        "attempts": weakest["attempts"],
        "sample_size": sample_size,
        "strength": strongest["label"],
        "strength_accuracy": strongest["recent_accuracy"],
        "explanation": f"Your {weakest['label'].lower()} score averaged {weakest['recent_accuracy']:.0f}% of the arena scoring rubric across your last {sample_size} saved round(s). A short practice round in this area can help reinforce it.",
        "exercise": SKILLS[weakest["key"]]["action"],
    }


def build_training_plan(attempts: Iterable[dict[str, Any]], days: int = 7) -> list[dict[str, str]]:
    count = max(1, min(14, int(days)))
    profile = build_skill_profile(attempts)
    practiced = [item for item in profile.values() if item["attempts"]]
    if practiced:
        priority = min(practiced, key=lambda item: (item["recent_accuracy"], item["attempts"]))["key"]
    else:
        priority = "interview"
    order = [priority] + [key for key in SKILLS if key != priority]
    plan = []
    for day_number in range(1, count + 1):
        skill = order[(day_number - 1) % len(order)]
        definition = SKILLS[skill]
        data = profile[skill]
        if data["attempts"]:
            objective = f"Build on your saved {data['recent_accuracy']:.0f}% recent result with one focused round."
        else:
            objective = f"Start with one beginner round and establish a baseline for {definition['label'].lower()}."
        plan.append({"day": f"Day {day_number}", "skill": definition["label"], "page": definition["page"], "objective": objective})
    return plan


def _day_for_attempt(attempt: dict[str, Any]) -> date | None:
    parsed = _parse_datetime(attempt.get("completed_at"))
    return parsed.date() if parsed else None


def mission_snapshot(attempts: Iterable[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now().astimezone()
    today = current.date()
    iso = today.isocalendar()
    week_key = f"{iso.year}-W{iso.week:02d}"
    dated = [(row, _day_for_attempt(row)) for row in attempts]
    dated = [(row, day) for row, day in dated if day is not None]
    today_rows = [row for row, day in dated if day == today]
    week_rows = [row for row, day in dated if day.isocalendar()[:2] == iso[:2]]
    def session_key(row: dict[str, Any]) -> str:
        details = row.get("details") or {}
        return str(details.get("session_group") or row.get("attempt_key", row.get("id", id(row))))
    today_count = len({session_key(row) for row in today_rows})
    week_count = len({session_key(row) for row in week_rows})
    week_skills = set()
    for row in week_rows:
        raw_skill = str(row.get("skill", ""))
        if raw_skill in SKILLS:
            week_skills.add(raw_skill)
        details = row.get("details") or {}
        for stage in details.get("stages", []) if isinstance(details, dict) else []:
            if isinstance(stage, dict) and stage.get("skill") in SKILLS:
                week_skills.add(stage["skill"])
    days = {day for _, day in dated}
    anchor = today if today in days else today - timedelta(days=1)
    streak = 0
    cursor = anchor
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    longest = 0
    for day in sorted(days):
        if day - timedelta(days=1) not in days:
            length, cursor = 0, day
            while cursor in days:
                length += 1
                cursor += timedelta(days=1)
            longest = max(longest, length)
    return {
        "today": today.isoformat(),
        "week": week_key,
        "today_attempts": today_count,
        "week_attempts": week_count,
        "week_skills": len(week_skills),
        "current_streak": streak,
        "longest_streak": longest,
        "missions": [
            {"key": "daily_two", "period": today.isoformat(), "title": "Daily Momentum", "description": "Complete 2 practice rounds today.", "progress": min(2, today_count), "goal": 2, "xp": 20, "ready": today_count >= 2},
            {"key": "weekly_five", "period": week_key, "title": "Weekly Builder", "description": "Complete 5 practice rounds this week.", "progress": min(5, week_count), "goal": 5, "xp": 75, "ready": week_count >= 5},
            {"key": "weekly_four_skills", "period": week_key, "title": "Skill Explorer", "description": "Practice 4 different skill arenas this week.", "progress": min(4, len(week_skills)), "goal": 4, "xp": 100, "ready": len(week_skills) >= 4},
        ],
    }


def performance_report(attempts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(attempts)
    profile = build_skill_profile(rows)
    practiced = [item for item in profile.values() if item["attempts"]]
    if not rows:
        return {"attempt_count": 0, "accuracy": None, "accuracy_attempt_count": 0, "average_duration": None, "xp_earned": 0, "strongest": None, "weakest": None, "profile": profile, "recent": [], "recommendation": None}
    strongest = max(practiced, key=lambda item: item["recent_accuracy"]) if practiced else None
    weakest = min(practiced, key=lambda item: item["recent_accuracy"]) if practiced else None
    durations = [max(0.0, float(row.get("duration_seconds", 0) or 0)) for row in rows]
    rec = coach_recommendation(rows)
    accuracy_rows = []
    for row in rows:
        details = row.get("details")
        metric_name = details.get("metric_name", "accuracy") if isinstance(details, dict) else "accuracy"
        if str(metric_name).casefold() == "accuracy":
            accuracy_rows.append(row)
    return {
        "attempt_count": len(rows),
        "accuracy": round(sum(_accuracy(row) for row in accuracy_rows) / len(accuracy_rows), 1) if accuracy_rows else None,
        "accuracy_attempt_count": len(accuracy_rows),
        "average_duration": round(sum(durations) / len(durations), 1),
        "xp_earned": sum(max(0, int(row.get("xp_earned", 0) or 0)) for row in rows),
        "strongest": strongest,
        "weakest": weakest,
        "profile": profile,
        "recent": rows[-20:],
        "recommendation": rec,
    }
