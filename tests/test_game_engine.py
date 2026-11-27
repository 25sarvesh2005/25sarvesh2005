"""Unit tests for the interactive RPG Boss Raid engine."""

from __future__ import annotations

from scripts.game_engine import (
    BOSS_ROSTER,
    apply_visitor_move,
    init_game_state,
    parse_issue_action,
    sanitize_note,
    sync_commit_synergy,
)


def test_parse_issue_action_allowlist_only() -> None:
    assert parse_issue_action("raid|strike") == "strike"
    assert parse_issue_action("  RAID|OVERCLOCK  ") == "overclock"
    assert parse_issue_action("raid|buff") == "buff"
    assert parse_issue_action("raid|tavern") == "tavern"
    assert parse_issue_action("raid|$(whoami)") is None
    assert parse_issue_action("Normal bug report") is None


def test_sanitize_note_strips_urls_and_boilerplate() -> None:
    raw = "Optional battle cry (max 58 chars): Hello! https://evil.example <script>"
    cleaned = sanitize_note(raw)
    assert "https://" not in cleaned
    assert "<" not in cleaned
    assert "Hello!" in cleaned


def test_visitor_move_buff_strike_and_boss_ko_progression() -> None:
    state = init_game_state(565)
    state, _ = apply_visitor_move(state, issue_number=1, user_login="alice", action="buff")
    assert state["hero_buff_charges"] == 1

    # Reduce HP low enough to trigger KO on strike
    state["boss_hp"] = 10
    state, reply = apply_visitor_move(state, issue_number=2, user_login="bob", action="strike")
    assert state["bosses_slain"] == 1
    assert state["boss_index"] == 1
    assert state["boss_hp"] == BOSS_ROSTER[1].max_hp
    assert state["hero_buff_charges"] == 0
    assert "KO!" in reply
    assert state["recent_raiders"][:2] == ["bob", "alice"]


def test_tavern_log_records_sanitized_note() -> None:
    state = init_game_state(565)
    state, _ = apply_visitor_move(
        state,
        issue_number=3,
        user_login="octocat",
        action="tavern",
        raw_note="Leave a short hello for the profile log: Cool pixel arena!",
    )
    assert len(state["tavern_log"]) == 1
    assert state["tavern_log"][0]["user"] == "octocat"
    assert state["tavern_log"][0]["note"] == "Cool pixel arena!"


def test_sync_commit_synergy_deals_damage_only_on_delta() -> None:
    state = init_game_state(565)
    same = sync_commit_synergy(state, 565)
    assert same["boss_hp"] == BOSS_ROSTER[0].max_hp

    updated = sync_commit_synergy(state, 575)
    assert updated["boss_hp"] == BOSS_ROSTER[0].max_hp - 30
    assert updated["last_synced_contributions"] == 575
