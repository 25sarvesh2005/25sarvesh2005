"""Deterministic telemetry aggregation, streak engine, XP curve, and quest evaluator."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from scripts.config import (
    DEFAULT_LANGUAGE_COLOR,
    LANGUAGE_COLORS,
    LEVEL_TITLES,
    QUEST_SPECS,
    XP_WEIGHTS,
)


@dataclass(frozen=True)
class LanguageShare:
    """Single programming language byte share across owned repositories."""

    name: str
    bytes_count: int
    percentage: float
    color: str


@dataclass(frozen=True)
class QuestProgress:
    """Evaluated state for a verifiable quest."""

    key: str
    title: str
    current: int
    target: int
    unit: str
    unlocked: bool
    progress_pct: float
    description: str


@dataclass(frozen=True)
class GamificationReport:
    """Complete deterministic telemetry & gamification snapshot."""

    username: str
    display_name: str
    generated_at_utc: str
    total_contributions: int
    contributions_12m: int
    active_days: int
    peak_day_contributions: int
    current_streak: int
    longest_streak: int
    owned_repo_count: int
    non_empty_owned_repos: int
    documented_repos: int
    ci_repos: int
    merged_prs: int
    external_merged_prs: int
    external_stars: int
    languages_ge_1pct: int
    account_age_days: int
    xp: int
    level: int
    level_title: str
    xp_in_level: int
    xp_for_next_level: int
    level_progress_pct: float
    top_languages: list[LanguageShare]
    quests: list[QuestProgress]
    unlocked_count: int
    total_quests: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize dataclass cleanly for JSON snapshot or template contexts."""
        return asdict(self)


def compute_streaks(daily: dict[str, int], *, reference_date: date | None = None) -> tuple[int, int]:
    """Return (current_streak_days, longest_streak_days) from sorted YYYY-MM-DD counts."""
    if not daily:
        return 0, 0

    ref = reference_date or datetime.now(UTC).date()
    parsed: dict[date, int] = {date.fromisoformat(d): int(c) for d, c in daily.items()}
    min_day = min(parsed)
    max_day = max(max(parsed), ref)

    longest = 0
    run = 0
    cursor = min_day
    while cursor <= max_day:
        if parsed.get(cursor, 0) > 0:
            run += 1
            if run > longest:
                longest = run
        else:
            run = 0
        cursor += timedelta(days=1)

    # Standard GitHub streak rule: allow today=0 if yesterday was active.
    current = 0
    check_day = ref if parsed.get(ref, 0) > 0 else ref - timedelta(days=1)
    while check_day >= min_day and parsed.get(check_day, 0) > 0:
        current += 1
        check_day -= timedelta(days=1)

    return current, longest


def compute_level(xp: int) -> tuple[int, str, int, int, float]:
    """Compute level, title, and progress into the next level from total XP."""
    safe_xp = max(0, xp)
    level = int(math.floor(math.sqrt(safe_xp / 20))) + 1
    floor_xp = 20 * ((level - 1) ** 2)
    next_floor_xp = 20 * (level**2)
    xp_in_level = safe_xp - floor_xp
    xp_span = max(1, next_floor_xp - floor_xp)
    pct = round(min(100.0, (xp_in_level / xp_span) * 100.0), 1)

    title = LEVEL_TITLES[-1][1]
    for min_lvl, candidate in LEVEL_TITLES:
        if level >= min_lvl:
            title = candidate
            break
    return level, title, xp_in_level, xp_span, pct


