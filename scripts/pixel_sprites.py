"""Pure-SVG integer pixel-art sprite compiler with horizontal run-length merging."""

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
    "K": "#141824",  # dark ink outline
    "W": "#F8FAFC",  # crisp highlight white
    "S": "#94A3B8",  # steel / slate
    "D": "#475569",  # dark steel / shadow
    "B": "#38BDF8",  # hero cyan / visor
    "I": "#1D4ED8",  # deep cobalt armor/cloak
    "N": "#1E293B",  # dark cloak body
    "F": "#FDBA74",  # warm skin tone
    "G": "#34D399",  # emerald / green
    "E": "#059669",  # deep emerald
    "Y": "#FBBF24",  # gold / amber
    "O": "#D97706",  # deep gold / wood
    "R": "#F43F5E",  # crimson / fire
    "M": "#9F1239",  # dark crimson
    "P": "#A78BFA",  # arcane purple
    "V": "#6D28D9",  # deep violet
    "C": "#FFFFFF",  # crisp cloud white
}

# 6x10 Wall Torch (scenery)
WALL_TORCH: tuple[str, ...] = (
    "..YY..",
    ".YRRY.",
    ".RYYR.",
    "..RR..",
    ".KKKK.",
    ".KDDK.",
    "..KK..",
    "..KK..",
    "..KK..",
    "......",
)

# 8x8 Crescent Moon (dark sky) & Sun / Cloud (light sky)
PIXEL_MOON: tuple[str, ...] = (
    "..YYYY..",
    ".YYY....",
    "YYY.....",
    "YY......",
    "YY......",
    "YYY.....",
    ".YYY....",
    "..YYYY..",
)

PIXEL_SUN: tuple[str, ...] = (
    "...YY...",
    ".Y.YY.Y.",
    "..YYYY..",
    "YYYYYYYY",
    "YYYYYYYY",
    "..YYYY..",
    ".Y.YY.Y.",
    "...YY...",
)

PIXEL_CLOUD: tuple[str, ...] = (
    "....CCCC......",
    "..CCCCCCCC....",
    ".CCCCCCCCCC...",
    "CCCCCCCCCCCCCC",
    ".SSSSSSSSSSSS.",
)

# 8x8 Cozy Coding Desk Mug
COFFEE_MUG: tuple[str, ...] = (
    "........",
    "........",
    ".WWWWWW.",
    ".WOOOOOW",
    ".WWWWWWW",
    ".WWWWWW.",
    ".WSSSSW.",
    ".KKKKKK.",
)

# 8x8 Energy Clash Spark (high-contrast on both light & dark arenas)
SWORD_CLASH: tuple[str, ...] = (
    "...RR...",
    ".R.YY.R.",
    "..RYYR..",
    "RYYOOYYR",
    "..RYYR..",
    ".R.YY.R.",
    "...RR...",
    "........",
)

# 16x16 Hooded Systems Architect holding a cyan terminal blade
HERO_ARCHITECT: tuple[str, ...] = (
    ".....KKKKKK.....",
    "....KIIIIIIK....",
    "...KIIIIIIIIK...",
    "...KIKKKKKKIK...",
    "...KIKBBBBKIK...",
    "...KIKKKKKKIK...",
    "....KKFFFFKK..B.",
    "...KNNNNNNNK..BB",
    "..KNNIIIIINNK.BW",
    "..KNKIIIIINKNBW.",
    "..KNKIIIIINKKY..",
    "..KKNIIIIINKK...",
    "...KNNNNNNNK....",
    "...KNNK.KNNK....",
    "...KKK...KKK....",
    "................",
)

# 10x10 Cute Terminal Spark Companion
COMPANION_SPARK: tuple[str, ...] = (
    "...KKKK...",
    "..KGGGGK..",
    ".KGGGGGGK.",
    "KGGWGGWGGK",
    "KGGKGGKGGK",
    "KGGGGGGGGK",
    "KGGEEEEGGK",
    ".KKEEEEKK.",
    "..KKKKKK..",
    "..........",
)

# 16x16 Boss Sprites
BOSS_SPRITES: dict[str, tuple[str, ...]] = {
    "nullpointer_wyrm": (
        "..KK........KK..",
        ".KRRK......KRRK.",
        ".KRYRK....KRYRK.",
        "..KRRKKKKKKRRK..",
        "..KRRRRRRRRRRK..",
        ".KRRRRRYYRRRRRK.",
        ".KRRKWWKKWWKRRK.",
        ".KRRRRRRRRRRRRK.",
        "..KRRMMMMMMRRK..",
        "...KMMMMMMMMK...",
        "..KMRRRRRRRRMK..",
        ".KMRRYYRRYYRRMK.",
        ".KMRRRRRRRRRRMK.",
        "..KKMRRKKRRMKK..",
        "...KKK....KKK...",
        "................",
    ),
    "merge_golem": (
        "....KKKKKKKK....",
        "...KSSSSSSSSK...",
        "..KSSDDDDDDSSK..",
        "..KSDYYYYYYDSK..",
        "..KSDYKWWKYDSK..",
        "..KSDDDDDDDDSK..",
        ".KKSSDDDDDDSSKK.",
        "KSSSDDDDDDDDSSSK",
        "KSDDSSYYYYSSDDKK",
        "KSDDSSSSSSSSDDKK",
        "KKDDSSDDDDSSDDKK",
        ".KK.KSDDDDSK.KK.",
        "....KSDKKDSK....",
        "...KSSK..KSSK...",
        "...KKK....KKK...",
        "................",
    ),
    "hallucination_phantom": (
        ".....KKKKKK.....",
        "...KKPPPPPPKK...",
        "..KPPPVVVVPPPK..",
        ".KPPVPPPPPPVPPK.",
        ".KPVPKWWKKWKVPK.",
        ".KPVPKBBKKBKVPK.",
        ".KPPPPPPPPPPPPK.",
        ".KPPVVPPPPVVPPK.",
        "..KPVVVVVVVVPK..",
        "..KPPVPPPPVPPK..",
        ".KPPK.KPPK.KPPK.",
        ".KPK..KPPK..KPK.",
        "..K...KVK....K..",
        ".......K........",
        "................",
        "................",
    ),
    "legacy_monolith": (
        ".KK.KK.KK.KK.KK.",
        ".KKKKKKKKKKKKKK.",
        ".KDDDDDDDDDDDDK.",
        ".KDDYDDDDDDYDDK.",
        ".KDDDDDDDDDDDDK.",
        ".KDDKRRRRRRKDDK.",
        ".KDDKRWWWWKRDDK.",
        ".KDDKRWKKWRKDDK.",
        ".KDDKRRRRRRKDDK.",
        ".KDDDDDDDDDDDDK.",
        ".KDDSSSSSSSSDDK.",
        ".KDDSSSSSSSSDDK.",
        ".KDDSSKKKKSSDDK.",
        ".KDDSSK..KSSDDK.",
        ".KKKKKKKKKKKKKK.",
        "................",
    ),
}

# 10x10 Unique Achievement Pixel Badge Sprites (1 per quest key)
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


def compile_pixel_grid(
    grid: tuple[str, ...],
    *,
    scale: int = 3,
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
