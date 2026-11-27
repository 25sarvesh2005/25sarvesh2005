"""Unit tests for deterministic telemetry aggregation and gamification."""

from __future__ import annotations

from datetime import date, timedelta

from scripts.compute_gamification import compute_level, compute_streaks, evaluate_metrics


def _sample_raw_metrics() -> dict:
    return {
        "schema_version": 1,
        "generated_at_utc": "2026-11-26T16:00:00Z",
        "user": {
            "login": "25sarvesh2005",
            "name": "Sarvesh Sharma",
            "created_at": "2023-09-24T02:46:47Z",
            "followers": 12,
            "following": 16,
            "public_repos_count": 10,
        },
        "contributions": {
            "daily": {
                "2023-09-24": 1,
                "2026-08-10": 4,
                "2026-08-11": 5,
                "2026-08-12": 2,
                "2026-08-13": 1,
                "2026-08-14": 27,
                "2026-08-15": 3,
                "2026-08-16": 2,
                "2026-08-17": 46,
                "2026-08-18": 1,
                "2026-11-23": 1,
            },
            "restricted_count_reported": 0,
        },
        "pull_requests": {
            "merged_total": 1,
            "merged_external": 0,
        },
        "owned_repositories": [
            {
                "name": "REPO-Score",
                "full_name": "25sarvesh2005/REPO-Score",
                "is_empty": False,
                "stargazers_count": 0,
                "external_stars": 0,
                "has_readme": True,
                "has_ci": True,
                "languages": {"Python": 700000, "TypeScript": 100000},
            },
            {
                "name": "telephony_ai",
                "full_name": "25sarvesh2005/telephony_ai",
                "is_empty": False,
                "stargazers_count": 2,
                "external_stars": 1,
                "has_readme": False,
                "has_ci": False,
                "languages": {"Python": 150000, "JavaScript": 50000, "CSS": 40000, "HTML": 40000},
            },
            {
                "name": "canteenapp",
                "full_name": "25sarvesh2005/canteenapp",
                "is_empty": False,
                "stargazers_count": 1,
                "external_stars": 1,
                "has_readme": False,
                "has_ci": False,
                "languages": {"Kotlin": 75000},
            },
            {
                "name": "CityCare_Clinic",
                "full_name": "25sarvesh2005/CityCare_Clinic",
                "is_empty": True,
                "stargazers_count": 0,
                "external_stars": 0,
                "has_readme": False,
                "has_ci": False,
                "languages": {},
            },
        ],
    }


def test_compute_streaks_handles_grace_and_gaps() -> None:
    daily = {
        "2026-11-20": 2,
        "2026-11-21": 4,
        "2026-11-22": 1,
        "2026-11-24": 3,
        "2026-11-25": 5,
    }
    cur_on_26, best = compute_streaks(daily, reference_date=date(2026, 11, 26))
    assert cur_on_26 == 2  # Nov 24-25 still active via Nov 26 grace
    assert best == 3

    cur_on_27, _ = compute_streaks(daily, reference_date=date(2026, 11, 27))
    assert cur_on_27 == 0  # Streak expired after missed Nov 26


def test_compute_level_zero_and_positive() -> None:
    lvl0, title0, xp_in, span, pct = compute_level(0)
    assert lvl0 == 1
    assert title0 == "System Initiate"
    assert xp_in == 0 and span == 20 and pct == 0.0

    lvl12, title12, xp_in_12, span_12, _ = compute_level(2460)
    assert lvl12 == 12
    assert title12 == "Systems Architect"
    assert xp_in_12 == 40
    assert span_12 == 460


def test_evaluate_metrics_counts_and_quests() -> None:
    report = evaluate_metrics(_sample_raw_metrics(), reference_date=date(2026, 11, 26))
    assert report.total_contributions == 93
    assert report.contributions_12m == 92
    assert report.active_days == 11
    assert report.peak_day_contributions == 46
    assert report.longest_streak == 9
    assert report.current_streak == 0
    assert report.owned_repo_count == 4
    assert report.non_empty_owned_repos == 3
    assert report.documented_repos == 1
    assert report.ci_repos == 1
    assert report.external_stars == 2
    assert report.languages_ge_1pct == 6

    by_key = {q.key: q for q in report.quests}
    assert by_key["genesis_commit"].unlocked is True
    assert by_key["week_sprint"].unlocked is True
    assert by_key["first_merge"].unlocked is True
    assert by_key["club_500"].unlocked is False
    assert by_key["os_ally"].unlocked is False
    assert by_key["community_signal"].current == 2
    assert report.grade in {"B", "C", "A", "S", "S+"}
    assert 0 <= report.grade_score <= 100
    assert len(report.skill_nodes) == 16


def test_grade_and_skill_tree_mastery_progression() -> None:
    raw = _sample_raw_metrics()
    for idx in range(5):
        raw["owned_repositories"].append(
            {
                "name": f"service-{idx}",
                "full_name": f"25sarvesh2005/service-{idx}",
                "is_empty": False,
                "stargazers_count": 2,
                "external_stars": 2,
                "has_readme": True,
                "has_ci": True,
                "has_docker": idx < 3,
                "test_file_count": 6,
                "packages": ["fastapi", "pydantic", "psycopg", "pytest", "google-genai", "chromadb", "react"],
                "languages": {"Python": 200000, "TypeScript": 100000},
            }
        )
    report = evaluate_metrics(raw, reference_date=date(2026, 11, 26))
    skills = {s.key: s for s in report.skill_nodes}
    assert skills["python"].mastery == "MASTERED"
    assert skills["fastapi"].mastery == "MASTERED"
    assert skills["docker"].mastery == "PROFICIENT"
    assert skills["docker"].rarity == "EPIC"
    assert report.docker_repos == 3
    assert report.tested_repos == 5
    assert report.grade == "B"  # Low active days (11) & 92 contribs keeps score honest
    assert len(report.grade_pillars) == 5
    assert [p.label for p in report.grade_pillars] == ["Commits", "CI/Tests", "Repos", "Domains", "PR/Stars"]

    # High activity + 150 active days raises score to A/S
    start = date(2026, 6, 1)
    for d in range(150):
        raw["contributions"]["daily"][(start + timedelta(days=d)).isoformat()] = 8
    high_report = evaluate_metrics(raw, reference_date=date(2026, 11, 26))
    assert high_report.grade in {"A", "S", "S+"}
