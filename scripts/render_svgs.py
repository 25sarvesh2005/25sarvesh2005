"""Compile pure-SVG Pixel RPG Hero Header, Battle Arena, Trainer Card, Quest Cartridges, Armory, and Snake Banner."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scripts.compute_gamification import GamificationReport, evaluate_metrics
from scripts.config import ARMORY_SLOTS, FEATURED_CARTRIDGES, QUEST_RARITY, THEMES
from scripts.game_engine import get_active_boss, init_game_state
from scripts.pixel_sprites import (
    BOSS_SPRITES,
    CARTRIDGE_ICONS,
    COFFEE_MUG,
    COMPANION_SPARK,
    CYBER_TERMINAL,
    HERO_ARCHITECT,
    PIXEL_CLOUD,
    PIXEL_MOON,
    PIXEL_PADLOCK,
    PIXEL_SUN,
    QUEST_SPRITES,
    SERVER_RACK,
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
    bar_width: float = 508.0,
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


def _build_badge_tiles(
    report: GamificationReport,
    theme: dict[str, str],
) -> list[dict[str, object]]:
    """Build 4x3 rarity-framed pixel-art badge tile descriptors with compiled rectangles."""
    tiles: list[dict[str, object]] = []
    for idx, quest in enumerate(report.quests[:12]):
        col = idx % 4
        row = idx // 4
        bx = 308 + col * 128
        by = 72 + row * 76
        grid = QUEST_SPRITES[quest.key]
        sprite_rects = compile_pixel_grid(
            grid,
            scale=2,
            ox=bx + 51,
            oy=by + 12,
            locked_color=None if quest.unlocked else theme["bg_track"],
        )
        padlock_rects = (
            []
            if quest.unlocked
            else compile_pixel_grid(
                PIXEL_PADLOCK,
                scale=1,
                ox=bx + 109,
                oy=by + 8,
                locked_color=theme["text_subtle"],
            )
        )
        rarity_label, rarity_key = QUEST_RARITY.get(quest.key, ("RARE", "accent_primary"))
        rarity_color = theme[rarity_key] if quest.unlocked else theme["border"]

        if quest.unlocked:
            sub = f"{quest.current}{(' ' + quest.unit) if quest.unit else ''}"
        else:
            cur_str = f"{quest.current // 1000}k" if quest.current >= 10000 else str(quest.current)
            tgt_str = f"{quest.target // 1000}k" if quest.target >= 1000 else str(quest.target)
            sub = f"{cur_str}/{tgt_str}{quest.unit}"

        progress_w = round(max(0.0, min(1.0, quest.progress_pct / 100.0)) * 107.0, 1)
        tiles.append(
            {
                "x": bx,
                "y": by,
                "w": 121,
                "h": 70,
                "title": quest.title,
                "sub": sub,
                "unlocked": quest.unlocked,
                "rarity": rarity_label,
                "rarity_color": rarity_color,
                "is_legend": quest.unlocked and rarity_label in {"LEGEND", "EPIC"},
                "progress_w": progress_w,
                "rects": sprite_rects,
                "padlock_rects": padlock_rects,
            }
        )
    return tiles


def _build_power_bars(report: GamificationReport, theme: dict[str, str]) -> list[dict[str, object]]:
    """Compute 4 RPG attribute meters driven strictly from verified GitHub metrics."""
    raw_stats = [
        (
            "OUT",
            f"{report.contributions_12m}/yr",
            min(100, round((report.contributions_12m / 1200.0) * 100)),
            theme["accent_signal"],
        ),
        (
            "SHD",
            f"{report.ci_repos}CI·{report.documented_repos}D",
            min(100, round(((report.ci_repos + report.documented_repos) / 22.0) * 100)),
            theme["accent_primary"],
        ),
        (
            "STR",
            f"{report.longest_streak}d/{report.active_days}d",
            min(100, round((report.active_days / 200.0) * 100)),
            theme["accent_amber"],
        ),
        (
            "IMP",
            f"{report.merged_prs}PR·{report.external_stars}★",
            min(100, round((report.merged_prs * 8) + (report.external_stars * 8))),
            theme["accent_arcane"],
        ),
    ]
    bars: list[dict[str, object]] = []
    for idx, (label, val_text, pct, color) in enumerate(raw_stats):
        bars.append(
            {
                "y": 244 + idx * 24,
                "label": label,
                "value": val_text,
                "fill_w": round((max(6, pct) / 100.0) * 118.0, 1),
                "color": color,
            }
        )
    return bars


def _build_armory_quadrants(theme: dict[str, str]) -> list[dict[str, object]]:
    """Layout 2x2 RPG inventory quadrants with wrapped monospace tool chips."""
    quadrants: list[dict[str, object]] = []
    for idx, (slot_title, accent_key, items) in enumerate(ARMORY_SLOTS):
        col = idx % 2
        row = idx // 2
        qx = 16 + col * 408
        qy = 44 + row * 80
        inner_max = 378

        chips: list[dict[str, object]] = []
        cursor_x = 0
        row_offset = 0
        for label in items:
            chip_w = max(44, round(len(label) * 6.0) + 14)
            if cursor_x > 0 and cursor_x + chip_w > inner_max:
                cursor_x = 0
                row_offset += 22
            chips.append(
                {
                    "x": qx + 12 + cursor_x,
                    "y": qy + 24 + row_offset,
                    "w": chip_w,
                    "label": label,
                }
            )
            cursor_x += chip_w + 6

        quadrants.append(
            {
                "idx": idx + 1,
                "x": qx,
                "y": qy,
                "w": 400,
                "h": 74,
                "title": slot_title,
                "accent": theme[accent_key],
                "chips": chips,
            }
        )
    return quadrants


def _build_quest_cartridge_contexts(
    raw_metrics: dict[str, Any] | None,
) -> list[dict[str, object]]:
    """Merge live verified repo metadata with curated flagship CartridgeSpecs."""
    repo_map: dict[str, dict[str, Any]] = {}
    if raw_metrics:
        for repo in raw_metrics.get("owned_repositories") or []:
            name = str(repo.get("name") or "")
            if name:
                repo_map[name] = repo

    cards: list[dict[str, object]] = []
    for spec in FEATURED_CARTRIDGES:
        meta = repo_map.get(spec.repo_name, {})
        langs = list((meta.get("languages") or {}).keys())
        primary_lang = langs[0] if langs else "Python"
        cards.append(
            {
                "slug": spec.slug,
                "repo_name": spec.repo_name,
                "title": spec.title,
                "accent_key": spec.accent_key,
                "line1": spec.line1,
                "line2": spec.line2,
                "stack_label": spec.stack_label,
                "live_url": spec.live_url,
                "has_ci": bool(meta.get("has_ci", False)),
                "has_readme": bool(meta.get("has_readme", True)),
                "external_stars": int(meta.get("external_stars", 0)),
                "primary_lang": primary_lang,
                "sprite_rects": compile_pixel_grid(CARTRIDGE_ICONS[spec.sprite_key], scale=3, ox=26, oy=31),
            }
        )
    return cards


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
    raw_metrics: dict[str, Any] | None = None,
) -> list[Path]:
    """Render Light and Dark Pixel RPG profile SVGs, Quest Cartridges, Armory, and Snake Banner."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["svg", "j2", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    hero_tpl = env.get_template("hero.svg.j2")
    battle_tpl = env.get_template("battle.svg.j2")
    trainer_tpl = env.get_template("trainer.svg.j2")
    quest_tpl = env.get_template("quest_card.svg.j2")
    armory_tpl = env.get_template("armory.svg.j2")
    snake_tpl = env.get_template("snake_banner.svg.j2")

    state = game_state if game_state is not None else init_game_state(report.total_contributions)
    boss = get_active_boss(state)
    boss_hp = int(state.get("boss_hp", boss.max_hp))
    boss_hp_width = round(max(0.0, min(1.0, boss_hp / max(1, boss.max_hp))) * 212.0, 2)
    boss_accent_key = BOSS_ACCENT_MAP.get(boss.key, "accent_boss")

    # Arena sprites (expanded 18x18 Hero & 16x16 Boss)
    hero_rects = compile_pixel_grid(HERO_ARCHITECT, scale=5, ox=58, oy=124)
    pet_rects = compile_pixel_grid(COMPANION_SPARK, scale=4, ox=160, oy=168)
    boss_rects = compile_pixel_grid(BOSS_SPRITES[boss.key], scale=5, ox=658, oy=132)

    torch_left_rects = compile_pixel_grid(WALL_TORCH, scale=3, ox=24, oy=136)
    torch_right_rects = compile_pixel_grid(WALL_TORCH, scale=3, ox=796, oy=136)
    clash_rects = compile_pixel_grid(SWORD_CLASH, scale=3, ox=408, oy=132)
    moon_rects = compile_pixel_grid(PIXEL_MOON, scale=3, ox=522, oy=58)
    sun_rects = compile_pixel_grid(PIXEL_SUN, scale=3, ox=522, oy=58)
    cloud_rects = compile_pixel_grid(PIXEL_CLOUD, scale=2, ox=282, oy=64)

    hero_moon_rects = compile_pixel_grid(PIXEL_MOON, scale=3, ox=788, oy=42)
    hero_sun_rects = compile_pixel_grid(PIXEL_SUN, scale=3, ox=788, oy=42)
    hero_cloud_rects = compile_pixel_grid(PIXEL_CLOUD, scale=2, ox=716, oy=48)

    # Trainer Cyber-Sanctuary diorama sprites (non-overlapping, grounded at y=142)
    trainer_rack_rects = compile_pixel_grid(SERVER_RACK, scale=3, ox=32, oy=109)
    trainer_avatar_rects = compile_pixel_grid(HERO_ARCHITECT, scale=4, ox=64, oy=74)
    trainer_pet_rects = compile_pixel_grid(COMPANION_SPARK, scale=3, ox=138, oy=115)
    mug_rects = compile_pixel_grid(COFFEE_MUG, scale=2, ox=174, oy=126)
    trainer_term_rects = compile_pixel_grid(CYBER_TERMINAL, scale=3, ox=202, oy=112)

    raiders_list = state.get("recent_raiders") or []
    raiders_text = ", ".join(f"@{r}" for r in raiders_list[:4]) if raiders_list else "Awaiting first challenger"

    tavern_list = state.get("tavern_log") or []
    if tavern_list:
        latest = tavern_list[0]
        tavern_text = f"@{latest['user']}: \"{latest['note'][:34]}\""
    else:
        tavern_text = "Sign Tavern Log below!"

    lang_segments = _build_language_segments(report, bar_width=508.0)
    xp_bar_width = round((report.level_progress_pct / 100.0) * 252.0, 2)
    sync_date = report.generated_at_utc[:10]
    buff_charges = int(state.get("hero_buff_charges", 0))
    cartridges = _build_quest_cartridge_contexts(raw_metrics)

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def _emit(name: str, content: str) -> None:
        validate_svg_xml(content)
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(path)

    for mode, theme in THEMES.items():
        _emit(
            f"hero-{mode}.svg",
            hero_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
                celestial_rects=hero_moon_rects if mode == "dark" else hero_sun_rects,
                cloud_rects=[] if mode == "dark" else hero_cloud_rects,
                sync_date=sync_date,
            ),
        )

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
                torch_left_rects=torch_left_rects,
                torch_right_rects=torch_right_rects,
                clash_rects=clash_rects,
                celestial_rects=moon_rects if mode == "dark" else sun_rects,
                cloud_rects=[] if mode == "dark" else cloud_rects,
                raiders_text=raiders_text,
                tavern_text=tavern_text,
                sync_date=sync_date,
            ),
        )

        _emit(
            f"trainer-{mode}.svg",
            trainer_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
                xp_bar_width=xp_bar_width,
                rack_rects=trainer_rack_rects,
                avatar_rects=trainer_avatar_rects,
                pet_rects=trainer_pet_rects,
                term_rects=trainer_term_rects,
                mug_rects=mug_rects,
                power_bars=_build_power_bars(report, theme),
                badge_tiles=_build_badge_tiles(report, theme),
                lang_segments=lang_segments,
                sync_date=sync_date,
            ),
        )

        for card in cartridges:
            _emit(
                f"quest-{card['slug']}-{mode}.svg",
                quest_tpl.render(
                    mode=mode,
                    theme=theme,
                    card=card,
                    accent=theme[str(card["accent_key"])],
                ),
            )

        _emit(
            f"armory-{mode}.svg",
            armory_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
                quadrants=_build_armory_quadrants(theme),
            ),
        )

        _emit(
            f"snake-banner-{mode}.svg",
            snake_tpl.render(
                mode=mode,
                theme=theme,
                report=report,
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
