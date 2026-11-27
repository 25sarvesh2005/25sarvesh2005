"""Configuration, GBA Pokémon Battle & Pokédex palettes, XP weights, and quest definitions."""

from __future__ import annotations

from dataclasses import dataclass

GITHUB_USERNAME = "25sarvesh2005"
DISPLAY_NAME = "Sarvesh Sharma"
API_BASE = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"

# Verified GitHub Linguist palette for languages present in owned repos
LANGUAGE_COLORS: dict[str, str] = {
    "Python": "#3572A5",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "CSS": "#563D7C",
    "HTML": "#E34C26",
    "Kotlin": "#A97BFF",
    "Power Query": "#E69F00",
    "Shell": "#89E051",
    "Dockerfile": "#384D54",
    "PowerShell": "#012456",
    "Batchfile": "#C1F12E",
    "Mako": "#7E858D",
}
DEFAULT_LANGUAGE_COLOR = "#8B949E"

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "name": "Night Cavern GBA",
        "bg_canvas": "#0D1117",
        "bg_card": "#131926",
        "bg_panel": "#1A2234",
        "bg_hud": "#182032",
        "bg_hud_inner": "#1F2940",
        "bg_dialog": "#15232E",
        "bg_dialog_rim": "#2A4A5E",
        "bg_track": "#253048",
        "sky_top": "#0A1124",
        "sky_bot": "#172546",
        "hill": "#121E36",
        "field_top": "#16243D",
        "field_bot": "#1B2C4A",
        "plat_rim": "#233556",
        "plat_top": "#314972",
        "plat_hi": "#415E8F",
        "dex_shell": "#6B1224",
        "dex_shell_hi": "#991B35",
        "dex_hinge": "#450B17",
        "dex_lcd": "#0F1D1A",
        "dex_dot": "#1B332D",
        "border": "#364666",
        "border_hi": "#5B74A6",
        "text_primary": "#EDF2FA",
        "text_muted": "#9AAAD0",
        "text_subtle": "#6F80A6",
        "accent_primary": "#38BDF8",
        "accent_pill_text": "#09101D",
        "accent_signal": "#34D399",
        "accent_amber": "#FBBF24",
        "accent_boss": "#F43F5E",
        "accent_arcane": "#A78BFA",
        "shadow": "#070C17",
    },
    "light": {
        "name": "FireRed Route GBA",
        "bg_canvas": "#FFFFFF",
        "bg_card": "#F5F1E3",
        "bg_panel": "#FAF7ED",
        "bg_hud": "#FAF7E8",
        "bg_hud_inner": "#EFE9D1",
        "bg_dialog": "#233A47",
        "bg_dialog_rim": "#5A909E",
        "bg_track": "#DCD4B8",
        "sky_top": "#C8E8F8",
        "sky_bot": "#EAF5DC",
        "hill": "#88C088",
        "field_top": "#CBE6AF",
        "field_bot": "#AED68D",
        "plat_rim": "#76A868",
        "plat_top": "#B8DF98",
        "plat_hi": "#D4EDBC",
        "dex_shell": "#C82333",
        "dex_shell_hi": "#E13B4B",
        "dex_hinge": "#8E1622",
        "dex_lcd": "#E8F2DA",
        "dex_dot": "#D3E2C0",
        "border": "#4A5162",
        "border_hi": "#788096",
        "text_primary": "#23262E",
        "text_muted": "#535B6E",
        "text_subtle": "#727B91",
        "accent_primary": "#1D4ED8",
        "accent_pill_text": "#FFFFFF",
        "accent_signal": "#16A34A",
        "accent_amber": "#D97706",
        "accent_boss": "#DC2626",
        "accent_arcane": "#7C3AED",
        "shadow": "#5E8B52",
    },
}

XP_WEIGHTS: dict[str, int] = {
    "contribution": 2,
    "active_day": 5,
    "merged_pr": 35,
    "documented_repo": 40,
    "ci_repo": 60,
    "external_star": 25,
    "language_ge_1pct": 50,
}

