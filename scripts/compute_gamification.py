"""Deterministic telemetry aggregation, streak engine, XP curve, Grade, and Skill Tree evaluator."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from scripts.config import (
    DEFAULT_LANGUAGE_COLOR,
    GRADE_THRESHOLDS,
    LANGUAGE_COLORS,
    LEVEL_TITLES,
    QUEST_SPECS,
    RARITY_COLOR_KEYS,
    SKILL_SPECS,
    XP_WEIGHTS,
    SkillSpec,
)


@dataclass(frozen=True)
class LanguageShare:
    """Single programming language byte share across owned repositories."""

    name: str
    bytes_count: int
    percentage: float
    color: str
    repo_count: int = 0
    mastery: str = "ACTIVE"
    pips: int = 2
    rarity: str = "RARE"


@dataclass(frozen=True)
class GradePillar:
    """Single transparent scoring pillar contributing to the overall Grade."""

    key: str
    label: str
    score: float
    max_score: float


@dataclass(frozen=True)
class SkillNodeEval:
    """Evaluated skill tree node with verified repo count, rarity, and mastery status."""

    key: str
    name: str
    branch: str
    branch_title: str
    rarity: str
    rarity_color_key: str
    mastery: str
    pips: int
    repo_count: int
    verified_repo_count: int


@dataclass(frozen=True)
class QuestProgress:
    """Evaluated state for a verifiable developer quest."""

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
    """Complete deterministic telemetry, grade, skill tree & quest snapshot."""

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
    tested_repos: int = 0
    total_test_files: int = 0
    docker_repos: int = 0
    grade: str = "B"
    grade_score: int = 60
    next_grade_hint: str = ""
    grade_pillars: list[GradePillar] = field(default_factory=list)
    skill_nodes: list[SkillNodeEval] = field(default_factory=list)

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


def _classify_language_mastery(pct: float, repo_count: int) -> tuple[str, int, str]:
    if pct >= 15.0 and repo_count >= 4:
        return "MASTERED", 4, "LEGENDARY"
    if pct >= 2.0 and repo_count >= 2:
        return "PROFICIENT", 3, "EPIC"
    if pct >= 1.0:
        return "ACTIVE", 2, "RARE"
    return "EXPLORING", 1, "UNCOMMON"


def _repo_matches_skill(repo: dict[str, Any], spec: SkillSpec) -> bool:
    if repo.get("is_empty", False):
        return False
    langs = repo.get("languages") or {}
    if any(lang in langs for lang in spec.match_languages):
        return True
    pkgs = [str(p).lower() for p in (repo.get("packages") or [])]
    if any(
        pkg == pat or (pat.endswith("/") and pkg.startswith(pat)) or (len(pat) >= 5 and pkg.startswith(pat))
        for pkg in pkgs
        for pat in spec.match_packages
    ):
        return True
    if spec.require_ci and repo.get("has_ci", False):
        return True
    if spec.require_docker and repo.get("has_docker", False):
        return True
    if spec.require_tests and int(repo.get("test_file_count", 0)) > 0:
        return True
    return False


def _evaluate_skill_nodes(repos: list[dict[str, Any]]) -> list[SkillNodeEval]:
    nodes: list[SkillNodeEval] = []
    for spec in SKILL_SPECS:
        matched = [r for r in repos if _repo_matches_skill(r, spec)]
        repo_cnt = len(matched)
        verified_cnt = sum(
            1
            for r in matched
            if r.get("has_ci", False) or int(r.get("test_file_count", 0)) > 0 or r.get("has_readme", False)
        )
        strict_verified = sum(
            1 for r in matched if r.get("has_ci", False) or int(r.get("test_file_count", 0)) > 0
        )

        if repo_cnt >= 4 and strict_verified >= 2:
            mastery, pips = "MASTERED", 4
        elif repo_cnt >= 2 and verified_cnt >= 1:
            mastery, pips = "PROFICIENT", 3
        elif repo_cnt >= 1 and verified_cnt >= 1:
            mastery, pips = "ACTIVE", 2
        elif repo_cnt >= 1:
            mastery, pips = "EXPLORING", 1
        else:
            mastery, pips = "LOCKED", 0

        nodes.append(
            SkillNodeEval(
                key=spec.key,
                name=spec.name,
                branch=spec.branch,
                branch_title=spec.branch_title,
                rarity=spec.rarity,
                rarity_color_key=RARITY_COLOR_KEYS[spec.rarity],
                mastery=mastery,
                pips=pips,
                repo_count=repo_cnt,
                verified_repo_count=verified_cnt,
            )
        )
    return nodes


def _compute_grade(
    *,
    contribs_12m: int,
    active_days: int,
    longest_streak: int,
    non_empty_repos: int,
    documented_repos: int,
    ci_repos: int,
    tested_repos: int,
    languages_ge_1pct: int,
    merged_prs: int,
    external_stars: int,
    skill_nodes: list[SkillNodeEval],
) -> tuple[str, int, list[GradePillar], str]:
    denom_repos = max(1, non_empty_repos)
    output_pts = round(
        min(12.0, (contribs_12m / 1200.0) * 12.0)
        + min(8.0, (active_days / 180.0) * 8.0)
        + min(5.0, (longest_streak / 14.0) * 5.0),
        1,
    )
    # Count documented repos or tests gracefully even when test_file_count is omitted in lightweight mocks
    effective_tested = tested_repos if tested_repos > 0 else ci_repos
    qa_pts = round(
        min(12.0, (ci_repos / denom_repos) * 12.0)
        + min(10.0, (effective_tested / denom_repos) * 10.0)
        + min(8.0, (documented_repos / denom_repos) * 8.0),
        1,
    )
    depth_pts = round(
        min(10.0, (non_empty_repos / 10.0) * 10.0)
        + min(10.0, (languages_ge_1pct / 6.0) * 10.0),
        1,
    )
    strong_skills = sum(1 for s in skill_nodes if s.pips >= 3)
    breadth_pts = round(min(15.0, (strong_skills / 11.0) * 15.0), 1)
    collab_pts = round(
        min(5.0, (merged_prs / 10.0) * 5.0)
        + min(5.0, (external_stars / 10.0) * 5.0),
        1,
    )

    pillars = [
        GradePillar(key="output", label="OUT", score=output_pts, max_score=25.0),
        GradePillar(key="qa", label="QA", score=qa_pts, max_score=30.0),
        GradePillar(key="depth", label="DEP", score=depth_pts, max_score=20.0),
        GradePillar(key="breadth", label="DOM", score=breadth_pts, max_score=15.0),
        GradePillar(key="collab", label="PR★", score=collab_pts, max_score=10.0),
    ]
    total_score = min(100, int(round(sum(p.score for p in pillars))))

    grade = "C"
    for min_pts, letter in GRADE_THRESHOLDS:
        if total_score >= min_pts:
            grade = letter
            break

    higher = [(pts, lbl) for pts, lbl in GRADE_THRESHOLDS if pts > total_score]
    if higher:
        next_pts, next_letter = min(higher, key=lambda x: x[0])
        hint = f"+{next_pts - total_score} pts to {next_letter}"
    else:
        hint = "Max Rank S+ Achieved"

    return grade, total_score, pillars, hint


def evaluate_metrics(raw: dict[str, Any], *, reference_date: date | None = None) -> GamificationReport:
    """Compute deterministic telemetry, grade, skill tree, and quests from normalized raw JSON."""
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
    tested_repos = sum(1 for r in repos if int(r.get("test_file_count", 0)) > 0)
    total_test_files = sum(int(r.get("test_file_count", 0)) for r in repos)
    docker_repos = sum(1 for r in repos if r.get("has_docker", False))
    external_stars = sum(int(r.get("external_stars", 0)) for r in repos)
    merged_prs = int(prs.get("merged_total", 0))
    external_merged_prs = int(prs.get("merged_external", 0))

    created_dt = date.fromisoformat(user["created_at"][:10])
    account_age_days = max(0, (ref - created_dt).days)

    lang_totals: dict[str, int] = {}
    lang_repos: dict[str, int] = {}
    for repo in repos:
        for lang, bcount in (repo.get("languages") or {}).items():
            if int(bcount) <= 0:
                continue
            lang_totals[lang] = lang_totals.get(lang, 0) + int(bcount)
            lang_repos[lang] = lang_repos.get(lang, 0) + 1

    total_bytes = sum(lang_totals.values())
    sorted_langs = sorted(lang_totals.items(), key=lambda kv: (-kv[1], kv[0]))
    languages_ge_1pct = sum(
        1 for _, bcount in sorted_langs if total_bytes > 0 and (bcount / total_bytes) * 100.0 >= 1.0
    )

    top_languages: list[LanguageShare] = []
    for lang, bcount in sorted_langs[:6]:
        pct = round((bcount / total_bytes) * 100.0, 1) if total_bytes > 0 else 0.0
        rcount = lang_repos.get(lang, 0)
        mastery, pips, rarity = _classify_language_mastery(pct, rcount)
        top_languages.append(
            LanguageShare(
                name=lang,
                bytes_count=bcount,
                percentage=pct,
                color=LANGUAGE_COLORS.get(lang, DEFAULT_LANGUAGE_COLOR),
                repo_count=rcount,
                mastery=mastery,
                pips=pips,
                rarity=rarity,
            )
        )

    skill_nodes = _evaluate_skill_nodes(repos)
    grade, grade_score, grade_pillars, next_grade_hint = _compute_grade(
        contribs_12m=contribs_12m,
        active_days=active_days,
        longest_streak=longest_streak,
        non_empty_repos=non_empty_repos,
        documented_repos=documented_repos,
        ci_repos=ci_repos,
        tested_repos=tested_repos,
        languages_ge_1pct=languages_ge_1pct,
        merged_prs=merged_prs,
        external_stars=external_stars,
        skill_nodes=skill_nodes,
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
        tested_repos=tested_repos,
        total_test_files=total_test_files,
        docker_repos=docker_repos,
        grade=grade,
        grade_score=grade_score,
        next_grade_hint=next_grade_hint,
        grade_pillars=grade_pillars,
        skill_nodes=skill_nodes,
    )
