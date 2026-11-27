"""Compile pure-SVG Pokémon GBA Battle Arena and Pokédex Telemetry SVGs."""

from __future__ import annotations

import argparse
import json
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scripts.compute_gamification import GamificationReport, QuestProgress, evaluate_metrics
from scripts.config import QUEST_PLAIN_LABELS, SUPERSEDED_QUESTS, THEMES
from scripts.game_engine import get_active_boss, init_game_state
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


def _build_language_segments(
    report: GamificationReport,
    bar_width: float = 278.0,
) -> list[dict[str, object]]:
    """Compute horizontal x/width offsets for the stacked language bar."""
    top = report.top_languages
    total_pct = sum(lang.percentage for lang in top) or 1.0
    segments: list[dict[str, object]] = []
    cursor = 0.0
    for idx, lang in enumerate(top):
        seg_w = (
            (bar_width - cursor)
            if idx == len(top) - 1
            else round((lang.percentage / total_pct) * bar_width, 2)
        )
        segments.append(
            {
                "name": lang.name,
                "percentage": lang.percentage,
                "color": lang.color,
                "x": round(cursor, 2),
                "width": max(0.0, seg_w),
            }
        )
        cursor += seg_w
    return segments


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

    selected = unlocked[:8]
    if len(selected) < 8:
        in_progress = [q for q in locked if q.current > 0]
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
    """Build 2x4 GBA Pokédex milestone entries with sprite, Pokéball caught icon & Dex index."""
    selected, next_target = _select_display_quests(report)
    tiles: list[dict[str, object]] = []
    for idx, quest in enumerate(selected):
        col = idx % 2
        row = idx // 2
        bx = 344 + col * 238
        by = 76 + row * 52
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
            ox=bx + 210,
            oy=by + 7,
            locked_color=None if quest.unlocked else theme["bg_track"],
        )
        progress_w = round(max(0.0, min(1.0, quest.progress_pct / 100.0)) * 176.0, 1)
        tiles.append(
            {
                "dex_no": f"#{idx + 1:03d}",
                "x": bx,
                "y": by,
                "w": 228,
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
        next_label = f"NEXT: {next_target.title} ({next_target.current}/{next_target.target} {unit})".strip()
    else:
        next_label = "ALL POKEDEX BADGES CAUGHT"
    return tiles, next_label


def _build_dex_stat_bars(report: GamificationReport, theme: dict[str, str]) -> list[dict[str, object]]:
    """Build 4 Pokémon GBA Summary stat bars cleanly mapped to verified GitHub metrics."""
    rows = [
        (
            "HP",
            "Contribs",
            f"{report.contributions_12m:,} / {report.total_contributions:,}",
            min(100, round((report.contributions_12m / 1200.0) * 100)),
            "#22C55E" if theme["name"].startswith("FireRed") else theme["accent_signal"],
        ),
        (
            "ATK",
            "Streak",
            f"{report.longest_streak}d best · {report.active_days}d",
            min(100, round((report.active_days / 200.0) * 100)),
            theme["accent_amber"],
        ),
        (
            "DEF",
            "CI + Doc",
            f"{report.ci_repos} CI · {report.documented_repos} Docs",
            min(100, round(((report.ci_repos + report.documented_repos) / 22.0) * 100)),
            theme["accent_primary"],
        ),
        (
            "SPD",
            "Impact",
            f"{report.merged_prs} PRs · {report.external_stars}★",
            min(100, round((report.merged_prs + report.external_stars) * 8)),
            theme["accent_arcane"],
        ),
    ]
    bars: list[dict[str, object]] = []
    for idx, (code, label, val_text, pct, color) in enumerate(rows):
        bars.append(
            {
                "y": 170 + idx * 23,
                "code": code,
                "label": label,
                "value": val_text,
                "fill_w": round((max(8, pct) / 100.0) * 110.0, 1),
                "color": color,
            }
        )
    return bars


def _wrap_dialog(text: str, width: int = 58) -> tuple[str, str]:
    wrapped = textwrap.wrap(text.strip(), width=width)
    if not wrapped:
        return "Choose a move or Star the repo!", ""
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
    """Render Light and Dark Pokémon GBA Battle Arena and Pokédex Telemetry Card SVGs."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["svg", "j2", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    battle_tpl = env.get_template("battle.svg.j2")
    trainer_tpl = env.get_template("trainer.svg.j2")

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
    boss_idx = int(state.get("boss_index", 0))
    boss_level = 12 + boss_idx * 3

    # Ground sprites squarely on their respective GBA elliptical platforms (scale=2 uniform density)
    boss_grid = BOSS_SPRITES[boss.key]
    bw, bh = sprite_bounds(boss_grid, scale=2)
    boss_rects = compile_pixel_grid(boss_grid, scale=2, ox=636 - (bw // 2), oy=140 - bh)

    hw, hh = sprite_bounds(HERO_TRAINER, scale=2)
    hero_rects = compile_pixel_grid(HERO_TRAINER, scale=2, ox=162 - (hw // 2), oy=221 - hh)

    cw, ch = sprite_bounds(COMPANION_FOX, scale=2)
    pet_rects = compile_pixel_grid(COMPANION_FOX, scale=2, ox=236 - (cw // 2), oy=224 - ch)

    # Pokédex LCD specimen diorama sprites (scale=2 uniform pixel density)
    dex_hw, dex_hh = sprite_bounds(HERO_TRAINER, scale=2)
    dex_hero_rects = compile_pixel_grid(HERO_TRAINER, scale=2, ox=58 - (dex_hw // 2), oy=144 - dex_hh)
    dex_cw, dex_ch = sprite_bounds(COMPANION_FOX, scale=2)
    dex_pet_rects = compile_pixel_grid(COMPANION_FOX, scale=2, ox=108 - (dex_cw // 2), oy=146 - dex_ch)

    raiders_list = state.get("recent_raiders") or []
    raiders_text = ", ".join(f"@{r}" for r in raiders_list[:4]) if raiders_list else "Open to visitors"

    tavern_list = state.get("tavern_log") or []
    if tavern_list:
        latest = tavern_list[0]
        tavern_text = f"@{latest['user']}: \"{latest['note'][:26]}\""
    else:
        tavern_text = "Sign Guestbook"

    event_line1, event_line2 = _wrap_dialog(str(state.get("last_event") or ""))

    lang_segments = _build_language_segments(report, bar_width=278.0)
    exp_bar_width = round((report.level_progress_pct / 100.0) * 140.0, 2)
    sync_date = report.generated_at_utc[:10]
    buff_charges = int(state.get("hero_buff_charges", 0))

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def _emit(name: str, content: str) -> None:
        validate_svg_xml(content)
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(path)

    for mode, theme in THEMES.items():
        header_ball = compile_pixel_grid(PIXEL_POKEBALL, scale=1, ox=16, oy=13)
        _emit(
            f"battle-{mode}.svg",
            battle_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
                game=state,
                boss=boss,
                boss_index_1=boss_idx + 1,
                boss_level=boss_level,
                boss_hp_width=boss_hp_width,
                boss_hp_color=boss_hp_color,
                exp_bar_width=exp_bar_width,
                buff_charges=buff_charges,
                event_line1=event_line1,
                event_line2=event_line2,
                header_ball=header_ball,
                hero_rects=hero_rects,
                pet_rects=pet_rects,
                boss_rects=boss_rects,
                raiders_text=raiders_text,
                tavern_text=tavern_text,
            ),
        )

        badge_tiles, next_label = _build_pokedex_entries(report, theme)
        _emit(
            f"trainer-{mode}.svg",
            trainer_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
                dex_hero_rects=dex_hero_rects,
                dex_pet_rects=dex_pet_rects,
                dex_stat_bars=_build_dex_stat_bars(report, theme),
                badge_tiles=badge_tiles,
                next_label=next_label,
                lang_segments=lang_segments,
                sync_date=sync_date,
            ),
        )

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile pure-SVG GBA Battle & Pokédex SVGs.")
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