LEVEL_TITLES: list[tuple[int, str]] = [
    (20, "Principal Engineer"),
    (15, "Telemetry Lead"),
    (10, "Systems Architect"),
    (5, "Stack Builder"),
    (1, "System Initiate"),
]


@dataclass(frozen=True)
class QuestSpec:
    """Definition of a single verifiable developer quest."""

    key: str
    title: str
    metric_key: str
    target: int
    unit: str
    description: str


QUEST_SPECS: tuple[QuestSpec, ...] = (
    QuestSpec(
        key="genesis_commit",
        title="Genesis Commit",
        metric_key="account_age_days",
        target=365,
        unit="d",
        description="Account active >= 1 year with verified public activity.",
    ),
    QuestSpec(
        key="shipwright",
        title="Shipwright",
        metric_key="non_empty_owned_repos",
        target=5,
        unit="repos",
        description="Ship 5+ non-empty public repositories.",
    ),
    QuestSpec(
        key="doc_architect",
        title="Doc Architect",
        metric_key="documented_repos",
        target=5,
        unit="docs",
        description="Maintain 5+ owned repositories with README documentation.",
    ),
    QuestSpec(
        key="ci_guardian",
        title="CI Guardian",
        metric_key="ci_repos",
        target=5,
        unit="ci",
        description="Configure GitHub Actions CI workflows on 5+ repositories.",
    ),
    QuestSpec(
        key="polyglot_stack",
        title="Polyglot Stack",
        metric_key="languages_ge_1pct",
        target=4,
        unit="langs",
        description="Write 4+ languages comprising >= 1% of owned codebases.",
    ),
    QuestSpec(
        key="club_500",
        title="500 Club",
        metric_key="total_contributions",
        target=500,
        unit="",
        description="Reach 500+ verified GitHub contributions.",
    ),
    QuestSpec(
        key="week_sprint",
        title="Week Sprint",
        metric_key="longest_streak",
        target=7,
        unit="d",
        description="Maintain a 7+ consecutive day contribution streak.",
    ),
    QuestSpec(
        key="first_merge",
        title="First Merge",
        metric_key="merged_prs",
        target=1,
        unit="pr",
        description="Land your first merged Pull Request.",
    ),
    QuestSpec(
        key="builder_1k",
        title="1K Builder",
        metric_key="total_contributions",
        target=1000,
        unit="",
        description="Reach 1,000 verified GitHub contributions.",
    ),
    QuestSpec(
        key="fortnight_streak",
        title="14d Streak",
        metric_key="longest_streak",
        target=14,
        unit="d",
        description="Maintain a 14-day consecutive contribution streak.",
    ),
    QuestSpec(
        key="os_ally",
        title="OSS Ally",
        metric_key="external_merged_prs",
        target=1,
        unit="pr",
        description="Merge a Pull Request into an external open-source repository.",
    ),
    QuestSpec(
        key="community_signal",
        title="Star Signal",
        metric_key="external_stars",
        target=10,
        unit="★",
        description="Earn 10 non-self stars across owned repositories.",
    ),
)

# Higher-tier quest supersedes lower tier on the summary card once unlocked.
SUPERSEDED_QUESTS: dict[str, str] = {
    "club_500": "builder_1k",
    "week_sprint": "fortnight_streak",
}

QUEST_PLAIN_LABELS: dict[str, str] = {
    "genesis_commit": "yrs on GitHub",
    "shipwright": "public builds",
    "doc_architect": "documented repos",
    "ci_guardian": "CI-gated repos",
    "polyglot_stack": "core languages",
    "club_500": "contributions",
    "builder_1k": "contributions",
    "week_sprint": "day streak",
    "fortnight_streak": "day streak",
    "first_merge": "merged PRs",
    "os_ally": "external PRs",
    "community_signal": "external stars",
}
