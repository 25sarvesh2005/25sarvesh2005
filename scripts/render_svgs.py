"""Compile pure-SVG Pixel RPG Battle Arena and Engineering Telemetry Card SVGs."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scripts.compute_gamification import GamificationReport, QuestProgress, evaluate_metrics
from scripts.config import QUEST_PLAIN_LABELS, SUPERSEDED_QUESTS, THEMES
from scripts.game_engine import get_active_boss, init_game_state
from scripts.pixel_sprites import (
    BOSS_SPRITES,
    BOSS_WAVE,
    COMPANION_SPARK,
    HERO_ARCHITECT,
    HERO_WAVE,
    PIXEL_CLOUD,
    PIXEL_MOON,
    PIXEL_SUN,
    QUEST_SPRITES,
    SWORD_CLASH,
    WALL_TORCH,
    compile_pixel_grid,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"

BOSS_ACCENT_MAP: dict[str, str] = {
    "nullpointer_wyrm": "accent_boss",
    "merge_golem": "accent_amber",
    "hallucination_phantom": "accent_arcane",
    "legacy_monolith": "accent_signal",
}


def _build_language_segments(
    report: GamificationReport,
    bar_width: float = 266.0,
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


def _select_display_quests(report: GamificationReport) -> list[QuestProgress]:
    """Select up to 9 high-signal unique milestones, hiding superseded tiers and 0-count locks."""
    by_key = {q.key: q for q in report.quests}
    unlocked = [
        q
        for q in report.quests
        if q.unlocked and not (q.key in SUPERSEDED_QUESTS and by_key[SUPERSEDED_QUESTS[q.key]].unlocked)
    ]
    in_progress = [
        q
        for q in report.quests
        if not q.unlocked and q.current > 0
    ]
    selected = unlocked[:9]
    if len(selected) < 9:
        selected.extend(in_progress[: 9 - len(selected)])
    if len(selected) < 6:
        remaining = [q for q in report.quests if q not in selected]
        selected.extend(remaining[: 6 - len(selected)])
    return selected[:9]


def _build_badge_tiles(
    report: GamificationReport,
    theme: dict[str, str],
) -> list[dict[str, object]]:
    """Build 3x3 horizontal achievement plaques with crisp 3x pixel sprites."""
    tiles: list[dict[str, object]] = []
    for idx, quest in enumerate(_select_display_quests(report)):
        col = idx % 3
        row = idx // 3
        bx = 324 + col * 168
        by = 72 + row * 58
        sprite_rects = compile_pixel_grid(
            QUEST_SPRITES[quest.key],
            scale=3,
            ox=bx + 9,
            oy=by + 11,
            locked_color=None if quest.unlocked else theme["bg_track"],
        )
        plain_unit = QUEST_PLAIN_LABELS.get(quest.key, quest.unit)
        if quest.key == "genesis_commit":
            years = round(quest.current / 365.0, 1)
            sub = f"{years:g} yrs on GitHub" if quest.unlocked else f"{quest.current}/{quest.target} days"
        elif quest.unlocked:
            sub = f"{quest.current:,} {plain_unit}".strip()
        else:
            sub = f"{quest.current}/{quest.target} {plain_unit}".strip()

        progress_w = round(max(0.0, min(1.0, quest.progress_pct / 100.0)) * 112.0, 1)
        tiles.append(
            {
                "x": bx,
                "y": by,
                "w": 160,
                "h": 52,
                "title": quest.title,
                "sub": sub,
                "unlocked": quest.unlocked,
                "progress_w": progress_w,
                "rects": sprite_rects,
            }
        )
    return tiles


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
    raw_metrics: dict[str, Any] | None = None,  # noqa: ARG001 - kept for API compatibility
) -> list[Path]:
    """Render Light and Dark Battle Arena and Developer Telemetry Card SVGs."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["svg", "j2", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    battle_tpl = env.get_template("battle.svg.j2")
    trainer_tpl = env.get_template("trainer.svg.j2")

    state = game_state if game_state is not None else init_game_state(report.total_contributions)
    boss = get_active_boss(state)
    boss_hp = int(state.get("boss_hp", boss.max_hp))
    boss_hp_width = round(max(0.0, min(1.0, boss_hp / max(1, boss.max_hp))) * 206.0, 2)
    boss_accent_key = BOSS_ACCENT_MAP.get(boss.key, "accent_boss")

    # Strict 4px world-pixel sprites grounded cleanly on stone floor y=204
    hero_rects = compile_pixel_grid(HERO_ARCHITECT, scale=4, ox=68, oy=140)
    pet_rects = compile_pixel_grid(COMPANION_SPARK, scale=4, ox=160, oy=166)
    boss_rects = compile_pixel_grid(BOSS_SPRITES[boss.key], scale=4, ox=672, oy=140)

    hero_wave_rects = compile_pixel_grid(HERO_WAVE, scale=4, ox=224, oy=160)
    boss_wave_rects = compile_pixel_grid(BOSS_WAVE, scale=4, ox=584, oy=160)
    clash_rects = compile_pixel_grid(SWORD_CLASH, scale=4, ox=406, oy=156)

    torch_left_rects = compile_pixel_grid(WALL_TORCH, scale=4, ox=24, oy=142)
    torch_right_rects = compile_pixel_grid(WALL_TORCH, scale=4, ox=796, oy=142)

    moon_rects = compile_pixel_grid(PIXEL_MOON, scale=4, ox=404, oy=56)
    sun_rects = compile_pixel_grid(PIXEL_SUN, scale=4, ox=404, oy=56)
    cloud_rects = compile_pixel_grid(PIXEL_CLOUD, scale=3, ox=342, oy=66)

    raiders_list = state.get("recent_raiders") or []
    raiders_text = ", ".join(f"@{r}" for r in raiders_list[:4]) if raiders_list else "Awaiting first challenger"

    tavern_list = state.get("tavern_log") or []
    if tavern_list:
        latest = tavern_list[0]
        tavern_text = f"@{latest['user']}: \"{latest['note'][:34]}\""
    else:
        tavern_text = "Sign guestbook below"

    lang_segments = _build_language_segments(report, bar_width=266.0)
    xp_bar_width = round((report.level_progress_pct / 100.0) * 266.0, 2)
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
        _emit(
            f"battle-{mode}.svg",
            battle_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
                game=state,
                boss=boss,
                boss_index_1=int(state.get("boss_index", 0)) + 1,
                boss_hp_width=boss_hp_width,
                boss_accent=theme[boss_accent_key],
                buff_charges=buff_charges,
                hero_rects=hero_rects,
                pet_rects=pet_rects,
                boss_rects=boss_rects,
                hero_wave_rects=hero_wave_rects,
                boss_wave_rects=boss_wave_rects,
                clash_rects=clash_rects,
                torch_left_rects=torch_left_rects,
                torch_right_rects=torch_right_rects,
                celestial_rects=moon_rects if mode == "dark" else sun_rects,
                cloud_rects=[] if mode == "dark" else cloud_rects,
                raiders_text=raiders_text,
                tavern_text=tavern_text,
            ),
        )

        _emit(
            f"trainer-{mode}.svg",
            trainer_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
                xp_bar_width=xp_bar_width,
                badge_tiles=_build_badge_tiles(report, theme),
                lang_segments=lang_segments,
                sync_date=sync_date,
            ),
        )

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile pure-SVG Pixel RPG profile assets.")
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
