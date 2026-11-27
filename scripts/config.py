"""Configuration, RPG color palettes, XP weights, quest badges, and featured cartridges."""

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
        "name": "Midnight Cartridge",
        "bg_canvas": "#0B0F17",
        "bg_stage": "#080C17",
        "bg_stage_top": "#070A14",
        "bg_stage_bot": "#121A30",
        "bg_card": "#101624",
        "bg_panel": "#172034",
        "bg_track": "#222C47",
        "bg_chip": "#11192B",
        "border": "#36456A",
        "border_hi": "#5A72AD",
        "text_primary": "#F1F5FF",
        "text_muted": "#9AAAD0",
        "text_subtle": "#6E7FA8",
        "accent_primary": "#38BDF8",
        "accent_pill_text": "#09101F",
        "accent_signal": "#34D399",
        "accent_amber": "#FBBF24",
        "accent_boss": "#F43F5E",
        "accent_arcane": "#A78BFA",
        "star": "#6474A8",
        "ground": "#1E2842",
        "ground_alt": "#182138",
        "horizon": "#131C32",
        "horizon_lit": "#FBBF24",
        "scanline": "#000000",
    },
    "light": {
        "name": "Pocket Parchment",
        "bg_canvas": "#FFFFFF",
        "bg_stage": "#F0E5CC",
        "bg_stage_top": "#F5ECD8",
        "bg_stage_bot": "#E3D4B2",
        "bg_card": "#FAF6EA",
        "bg_panel": "#F3EAD5",
        "bg_track": "#DFD3B4",
        "bg_chip": "#EAE0C6",
        "border": "#8C7A58",
        "border_hi": "#6A5A3E",
        "text_primary": "#201D1E",
        "text_muted": "#594D39",
        "text_subtle": "#786A50",
        "accent_primary": "#1D4ED8",
        "accent_pill_text": "#FFFFFF",
        "accent_signal": "#15803D",
        "accent_amber": "#B45309",
        "accent_boss": "#BE123C",
        "accent_arcane": "#6D28D9",
        "star": "#B8A985",
        "ground": "#D9CBA7",
        "ground_alt": "#CEBF98",
        "horizon": "#DECFA9",
        "horizon_lit": "#D97706",
        "scanline": "#8C7A58",
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

# Quest rarity styling mapped to theme accent keys
QUEST_RARITY: dict[str, tuple[str, str]] = {
    "genesis_commit": ("RARE", "accent_signal"),
    "shipwright": ("RARE", "accent_signal"),
    "first_merge": ("RARE", "accent_signal"),
    "week_sprint": ("RARE", "accent_primary"),
    "doc_architect": ("EPIC", "accent_arcane"),
    "ci_guardian": ("EPIC", "accent_primary"),
    "polyglot_stack": ("EPIC", "accent_arcane"),
    "fortnight_streak": ("EPIC", "accent_arcane"),
    "club_500": ("LEGEND", "accent_amber"),
    "builder_1k": ("LEGEND", "accent_amber"),
    "os_ally": ("LEGEND", "accent_amber"),
    "community_signal": ("LEGEND", "accent_amber"),
}


@dataclass(frozen=True)
class CartridgeSpec:
    """Featured flagship repository rendered as a clickable Pixel Quest Cartridge."""

    slug: str
    repo_name: str
    title: str
    sprite_key: str
    accent_key: str
    line1: str
    line2: str
    stack_label: str
    live_url: str = ""


FEATURED_CARTRIDGES: tuple[CartridgeSpec, ...] = (
    CartridgeSpec(
        slug="reposcore",
        repo_name="REPO-Score",
        title="RepoScore",
        sprite_key="shield_core",
        accent_key="accent_primary",
        line1="Hardened Docker sandbox + AST/Semgrep/OSV",
        line2="Deterministic 10-dimension repo evaluator",
        stack_label="Python · FastAPI · Next.js · Docker",
    ),
    CartridgeSpec(
        slug="whitfield-wms",
        repo_name="WAREHOUSE-MANAGEMENT-SYSTEM",
        title="Whitfield WMS",
        sprite_key="crate_ledger",
        accent_key="accent_signal",
        line1="Double-entry SELECT FOR UPDATE ledger",
        line2="FastMCP server & multi-modal voice intake",
        stack_label="Python · FastAPI · React 19 · PostgreSQL",
        live_url="https://warehouse-management-system-jade-seven.vercel.app",
    ),
    CartridgeSpec(
        slug="revenueos",
        repo_name="RevenueOS",
        title="RevenueOS",
        sprite_key="chart_core",
        accent_key="accent_amber",
        line1="Kimball star-schema ETL & DAX compiler",
        line2="Automated .pbit Power BI + Electron studio",
        stack_label="Python · Electron · FastAPI · PostgreSQL",
    ),
    CartridgeSpec(
        slug="verirag",
        repo_name="VeriRAG",
        title="VeriRAG",
        sprite_key="prism_rag",
        accent_key="accent_arcane",
        line1="Dual dense + BM25 RRF hybrid retriever",
        line2="Cross-encoder reranking & claim verdicts",
        stack_label="Python · FastAPI · PyTorch · Transformers",
    ),
    CartridgeSpec(
        slug="citycare",
        repo_name="CityCareClinic",
        title="CityCare Clinic",
        sprite_key="clinic_core",
        accent_key="accent_boss",
        line1="Multi-tenant clinical booking platform",
        line2="ChromaDB RAG, FastMCP & Telegram bot",
        stack_label="Python · React 19 · TanStack · MongoDB",
    ),
    CartridgeSpec(
        slug="smartris",
        repo_name="SMARTRIS",
        title="SmartRIS",
        sprite_key="wave_array",
        accent_key="accent_primary",
        line1="Reconfigurable Intelligent Surface & 6G",
        line2="Holographic beamforming physics simulator",
        stack_label="Python · FastAPI · React · TypeScript",
        live_url="https://smartris.vercel.app",
    ),
)

ARMORY_SLOTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "BACKEND & STORAGE",
        "accent_primary",
        ("Python", "FastAPI", "Pydantic v2", "SQLAlchemy", "PostgreSQL", "MongoDB", "Redis"),
    ),
    (
        "AI & VERIFICATION",
        "accent_arcane",
        ("Gemini", "PyTorch", "SentenceTransformers", "BM25", "ChromaDB", "FastMCP", "Playwright"),
    ),
    (
        "FRONTEND & DESKTOP",
        "accent_amber",
        ("TypeScript", "React 19", "Next.js", "TanStack", "Vite", "Tailwind CSS", "Electron"),
    ),
    (
        "INFRA & CI GATES",
        "accent_signal",
        ("Docker", "GitHub Actions", "Pytest", "Ruff", "Mypy", "ESLint"),
    ),
)