def evaluate_metrics(raw: dict[str, Any], *, reference_date: date | None = None) -> GamificationReport:
    """Compute deterministic telemetry and quests from normalized raw metrics JSON."""
    ref = reference_date or datetime.now(UTC).date()
    user = raw["user"]
    daily: dict[str, int] = raw["contributions"]["daily"]
    repos: list[dict[str, Any]] = raw["owned_repositories"]
    prs = raw["pull_requests"]

    total_contribs = sum(int(v) for v in daily.values())
    cutoff_12m = (ref - timedelta(days=364)).isoformat()
    contribs_12m = sum(int(v) for d, v in daily.items() if cutoff_12m <= d <= ref.isoformat())
    active_days = sum(1 for v in daily.values() if int(v) > 0)
    peak_day = max((int(v) for v in daily.values()), default=0)
    current_streak, longest_streak = compute_streaks(daily, reference_date=ref)

    non_empty_repos = sum(1 for r in repos if not r.get("is_empty", False))
    documented_repos = sum(1 for r in repos if r.get("has_readme", False))
    ci_repos = sum(1 for r in repos if r.get("has_ci", False))
    external_stars = sum(int(r.get("external_stars", 0)) for r in repos)
    merged_prs = int(prs.get("merged_total", 0))
    external_merged_prs = int(prs.get("merged_external", 0))

    created_dt = date.fromisoformat(user["created_at"][:10])
    account_age_days = max(0, (ref - created_dt).days)

    lang_totals: dict[str, int] = {}
    for repo in repos:
        for lang, bcount in (repo.get("languages") or {}).items():
            lang_totals[lang] = lang_totals.get(lang, 0) + int(bcount)

    total_bytes = sum(lang_totals.values())
    sorted_langs = sorted(lang_totals.items(), key=lambda kv: (-kv[1], kv[0]))
    languages_ge_1pct = sum(
        1 for _, bcount in sorted_langs if total_bytes > 0 and (bcount / total_bytes) * 100.0 >= 1.0
    )

    top_languages: list[LanguageShare] = []
    for lang, bcount in sorted_langs[:5]:
        pct = round((bcount / total_bytes) * 100.0, 1) if total_bytes > 0 else 0.0
        top_languages.append(
            LanguageShare(
                name=lang,
                bytes_count=bcount,
                percentage=pct,
                color=LANGUAGE_COLORS.get(lang, DEFAULT_LANGUAGE_COLOR),
            )
        )

    xp = (
        total_contribs * XP_WEIGHTS["contribution"]
        + active_days * XP_WEIGHTS["active_day"]
        + merged_prs * XP_WEIGHTS["merged_pr"]
        + documented_repos * XP_WEIGHTS["documented_repo"]
        + ci_repos * XP_WEIGHTS["ci_repo"]
        + external_stars * XP_WEIGHTS["external_star"]
        + languages_ge_1pct * XP_WEIGHTS["language_ge_1pct"]
    )
    level, level_title, xp_in_level, xp_span, level_pct = compute_level(xp)

    metric_lookup: dict[str, int] = {
        "account_age_days": account_age_days,
        "non_empty_owned_repos": non_empty_repos,
        "documented_repos": documented_repos,
        "ci_repos": ci_repos,
        "languages_ge_1pct": languages_ge_1pct,
        "total_contributions": total_contribs,
        "longest_streak": longest_streak,
        "merged_prs": merged_prs,
        "external_merged_prs": external_merged_prs,
        "external_stars": external_stars,
    }

    quests: list[QuestProgress] = []
    for spec in QUEST_SPECS:
        cur = metric_lookup[spec.metric_key]
        unlocked = cur >= spec.target
        pct = round(min(100.0, (cur / max(1, spec.target)) * 100.0), 1)
        quests.append(
            QuestProgress(
                key=spec.key,
                title=spec.title,
                current=cur,
                target=spec.target,
                unit=spec.unit,
                unlocked=unlocked,
                progress_pct=pct,
                description=spec.description,
            )
        )

    unlocked_count = sum(1 for q in quests if q.unlocked)
    return GamificationReport(
        username=user["login"],
        display_name=user["name"],
        generated_at_utc=raw["generated_at_utc"],
        total_contributions=total_contribs,
        contributions_12m=contribs_12m,
        active_days=active_days,
        peak_day_contributions=peak_day,
        current_streak=current_streak,
        longest_streak=longest_streak,
        owned_repo_count=len(repos),
        non_empty_owned_repos=non_empty_repos,
        documented_repos=documented_repos,
        ci_repos=ci_repos,
        merged_prs=merged_prs,
        external_merged_prs=external_merged_prs,
        external_stars=external_stars,
        languages_ge_1pct=languages_ge_1pct,
        account_age_days=account_age_days,
        xp=xp,
        level=level,
        level_title=level_title,
        xp_in_level=xp_in_level,
        xp_for_next_level=xp_span,
        level_progress_pct=level_pct,
        top_languages=top_languages,
        quests=quests,
        unlocked_count=unlocked_count,
        total_quests=len(quests),
    )
