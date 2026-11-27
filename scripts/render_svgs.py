"""Compile pure-SVG Pixel RPG Battle Arena and Trainer Card assets."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scripts.compute_gamification import GamificationReport, evaluate_metrics
from scripts.config import THEMES
from scripts.game_engine import get_active_boss, init_game_state
from scripts.pixel_sprites import (
    BOSS_SPRITES,
    COFFEE_MUG,
    COMPANION_SPARK,
    HERO_ARCHITECT,
    PIXEL_CLOUD,
    PIXEL_MOON,
    PIXEL_SUN,
    QUEST_SPRITES,
    SWORD_CLASH,
    WALL_TORCH,
    compile_pixel_grid,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"


def _build_language_segments(report: GamificationReport, bar_width: float = 506.0) -> list[dict[str, object]]:
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


def _build_badge_tiles(report: GamificationReport, *, locked_fill: str) -> list[dict[str, object]]:
    """Build 4x3 pixel-art badge tile descriptors with compiled pixel rectangles."""
    tiles: list[dict[str, object]] = []
    for idx, quest in enumerate(report.quests[:12]):
        col = idx % 4
        row = idx // 4
        bx = 306 + col * 128
        by = 72 + row * 62
        grid = QUEST_SPRITES[quest.key]
        sprite_rects = compile_pixel_grid(
            grid,
            scale=2,
            ox=bx + 50,
            oy=by + 6,
            locked_color=None if quest.unlocked else locked_fill,
        )
        if quest.unlocked:
            sub = f"{quest.current}{(' ' + quest.unit) if quest.unit else ''}"
        else:
            cur_str = f"{quest.current // 1000}k" if quest.current >= 10000 else str(quest.current)
            tgt_str = f"{quest.target // 1000}k" if quest.target >= 1000 else str(quest.target)
            sub = f"{cur_str}/{tgt_str}{quest.unit}"
        tiles.append(
            {
                "x": bx,
                "y": by,
                "title": quest.title,
                "sub": sub,
                "unlocked": quest.unlocked,
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
) -> list[Path]:
    """Render Light and Dark Battle Arena and Pixel Trainer Card SVGs."""
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
    boss_hp_width = round(max(0.0, min(1.0, boss_hp / max(1, boss.max_hp))) * 196.0, 2)

    hero_rects = compile_pixel_grid(HERO_ARCHITECT, scale=5, ox=58, oy=92)
    pet_rects = compile_pixel_grid(COMPANION_SPARK, scale=4, ox=152, oy=132)
    boss_rects = compile_pixel_grid(BOSS_SPRITES[boss.key], scale=5, ox=652, oy=92)

    torch_left_rects = compile_pixel_grid(WALL_TORCH, scale=3, ox=24, oy=108)
    torch_right_rects = compile_pixel_grid(WALL_TORCH, scale=3, ox=794, oy=108)
    clash_rects = compile_pixel_grid(SWORD_CLASH, scale=2, ox=412, oy=78)
    moon_rects = compile_pixel_grid(PIXEL_MOON, scale=3, ox=496, oy=52)
    sun_rects = compile_pixel_grid(PIXEL_SUN, scale=3, ox=496, oy=52)
    cloud_rects = compile_pixel_grid(PIXEL_CLOUD, scale=2, ox=286, oy=58)

    trainer_avatar_rects = compile_pixel_grid(HERO_ARCHITECT, scale=4, ox=38, oy=70)
    trainer_pet_rects = compile_pixel_grid(COMPANION_SPARK, scale=3, ox=108, oy=104)
    mug_rects = compile_pixel_grid(COFFEE_MUG, scale=2, ox=144, oy=124)

    raiders_list = state.get("recent_raiders") or []
    raiders_text = ", ".join(f"@{r}" for r in raiders_list[:4]) if raiders_list else "Awaiting first challenger"

    tavern_list = state.get("tavern_log") or []
    if tavern_list:
        latest = tavern_list[0]
        tavern_text = f"@{latest['user']}: \"{latest['note'][:34]}\""
    else:
        tavern_text = "Sign Tavern Log below!"

    lang_segments = _build_language_segments(report)
    xp_bar_width = round((report.level_progress_pct / 100.0) * 240.0, 2)
    sync_date = report.generated_at_utc[:10]

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for mode, theme in THEMES.items():
        battle_svg = battle_tpl.render(
            mode=mode,
            theme=theme,
            report=report,
            game=state,
            boss=boss,
            boss_index_1=int(state.get("boss_index", 0)) + 1,
            boss_hp_width=boss_hp_width,
            hero_rects=hero_rects,
            pet_rects=pet_rects,
            boss_rects=boss_rects,
            torch_left_rects=torch_left_rects,
            torch_right_rects=torch_right_rects,
            clash_rects=clash_rects,
            celestial_rects=moon_rects if mode == "dark" else sun_rects,
            cloud_rects=[] if mode == "dark" else cloud_rects,
            raiders_text=raiders_text,
            tavern_text=tavern_text,
            sync_date=sync_date,
        )
        validate_svg_xml(battle_svg)
        b_path = out_dir / f"battle-{mode}.svg"
        b_path.write_text(battle_svg, encoding="utf-8")
        written.append(b_path)

        badge_tiles = _build_badge_tiles(report, locked_fill=theme["bg_track"])
        trainer_svg = trainer_tpl.render(
            mode=mode,
            theme=theme,
            report=report,
            xp_bar_width=xp_bar_width,
            avatar_rects=trainer_avatar_rects,
            pet_rects=trainer_pet_rects,
            mug_rects=mug_rects,
            badge_tiles=badge_tiles,
            lang_segments=lang_segments,
            sync_date=sync_date,
        )
        validate_svg_xml(trainer_svg)
        t_path = out_dir / f"trainer-{mode}.svg"
        t_path.write_text(trainer_svg, encoding="utf-8")
        written.append(t_path)

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

    paths = render_all_svgs(report, args.out_dir, game_state=game_state)

    if args.report_out:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    for path in paths:
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
