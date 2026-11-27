"""Deterministic interactive RPG Boss Raid engine powered by GitHub Issues & commits."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BossSpec:
    """Definition of a rotating pixel-art dungeon boss."""

    key: str
    name: str
    subtitle: str
    max_hp: int


BOSS_ROSTER: tuple[BossSpec, ...] = (
    BossSpec(
        key="nullpointer_wyrm",
        name="NullPointer Wyrm",
        subtitle="LVL 12 DUNGEON GUARDIAN",
        max_hp=240,
    ),
    BossSpec(
        key="merge_golem",
        name="Merge Conflict Golem",
        subtitle="LVL 15 BRANCH TITAN",
        max_hp=320,
    ),
    BossSpec(
        key="hallucination_phantom",
        name="Hallucination Phantom",
        subtitle="LVL 18 UNGROUNDED WRAITH",
        max_hp=400,
    ),
    BossSpec(
        key="legacy_monolith",
        name="Legacy Monolith",
        subtitle="LVL 20 SPAGHETTI FORTRESS",
        max_hp=500,
    ),
)

VALID_ACTIONS = frozenset({"strike", "overclock", "buff", "tavern"})


def init_game_state(initial_contributions: int = 565) -> dict[str, Any]:
    """Create clean initial Boss Raid state anchored to verified baseline."""
    first_boss = BOSS_ROSTER[0]
    return {
        "schema_version": 1,
        "boss_index": 0,
        "boss_hp": first_boss.max_hp,
        "bosses_slain": 0,
        "total_raids": 0,
        "hero_buff_charges": 0,
        "last_synced_contributions": initial_contributions,
        "last_event": f"{first_boss.name} appeared! Click an action below to attack.",
        "recent_raiders": [],
        "tavern_log": [],
    }


def get_active_boss(state: dict[str, Any]) -> BossSpec:
    """Return currently active boss specification."""
    idx = int(state.get("boss_index", 0)) % len(BOSS_ROSTER)
    return BOSS_ROSTER[idx]


def parse_issue_action(issue_title: str) -> str | None:
    """Extract allowlisted raid action from issue title like 'raid|strike'."""
    match = re.match(r"^\s*raid\|([a-z]+)\s*$", issue_title.lower())
    if not match:
        return None
    action = match.group(1)
    return action if action in VALID_ACTIONS else None


def sanitize_note(raw_body: str, *, max_len: int = 58) -> str:
    """Strip markdown boilerplate, URLs, and unsafe characters from optional visitor notes."""
    text = re.sub(r"Optional battle cry[^:]*:\s*", "", raw_body or "", flags=re.I)
    text = re.sub(r"Leave a short hello[^:]*:\s*", "", text, flags=re.I)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9 .,!?_'+\-:/()@#]", "", text).strip()
    text = re.sub(r"\s{2,}", " ", text)
    return text[:max_len].strip()


def sanitize_username(login: str) -> str:
    """Restrict GitHub handle to safe display characters."""
    cleaned = re.sub(r"[^a-zA-Z0-9\-]", "", login or "")
    return cleaned[:39] or "wanderer"


def _deterministic_roll(seed_str: str, low: int, high: int) -> int:
    digest = hashlib.sha256(seed_str.encode("utf-8")).digest()
    val = int.from_bytes(digest[:4], "big")
    return low + (val % (high - low + 1))


def _advance_boss_if_defeated(state: dict[str, Any]) -> str | None:
    if int(state["boss_hp"]) > 0:
        return None
    slain_boss = get_active_boss(state)
    state["bosses_slain"] = int(state.get("bosses_slain", 0)) + 1
    state["boss_index"] = (int(state.get("boss_index", 0)) + 1) % len(BOSS_ROSTER)
    next_boss = get_active_boss(state)
    state["boss_hp"] = next_boss.max_hp
    return f"KO! {slain_boss.name} defeated — {next_boss.name} enters!"


def apply_visitor_move(
    state: dict[str, Any],
    *,
    issue_number: int,
    user_login: str,
    action: str,
    raw_note: str = "",
) -> tuple[dict[str, Any], str]:
    """Apply a single validated visitor action and return (updated_state, combat_reply)."""
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported raid action: {action}")

    next_state = json.loads(json.dumps(state))
    player = sanitize_username(user_login)
    note = sanitize_note(raw_note)
    boss = get_active_boss(next_state)
    seed = f"{issue_number}:{player}:{action}:{next_state.get('total_raids', 0)}"

    buffs = int(next_state.get("hero_buff_charges", 0))
    bonus_dmg = buffs * 10

    if action == "strike":
        dmg = _deterministic_roll(seed, 16, 28) + bonus_dmg
        next_state["hero_buff_charges"] = 0
        next_state["boss_hp"] = max(0, int(next_state["boss_hp"]) - dmg)
        summary = f"@{player} struck {boss.name} for {dmg} DMG!"
    elif action == "overclock":
        dmg = _deterministic_roll(seed, 26, 44) + bonus_dmg
        next_state["hero_buff_charges"] = 0
        next_state["boss_hp"] = max(0, int(next_state["boss_hp"]) - dmg)
        summary = f"@{player} cast Overclock Crit for {dmg} DMG!"
    elif action == "buff":
        next_state["hero_buff_charges"] = min(5, buffs + 1)
        summary = f"@{player} brewed Focus Potion (+10 next hit DMG)!"
    else:  # tavern
        clean_msg = note or "Dropped by to explore the builds!"
        entry = {"user": player, "note": clean_msg, "issue": issue_number}
        log = [entry, *[x for x in next_state.get("tavern_log", []) if x.get("issue") != issue_number]]
        next_state["tavern_log"] = log[:4]
        summary = f"@{player} signed Tavern: \"{clean_msg[:36]}\""

    next_state["total_raids"] = int(next_state.get("total_raids", 0)) + 1
    ko_msg = _advance_boss_if_defeated(next_state)
    final_msg = f"{summary} {ko_msg}" if ko_msg else summary
    next_state["last_event"] = final_msg

    raiders = [r for r in next_state.get("recent_raiders", []) if r != player]
    next_state["recent_raiders"] = [player, *raiders][:4]

    new_boss = get_active_boss(next_state)
    reply = (
        f"⚔️ **{summary}**\n\n"
        + (f"🏆 **{ko_msg}**\n\n" if ko_msg else "")
        + f"- **Active Boss:** {new_boss.name} (`{next_state['boss_hp']} / {new_boss.max_hp} HP`)\n"
        + f"- **Bosses Slain:** `{next_state['bosses_slain']}` · **Total Raid Moves:** `{next_state['total_raids']}`\n\n"
        + "Thanks for playing! The profile battle scene updates automatically on `https://github.com/25sarvesh2005`."
    )
    return next_state, reply


def sync_commit_synergy(state: dict[str, Any], total_contributions: int) -> dict[str, Any]:
    """Deal bonus Architect Slash damage whenever Sarvesh logs new real GitHub contributions."""
    next_state = json.loads(json.dumps(state))
    prev = int(next_state.get("last_synced_contributions", total_contributions))
    delta = max(0, total_contributions - prev)
    next_state["last_synced_contributions"] = max(prev, total_contributions)

    if delta <= 0:
        return next_state

    boss = get_active_boss(next_state)
    dmg = min(boss.max_hp, delta * 3)
    next_state["boss_hp"] = max(0, int(next_state["boss_hp"]) - dmg)
    summary = f"Architect @25sarvesh2005 pushed +{delta} contribs ({dmg} DMG)!"
    ko_msg = _advance_boss_if_defeated(next_state)
    next_state["last_event"] = f"{summary} {ko_msg}" if ko_msg else summary
    return next_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Process a visitor issue raid move.")
    parser.add_argument("--state", type=Path, required=True, help="Path to game_state.json")
    parser.add_argument("--reply-out", type=Path, required=True, help="Markdown reply output file")
    args = parser.parse_args()

    issue_title = os.environ.get("EVENT_ISSUE_TITLE", "")
    issue_body = os.environ.get("EVENT_ISSUE_BODY", "")
    issue_num = int(os.environ.get("EVENT_ISSUE_NUMBER", "0") or 0)
    user_login = os.environ.get("EVENT_USER_LOGIN", "wanderer")

    action = parse_issue_action(issue_title)
    if action is None:
        args.reply_out.write_text(
            "Invalid raid command. Use the action buttons on the profile README (`raid|strike`, `raid|overclock`, `raid|buff`, `raid|tavern`).",
            encoding="utf-8",
        )
        raise SystemExit(2)

    if args.state.exists():
        state = json.loads(args.state.read_text(encoding="utf-8"))
    else:
        state = init_game_state()

    updated, reply = apply_visitor_move(
        state,
        issue_number=issue_num,
        user_login=user_login,
        action=action,
        raw_note=issue_body,
    )
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    args.reply_out.write_text(reply, encoding="utf-8")
    print(f"Processed {action} from @{sanitize_username(user_login)} (#{issue_num})")


if __name__ == "__main__":
    main()
