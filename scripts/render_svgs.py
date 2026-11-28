"""Compile pure-SVG Pokémon GBA Battle Arena, Hero Codex Card, and Skill Tree Matrix SVGs."""

from __future__ import annotations

import argparse
import json
import math
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scripts.compute_gamification import GamificationReport, QuestProgress, evaluate_metrics
from scripts.config import (
    BOSS_QUIPS,
    BOSS_TYPES,
    BRANCH_META,
    QUEST_PLAIN_LABELS,
    SUPERSEDED_QUESTS,
    THEMES,
)
from scripts.game_engine import BOSS_ROSTER, get_active_boss, init_game_state
from scripts.pixel_sprites import (
    BOSS_SPRITES,
    COMPANION_FOX,
    HERO_TRAINER,
    PIXEL_POKEBALL,
    QUEST_SPRITES,
    compile_pixel_grid,
    sprite_bounds,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"

RARITY_SHORT: dict[str, str] = {
    "LEGENDARY": "LEGEND",
    "EPIC": "EPIC",
    "RARE": "RARE",
    "UNCOMMON": "UNCOM",
}


def _select_display_quests(report: GamificationReport) -> tuple[list[QuestProgress], QuestProgress | None]:
    """Return up to 8 high-signal milestones (unlocked first) plus the closest next target."""
    by_key = {q.key: q for q in report.quests}
    unlocked = [
        q
        for q in report.quests
        if q.unlocked and not (q.key in SUPERSEDED_QUESTS and by_key[SUPERSEDED_QUESTS[q.key]].unlocked)
    ]
    locked = sorted(
        (q for q in report.quests if not q.unlocked),
        key=lambda q: (-q.progress_pct, q.key),
    )
    next_target = next((q for q in locked if q.current > 0), locked[0] if locked else None)

    in_progress = [q for q in locked if q.current > 0]
    reserved_wip = min(2, len(in_progress))
    selected = unlocked[: 8 - reserved_wip]
    if len(selected) < 8:
        selected.extend(in_progress[: 8 - len(selected)])
    if len(selected) < 6:
        remaining = [q for q in locked if q not in selected]
        selected.extend(remaining[: 6 - len(selected)])
    return selected[:8], next_target


def _format_quest_sub(quest: QuestProgress) -> str:
    plain_unit = QUEST_PLAIN_LABELS.get(quest.key, quest.unit)
    if quest.key == "genesis_commit":
        years = round(quest.current / 365.0, 1)
        return f"{years:g} yrs on GitHub" if quest.unlocked else f"{quest.current}/{quest.target} days"
    if quest.unlocked:
        return f"{quest.current:,} {plain_unit}".strip()
    return f"{quest.current}/{quest.target} {plain_unit}".strip()


def _build_pokedex_entries(
    report: GamificationReport,
    theme: dict[str, str],
) -> tuple[list[dict[str, object]], str]:
    """Build 2x4 Hero Codex milestone entries with sprite, Pokéball caught icon & Dex index."""
    selected, next_target = _select_display_quests(report)
    tiles: list[dict[str, object]] = []
    for idx, quest in enumerate(selected):
        col = idx % 2
        row = idx // 2
        bx = 354 + col * 234
        by = 74 + row * 51
        sprite_rects = compile_pixel_grid(
            QUEST_SPRITES[quest.key],
            scale=2,
            ox=bx + 8,
            oy=by + 11,
            locked_color=None if quest.unlocked else theme["bg_track"],
        )
        ball_rects = compile_pixel_grid(
            PIXEL_POKEBALL,
            scale=1,
            ox=bx + 206,
            oy=by + 7,
            locked_color=None if quest.unlocked else theme["bg_track"],
        )
        progress_w = round(max(0.0, min(1.0, quest.progress_pct / 100.0)) * 172.0, 1)
        tiles.append(
            {
                "dex_no": f"#{idx + 1:03d}",
                "x": bx,
                "y": by,
                "w": 224,
                "h": 44,
                "title": quest.title,
                "sub": _format_quest_sub(quest),
                "unlocked": quest.unlocked,
                "progress_w": progress_w,
                "rects": sprite_rects,
                "ball_rects": ball_rects,
            }
        )

    if next_target is not None:
        unit = QUEST_PLAIN_LABELS.get(next_target.key, next_target.unit)
        next_label = f"NEXT UP: {next_target.title} ({next_target.current}/{next_target.target} {unit})".strip()
    else:
        next_label = "ALL QUEST TROPHIES UNLOCKED!"
    return tiles, next_label


def _build_dex_stat_bars(report: GamificationReport, theme: dict[str, str]) -> list[dict[str, object]]:
    """Build 4 readable player telemetry bars whose numbers match their bar fill ratios."""
    denom = max(1, report.non_empty_owned_repos)
    rows = [
        (
            "OUTPUT",
            f"{report.contributions_12m:,} / yr",
            min(100, round((report.contributions_12m / 1200.0) * 100)),
            "#22C55E" if theme["name"].startswith("FireRed") else theme["accent_signal"],
        ),
        (
            "STREAK",
            f"{report.active_days}d · {report.longest_streak}d best",
            min(100, round((report.active_days / 200.0) * 100)),
            theme["accent_amber"],
        ),
        (
            "SHIELD",
            f"{report.ci_repos} CI · {report.documented_repos} Docs",
            min(100, round(((report.ci_repos + report.documented_repos) / (denom * 2)) * 100)),
            theme["accent_primary"],
        ),
        (
            "IMPACT",
            f"{report.merged_prs} PRs · {report.external_stars} Stars",
            min(100, round((report.merged_prs + report.external_stars) * 6)),
            theme["accent_arcane"],
        ),
    ]
    bars: list[dict[str, object]] = []
    for idx, (code, val_text, pct, color) in enumerate(rows):
        bars.append(
            {
                "y": 164 + idx * 20,
                "code": code,
                "value": val_text,
                "fill_w": round((max(8, pct) / 100.0) * 106.0, 1),
                "color": color,
            }
        )
    return bars


def _build_language_tiles(report: GamificationReport, theme: dict[str, str]) -> list[dict[str, object]]:
    """Build 2x3 readable language stat chips with exact %, full repo count, and mastery color."""
    mastery_colors = {
        "MASTERED": theme["accent_amber"],
        "PROFICIENT": theme["accent_primary"],
        "ACTIVE": theme["accent_arcane"],
        "EXPLORING": theme["text_muted"],
    }
    tiles: list[dict[str, object]] = []
    for idx, lang in enumerate(report.top_languages[:6]):
        col = idx % 2
        row = idx // 2
        repo_word = "1 repo" if lang.repo_count == 1 else f"{lang.repo_count} repos"
        tiles.append(
            {
                "x": 26 + col * 149,
                "y": 258 + row * 22,
                "w": 141,
                "h": 19,
                "name": lang.name,
                "pct": f"{lang.percentage}%",
                "repos": repo_word,
                "dot": lang.color,
                "m_color": mastery_colors.get(lang.mastery, theme["text_muted"]),
            }
        )
    return tiles


HUB_CX = 279
HUB_CY = 267

SECTOR_DISPLAY_NAMES: dict[str, str] = {
    "backend": "Backend Engine",
    "ai": "AI & Agents",
    "data": "Data & BI",
    "apps": "Apps & Build",
    "frontend": "UI & Web",
    "infra": "Ops & QA",
}

# Exact coordinates per key in 6 radial sectors around HUB (279, 267)
CONSTELLATION_POS: dict[str, tuple[int, int]] = {
    # Sector 1: Backend Engine (Steep Ascending Spire)
    "python": (324, 196),
    "pydantic": (302, 128),
    "fastapi": (392, 168),
    "async_httpx": (388, 92),
    # Sector 2: AI & Agents (Sweeping Forward Spear)
    "gemini": (360, 264),
    "rag": (416, 214),
    "fastmcp": (434, 316),
    "pytorch": (502, 258),
    # Sector 3: Data & BI (Delta Cascade)
    "postgres": (334, 338),
    "alembic_etl": (306, 408),
    "nosql_cache": (412, 368),
    "analytics": (406, 444),
    # Sector 4: Apps & Build (Sweeping Talon)
    "ssr_jinja": (226, 336),
    "electron": (146, 366),
    "kotlin": (238, 412),
    "playwright": (154, 444),
    # Sector 5: UI & Web (Twin Wing Horizon)
    "web_core": (196, 266),
    "react_next": (140, 212),
    "typescript": (122, 318),
    "vite_tailwind": (58, 258),
    # Sector 6: Ops & QA (Stepped Bastion)
    "pytest_qa": (228, 194),
    "gh_actions": (250, 124),
    "linters": (158, 166),
    "docker": (168, 90),
}

# Intra-sector edges (parent_key, child_key, is_synergy_chord)
CONSTELLATION_EDGES: tuple[tuple[str, str, bool], ...] = (
    # Backend Engine
    ("__hub__", "python", False),
    ("python", "pydantic", False),
    ("python", "fastapi", False),
    ("pydantic", "fastapi", True),
    ("pydantic", "async_httpx", False),
    ("fastapi", "async_httpx", False),
    # AI & Agents
    ("__hub__", "gemini", False),
    ("gemini", "rag", False),
    ("gemini", "fastmcp", False),
    ("rag", "fastmcp", True),
    ("rag", "pytorch", False),
    ("fastmcp", "pytorch", False),
    # Data & BI
    ("__hub__", "postgres", False),
    ("postgres", "nosql_cache", False),
    ("postgres", "alembic_etl", False),
    ("nosql_cache", "alembic_etl", True),
    ("nosql_cache", "analytics", False),
    ("alembic_etl", "analytics", False),
    # Apps & Build
    ("__hub__", "ssr_jinja", False),
    ("ssr_jinja", "electron", False),
    ("ssr_jinja", "kotlin", False),
    ("electron", "kotlin", True),
    ("electron", "playwright", False),
    ("kotlin", "playwright", False),
    # UI & Web
    ("__hub__", "web_core", False),
    ("web_core", "react_next", False),
    ("web_core", "typescript", False),
    ("react_next", "typescript", True),
    ("react_next", "vite_tailwind", False),
    ("typescript", "vite_tailwind", False),
    # Ops & QA
    ("__hub__", "pytest_qa", False),
    ("pytest_qa", "gh_actions", False),
    ("pytest_qa", "linters", False),
    ("gh_actions", "linters", True),
    ("gh_actions", "docker", False),
    ("linters", "docker", False),
)

# Subtle outer ring cross-sector bridges
INTER_BRANCH_BRIDGES: tuple[tuple[str, str], ...] = (
    ("gh_actions", "pydantic"),
    ("fastapi", "rag"),
    ("fastmcp", "nosql_cache"),
    ("alembic_etl", "kotlin"),
    ("electron", "typescript"),
    ("react_next", "linters"),
)

# Wedge polygons clipped to left panel (sector_key, start_deg, end_deg, tag_x, tag_y, anchor, short_title)
SECTOR_WEDGES: tuple[tuple[str, int, int, int, int, str, str], ...] = (
    ("backend", -90, -30, 290, 62, "start", "BACKEND"),
    ("ai", -30, 30, 534, 192, "end", "AI & AGENTS"),
    ("data", 30, 90, 534, 479, "end", "DATA & BI"),
    ("apps", 90, 150, 24, 479, "start", "APPS & BUILD"),
    ("frontend", 150, 210, 24, 192, "start", "UI & WEB"),
    ("infra", 210, 270, 268, 62, "end", "OPS & QA"),
)


def _node_icon_path(icon: str, cx: int, cy: int) -> str:
    """Return crisp hairline SVG vector path data centered at (cx, cy)."""
    if icon == "code":
        return f"M{cx - 2},{cy - 3} L{cx - 4.5},{cy} L{cx - 2},{cy + 3} M{cx + 2},{cy - 3} L{cx + 4.5},{cy} L{cx + 2},{cy + 3}"
    if icon == "bolt":
        return f"M{cx + 1},{cy - 4.5} L{cx - 2.5},{cy + 0.2} L{cx + 0.5},{cy + 0.2} L{cx - 1},{cy + 4.5} L{cx + 3},{cy - 0.3} L{cx - 0.2},{cy - 0.3} Z"
    if icon == "shield":
        return f"M{cx},{cy - 4.5} L{cx + 4},{cy - 2.4} V{cy + 0.5} Q{cx + 4},{cy + 3.4} {cx},{cy + 4.6} Q{cx - 4},{cy + 3.4} {cx - 4},{cy + 0.5} V{cy - 2.4} Z"
    if icon == "network":
        return f"M{cx},{cy - 4} L{cx - 3.6},{cy + 2.8} M{cx},{cy - 4} L{cx + 3.6},{cy + 2.8} M{cx - 3.6},{cy + 2.8} H{cx + 3.6}"
    if icon == "layers":
        return f"M{cx},{cy - 4.4} L{cx + 4.2},{cy - 1.8} L{cx},{cy + 0.6} L{cx - 4.2},{cy - 1.8} Z M{cx - 4.2},{cy + 1} L{cx},{cy + 3.2} L{cx + 4.2},{cy + 1} M{cx - 3.4},{cy + 3.2} L{cx},{cy + 4.8} L{cx + 3.4},{cy + 3.2}"
    if icon == "terminal":
        return f"M{cx - 3.8},{cy - 2.4} L{cx - 0.8},{cy} L{cx - 3.8},{cy + 2.4} M{cx + 0.2},{cy + 2.6} H{cx + 4}"
    if icon == "neural":
        return f"M{cx},{cy - 4.2} L{cx + 4},{cy + 3} H{cx - 4} Z M{cx - 1.4},{cy + 0.6} H{cx + 1.4}"
    if icon == "db":
        return f"M{cx - 3.8},{cy - 2.4} Q{cx},{cy - 4.2} {cx + 3.8},{cy - 2.4} Q{cx},{cy - 0.6} {cx - 3.8},{cy - 2.4} M{cx - 3.8},{cy - 2.4} V{cy + 2.4} Q{cx},{cy + 4.2} {cx + 3.8},{cy + 2.4} V{cy - 2.4} M{cx - 3.8},{cy} Q{cx},{cy + 1.8} {cx + 3.8},{cy}"
    if icon == "chart":
        return f"M{cx - 4},{cy + 3.4} H{cx + 4} M{cx - 2.6},{cy + 3.4} V{cy + 0.6} M{cx},{cy + 3.4} V{cy - 1.8} M{cx + 2.6},{cy + 3.4} V{cy - 3.8}"
    if icon == "screen":
        return f"M{cx - 4.4},{cy - 3.4} H{cx + 4.4} V{cy + 1.8} H{cx - 4.4} Z M{cx - 2},{cy + 3.8} H{cx + 2} M{cx},{cy + 1.8} V{cy + 3.8}"
    if icon == "mobile":
        return f"M{cx - 2.5},{cy - 4.2} H{cx + 2.5} V{cy + 4.2} H{cx - 2.5} Z M{cx - 0.8},{cy + 2.6} H{cx + 0.8}"
    if icon == "check":
        return f"M{cx - 3.5},{cy + 0.2} L{cx - 1},{cy + 2.8} L{cx + 3.8},{cy - 2.8}"
    if icon == "cube":
        return f"M{cx},{cy - 4.5} L{cx + 4},{cy - 2.2} V{cy + 2.2} L{cx},{cy + 4.5} L{cx - 4},{cy + 2.2} V{cy - 2.2} Z M{cx},{cy - 4.5} V{cy + 4.5} M{cx - 4},{cy - 2.2} L{cx},{cy} L{cx + 4},{cy - 2.2}"
    # Default astral spark
    return f"M{cx},{cy - 4.8} L{cx + 1.2},{cy - 1.2} L{cx + 4.8},{cy} L{cx + 1.2},{cy + 1.2} L{cx},{cy + 4.8} L{cx - 1.2},{cy + 1.2} L{cx - 4.8},{cy} L{cx - 1.2},{cy - 1.2} Z"


def _octagon_points(cx: int, cy: int, r: int) -> str:
    """Return regular octagon vertex coordinates centered at (cx, cy)."""
    pts: list[str] = []
    for i in range(8):
        ang = math.radians(22.5 + i * 45.0)
        pts.append(f"{round(cx + r * math.cos(ang), 1)},{round(cy + r * math.sin(ang), 1)}")
    return " ".join(pts)


def _build_constellation_tree(
    report: GamificationReport,
    theme: dict[str, str],
    mode: str,
) -> dict[str, Any]:
    """Build radial constellation wedges, branching edges, socketed nodes & RPG character sheet."""
    branch_accents = {b_key: theme[acc_key] for b_key, _, acc_key in BRANCH_META}
    mastery_colors = {
        "MASTERED": theme["accent_amber"],
        "PROFICIENT": theme["accent_signal"],
        "ACTIVE": theme["accent_primary"],
        "EXPLORING": theme["text_muted"],
        "LOCKED": theme["text_subtle"],
    }
    by_key = {n.key: n for n in report.skill_nodes}
    by_branch: dict[str, list[Any]] = {b_key: [] for b_key, _, _ in BRANCH_META}
    for n in report.skill_nodes:
        if n.branch in by_branch:
            by_branch[n.branch].append(n)

    # Sector wedges: illuminate primary active aura cleanly without loud flat rainbow slices
    wedges: list[dict[str, Any]] = []
    divider_rays: list[dict[str, float]] = []
    sector_rows: list[dict[str, Any]] = []
    ray_r = 380.0
    is_dark = mode == "dark"
    for sec_key, deg_start, deg_end, tag_x, tag_y, anchor, short_title in SECTOR_WEDGES:
        sec_nodes = by_branch.get(sec_key, [])
        sec_pips = sum(n.pips for n in sec_nodes)
        max_sec_pips = max(1, len(sec_nodes) * 4)
        glow_ratio = sec_pips / max_sec_pips
        is_signature = sec_key in {"backend", "ai", "apps"}
        if glow_ratio >= 0.90:
            beam_alpha = 0.20 if is_dark else 0.11
        elif is_signature and glow_ratio >= 0.50:
            beam_alpha = 0.18 if is_dark else 0.09
        else:
            beam_alpha = 0.06 if is_dark else 0.03
        beam_mid = round(beam_alpha * 0.40, 3)

        pts = [f"{HUB_CX},{HUB_CY}"]
        for deg in (deg_start, (deg_start + deg_end) / 2.0, deg_end):
            rad = math.radians(deg)
            pts.append(f"{round(HUB_CX + ray_r * math.cos(rad), 1)},{round(HUB_CY + ray_r * math.sin(rad), 1)}")
        accent = branch_accents[sec_key]
        wedges.append(
            {
                "key": sec_key,
                "points": " ".join(pts),
                "accent": accent,
                "beam_alpha": beam_alpha,
                "beam_mid": beam_mid,
                "tag_x": tag_x,
                "tag_y": tag_y,
                "anchor": anchor,
                "title": short_title,
            }
        )
        sector_rows.append(
            {
                "title": SECTOR_DISPLAY_NAMES.get(sec_key, sec_key.title()),
                "accent": accent,
                "pips_label": f"{sec_pips}/{max_sec_pips}",
                "fill_w": round(glow_ratio * 58.0, 1),
            }
        )
        r_start = math.radians(deg_start)
        divider_rays.append(
            {
                "x1": round(HUB_CX + 38.0 * math.cos(r_start), 1),
                "y1": round(HUB_CY + 38.0 * math.sin(r_start), 1),
                "x2": round(HUB_CX + ray_r * math.cos(r_start), 1),
                "y2": round(HUB_CY + ray_r * math.sin(r_start), 1),
            }
        )

    # Curved Constellation Bezier Arcs + exact curve-midpoint relay dots
    edges: list[dict[str, Any]] = []
    joint_dots: list[dict[str, Any]] = []
    for idx_edge, (src_key, dst_key, is_synergy) in enumerate(CONSTELLATION_EDGES):
        sx, sy = (HUB_CX, HUB_CY) if src_key == "__hub__" else CONSTELLATION_POS[src_key]
        dx, dy = CONSTELLATION_POS[dst_key]
        dst_node = by_key[dst_key]
        src_pips = 4 if src_key == "__hub__" else by_key[src_key].pips
        active = dst_node.pips > 0 and src_pips > 0
        stroke = branch_accents[dst_node.branch] if active else theme["border"]

        vx, vy = dx - sx, dy - sy
        length = math.hypot(vx, vy) or 1.0
        mx, my = (sx + dx) / 2.0, (sy + dy) / 2.0
        # Gentle organic bow alternating sign per edge without crossing neighbors
        bend = 0.0 if is_synergy else (10.5 if src_key != "__hub__" else 13.0) * (1 if idx_edge % 2 == 0 else -1)
        nx_u, ny_u = -vy / length, vx / length
        qx, qy = round(mx + bend * nx_u, 1), round(my + bend * ny_u, 1)
        path_d = f"M{sx},{sy} Q{qx},{qy} {dx},{dy}"

        edges.append(
            {
                "d": path_d,
                "stroke": stroke,
                "active": active,
                "synergy": is_synergy,
            }
        )
        if not is_synergy and src_key != "__hub__":
            # Quadratic Bezier midpoint at t=0.5: 0.25*P0 + 0.5*Q + 0.25*P1
            joint_dots.append(
                {
                    "cx": round(0.25 * sx + 0.5 * qx + 0.25 * dx, 1),
                    "cy": round(0.25 * sy + 0.5 * qy + 0.25 * dy, 1),
                    "fill": stroke if active else theme["bg_track"],
                    "active": active,
                }
            )

    bridges: list[dict[str, Any]] = []
    for a_key, b_key in INTER_BRANCH_BRIDGES:
        ax, ay = CONSTELLATION_POS[a_key]
        bx, by = CONSTELLATION_POS[b_key]
        active = by_key[a_key].pips >= 2 and by_key[b_key].pips >= 2
        mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
        # Bow gently inward/outward along radial vector from Hub
        rx, ry = mx - HUB_CX, my - HUB_CY
        rl = math.hypot(rx, ry) or 1.0
        qx, qy = round(mx + (rx / rl) * 10.0, 1), round(my + (ry / rl) * 10.0, 1)
        bridges.append(
            {
                "d": f"M{ax},{ay} Q{qx},{qy} {bx},{by}",
                "stroke": theme["border_hi"] if active else theme["border"],
                "active": active,
            }
        )

    # Nodes with top-arch rim socket pips, inner vector emblem, and crisp bottom pill label
    pip_angles = (-138.0, -113.0, -67.0, -42.0)
    nodes_ctx: list[dict[str, Any]] = []
    for spec in report.skill_nodes:
        nx, ny = CONSTELLATION_POS[spec.key]
        r = 14 if spec.is_capstone else 11
        branch_color = branch_accents[spec.branch]
        rarity_color = theme[spec.rarity_color_key]
        ring_color = rarity_color if spec.pips > 0 else theme["border"]
        m_color = mastery_colors.get(spec.mastery, theme["text_muted"])

        pip_list: list[dict[str, Any]] = []
        pip_r = r + 3.2
        for idx, ang_deg in enumerate(pip_angles):
            ang = math.radians(ang_deg)
            lit = idx < spec.pips
            pip_list.append(
                {
                    "cx": round(nx + pip_r * math.cos(ang), 1),
                    "cy": round(ny + pip_r * math.sin(ang), 1),
                    "fill": m_color if lit else theme["bg_track"],
                    "stroke": ring_color if lit else theme["border"],
                }
            )

        label_text = spec.name
        label_w = max(32, int(round(len(label_text) * 4.5 + 4)))
        nodes_ctx.append(
            {
                "key": spec.key,
                "x": nx,
                "y": ny,
                "r": r,
                "is_capstone": spec.is_capstone,
                "octagon_pts": _octagon_points(nx, ny, r) if spec.is_capstone else "",
                "octagon_inner_pts": _octagon_points(nx, ny, r - 3) if spec.is_capstone else "",
                "ring_color": ring_color,
                "glow_color": branch_color if spec.pips > 0 else theme["border"],
                "active": spec.pips > 0,
                "mastered": spec.pips == 4,
                "icon_path": _node_icon_path(spec.icon, nx, ny),
                "icon_color": branch_color if spec.pips > 0 else theme["text_subtle"],
                "pips": pip_list,
                "label_text": label_text,
                "pill_w": label_w,
                "pill_x": round(nx - label_w / 2.0, 1),
                "pill_y": ny + r + 4,
                "label_y": ny + r + 11.5,
                "label_color": theme["text_primary"] if spec.pips > 0 else theme["text_subtle"],
            }
        )

    # Central Astrolabe Hub dual sacred triangles pointing cleanly toward all 6 sectors
    hub_tri_pts = " ".join(
        f"{round(HUB_CX + 23 * math.cos(math.radians(-60 + i * 120)), 1)},{round(HUB_CY + 23 * math.sin(math.radians(-60 + i * 120)), 1)}"
        for i in range(3)
    )
    hub_tri_inv_pts = " ".join(
        f"{round(HUB_CX + 23 * math.cos(math.radians(i * 120)), 1)},{round(HUB_CY + 23 * math.sin(math.radians(i * 120)), 1)}"
        for i in range(3)
    )
    hub_ticks: list[dict[str, float]] = []
    for i in range(16):
        ang = math.radians(i * 22.5)
        hub_ticks.append(
            {
                "x1": round(HUB_CX + 30 * math.cos(ang), 1),
                "y1": round(HUB_CY + 30 * math.sin(ang), 1),
                "x2": round(HUB_CX + 34.5 * math.cos(ang), 1),
                "y2": round(HUB_CY + 34.5 * math.sin(ang), 1),
            }
        )

    mastered_count = sum(1 for n in report.skill_nodes if n.mastery == "MASTERED")
    proficient_count = sum(1 for n in report.skill_nodes if n.mastery == "PROFICIENT")
    active_count = sum(1 for n in report.skill_nodes if n.pips > 0)
    capstone_rows = [
        {
            "name": n.name,
            "repos": f"{n.repo_count}r",
            "color": mastery_colors.get(n.mastery, theme["text_muted"]),
        }
        for n in report.skill_nodes
        if n.is_capstone
    ]
    earned_pips = sum(n.pips for n in report.skill_nodes)
    max_pips = len(report.skill_nodes) * 4

    rarity_counts = {
        "LEGEND": sum(1 for n in report.skill_nodes if n.rarity == "LEGENDARY" and n.pips > 0),
        "EPIC": sum(1 for n in report.skill_nodes if n.rarity == "EPIC" and n.pips > 0),
        "RARE_UNC": sum(1 for n in report.skill_nodes if n.rarity in {"RARE", "UNCOMMON"} and n.pips > 0),
    }

    return {
        "hub_cx": HUB_CX,
        "hub_cy": HUB_CY,
        "hub_tri_pts": hub_tri_pts,
        "hub_tri_inv_pts": hub_tri_inv_pts,
        "hub_ticks": hub_ticks,
        "wedges": wedges,
        "divider_rays": divider_rays,
        "edges": edges,
        "bridges": bridges,
        "joint_dots": joint_dots,
        "nodes": nodes_ctx,
        "sector_rows": sector_rows,
        "capstone_rows": capstone_rows,
        "mastered_count": mastered_count,
        "proficient_count": proficient_count,
        "active_only_count": max(0, active_count - mastered_count - proficient_count),
        "active_skill_count": active_count,
        "total_skill_count": len(report.skill_nodes),
        "earned_pips": earned_pips,
        "max_pips": max_pips,
        "rarity_counts": rarity_counts,
    }


def _grade_color(grade: str, theme: dict[str, str]) -> str:
    if grade.startswith("S"):
        return theme["accent_amber"]
    if grade == "A":
        return theme["accent_primary"]
    return theme["accent_signal"]


def _wrap_dialog(text: str, width: int = 58) -> tuple[str, str]:
    wrapped = textwrap.wrap(text.strip(), width=width)
    if not wrapped:
        return "Drop a Star for an instant KO or pick a move!", ""
    if len(wrapped) == 1:
        return wrapped[0], ""
    second = wrapped[1] if len(wrapped) == 2 else f"{wrapped[1][: width - 3].rstrip()}..."
    return wrapped[0], second


def _hp_bar_color(ratio: float) -> str:
    if ratio > 0.50:
        return "#22C55E"
    if ratio > 0.20:
        return "#EAB308"
    return "#EF4444"


def _classify_battle_fx(last_event: str, buff_charges: int) -> tuple[str, str]:
    """Return dynamic comic impact VFX type & caption from latest raid event."""
    upper = last_event.upper()
    if "1-HIT KO" in upper:
        return "star_ko", "1-HIT K.O.!"
    if "KRAKOOM" in upper or "CRIT" in upper:
        return "crit", "KRAKOOM!"
    if "SLASH" in upper or "COMBO" in upper:
        return "strike", "SLASH!"
    if "POWER UP" in upper or buff_charges > 0:
        return "buff", f"+{max(1, buff_charges) * 10} ATK"
    return "idle", ""


def validate_svg_xml(svg_text: str) -> None:
    """Validate well-formed SVG XML and reject <foreignObject> or <script> tags."""
    root = ET.fromstring(svg_text)
    if not root.tag.endswith("svg"):
        raise ValueError(f"Root element must be <svg>, got {root.tag}")
    for elem in root.iter():
        tag_lower = elem.tag.lower()
        if tag_lower.endswith("foreignobject") or tag_lower.endswith("script"):
            raise ValueError(f"Forbidden SVG element detected: {elem.tag}")


def render_all_svgs(
    report: GamificationReport,
    out_dir: Path,
    *,
    game_state: dict[str, Any] | None = None,
    raw_metrics: dict[str, Any] | None = None,  # noqa: ARG001
) -> list[Path]:
    """Render Light and Dark GBA Battle Arena, Hero Codex Card, and Skill Tree SVGs."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["svg", "j2", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    battle_tpl = env.get_template("battle.svg.j2")
    trainer_tpl = env.get_template("trainer.svg.j2")
    skill_tpl = env.get_template("skill_tree.svg.j2")

    state = (
        game_state
        if game_state is not None
        else init_game_state(report.total_contributions, report.external_stars)
    )
    boss = get_active_boss(state)
    boss_hp = int(state.get("boss_hp", boss.max_hp))
    hp_ratio = max(0.0, min(1.0, boss_hp / max(1, boss.max_hp)))
    boss_hp_width = round(hp_ratio * 244.0, 2)
    boss_hp_color = _hp_bar_color(hp_ratio)
    boss_idx = int(state.get("boss_index", 0)) % len(BOSS_ROSTER)
    boss_level = 12 + boss_idx * 3
    boss_quip = BOSS_QUIPS.get(boss.key, "READY!")
    boss_type = BOSS_TYPES.get(boss.key, "RAID · BOSS")
    total_bosses = len(BOSS_ROSTER)

    boss_grid = BOSS_SPRITES[boss.key]
    bw, bh = sprite_bounds(boss_grid, scale=2)
    boss_rects = compile_pixel_grid(boss_grid, scale=2, ox=636 - (bw // 2), oy=140 - bh)

    hw, hh = sprite_bounds(HERO_TRAINER, scale=2)
    hero_rects = compile_pixel_grid(HERO_TRAINER, scale=2, ox=162 - (hw // 2), oy=221 - hh)

    cw, ch = sprite_bounds(COMPANION_FOX, scale=2)
    pet_rects = compile_pixel_grid(COMPANION_FOX, scale=2, ox=234 - (cw // 2), oy=224 - ch)

    dex_hero_rects = compile_pixel_grid(HERO_TRAINER, scale=2, ox=56 - (hw // 2), oy=144 - hh)
    dex_pet_rects = compile_pixel_grid(COMPANION_FOX, scale=2, ox=104 - (cw // 2), oy=146 - ch)

    raiders_list = state.get("recent_raiders") or []
    raiders_text = ", ".join(f"@{r}" for r in raiders_list[:4]) if raiders_list else "Open to raiders"

    tavern_list = state.get("tavern_log") or []
    if tavern_list:
        latest = tavern_list[0]
        tavern_text = f"@{latest['user']}: \"{latest['note'][:24]}\""
    else:
        tavern_text = "Sign Guestbook"

    buff_charges = int(state.get("hero_buff_charges", 0))
    last_event_raw = str(state.get("last_event") or "")
    fx_kind, fx_label = _classify_battle_fx(last_event_raw, buff_charges)
    event_line1, event_line2 = _wrap_dialog(last_event_raw)
    if "signed Tavern:" in last_event_raw or "GUEST LOG" in last_event_raw:
        battle_subline = f"Squad: {raiders_text} · Tip: ★ Star repo for instant 1-Hit KO!"
    else:
        battle_subline = f"Squad: {raiders_text} · Log: {tavern_text}"

    primary_lang_tag = report.top_languages[0].name.upper()[:12] if report.top_languages else "PYTHON"
    secondary_tag = report.top_languages[1].name.upper()[:12] if len(report.top_languages) > 1 else "SYSTEMS"
    dex_exp_w = round((report.level_progress_pct / 100.0) * 106.0, 1)

    exp_bar_width = round((report.level_progress_pct / 100.0) * 140.0, 2)
    sync_date = report.generated_at_utc[:10]

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def _emit(name: str, content: str) -> None:
        validate_svg_xml(content)
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(path)

    for mode, theme in THEMES.items():
        header_ball = compile_pixel_grid(PIXEL_POKEBALL, scale=1, ox=16, oy=13)
        tree_ball = compile_pixel_grid(PIXEL_POKEBALL, scale=1, ox=16, oy=14)
        g_color = _grade_color(report.grade, theme)

        _emit(
            f"battle-{mode}.svg",
            battle_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
                game=state,
                boss=boss,
                boss_quip=boss_quip,
                boss_type=boss_type,
                total_bosses=total_bosses,
                boss_index_1=boss_idx + 1,
                boss_level=boss_level,
                boss_hp_width=boss_hp_width,
                boss_hp_color=boss_hp_color,
                boss_danger=(hp_ratio <= 0.25),
                fx_kind=fx_kind,
                fx_label=fx_label,
                exp_bar_width=exp_bar_width,
                buff_charges=buff_charges,
                event_line1=event_line1,
                event_line2=event_line2,
                header_ball=header_ball,
                hero_rects=hero_rects,
                pet_rects=pet_rects,
                boss_rects=boss_rects,
                battle_subline=battle_subline,
            ),
        )

        badge_tiles, next_label = _build_pokedex_entries(report, theme)
        _emit(
            f"trainer-{mode}.svg",
            trainer_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
                grade_color=g_color,
                dex_hero_rects=dex_hero_rects,
                dex_pet_rects=dex_pet_rects,
                dex_stat_bars=_build_dex_stat_bars(report, theme),
                dex_exp_w=dex_exp_w,
                language_tiles=_build_language_tiles(report, theme),
                badge_tiles=badge_tiles,
                next_label=next_label,
                sync_date=sync_date,
                primary_lang_tag=primary_lang_tag,
                secondary_tag=secondary_tag,
            ),
        )

        constellation = _build_constellation_tree(report, theme, mode)
        _emit(
            f"skill_tree-{mode}.svg",
            skill_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
                grade_color=g_color,
                header_ball=tree_ball,
                sync_date=sync_date,
                **constellation,
            ),
        )

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile pure-SVG GBA Battle, Hero Codex & Skill Tree SVGs.")
    parser.add_argument("--metrics", type=Path, required=True, help="Normalized metrics JSON path.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory for SVGs.")
    parser.add_argument(
        "--game-state",
        type=Path,
        default=None,
        help="Optional game_state.json path (initialized cleanly if missing).",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=None,
        help="Optional evaluated gamification summary JSON path.",
    )
    args = parser.parse_args()

    raw = json.loads(args.metrics.read_text(encoding="utf-8"))
    report = evaluate_metrics(raw)

    game_state: dict[str, Any] | None = None
    if args.game_state is not None and args.game_state.exists():
        game_state = json.loads(args.game_state.read_text(encoding="utf-8"))

    paths = render_all_svgs(report, args.out_dir, game_state=game_state, raw_metrics=raw)

    if args.report_out:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    for path in paths:
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
