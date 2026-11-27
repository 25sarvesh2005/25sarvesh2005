"""Pure-SVG GBA 2px pixel-art sprite compiler with tinted outlines & run-length merging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PixelRect:
    """Merged horizontal pixel span for compact crisp-edge SVG output."""

    x: int
    y: int
    w: int
    h: int
    fill: str


SPRITE_PALETTE: dict[str, str] = {
    "K": "#182032",  # tinted dark navy ink
    "Z": "#4C0519",  # deep crimson ink
    "Q": "#2E1065",  # deep twilight purple ink
    "X": "#064E3B",  # deep forest ink
    "W": "#F8FAFC",  # crisp specular white
    "C": "#FFFFFF",  # pure highlight white
    "S": "#94A3B8",  # cool steel grey
    "D": "#475569",  # dark slate shadow
    "H": "#BAE6FD",  # ice cyan highlight
    "B": "#38BDF8",  # radiant sky cyan
    "I": "#1D4ED8",  # deep sapphire blue
    "N": "#1E293B",  # dark navy cloth
    "F": "#FDBA74",  # warm skin midtone
    "J": "#EA580C",  # warm skin shadow
    "L": "#A7F3D0",  # bright mint emerald
    "G": "#10B981",  # vibrant emerald
    "E": "#047857",  # deep emerald shadow
    "A": "#FEF08A",  # bright yellow spark
    "Y": "#F59E0B",  # golden amber
    "O": "#B45309",  # deep amber bronze
    "T": "#FDA4AF",  # rose highlight
    "R": "#E11D48",  # crimson scale / coat
    "M": "#9F1239",  # shaded crimson
    "P": "#A78BFA",  # arcane lavender
    "U": "#C4B5FD",  # pale spectral mist
    "V": "#6D28D9",  # deep violet
}

# 10x10 Classic Pokeball Icon (caught milestone indicator in Pokedex)
PIXEL_POKEBALL: tuple[str, ...] = (
    "...KKKK...",
    ".KKRRRRKK.",
    "KRRRRRRRKK",
    "KRRTRRRRKK",
    "KKKKWWKKKK",
    "KKKWWWWKKK",
    "KSSWWWWSSK",
    ".KSSSSSSK.",
    "..KKKKKK..",
    "..........",
)

# 26x28 Three-Quarter Back-View GBA Pokémon Trainer (sapphire cap, crimson visor band, satchel & jacket facing up-right)
HERO_TRAINER: tuple[str, ...] = (
    "........KKKKKKKK..........",
    "......KKIIIIIIIIKK........",
    ".....KIIHHHHHHIIIIK.......",
    "....KIIHHWWWWWHIIIIK......",
    "....KIIRRRRRRRRRRIIK......",
    "...KIKKKKKKKKKKKKKKKK.....",
    "...KIKNNNHHHKNNNNFJK......",
    "...KNNNNNNNKFFFFFJK.......",
    "....KNNNNNNKFFFJJK........",
    ".....KKKKKKKFFKK..........",
    "....KKIIIIIIIIIKK.........",
    "...KIIHHHHIIIIIHIK....W...",
    "..KIIHHHHIIOOOIHIK...WH...",
    "..KIIIIIINNOOONIIK..WHB...",
    ".KIIIINNNNNNOONNNK.WHB....",
    ".KIIINNNNNNNNNNNK.WHB.....",
    "..KKKNNNNNNNNNNK.KYK......",
    "....KNNNNNNNNNK..K........",
    "....KNNNNNNNNNK...........",
    "....KNNNNKKNNNK...........",
    "....KNNNK..KNNK...........",
    "....KNNNK..KNNK...........",
    "....KDDDK..KDDK...........",
    "....KDDDK..KDDK...........",
    "....KWWWK..KWWK...........",
    "...KRRRRK..KRRRRK.........",
    "...KKKKKK..KKKKKK.........",
    "..........................",
)

# 24x20 Shaded GBA Starter Companion ("Sparklynx" crouched facing up-right with curled tail & bright catchlight eye)
COMPANION_FOX: tuple[str, ...] = (
    "............KK....KK....",
    "...........KLLK..KGGK...",
    ".KKKK......KLGK..KGEK...",
    "KLLLLKK....KGGKKKKGEK...",
    "KLLGGGGK..KGGGGGGGGGEK..",
    ".KGGGEEEKKGGGGGGGGGGWK..",
    "..KKGEEEKGGGGGLLLGGKWWK.",
    "....KGGGKGGGGGLLLGKKKK..",
    ".....KGGGEEEEGGGGGGGGK..",
    "......KGGGGGGGGGGGYYGK..",
    "......KGGGGGGGGGGGGGGK..",
    ".....KGGGGGGGGGGEEEEGK..",
    ".....KGGGEEGGGGEEEEEEKK.",
    ".....KGGK.KGGGKEEEKK....",
    "....KGGK..KGGK.KGGK.....",
    "....KLLK..KLLK.KLLK.....",
    "....KKKK..KKKK.KKKK.....",
    "........................",
    "........................",
    "........................",
)

# 34x26 Shaded Pokémon GBA Bosses facing down-left toward Player (full 26-row height)
BOSS_SPRITES: dict[str, tuple[str, ...]] = {
    "nullpointer_wyrm": (
        "......ZZ........ZZ......ZZZZZ.....",
        ".....ZRRZ......ZRZZ...ZZMMMMMZ....",
        "....ZRTTRZ....ZRTZZ..ZMMMMMMMMZ...",
        "...ZRRRRRRZZZZRRRRZ.ZMMMMRRMMMMZ..",
        "..ZRRRRRAAARRRRRRRZ.ZMMMZZRMMMMZ..",
        ".ZRRRRAAWWWRRRRRRRZ.ZMMZ..ZZMMZ...",
        "ZRRRRRKKKKRRRRRRRRZZZMZ.....ZZ....",
        "ZRRWWWRRRRRRYYYYRRRZZZ............",
        ".ZZWWZ.ZRRRRYYYYYYRZ..............",
        "...ZZ...ZRRRYYAAYYRZZ........ZZ...",
        ".......ZMRRRYYAAYYRMMZ......ZRMZ..",
        "......ZMMRRRYYYYYYRRMMZ....ZRRRMZ.",
        ".....ZMMRRRRYYYYYYRRRMMZ..ZRRRRMMZ",
        "....ZMMRRRRRRRRRRRRRRRMMZZRRMMMMZ.",
        "....ZMMRRRRMMRRRRMMRRRRMMMMRRMMZ..",
        ".....ZMMMRRMMZ..ZMMRRRRRRRRRMMZ...",
        "......ZMMRRMMZ...ZMMMRRRRRRMMZ....",
        "......ZMMZZMMZ....ZMMMRRRRMMZ.....",
        ".....ZMMZ..ZMMZ....ZZMMMMMMZ......",
        ".....ZMRZ..ZMRZ......ZZZZZZ.......",
        "....ZRRZ....ZRRZ..................",
        "....ZYYZ....ZYYZ..................",
        "....ZZZZ....ZZZZ..................",
        "..................................",
        "..................................",
        "..................................",
    ),
    "merge_golem": (
        "..........KKKKKKKKKK..............",
        "........KKSSSSSSSSSSKK............",
        "......KKSSWWWWSSSSDDSSKK..........",
        ".....KSSWWSSSSSSSDDDDDSSK.........",
        "....KSSKKKKKKKKKKDDDDDDDSK........",
        "...KSSKAAAAKKAAAAKDDDDDDDSK.......",
        "...KSSKYYYYKKYYYYKDDDDDDDDSSKK....",
        "..KSSSKKKKKKKKKKKKSSDDDDDDDDSSK...",
        ".KSSDDSSSSSSSSSSSSDDSSDDDDSSDDDK..",
        "KSSSDDDSSYYYYYYSSSDDSSDDDDSSDDDK..",
        "KSDDDDDSSYYAAYYSSSDDDDDDDDSSDDDK..",
        "KSDDDDDSSYYYYYYSSSDDDDDDDDSSDDDK..",
        "KSSDDKKSSSSSSSSSSSDDDDDDDSSSDDDK..",
        ".KKKK.KSSDDDDDDDDDDDDDDSSSDDDKK...",
        "......KSSDDDDDDDDDDDDDDSSSSKK.....",
        "......KSSDDDDKKKKKKDDDDSSSK.......",
        "......KSSDDDK......KDDDDSSK.......",
        ".....KSSDDDK........KDDDSSK.......",
        ".....KSSDDK..........KDDSSK.......",
        ".....KSSDDK..........KDDSSK.......",
        "....KSSDDK............KDDSSK......",
        "....KSSSK..............KSSSK......",
        "....KKKKK..............KKKKK......",
        "..................................",
        "..................................",
        "..................................",
    ),
    "hallucination_phantom": (
        "...........QQQQQQQQQ..............",
        "........QQQPPPPPPPPPQ.............",
        "......QQPPUUUUPPPPPPPPQ...........",
        ".....QPPPUUPPPPPPPPPPPPQ..........",
        "....QPPPPQQQQQQPPPPQQQPPQ.........",
        "...QPPPPQRRRRWWQPPQWWQPPPQ........",
        "...QPPPPQRRRRKKQPPQKKQPPPQ........",
        "..QPPPPPPQQQQQQPPPPQQQPPPPQ.......",
        "..QPPVVPPPPPPPPPPPPPPPVVPPPQ......",
        ".QPPVQ.QPPVVWWWWWWWWVVPPPPPPQ.....",
        "QHHQQ..QPPVVVVWWWWVVVPPVVPPPPQ....",
        ".QQ.....QPPVVVVVVVVVPPVVVVPPPQ....",
        "........QPPVVVVVVVVPPPVVVVPPPQ....",
        "........QPPPVVVVVVVPPPPVVVPPQ.....",
        "........QPPPVVVVVVVPPPPVVPPQ......",
        ".......QPPPQPPVVVVPPQQPPPPPPQ.....",
        "......QPPPQ.QPVVVPQ..QPPQQPPPQ....",
        "......QPPQ...QPVPQ....QQ..QPPQ....",
        ".....QPPQ.....QPVQ.........QPQ....",
        ".....QPQ.......QQ...........Q.....",
        "......Q...........................",
        "..................................",
        "..................................",
        "..................................",
        "..................................",
        "..................................",
    ),
    "legacy_monolith": (
        ".......KK..KKKKKK..KK.............",
        "......KDDKKDDDDDDKKDDK............",
        ".....KDDSSDDDDDDDDSSDDK...........",
        ".....KDDDDAAAADDDDDDDDK...........",
        ".....KDDDDYYYYDDDDDDDDK...........",
        "....KDDKKKRRRRRRKKKDDDDK..........",
        "...KDDDKRRWWAAWWRRKDDDDDK.........",
        "...KDDDKRRWKKKKWRRKDDDDDK.........",
        "....KDDKKKRRRRRRKKKDDDDK..........",
        ".....KDDDDGGDDDDGGDDDDK...........",
        ".....KDDDDLLGGGGLLDDDDK...........",
        ".....KDDDDGGDDDDGGDDDDK...........",
        ".....KDDDDDDDDDDDDDDDDK...........",
        ".....KDDSSSSSSSSSSSSDDK...........",
        "....KDDSSSDDDDDDDDSSSDDK..........",
        "....KDDSSSDDDDDDDDSSSDDK..........",
        "....KDDSSK.KDDDDK..KSSDK..........",
        "....KDDSSK.KDDDDK..KSSDK..........",
        "....KDDSSK.KDDDDK..KSSDK..........",
        "....KDDSSK.KDDDDK..KSSDK..........",
        "....KKKKKK.KKKKKK..KKKKK..........",
        "..................................",
        "..................................",
        "..................................",
        "..................................",
        "..................................",
    ),
}

# 10x10 Achievement Badge Sprites (rendered at 2px inside Pokedex slots = 20x20)
QUEST_SPRITES: dict[str, tuple[str, ...]] = {
    "genesis_commit": (
        "....KK....",
        "...KGGK...",
        "..KGGWGK..",
        "...KGGK...",
        "....KK....",
        "..KGGGGK..",
        "...KGGK...",
        "..KOOOOOK.",
        ".KOOOOOOOK",
        "..KKKKKKK.",
    ),
    "shipwright": (
        "....KK....",
        "...KWWK...",
        "..KWWWWK..",
        "..KWWWWK..",
        "....KK....",
        "KOOOOOOOOK",
        ".KOOOOOOK.",
        ".KODDDDOK.",
        "..KKKKKK..",
        ".KBBBBBBK.",
    ),
    "doc_architect": (
        "..KKKKKK..",
        ".KWWWWWWK.",
        ".KWBBBBWK.",
        ".KWWWWWWK.",
        ".KWSSSWWK.",
        ".KWWWWWWK.",
        ".KWSSSWWK.",
        ".KWWWWWWK.",
        "..KKKKKK..",
        "..........",
    ),
    "ci_guardian": (
        ".KKKKKKKK.",
        "KBBBBBBBBK",
        "KBBGGGGGBK",
        "KBBGGGGGBK",
        "KBGGWGGGBK",
        "KBBGGGGGBK",
        ".KBBBBBBK.",
        "..KBBBBK..",
        "...KBBK...",
        "....KK....",
    ),
    "polyglot_stack": (
        "....KK....",
        "...KBBK...",
        "..KBPBPK..",
        ".KBPWWPPK.",
        "KBPPWWPPYK",
        ".KPPGGPYK.",
        "..KPGPYK..",
        "...KGYK...",
        "....KK....",
        "..........",
    ),
    "club_500": (
        "....KK....",
        "...KRRK...",
        "..KRYYRK..",
        ".KRYWWYRK.",
        ".KRYYYYRK.",
        ".KRRRRRRK.",
        "..KMMMMK..",
        "...KMMK...",
        "....KK....",
        "..........",
    ),
    "week_sprint": (
        ".....KKK..",
        "....KYYK..",
        "...KYYK...",
        "..KYYYK...",
        ".KYYYYYYK.",
        "...KKYYK..",
        "...KYYK...",
        "..KYYK....",
        "..KKK.....",
        "..........",
    ),
    "first_merge": (
        ".KK....KK.",
        "KYYK..KYYK",
        ".KKK..KKK.",
        "..KYYYYK..",
        "...KYYK...",
        "...KYYK...",
        "...KYYK...",
        "..KYYYYK..",
        "...KKKK...",
        "..........",
    ),
    "builder_1k": (
        ".KKKKKKKK.",
        "KYYYYYYYYK",
        ".KKYYYYKK.",
        "...KYYK...",
        "..KSSSSK..",
        ".KSSSSSSK.",
        "KSSSSSSSSK",
        ".KKKKKKKK.",
        "..........",
        "..........",
    ),
    "fortnight_streak": (
        "......KK..",
        "....KKRRK.",
        "...KRRYYK.",
        "..KRYYYYK.",
        ".KRRYYKK..",
        ".KRRK.....",
        ".KRK......",
        "KKK.......",
        "..........",
        "..........",
    ),
    "os_ally": (
        ".KKKKKKKK.",
        ".KPPPPPPK.",
        ".KPWWWWPK.",
        ".KPWGGWPK.",
        ".KPPPPPPK.",
        ".KPK..KPK.",
        ".KPK......",
        ".KKK......",
        "..........",
        "..........",
    ),
    "community_signal": (
        "....KK....",
        "...KYYK...",
        "KKKYYYYKKK",
        "KYYYYYYYYK",
        ".KYYWWYYK.",
        "..KYYYYK..",
        ".KYYKKYYK.",
        "KKK....KKK",
        "..........",
        "..........",
    ),
}


def sprite_bounds(grid: tuple[str, ...], *, scale: int = 2) -> tuple[int, int]:
    """Return actual rendered (width, height) of non-empty pixel rows."""
    non_empty_rows = [idx for idx, r in enumerate(grid) if any(ch != "." and ch in SPRITE_PALETTE for ch in r)]
    if not non_empty_rows:
        return 0, 0
    max_col = max((len(r) for r in grid), default=0)
    return max_col * scale, (max(non_empty_rows) + 1) * scale


def compile_pixel_grid(
    grid: tuple[str, ...],
    *,
    scale: int = 2,
    ox: int = 0,
    oy: int = 0,
    locked_color: str | None = None,
) -> list[PixelRect]:
    """Compile ASCII pixel grid into RLE-merged PixelRect rectangles."""
    rects: list[PixelRect] = []
    for row_idx, row in enumerate(grid):
        col = 0
        width = len(row)
        while col < width:
            ch = row[col]
            if ch == "." or ch not in SPRITE_PALETTE:
                col += 1
                continue
            run_end = col + 1
            if locked_color is not None:
                while run_end < width and row[run_end] != "." and row[run_end] in SPRITE_PALETTE:
                    run_end += 1
                fill = locked_color
            else:
                while run_end < width and row[run_end] == ch:
                    run_end += 1
                fill = SPRITE_PALETTE[ch]
            rects.append(
                PixelRect(
                    x=ox + col * scale,
                    y=oy + row_idx * scale,
                    w=(run_end - col) * scale,
                    h=scale,
                    fill=fill,
                )
            )
            col = run_end
    return rects
