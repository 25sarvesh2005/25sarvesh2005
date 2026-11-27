"""Tests for pure-SVG Pixel RPG rendering, milestone filtering, and XSS safety."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts.compute_gamification import evaluate_metrics
from scripts.game_engine import apply_visitor_move, init_game_state
from scripts.render_svgs import _select_display_quests, render_all_svgs, validate_svg_xml
from tests.test_compute_gamification import _sample_raw_metrics


def test_render_all_svgs_outputs_valid_pure_svgs(tmp_path: Path) -> None:
    raw = _sample_raw_metrics()
    # Inject XML-special characters to confirm autoescaping works cleanly.
    raw["user"]["name"] = "Sarvesh <Sharma> & Co"
    report = evaluate_metrics(raw, reference_date=date(2026, 11, 26))

    game_state = init_game_state(report.total_contributions)
    game_state, _ = apply_visitor_move(
        game_state,
        issue_number=7,
        user_login="visitor-1",
        action="tavern",
        raw_note="Nice <script>test</script>!",
    )

    paths = render_all_svgs(report, tmp_path, game_state=game_state, raw_metrics=raw)
    names = sorted(p.name for p in paths)
    assert names == [
        "battle-dark.svg",
        "battle-light.svg",
        "trainer-dark.svg",
        "trainer-light.svg",
    ]
    for p in paths:
        content = p.read_text(encoding="utf-8")
        validate_svg_xml(content)
        assert "<foreignObject" not in content
        assert "<script" not in content


def test_select_display_quests_dedupes_superseded_tiers_and_caps_at_8() -> None:
    raw = _sample_raw_metrics()
    raw["contributions"]["daily"]["2026-11-24"] = 950  # crosses both 500 Club & 1K Builder
    report = evaluate_metrics(raw, reference_date=date(2026, 11, 26))
    selected, next_target = _select_display_quests(report)
    keys = {q.key for q in selected}
    assert len(selected) <= 8
    assert "builder_1k" in keys
    assert "club_500" not in keys
    assert next_target is not None and not next_target.unlocked


def test_static_action_buttons_are_valid_pure_svgs() -> None:
    static_dir = Path(__file__).resolve().parent.parent / "assets" / "static"
    buttons = sorted(p.name for p in static_dir.glob("btn-*.svg"))
    assert buttons == ["btn-buff.svg", "btn-overclock.svg", "btn-star.svg", "btn-strike.svg", "btn-tavern.svg"]
    for name in buttons:
        validate_svg_xml((static_dir / name).read_text(encoding="utf-8"))


def test_validate_svg_xml_rejects_foreign_object() -> None:
    bad_svg = '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>'
    with pytest.raises(ValueError, match="Forbidden SVG element"):
        validate_svg_xml(bad_svg)
